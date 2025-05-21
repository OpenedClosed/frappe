"""Вспомогательные функции приложения Чаты."""
import base64
import hashlib
import json
import locale
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from chats.db.mongo.enums import ChatSource, ChatStatus, SenderRole
from chats.db.mongo.schemas import (ChatMessage, ChatReadInfo, ChatSession,
                                    Client, MasterClient)
from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from fastapi import HTTPException, Request, WebSocket
from infra import settings
from knowledge.admin import BotSettingsAdmin
from knowledge.db.mongo.enums import (AIModelEnum, BotColorEnum,
                                      CommunicationStyleEnum,
                                      PersonalityTraitsEnum)
from knowledge.db.mongo.mapping import (COMMUNICATION_STYLE_DETAILS,
                                        FUNCTIONALITY_DETAILS,
                                        PERSONALITY_TRAITS_DETAILS)
from knowledge.db.mongo.schemas import BotSettings
from pymongo import DESCENDING
from telegram_bot.infra import settings as bot_settings

# ===== Основные функции для работы с сессией чата =====


def generate_short_id() -> str:
    """Генерирует короткий уникальный ID на основе UUID4 и base64."""
    uid = uuid.uuid4()
    return base64.urlsafe_b64encode(uid.bytes).rstrip(b'=').decode()


def generate_chat_id() -> str:
    """Создаёт короткий уникальный chat_id."""
    return f"chat-{generate_short_id()}"


async def generate_client_id(
    source: Union[Request, WebSocket],
    chat_source: ChatSource = ChatSource.INTERNAL,
    external_id: Optional[str] = None
) -> str:
    """Создаёт `client_id`, обрабатывая возможный JSON в `chat_source.value` и `external_id`."""
    chat_source_value = chat_source.value
    try:
        chat_source_dict = json.loads(chat_source_value)
        chat_source_value = chat_source_dict.get("en", chat_source_value)
    except (json.JSONDecodeError, TypeError):
        pass

    if external_id and external_id != "anonymous":
        return f"{chat_source_value}_{external_id}"

    if not isinstance(source, (Request, WebSocket)):
        raise ValueError("Invalid source type. Must be Request or WebSocket.")

    headers = source.headers
    client_ip = headers.get("x-forwarded-for",
                            "").split(",")[0].strip() or source.client.host
    user_agent = headers.get("user-agent", "unknown")

    if "PostmanRuntime" in user_agent:
        user_agent = "unknown"

    hash_input = f"{client_ip}-{user_agent}"
    short_hash = base64.urlsafe_b64encode(
        hashlib.sha256(hash_input.encode()).digest()
    ).decode()[:12]

    return f"{chat_source_value.upper()}_{short_hash}"


async def get_client_id(websocket: WebSocket, chat_id: str, is_superuser: bool) -> str:
    """
    Определяет client_id или external_id, связанный с чатом, в зависимости от типа пользователя.
    Суперпользователь видит внешний ID, если он есть.
    """
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        raise ValueError(f"Chat session with ID {chat_id} not found.")

    chat_session = ChatSession(**chat_data)

    if not is_superuser:
        return await generate_client_id(websocket)

    if not chat_session.client:
        return ""

    master = await get_master_client_by_id(chat_session.client.client_id)
    if master:
        return master.external_id or master.client_id

    return chat_session.client.client_id


async def get_master_client_by_id(client_id: str) -> MasterClient | None:
    """Возвращает карточку клиента по его client_id."""
    doc = await mongo_db.clients.find_one({"client_id": client_id})
    return MasterClient(**doc) if doc else None


def determine_language(accept_language: str) -> str:
    """Определяет язык пользователя из заголовков запроса."""
    user_language = accept_language.split(",")[0].split("-")[0]
    return user_language if user_language in settings.SUPPORTED_LANGUAGES else "en"


def find_last_bot_message(chat_session: ChatSession) -> Optional[ChatMessage]:
    """Возвращает последнее сообщение бота или консультанта."""
    return next(
        (msg for msg in reversed(chat_session.messages)
         if msg.sender_role in {SenderRole.AI, SenderRole.CONSULTANT}),
        None
    )


