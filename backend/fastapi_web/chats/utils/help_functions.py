"""Вспомогательные функции приложения Чаты."""
import hashlib
import json
import locale
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

import httpx
from fastapi import HTTPException, Request, WebSocket
from pymongo import DESCENDING
from telegram_bot.infra import settings as bot_settings

from chats.db.mongo.enums import ChatSource, ChatStatus, SenderRole
from chats.db.mongo.schemas import ChatMessage, ChatSession, Client
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

from .knowledge_base import KNOWLEDGE_BASE

# ===== Основные функции для работы с сессией чата =====


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

    if external_id:
        return f"{chat_source_value}_{external_id}"

    if not isinstance(source, (Request, WebSocket)):
        raise ValueError("Invalid source type. Must be Request or WebSocket.")

    headers = source.headers
    client_ip = headers.get("x-forwarded-for",
                            "").split(",")[0].strip() or source.client.host
    user_agent = headers.get("user-agent", "unknown")

    if "PostmanRuntime" in user_agent:
        user_agent = "unknown"

    return f"{chat_source_value}_{hashlib.sha256(f'{client_ip}-{user_agent}'.encode()).hexdigest()}"


async def get_client_id(websocket: WebSocket, chat_id: str,
                        is_superuser: bool) -> str:
    """Определяет `client_id`, связанный с чатом, в зависимости от типа пользователя."""
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        raise ValueError(f"Chat session with ID {chat_id} not found.")

    chat_session = ChatSession(**chat_data)
    return chat_session.get_client_id() if is_superuser else await generate_client_id(websocket)


def generate_chat_id() -> str:
    """Создаёт уникальный идентификатор чата."""
    return f"chat-{uuid.uuid4()}-{int(datetime.utcnow().timestamp())}"


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
    client_id = await generate_client_id(
        request, chat_source=chat_source, external_id=client_external_id
    ) if request else f"{chat_source.value}_{client_external_id}"

    redis_key = f"chat:{client_id}"

    if mode == "new" and (old_chat_id := await redis_db.get(redis_key)):
        old_chat_id = old_chat_id.decode()
        if chat_data := await mongo_db.chats.find_one({"chat_id": old_chat_id}):
            await mongo_db.chats.update_one(
                {"chat_id": old_chat_id},
                {"$set": {"closed_by_request": True, "last_activity": datetime.utcnow()}}
            )
        await redis_db.delete(redis_key)

    if chat_id_from_redis := await redis_db.get(redis_key):
        chat_id_from_redis = chat_id_from_redis.decode()
        if chat_data := await mongo_db.chats.find_one({"chat_id": chat_id_from_redis}):
            remaining_time = max(0, settings.CHAT_TIMEOUT.total_seconds() -
                                 (datetime.utcnow() - chat_data["last_activity"]).total_seconds())
            return {
                "message": "Chat session is active.",
                "chat_id": chat_data["chat_id"],
                "client_id": client_id,
                "created_at": chat_data["created_at"],
                "last_activity": chat_data["last_activity"],
                "remaining_time": remaining_time,
                "status": ChatSession(**chat_data).compute_status(remaining_time).value,
            }

    if chat_source != ChatSource.INTERNAL and (chat_data := await mongo_db.chats.find_one({"client.client_id": client_id})):
        chat_session = ChatSession(**chat_data)
        await redis_db.set(redis_key, chat_session.chat_id, ex=int(settings.CHAT_TIMEOUT.total_seconds()))

        return {
            "message": "Chat session restored from MongoDB.",
            "chat_id": chat_session.chat_id,
            "client_id": client_id,
            "status": chat_session.compute_status(settings.CHAT_TIMEOUT.total_seconds()).value,
        }

    client = Client(
        client_id=client_id,
        source=chat_source,
        external_id=client_external_id,
        metadata=metadata
    )
    chat_id = generate_chat_id()

    chat_session = ChatSession(
        chat_id=chat_id,
        client=client,
        bot_id=bot_id,
        company_name=company_name,
        last_activity=datetime.utcnow(),
        external_id=chat_external_id if chat_source != ChatSource.INTERNAL else None
    )

    await mongo_db.chats.insert_one(chat_session.dict())
    await redis_db.set(redis_key, chat_id, ex=int(settings.CHAT_TIMEOUT.total_seconds()))

    return {
        "message": "New chat session created.",
        "chat_id": chat_id,
        "client_id": client_id,
        "status": ChatStatus.IN_PROGRESS.value,
    }


async def get_knowledge_base() -> Dict[str, dict]:
    """Получает базу знаний."""
    document = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
    if not document:
        raise HTTPException(404, "Knowledge base not found.")
    document.pop("_id", None)
    return document["knowledge_base"] if document["knowledge_base"] else KNOWLEDGE_BASE


# ===== Контекст для ИИ помощника =====

locale.setlocale(locale.LC_TIME, "C")


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
            greeting={
                "en": "Hello! How can I assist you?",
                "ru": "Здравствуйте! Чем могу помочь?"},
            error_message={
                "en": "Please wait for a consultant.",
                "ru": "Пожалуйста, подождите, консультант скоро ответит."},
            farewell_message={
                "en": "Goodbye! Feel free to ask anything else.",
                "ru": "До свидания! Если вам что-то понадобится, обращайтесь."},
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
        "welcome_message": settings.greeting or {"en": "Hello!", "ru": "Здравствуйте!"},
        "redirect_message": settings.error_message or {"en": "Please wait...", "ru": "Ожидайте..."},
        "farewell_message": settings.farewell_message or {"en": "Goodbye!", "ru": "До свидания!"},
        "app_name": settings.project_name,
        "app_description": settings.additional_instructions,
        "forbidden_topics": settings.forbidden_topics,
        "avatar": settings.avatar.url if settings.avatar else None,
        "bot_color": settings.bot_color.value
    }

    prompt_text = generate_prompt_text(settings, admin_model)
    bot_config["prompt_text"] = prompt_text

    return bot_config


def generate_prompt_text(settings: BotSettings, admin_model: BotSettingsAdmin) -> str:
    """Создаёт текст промпта на основе настроек бота."""
    
    excluded_fields = {"greeting", "error_message", "farewell_message", "ai_model", 
                       "personality_traits", "created_at", "avatar"}
    
    all_fields = set(admin_model.detail_fields) | set(admin_model.list_display)
    lines = ["You are AI Assistant. REMEMBER!:"]
    lines += ["SYSTEM PROMPT:"]
    devider = "="*50
    lines.append(devider)

    for field_name in all_fields:
        if field_name in excluded_fields:
            continue

        field_title = admin_model.field_titles.get(field_name, {}).get("en", field_name)
        raw_value = getattr(settings, field_name, None)
        if not raw_value:
            continue

        processed_value = extract_value(raw_value)
        formatted_value = format_value(field_name, processed_value)
        if field_name == "employee_name":
            field_title = "Your (Bot) name (Not user name!!! Don`t to be confused with the username of the user being conversating)"
        lines += [f"{field_title.upper()}: {formatted_value}", "-"*10]


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
        return ", ".join(str(f.value) if hasattr(f, "value") else str(f) for f in value)

    if hasattr(value, "value"):
        return value.value

    return str(value)
