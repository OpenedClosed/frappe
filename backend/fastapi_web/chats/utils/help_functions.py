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
from fastapi import Request, WebSocket
from pymongo import DESCENDING
from telegram_bot.infra import settings as bot_settings

from chats.db.mongo.enums import ChatSource, ChatStatus, SenderRole
from chats.db.mongo.schemas import (ChatMessage, ChatReadInfo, ChatSession,
                                    Client, MasterClient)
from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from infra import settings
from knowledge.admin import BotSettingsAdmin
from knowledge.db.mongo.enums import (AIModelEnum, BotColorEnum,
                                      CommunicationStyleEnum,
                                      PersonalityTraitsEnum)
from knowledge.db.mongo.mapping import (COMMUNICATION_STYLE_DETAILS,
                                        FUNCTIONALITY_DETAILS,
                                        PERSONALITY_TRAITS_DETAILS)
from knowledge.db.mongo.schemas import BotSettings
from knowledge.utils.help_functions import pick_model_and_client

# ==============================
# БЛОК: Генерация идентификаторов
# ==============================


def short_uuid_b64() -> str:
    """Возвращает UUID4, закодированный в URL‑безопасный base64 без знаков «=»."""
    uid = uuid.uuid4()
    return base64.urlsafe_b64encode(uid.bytes).rstrip(b"=").decode()


def generate_short_id() -> str:
    """Генерирует короткий уникальный ID."""
    return short_uuid_b64()


def generate_chat_id() -> str:
    """Создаёт уникальный chat_id."""
    return f"chat-{generate_short_id()}"

# ==============================
# БЛОК: Работа с client_id
# ==============================


async def generate_client_id(
    source: Union[Request, WebSocket],
    chat_source: ChatSource = ChatSource.INTERNAL,
    external_id: Optional[str] = None,
) -> str:
    """Создаёт client_id, учитывая источник и external_id."""
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
        hashlib.sha256(hash_input.encode()).digest()).decode()[:12]

    return f"{chat_source_value.upper()}_{short_hash}"


async def get_client_id(websocket: WebSocket, chat_id: str,
                        is_superuser: bool) -> str:
    """Возвращает client_id для пользователя чата."""
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        raise ValueError("Chat session not found")

    chat_session = ChatSession(**chat_data)

    if not is_superuser:
        return await generate_client_id(websocket)

    if not chat_session.client:
        return ""

    master = await get_master_client_by_id(chat_session.client.client_id)
    if master:
        return master.external_id or master.client_id

    return chat_session.client.client_id

# ==============================
# БЛОК: Работа с MasterClient
# ==============================


async def get_master_client_by_id(client_id: str) -> Optional[MasterClient]:
    """Возвращает MasterClient по client_id."""
    doc = await mongo_db.clients.find_one({"client_id": client_id})
    return MasterClient(**doc) if doc else None


def determine_language(accept_language: str) -> str:
    """Определяет язык из заголовка Accept-Language."""
    user_language = accept_language.split(",")[0].split("-")[0]
    return user_language if user_language in settings.SUPPORTED_LANGUAGES else "en"