async def send_message_to_bot(chat_id: str, chat_session: dict) -> None:
    """Отправляет информацию о чате в админский бот."""
    if settings.HOST == "localhost":
        return

    bot_webhook_url = "http://bot:9999/webhook/send_message"
    admin_chat_url = f"https://{settings.HOST}/admin/chats/chat_sessions/{chat_id}?isForm=false"

    created_at = (
        chat_session['created_at'].isoformat()
        if isinstance(chat_session['created_at'], datetime)
        else chat_session['created_at']
    )
    last_activity = (
        chat_session['last_activity'].isoformat()
        if isinstance(chat_session['last_activity'], datetime)
        else chat_session['last_activity']
    )

    message_text = f"""
🚨 <b>Chat Alert</b> 🚨

<b>Chat ID</b>: {chat_session["chat_id"]}
<b>Client ID</b>: {chat_session["client"]["client_id"]}
<b>Created At</b>: {created_at}
<b>Last Activity</b>: {last_activity}
<b>Manual Mode</b>: {"Enabled" if chat_session["manual_mode"] else "Disabled"}
<b>Messages Count</b>: {len(chat_session["messages"])}
<b>Brief Answers Count</b>: {len(chat_session["brief_answers"])}

📎 <a href='{admin_chat_url}'>View Chat in Admin Panel</a>
"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            bot_webhook_url,
            json={
                "chat_id": bot_settings.ADMIN_CHAT_ID,
                "text": message_text,
                "parse_mode": "HTML",
            },
        )
        if response.status_code != 200:
            logging.info(f"Message not sent! Error: {response.text}")


async def get_all_chats_for_client(client_id: str) -> List[dict]:
    """Получает все чаты конкретного клиента из MongoDB."""
    return [chat async for chat in mongo_db.chats.find({"client.client_id": client_id})]


async def get_active_chats_for_client(
        client_id: str) -> List[Tuple[dict, int]]:
    """Возвращает отсортированный список активных чатов клиента (chat_data, ttl)."""
    all_chats = await get_all_chats_for_client(client_id)
    active_chats = []

    for chat in all_chats:
        chat_id = chat["chat_id"]
        redis_key = f"chat:session:{chat_id}"
        ttl = await redis_db.ttl(redis_key)
        if ttl > 0:
            active_chats.append((chat, ttl))

    active_chats.sort(key=lambda x: x[0]["created_at"], reverse=True)
    return active_chats


async def serialize_active_chat(chat_data: dict, ttl: int) -> Dict[str, Any]:
    """
    Унифицированная сериализация данных активного чата в API-ответ.
    """
    return {
        "message": "Chat session is active.",
        "chat_id": chat_data["chat_id"],
        "client_id": chat_data["client"]["client_id"],
        "created_at": chat_data["created_at"],
        "last_activity": chat_data["last_activity"],
        "remaining_time": ttl,
        "status": ChatSession(**chat_data).compute_status(ttl).value,
    }



async def get_or_create_master_client(
    source: ChatSource,
    external_id: str,
    internal_client_id: str,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> MasterClient:
    """Создаёт/возвращает MasterClient, «чистит» metadata."""
    col = mongo_db.clients

    is_internal = source == ChatSource.INTERNAL
    is_anonymous = not external_id or external_id == "anonymous"

    logging.debug("📥 [MasterClient] Входные данные:")
    logging.debug(f"  source: {source}")
    logging.debug(f"  external_id: {external_id!r}")
    logging.debug(f"  internal_client_id: {internal_client_id}")
    logging.debug(f"  name: {name}")
    logging.debug(f"  avatar_url: {avatar_url}")
    logging.debug(f"  metadata: {metadata}")

    client_id = internal_client_id
    logging.debug(f"🔑 [MasterClient] Используем client_id: {client_id}")

    # 🔍 Стратегия поиска
    if is_internal and is_anonymous:
        logging.debug("🔍 [MasterClient] Ищем по client_id (внутренний анонимный клиент)")
        doc = await col.find_one({"client_id": client_id})
    else:
        logging.debug("🔍 [MasterClient] Ищем по source + external_id")
        doc = await col.find_one({"source": source.value, "external_id": external_id})

    if doc:
        logging.info(f"✅ [MasterClient] Найден клиент: client_id={doc.get('client_id')}")
        update_fields: dict[str, Any] = {}
        if name and name != doc.get("name"):
            update_fields["name"] = name
        if avatar_url and avatar_url != doc.get("avatar_url"):
            update_fields["avatar_url"] = avatar_url
        if metadata:
            lang = metadata.get("user_language")
            if lang and lang != doc.get("metadata", {}).get("user_language"):
                update_fields["metadata.user_language"] = lang
        if update_fields:
            logging.info(f"🛠 [MasterClient] Обновляем поля: {update_fields}")
            await col.update_one({"_id": doc["_id"]}, {"$set": update_fields})
            doc = await col.find_one({"_id": doc["_id"]})
        doc.pop("id", None)
        return MasterClient(**doc)

    # ――― Сохраняем только чистые паспортные данные
    safe_meta: dict[str, Any] = {}
    for key in ("locale", "ig_username", "user_language"):
        if metadata and key in metadata:
            safe_meta[key] = metadata[key]

    if not external_id or external_id == "anonymous":
        save_external_id = "anonymous"
    else:
        save_external_id = external_id

    logging.debug(f"📄 [MasterClient] save_external_id: {save_external_id}")

    client = MasterClient(
        client_id=client_id,
        source=source,
        external_id=save_external_id,
        name=name,
        avatar_url=avatar_url,
        metadata=safe_meta,
        created_at=datetime.utcnow()
    )

    logging.info(f"🆕 [MasterClient] Создаём нового клиента: client={client.dict(exclude={'id'})}")
    await col.insert_one(client.dict(exclude={"id"}))
    return client




# async def handle_chat_creation(
#     mode: Optional[str] = None,
#     chat_source: ChatSource = ChatSource.INTERNAL,
#     chat_external_id: Optional[str] = None,
#     client_external_id: Optional[str] = None,
#     company_name: Optional[str] = None,
#     bot_id: Optional[str] = None,
#     metadata: Optional[Dict[str, Any]] = None,
#     request: Optional[Request] = None
# ) -> dict:
#     """Создаёт или получает чат-сессию, используя Redis и MongoDB."""
#     metadata = metadata or {}

#     if chat_source != ChatSource.INTERNAL:
#         master_client = await get_or_create_master_client(
#             source=chat_source,
#             external_id=client_external_id,
#             name=metadata.get("name"),
#             avatar_url=metadata.get("avatar_url"),
#             metadata=metadata
#         )
#         client_id = master_client.client_id
#     else:
#         client_id = await generate_client_id(
#             request, chat_source=chat_source, external_id=client_external_id
#         )


#     active_chats = await get_active_chats_for_client(client_id)

#     if mode != "new" and active_chats:
#         chat_data, ttl = active_chats[0]
#         return await serialize_active_chat(chat_data, ttl)

#     if mode == "new":
#         for chat_data, _ in active_chats:
#             await mongo_db.chats.update_one(
#                 {"chat_id": chat_data["chat_id"]},
#                 {"$set": {"closed_by_request": True, "last_activity": datetime.utcnow()}}
#             )

#     if chat_source != ChatSource.INTERNAL:
#         if chat_data := await mongo_db.chats.find_one({"client.client_id": client_id}):
#             chat_session = ChatSession(**chat_data)
#             await redis_db.set(
#                 f"chat:session:{chat_session.chat_id}",
#                 "1",
#                 ex=int(settings.CHAT_TIMEOUT.total_seconds())
#             )
#             return {
#                 "message": "Chat session restored from MongoDB.",
#                 "chat_id": chat_session.chat_id,
#                 "client_id": client_id,
#                 "status": chat_session.compute_status(settings.CHAT_TIMEOUT.total_seconds()).value,
#             }

#     client = Client(
#         client_id=client_id,
#         source=chat_source
#     )
#     chat_id = generate_chat_id()

#     chat_session = ChatSession(
#         chat_id=chat_id,
#         client=client,
#         bot_id=bot_id,
#         company_name=company_name,
#         last_activity=datetime.utcnow(),
#         external_id=chat_external_id if chat_source != ChatSource.INTERNAL else None
#     )

#     await mongo_db.chats.insert_one(chat_session.dict())
#     await redis_db.set(
#         f"chat:session:{chat_id}",
#         "1",
#         ex=int(settings.CHAT_TIMEOUT.total_seconds())
#     )

#     return {
#         "message": "New chat session created.",
#         "chat_id": chat_id,
#         "client_id": client_id,
#         "status": ChatStatus.IN_PROGRESS.value,
#     }




async def handle_chat_creation(
    mode: Optional[str] = None,
    chat_source: ChatSource = ChatSource.INTERNAL,
    chat_external_id: Optional[str] = None,
    client_external_id: Optional[str] = None,
    company_name: Optional[str] = None,
    bot_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> dict:
    """Создаёт или получает чат-сессию, используя Redis и MongoDB."""
    metadata = metadata or {}

    # 🔐 Генерируем client_id (всегда)
    if not client_external_id:
        client_external_id = "anonymous"
    client_id = await generate_client_id(
        request,
        chat_source=chat_source,
        external_id=client_external_id
    )

    # 🎯 Получаем или создаём MasterClient
    master_client = await get_or_create_master_client(
        source=chat_source,
        external_id=client_external_id,
        internal_client_id=client_id,
        name=metadata.get("name"),
        avatar_url=metadata.get("avatar_url"),
        metadata=metadata
    )

    client_id = master_client.client_id  # гарантированно из БД

    # 🔄 Проверка на активный чат
    active_chats = await get_active_chats_for_client(client_id)

    if mode != "new" and active_chats:
        chat_data, ttl = active_chats[0]
        return await serialize_active_chat(chat_data, ttl)

    if mode == "new":
        for chat_data, _ in active_chats:
            await mongo_db.chats.update_one(
                {"chat_id": chat_data["chat_id"]},
                {"$set": {"closed_by_request": True, "last_activity": datetime.utcnow()}}
            )

    # 🔁 Восстановление для внешних
    if chat_source != ChatSource.INTERNAL:
        if chat_data := await mongo_db.chats.find_one({"client.client_id": client_id}):
            chat_session = ChatSession(**chat_data)
            await redis_db.set(
                f"chat:session:{chat_session.chat_id}",
                "1",
                ex=int(settings.CHAT_TIMEOUT.total_seconds())
            )
            return {
                "message": "Chat session restored from MongoDB.",
                "chat_id": chat_session.chat_id,
                "client_id": client_id,
                "status": chat_session.compute_status(settings.CHAT_TIMEOUT.total_seconds()).value,
            }

    # 🆕 Создание новой сессии
    chat = ChatSession(
        chat_id=generate_chat_id(),
        client=Client(client_id=client_id, source=chat_source),
        bot_id=bot_id,
        company_name=company_name,
        external_id=chat_external_id if chat_source != ChatSource.INTERNAL else client_external_id,
        last_activity=datetime.utcnow()
    )

    await mongo_db.chats.insert_one(chat.dict())
    await redis_db.set(
        f"chat:session:{chat.chat_id}",
        "1",
        ex=int(settings.CHAT_TIMEOUT.total_seconds())
    )

    return {
        "message": "New chat session created.",
        "chat_id": chat.chat_id,
        "client_id": client_id,
        "status": ChatStatus.IN_PROGRESS.value,
    }




async def update_read_state_for_client(
        chat_id: str, client_id: str, user_id: Optional[str], last_read_msg: str) -> bool:
    """Обновляет read_state для клиента в чате, если это необходимо."""
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        return False

    read_state_raw = chat_data.get("read_state", [])
    read_state: List[ChatReadInfo] = [
        ChatReadInfo(**ri) if isinstance(ri, dict) else ri
        for ri in read_state_raw
    ]

    now = datetime.utcnow()
    modified = False

    for ri in read_state:
        if ri.client_id == client_id:
            if ri.last_read_msg != last_read_msg:
                ri.last_read_msg = last_read_msg
                ri.last_read_at = now
                modified = True
            break
    else:
        read_state.append(ChatReadInfo(
            client_id=client_id,
            user_id=user_id,
            last_read_msg=last_read_msg,
            last_read_at=now
        ))
        modified = True

    if modified:
        await mongo_db.chats.update_one(
            {"chat_id": chat_id},
            {"$set": {"read_state": [ri.model_dump(
                mode="python") for ri in read_state]}}
        )

    return modified


# ===== Контекст для ИИ помощника =====

locale.setlocale(locale.LC_TIME, "C")

def format_chat_history_from_models(chat_history: List[ChatMessage]) -> str:
    return "\n".join(
        f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}] [{msg.sender_role.name}] {msg.message}"
        for msg in chat_history
    )

def get_current_datetime() -> str:
    """Возвращает текущее время в формате 'Monday, 08-02-2025 14:30:00 UTC'."""
    now = datetime.now(timezone.utc)
    return now.strftime(
        "%A, %d-%m-%Y %H:%M:%S UTC%z").replace("UTC+0000", "UTC")


async def get_weather_for_region(region_name: str) -> Dict[str, Any]:
    """Получает прогноз погоды на 5 дней с кэшированием в Redis (английские сообщения)."""
    redis_key = f"weather:{region_name.lower()}"
    cached = await redis_db.get(redis_key)
    if cached:
        return json.loads(cached)

    params = {
        "q": region_name,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://api.openweathermap.org/data/2.5/forecast", params=params)
            if response.status_code != 200:
                return {"error": "Weather is not available"}
            data = response.json()
            forecast = parse_weather_data(data)
            await redis_db.set(
                redis_key,
                json.dumps(forecast),
                ex=int(settings.WEATHER_CACHE_LIFETIME.total_seconds())
            )
            return forecast
        except Exception as e:
            return {"error": f"Weather fetching error: {e}"}


async def get_coordinates(address: str) -> Dict[str, float]:
    """Возвращает координаты (широта и долгота) для заданного адреса."""
    params = {
        "q": address,
        "limit": 1,
        "appid": settings.WEATHER_API_KEY,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://api.openweathermap.org/geo/1.0/direct", params=params)
            if response.status_code != 200 or not response.json():
                return {}
            data = response.json()
            return {"lat": data[0]["lat"], "lon": data[0]["lon"]}
        except Exception as e:
            return {"error": f"Coordinates error: {e}"}


async def get_weather_for_location(lat: float, lon: float) -> Dict[str, Any]:
    """Получает прогноз погоды по координатам с кэшированием (английские сообщения)."""
    redis_key = f"weather:{lat},{lon}"
    cached = await redis_db.get(redis_key)
    if cached:
        return json.loads(cached)

    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://api.openweathermap.org/data/2.5/forecast", params=params)
            if response.status_code != 200:
                return {"error": "Weather is not available"}
            data = response.json()
            forecast = parse_weather_data(data)
            await redis_db.set(
                redis_key,
                json.dumps(forecast),
                ex=int(settings.WEATHER_CACHE_LIFETIME.total_seconds())
            )
            return forecast
        except Exception as e:
            return {"error": f"Weather fetching error: {e}"}


async def get_weather_by_address(address: str) -> Dict[str, Any]:
    """Получает прогноз погоды для адреса (английские сообщения об ошибке)."""
    coords = await get_coordinates(address)
    if not coords:
        return {"error": "Failed to get coordinates"}
    return await get_weather_for_location(coords["lat"], coords["lon"])


def parse_weather_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Парсит прогноз погоды и группирует данные по датам."""
    forecast = {}
    for entry in data["list"]:
        date_str = entry["dt_txt"].split(" ")[0]
        temp = entry["main"]["temp"]
        desc = entry["weather"][0]["description"].capitalize()
        if date_str not in forecast:
            forecast[date_str] = {
                "temp_min": temp,
                "temp_max": temp,
                "description": desc}
        else:
            forecast[date_str]["temp_min"] = min(
                forecast[date_str]["temp_min"], temp)
            forecast[date_str]["temp_max"] = max(
                forecast[date_str]["temp_max"], temp)
    return {"forecast": forecast}


