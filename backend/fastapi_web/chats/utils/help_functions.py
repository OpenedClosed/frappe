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
from telegram_bot.infra import settings as bot_settings

from chats.db.mongo.enums import ChatSource, ChatStatus, SenderRole
from chats.db.mongo.schemas import ChatMessage, ChatSession, Client
from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from infra import settings

from .knowledge_base import KNOWLEDGE_BASE

# ===== Основные функции для работы с сессией чата =====


async def generate_client_id(
    source: Union[Request, WebSocket],
    chat_source: ChatSource = ChatSource.INTERNAL,
    external_id: Optional[str] = None
) -> str:
    """Создает `client_id` в зависимости от источника клиента."""
    if external_id:
        return f"{chat_source.value}_{external_id}"

    if not isinstance(source, (Request, WebSocket)):
        raise ValueError("Invalid source type. Must be Request or WebSocket.")

    headers = source.headers
    forwarded_for = headers.get("x-forwarded-for")
    client_ip = forwarded_for.split(",")[0].strip(
    ) if forwarded_for else source.client.host
    user_agent = headers.get("user-agent", "unknown")

    if "PostmanRuntime" in user_agent:
        user_agent = "unknown"

    return f"{chat_source.value}_{hashlib.sha256(f'{client_ip}-{user_agent}'.encode()).hexdigest()}"


async def get_client_id(websocket: WebSocket, chat_id: str,
                        is_superuser: bool) -> str:
    """Определяет client_id с которым связан чат в зависимости от типа пользователя."""
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        raise ValueError(f"Chat session with ID {chat_id} not found.")

    chat_session = ChatSession(**chat_data)

    if is_superuser:
        return chat_session.get_client_id()

    return await generate_client_id(websocket)


def generate_chat_id() -> str:
    """Создать уникальный идентификатор чата."""
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
    """Отправка информации о чате в админский бот."""
    if settings.HOST == "localhost":
        return

    bot_webhook_url: str = "http://bot:9999/webhook/send_message"
    admin_chat_url: str = f"https://{settings.HOST}/admin/chats/chat_sessions/{chat_id}?isForm=false"

    created_at: str = (
        chat_session['created_at'].isoformat()
        if isinstance(chat_session['created_at'], datetime)
        else chat_session['created_at']
    )
    last_activity: str = (
        chat_session['last_activity'].isoformat()
        if isinstance(chat_session['last_activity'], datetime)
        else chat_session['last_activity']
    )

    message_text: str = f"""
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
        response: httpx.Response = await client.post(
            bot_webhook_url,
            json={
                "chat_id": bot_settings.ADMIN_CHAT_ID,
                "text": message_text,
                "parse_mode": "HTML",
            },
        )
        if response.status_code != 200:
            logging.info(f"Сообщение не отправлено! Ошибка: {response.text}")


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
    """Создаёт или получает чат-сессию с приоритетом Redis → MongoDB (для внешних чатов)."""

    metadata = metadata or {}
    chat_data = None
    client_id = await generate_client_id(
        request, chat_source=chat_source, external_id=client_external_id
    ) if request else f"{chat_source.value}_{client_external_id}"

    redis_key = f"chat:{client_id}"

    if mode == "new":
        if old_chat_id := await redis_db.get(redis_key):
            old_chat_id = old_chat_id.decode()
            if chat_data := await mongo_db.chats.find_one({"chat_id": old_chat_id}):
                await mongo_db.chats.update_one(
                    {"chat_id": old_chat_id},
                    {"$set": {"closed_by_request": True,
                              "last_activity": datetime.utcnow()}}
                )
            await redis_db.delete(redis_key)

    if chat_id_from_redis := await redis_db.get(redis_key):
        chat_id_from_redis = chat_id_from_redis.decode()
        if chat_data := await mongo_db.chats.find_one({"chat_id": chat_id_from_redis}):
            remaining_time = max(0, settings.CHAT_TIMEOUT.total_seconds(
            ) - (datetime.utcnow() - chat_data["last_activity"]).total_seconds())
            return {
                "message": "Chat session active.",
                "chat_id": chat_data["chat_id"],
                "client_id": client_id,
                "created_at": chat_data["created_at"],
                "last_activity": chat_data["last_activity"],
                "remaining_time": remaining_time,
                "status": ChatSession(**chat_data).compute_status(remaining_time).value,
            }

    if chat_source != ChatSource.INTERNAL and chat_data:
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
        metadata=metadata)
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
    """Получить документ с базой знаний."""
    document = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
    if not document:
        raise HTTPException(404, "База знаний не найдена")
    document.pop("_id", None)
    if document["knowledge_base"]:
        return document["knowledge_base"]
    else:
        return KNOWLEDGE_BASE


# ===== Контекст для ИИ помощника =====

locale.setlocale(locale.LC_TIME, "C")


def get_current_datetime() -> str:
    """Возвращает текущую дату и время в формате 'Monday, 08-02-2025 14:30:00 UTC'."""
    now = datetime.now(timezone.utc)
    formatted_datetime = now.strftime(
        "%A, %d-%m-%Y %H:%M:%S UTC%z").replace("UTC+0000", "UTC")
    return formatted_datetime


async def get_weather_for_region(region_name: str) -> Dict[str, Any]:
    """Получает прогноз погоды на 5 дней с кэшированием в Redis."""
    redis_key = f"weather:{region_name.lower()}"
    cached_weather = await redis_db.get(redis_key)
    if cached_weather:
        return json.loads(cached_weather)

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
                return {"error": "Погода недоступна"}

            data = response.json()
            forecast = parse_weather_data(data)
            await redis_db.set(redis_key, json.dumps(forecast), ex=int(settings.WEATHER_CACHE_LIFETIME.total_seconds()))
            return forecast

        except Exception as e:
            return {"error": f"Ошибка получения погоды: {e}"}


async def get_coordinates(address: str) -> Dict[str, float]:
    """Получает координаты (широта, долгота) для заданного адреса."""
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
            return {"error": f"Ошибка получения координат: {e}"}


async def get_weather_for_location(lat: float, lon: float) -> Dict[str, Any]:
    """Получает прогноз погоды по координатам с кэшированием."""
    redis_key = f"weather:{lat},{lon}"
    cached_weather = await redis_db.get(redis_key)
    if cached_weather:
        return json.loads(cached_weather)

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
                return {"error": "Погода недоступна"}

            data = response.json()
            forecast = parse_weather_data(data)
            await redis_db.set(redis_key, json.dumps(forecast), ex=int(settings.WEATHER_CACHE_LIFETIME.total_seconds()))
            return forecast

        except Exception as e:
            return {"error": f"Ошибка получения погоды: {e}"}


async def get_weather_by_address(address: str) -> Dict[str, Any]:
    """Получает прогноз погоды для заданного адреса."""
    coordinates = await get_coordinates(address)
    if not coordinates:
        return {"error": "Не удалось получить координаты"}
    return await get_weather_for_location(coordinates["lat"], coordinates["lon"])


def parse_weather_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Парсит прогноз погоды и группирует данные по дням."""
    forecast = {}

    for entry in data["list"]:
        date = entry["dt_txt"].split(" ")[0]
        temp = entry["main"]["temp"]
        description = entry["weather"][0]["description"].capitalize()

        if date not in forecast:
            forecast[date] = {
                "temp_min": temp,
                "temp_max": temp,
                "description": description}
        else:
            forecast[date]["temp_min"] = min(forecast[date]["temp_min"], temp)
            forecast[date]["temp_max"] = max(forecast[date]["temp_max"], temp)

    return {"forecast": forecast}