async def get_or_create_master_client(
    source: ChatSource,
    external_id: str,
    internal_client_id: str,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> MasterClient:
    """Возвращает существующего или создаёт нового MasterClient."""
    col = mongo_db.clients

    is_internal = source == ChatSource.INTERNAL
    is_anonymous = not external_id or external_id == "anonymous"

    if is_internal and is_anonymous:
        doc = await col.find_one({"client_id": internal_client_id})
    else:
        doc = await col.find_one({"source": source.value, "external_id": external_id})

    if doc:
        update_fields: Dict[str, Any] = {}
        if name and name != doc.get("name"):
            update_fields["name"] = name
        if avatar_url and avatar_url != doc.get("avatar_url"):
            update_fields["avatar_url"] = avatar_url
        if metadata:
            lang = metadata.get("user_language")
            if lang and lang != doc.get("metadata", {}).get("user_language"):
                update_fields["metadata.user_language"] = lang
        if update_fields:
            await col.update_one({"_id": doc["_id"]}, {"$set": update_fields})
            doc = await col.find_one({"_id": doc["_id"]})
        doc.pop("id", None)
        return MasterClient(**doc)

    safe_meta: Dict[str, Any] = {}
    for key in ("locale", "ig_username", "user_language"):
        if metadata and key in metadata:
            safe_meta[key] = metadata[key]

    save_external_id = external_id if external_id and external_id != "anonymous" else "anonymous"

    client = MasterClient(
        client_id=internal_client_id,
        source=source,
        external_id=save_external_id,
        name=name,
        avatar_url=avatar_url,
        metadata=safe_meta,
        created_at=datetime.utcnow(),
    )

    await col.insert_one(client.dict(exclude={"id"}))
    return client

# ==============================
# БЛОК: Работа с сообщениями
# ==============================


def find_last_bot_message(chat_session: ChatSession) -> Optional[ChatMessage]:
    """Возвращает последнее сообщение бота или консультанта."""
    return next(
        (
            msg
            for msg in reversed(chat_session.messages)
            if msg.sender_role in {SenderRole.AI, SenderRole.CONSULTANT}
        ),
        None,
    )

# ==============================
# БЛОК: Уведомление админ‑бота
# ==============================


async def send_message_to_bot(
        chat_id: str, chat_session: Dict[str, Any]) -> None:
    """Отправляет информацию о чате в админ‑бот."""
    if settings.HOST == "localhost":
        return

    bot_webhook_url = "http://bot:9999/webhook/send_message"
    admin_chat_url = (
        f"https://{settings.HOST}/admin/chats/chat_sessions/{chat_id}?isForm=false"
    )

    def dt_iso(value: Any) -> str:
        return value.isoformat() if isinstance(value, datetime) else str(value)

    message_text = (
        "\n".join(
            [
                "🚨 <b>Chat Alert</b> 🚨",
                "",
                f"<b>Chat ID</b>: {chat_session['chat_id']}",
                f"<b>Client ID</b>: {chat_session['client']['client_id']}",
                f"<b>Created At</b>: {_dt_iso(chat_session['created_at'])}",
                f"<b>Last Activity</b>: {_dt_iso(chat_session['last_activity'])}",
                f"<b>Manual Mode</b>: {'Enabled' if chat_session['manual_mode'] else 'Disabled'}",
                f"<b>Messages Count</b>: {len(chat_session['messages'])}",
                f"<b>Brief Answers Count</b>: {len(chat_session['brief_answers'])}",
                "",
                f"📎 <a href='{admin_chat_url}'>View Chat in Admin Panel</a>",
            ]
        )
    )

    async with httpx.AsyncClient() as client:
        await client.post(
            bot_webhook_url,
            json={
                "chat_id": bot_settings.ADMIN_CHAT_ID,
                "text": message_text,
                "parse_mode": "HTML",
            },
        )

# ==============================
# БЛОК: Работа с чатами клиента
# ==============================


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
    """Унифицированная сериализация данных активного чата в API-ответ."""
    return {
        "message": "Chat session is active.",
        "chat_id": chat_data["chat_id"],
        "client_id": chat_data["client"]["client_id"],
        "created_at": chat_data["created_at"],
        "last_activity": chat_data["last_activity"],
        "remaining_time": ttl,
        "status": ChatSession(**chat_data).compute_status(ttl).value,
    }


# ==============================
# БЛОК: Создание / восстановление сессии
# ==============================

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

    if not client_external_id:
        client_external_id = "anonymous"
    client_id = await generate_client_id(
        request,
        chat_source=chat_source,
        external_id=client_external_id
    )

    master_client = await get_or_create_master_client(
        source=chat_source,
        external_id=client_external_id,
        internal_client_id=client_id,
        name=metadata.get("name"),
        avatar_url=metadata.get("avatar_url"),
        metadata=metadata
    )

    client_id = master_client.client_id

    active_chats = await get_active_chats_for_client(client_id)

    if mode != "new" and active_chats:
        chat_data, ttl = active_chats[0]
        return await serialize_active_chat(chat_data, ttl)

    if mode == "new":
        for chat_data, _ in active_chats:
            await mongo_db.chats.update_one(
                {"chat_id": chat_data["chat_id"]},
                {
                    "$set": {
                        "closed_by_request": True,
                        "last_activity": datetime.utcnow()
                    }
                }
            )

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

# ==============================
# БЛОК: Read-state
# ==============================


async def update_read_state_for_client(
    chat_id: str,
    client_id: str,
    user_id: Optional[str],
    last_read_msg: str
) -> bool:
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


# ==============================
# БЛОК: Контекст для ИИ-помощника
# ==============================

locale.setlocale(locale.LC_TIME, "C")


# ==============================
# БЛОК: Форматирование истории
# ==============================

def format_chat_history_from_models(chat_history: List[ChatMessage]) -> str:
    """Форматирует историю сообщений для промпта."""
    return "\n".join(
        f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}] "
        f"[{msg.sender_role.name}] {msg.message}"
        for msg in chat_history
    )