async def get_bot_context() -> Dict[str, Any]:
    """Загружает настройки бота из БД или использует значения по умолчанию."""
    data = await mongo_db.bot_settings.find_one({}, sort=[("_id", DESCENDING)])
    if data:
        bot_settings = BotSettings(**data)
    else:
        bot_settings = BotSettings(
            project_name="Default Project",
            employee_name="Default Employee",
            mention_name=False,
            avatar=None,
            bot_color=BotColorEnum.RED,
            communication_tone=CommunicationStyleEnum.CASUAL,
            personality_traits=PersonalityTraitsEnum.BALANCED,
            additional_instructions="",
            role="Default Role",
            target_action=[],
            core_principles=None,
            special_instructions=[],
            forbidden_topics=[],
            greeting = {
                "en": "Hello! How can I assist you?",
                "pl": "Cześć! W czym mogę pomóc?",
                "uk": "Вітаю! Чим я можу допомогти?",
                "ru": "Здравствуйте! Чем могу помочь?",
                "ka": "გამარჯობა! რით შემიძლია დაგეხმარო?"
            },
            error_message = {
                "en": "Please wait for a consultant.",
                "pl": "Proszę poczekać na konsultanta.",
                "uk": "Будь ласка, зачекайте на консультанта.",
                "ru": "Пожалуйста, подождите, консультант скоро ответит.",
                "ka": "გთხოვთ, დაელოდოთ კონსულტანტს."
            },
            farewell_message = {
                "en": "Goodbye! Feel free to ask anything else.",
                "pl": "Do widzenia! Jeśli masz pytania, śmiało pytaj.",
                "uk": "До побачення! Звертайтесь, якщо виникнуть питання.",
                "ru": "До свидания! Если вам что-то понадобится, обращайтесь.",
                "ka": "ნახვამდის! თავისუფლად შეგიძლიათ კიდევ რაღაც მკითხოთ."
            },
            fallback_ai_error_message = {
                "en": "Unfortunately, I'm having trouble generating a response right now. Please try again later.",
                "pl": "Niestety, mam teraz problem z wygenerowaniem odpowiedzi. Spróbuj ponownie później.",
                "uk": "На жаль, зараз виникла проблема з генерацією відповіді. Спробуйте пізніше.",
                "ru": "К сожалению, я не могу сейчас сгенерировать ответ. Пожалуйста, попробуйте позже.",
                "ka": "სამწუხაროდ, ახლა ვერ ვქმნი პასუხს. გთხოვთ, სცადეთ მოგვიანებით."
            },
            ai_model=AIModelEnum.GPT_4_O,
            created_at=datetime.utcnow()
        )
    return build_bot_settings_context(bot_settings, BotSettingsAdmin(mongo_db))


def build_bot_settings_context(
    settings: BotSettings,
    admin_model: BotSettingsAdmin
) -> Dict[str, Any]:
    """Формирует словарь контекста бота из настроек и админ-модели."""

    bot_config = {
        "ai_model": settings.ai_model.value if settings.ai_model else "gpt-4o",
        "temperature": PERSONALITY_TRAITS_DETAILS.get(settings.personality_traits, 0.1),
        "welcome_message": settings.greeting,
        "redirect_message": settings.error_message,
        "farewell_message": settings.farewell_message,
        "fallback_ai_error_message": settings.fallback_ai_error_message,
        "app_name": settings.project_name,
        "app_description": settings.additional_instructions,
        "forbidden_topics": settings.forbidden_topics,
        "avatar": settings.avatar.url if settings.avatar else None,
        "bot_color": settings.bot_color.value,
        "postprocessing_instruction": settings.postprocessing_instruction or (
            "Do not invent facts. Do not generate placeholder links. "
            "Do not provide addresses, phones, or prices unless clearly present in the snippets or chat history."
        ),
        "language_instruction": settings.language_instruction or (
            "Always respond in the language of the user's latest messages. "
            "If it is unclear, use the language of the recent chat context or interface."
        )
    }

    prompt_text = generate_prompt_text(settings, admin_model)
    bot_config["prompt_text"] = prompt_text

    return bot_config