def get_current_datetime() -> str:
    """Возвращает текущее время в виде 'Monday, 08-02-2025 14:30:00 UTC'."""
    now = datetime.now(timezone.utc)
    return now.strftime(
        "%A, %d-%m-%Y %H:%M:%S UTC%z").replace("UTC+0000", "UTC")


# ==============================
# БЛОК: Погода
# ==============================

async def fetch_weather(
        params: Dict[str, Any], redis_key: str) -> Dict[str, Any]:
    """Базовый запрос в OpenWeather с кэшированием."""
    cached = await redis_db.get(redis_key)
    if cached:
        return json.loads(cached)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://api.openweathermap.org/data/2.5/forecast", params=params)
            if resp.status_code != 200:
                return {"error": "Weather is not available"}
            data = resp.json()
            forecast = parse_weather_data(data)
            await redis_db.set(
                redis_key,
                json.dumps(forecast),
                ex=int(settings.WEATHER_CACHE_LIFETIME.total_seconds())
            )
            return forecast
        except Exception as e:
            return {"error": f"Weather fetching error: {e}"}


async def get_weather_for_region(region_name: str) -> Dict[str, Any]:
    """Возвращает прогноз погоды по названию региона."""
    key = f"weather:{region_name.lower()}"
    params = {
        "q": region_name,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }
    return await fetch_weather(params, key)


async def get_coordinates(address: str) -> Dict[str, float]:
    """Возвращает координаты для адреса."""
    params = {"q": address, "limit": 1, "appid": settings.WEATHER_API_KEY}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://api.openweathermap.org/geo/1.0/direct", params=params)
            if resp.status_code != 200 or not resp.json():
                return {}
            data = resp.json()[0]
            return {"lat": data["lat"], "lon": data["lon"]}
        except Exception as e:
            return {"error": f"Coordinates error: {e}"}


async def get_weather_for_location(lat: float, lon: float) -> Dict[str, Any]:
    """Возвращает прогноз погоды по координатам."""
    key = f"weather:{lat},{lon}"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }
    return await fetch_weather(params, key)


async def get_weather_by_address(address: str) -> Dict[str, Any]:
    """Возвращает прогноз погоды по адресу."""
    coords = await get_coordinates(address)
    if not coords:
        return {"error": "Failed to get coordinates"}
    return await get_weather_for_location(coords["lat"], coords["lon"])


def parse_weather_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Парсит прогноз погоды и группирует по датам."""
    forecast: Dict[str, Any] = {}
    for entry in data["list"]:
        date_key = entry["dt_txt"].split(" ")[0]
        temp = entry["main"]["temp"]
        desc = entry["weather"][0]["description"].capitalize()
        day = forecast.setdefault(
            date_key, {"temp_min": temp, "temp_max": temp, "description": desc}
        )
        day["temp_min"] = min(day["temp_min"], temp)
        day["temp_max"] = max(day["temp_max"], temp)
    return {"forecast": forecast}


# ==============================
# БЛОК: Контекст бота
# ==============================

async def get_bot_context() -> Dict[str, Any]:
    """Загружает настройки бота или берёт значения по умолчанию."""
    data = await mongo_db.bot_settings.find_one({}, sort=[("_id", DESCENDING)])
    bot_settings = BotSettings(**data) if data else BotSettings(
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
        greeting={
            "en": "Hello! How can I assist you?",
            "pl": "Cześć! W czym mogę pomóc?",
            "uk": "Вітаю! Чим я можу допомогти?",
            "ru": "Здравствуйте! Чем могу помочь?",
            "ka": "გამარჯობა! რით შემ 가능합니다?"
        },
        error_message={
            "en": "Please wait for a consultant.",
            "pl": "Proszę poczekać na konsultanta.",
            "uk": "Будь ласка, зачекайте на консультанта.",
            "ru": "Пожалуйста, подождите, консультант скоро ответит.",
            "ka": "გთხოვთ, დაელოდოთ კონსულტანტს."
        },
        farewell_message={
            "en": "Goodbye! Feel free to ask anything else.",
            "pl": "Do widzenia! Jeśli masz pytania, śmiało pytaj.",
            "uk": "До побачення! Звертайтесь, якщо виникнуть питання.",
            "ru": "До свидания! Если вам что-то понадобится, обращайтесь.",
            "ka": "ნახვამდის! თავისუფლად შეგიძლიათ კიდევ რაღაც მკითხოთ."
        },
        fallback_ai_error_message={
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
    """Формирует контекст бота из настроек."""
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
        ),
    }
    bot_config["prompt_text"] = generate_prompt_text(settings, admin_model)
    return bot_config


# ==============================
# БЛОК: Генерация промпта
# ==============================

def generate_prompt_text(
    settings: BotSettings,
    admin_model: BotSettingsAdmin
) -> str:
    """Создаёт текст промпта на основе настроек."""
    excluded = {"greeting", "error_message", "farewell_message", "ai_model",
                "personality_traits", "created_at", "avatar"}

    all_fields = set(admin_model.detail_fields) | set(admin_model.list_display)
    lines = ["You are AI Assistant. REMEMBER!:",
             "SYSTEM PROMPT:", "=" * 50]

    for field in all_fields:
        if field in excluded:
            continue
        field_title = admin_model.field_titles.get(field, {}).get("en", field)
        raw_value = getattr(settings, field, None)
        if not raw_value:
            continue
        processed = extract_value(raw_value)
        formatted = format_value(field, processed)
        if field == "employee_name":
            field_title = "Your (Bot) name (Not user name!!! Don`t to be confused with the username of the user being conversating)"
        lines += [f"{field_title.upper()}: {formatted}", "-" * 10]

    lines += ["IMPORTANT: FOLLOW ALL RULES STRICTLY!", "=" * 50]
    return "\n".join(lines)


def extract_value(value: Any) -> Any:
    """Преобразует значение для промпта."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            value = parsed.get("en", value)
        except (json.JSONDecodeError, TypeError):
            pass
        if value in COMMUNICATION_STYLE_DETAILS:
            return f"\n{value}:\n{COMMUNICATION_STYLE_DETAILS[value]}"
        if value in FUNCTIONALITY_DETAILS:
            return f"\n{value}:\n{FUNCTIONALITY_DETAILS[value]}"
        return value

    if isinstance(value, dict):
        return value.get("en", str(value))

    if isinstance(value, list):
        return [extract_value(item) for item in value]

    return value