def generate_prompt_text(settings: BotSettings,
                         admin_model: BotSettingsAdmin) -> str:
    """Создаёт текст промпта на основе настроек бота."""

    excluded_fields = {"greeting", "error_message", "farewell_message", "ai_model",
                       "personality_traits", "created_at", "avatar"}

    all_fields = set(admin_model.detail_fields) | set(admin_model.list_display)
    lines = ["You are AI Assistant. REMEMBER!:"]
    lines += ["SYSTEM PROMPT:"]
    devider = "=" * 50
    lines.append(devider)

    for field_name in all_fields:
        if field_name in excluded_fields:
            continue

        field_title = admin_model.field_titles.get(
            field_name, {}).get("en", field_name)
        raw_value = getattr(settings, field_name, None)
        if not raw_value:
            continue

        processed_value = extract_value(raw_value)
        formatted_value = format_value(field_name, processed_value)
        if field_name == "employee_name":
            field_title = "Your (Bot) name (Not user name!!! Don`t to be confused with the username of the user being conversating)"
        lines += [f"{field_title.upper()}: {formatted_value}", "-" * 10]

    lines += ["IMPORTANT: FOLLOW ALL RULES STRICTLY!", devider]
    return "\n".join(lines)


def extract_value(value):
    """Преобразует значение: парсит JSON, берёт 'en' из словаря или возвращает объект как строку."""

    if isinstance(value, str):
        parsed_value = None
        try:
            parsed_value = json.loads(value)
            parsed_value = parsed_value.get("en", value)
        except (json.JSONDecodeError, TypeError):
            pass
        if value in COMMUNICATION_STYLE_DETAILS:
            value = f"\n{parsed_value}:\n{COMMUNICATION_STYLE_DETAILS[value]}"
            return value
        elif value in FUNCTIONALITY_DETAILS:
            value = f"\n{parsed_value}:\n{FUNCTIONALITY_DETAILS[value]}"
            return value
        return parsed_value if parsed_value else value

    if isinstance(value, dict):
        return value.get("en", str(value))

    if isinstance(value, list):
        return [extract_value(item) for item in value]

    return value


def format_value(field_name: str, value: Any) -> str:
    """Форматирует значение для вывода в промпт."""

    if isinstance(value, list):
        return ", ".join(str(f.value) if hasattr(
            f, "value") else str(f) for f in value)

    if hasattr(value, "value"):
        return value.value

    return str(value)


def split_text_into_chunks(text, max_length=998) -> List[str]:
    """
    Делит текст на чанки, сохраняя переносы строк, кавычки, emoji и т.д.
    Не завершает на числовых точках (1., 2., 3. и т.д.)
    """
    pattern = re.compile(
        r"""
        (?<!\d)                           # Исключаем цифры перед точкой: 1. 2. и т.д.
        (
            .*?                           # Всё, что угодно, не жадно
            [.!?…:;]+                     # Завершающие знаки
            [)\]"»»”’…\s\w]*              # Возможные закрывающие знаки, пробелы, emoji
        )
        (?=\n|\s|$)                       # Должен быть пробел, перенос строки или конец текста
        """,
        re.VERBOSE | re.DOTALL
    )

    sentences = pattern.findall(text)

    # Fallback: если регулярка ничего не нашла
    if not sentences:
        sentences = [text]

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.rstrip())
            current_chunk = sentence

    if current_chunk.strip():
        chunks.append(current_chunk.rstrip())

    return chunks