def format_value(field_name: str, value: Any) -> str:
    """Форматирует значение для промпта."""
    if isinstance(value, list):
        return ", ".join(str(item.value if hasattr(
            item, "value") else item) for item in value)
    if hasattr(value, "value"):
        return value.value
    return str(value)


# ==============================
# БЛОК: Вспомогательный текст
# ==============================

def split_text_into_chunks(text: str, max_length: int = 998) -> List[str]:
    """Делит текст на части по предложениям, не обрывая числовые списки."""
    pattern = re.compile(
        r"(?<!\d)(.*?[.!?…:;]+[)\]\"»”’…\s\w]*)(?=\n|\s|$)",
        re.VERBOSE | re.DOTALL,
    )
    sentences = pattern.findall(text) or [text]

    chunks, chunk = [], ""
    for sentence in sentences:
        if len(chunk) + len(sentence) <= max_length:
            chunk += sentence
        else:
            if chunk.strip():
                chunks.append(chunk.rstrip())
            chunk = sentence
    if chunk.strip():
        chunks.append(chunk.rstrip())
    return chunks


def clean_markdown(text: str) -> str:
    """Удаляет markdown-форматирование, оставляя чистый текст."""
    if not text:
        return ""

    text = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r"\1", text)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*\*([^*]+)\*\*\*", r"\1", text)
    text = re.sub(r"___([^_]+)___", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"~([^~]+)~", r"\1", text)
    text = re.sub(r"^\s*[-*+•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

# ==============================
# БЛОК: Обработка сообщения пользователя
# ==============================


def extract_json_from_response(resp: dict) -> dict[str, Any]:
    """Извлекает первый JSON-блок из ответа модели."""
    try:
        text = resp["candidates"][0]["content"]["parts"][0]["text"]
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(match.group(0)) if match else {}
    except Exception:
        return {}


async def chat_generate_any(
    model_name: str,
    messages: list[dict],
    temperature: float = 0.1,
    system_instruction: str | None = None
) -> dict:
    """Единый вызов генерации текста для OpenAI и Gemini."""
    client, real_model = pick_model_and_client(model_name)

    if real_model.startswith("gpt"):
        response = await client.chat.completions.create(
            model=real_model,
            messages=messages,
            temperature=temperature
        )
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": response.choices[0].message.content.strip()
                    }]
                }
            }]
        }

    elif real_model.startswith("gemini"):
        response = await client.chat_generate(
            model=real_model,
            messages=messages,
            temperature=temperature,
            system_instruction=system_instruction
        )
        return response

    raise ValueError(f"Unsupported model: {real_model}")