def clean_markdown(text: str) -> str:
    """
    Превращает markdown-текст в аккуратный читаемый текст:
    - удаляет жирный, курсив, заголовки, код, ссылки, списки;
    - сохраняет только понятный текст без форматирования.
    """
    if not text:
        return ""

    # Ссылки вида [текст](https://...) -> просто текст
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'\1', text)

    # Удаляем заголовки (#, ## и т.п.)
    text = re.sub(r'^\s*#{1,6}\s*', '', text, flags=re.MULTILINE)

    # Блоки кода (```...```)
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Моноширинный (`текст`)
    text = re.sub(r'`([^`]*)`', r'\1', text)

    # Жирный и курсив любой вложенности — три символа (***)
    text = re.sub(r'\*\*\*([^*]+)\*\*\*', r'\1', text)
    text = re.sub(r'___([^_]+)___', r'\1', text)

    # Двойной жирный: **текст** или __текст__
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)

    # Одиночный курсив: *текст* или _текст_
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)

    # Зачёркивание: ~текст~
    text = re.sub(r'~([^~]+)~', r'\1', text)

    # Списки: удаляем символы -, *, +, • в начале строки
    text = re.sub(r'^\s*[-*+•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Удаляем лишние пробелы и пустые строки
    text = re.sub(r'\n{2,}', '\n', text)  # двойные \n -> один
    text = re.sub(r'[ \t]+', ' ', text)   # табы и многопробелы -> один пробел
    text = text.strip()

    return text