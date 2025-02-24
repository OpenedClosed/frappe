"""Вспомогательные функции приложения Чаты."""
import hashlib
import logging
import uuid
from datetime import datetime
from typing import Optional, Union, Dict, Any

import httpx
from fastapi import Request, WebSocket
from telegram_bot.infra import settings as bot_settings

from chats.db.mongo.enums import ChatSource, SenderRole
from chats.db.mongo.schemas import ChatMessage, ChatSession
from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from infra import settings
import httpx
import json
import locale
from datetime import timezone

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


locale.setlocale(locale.LC_TIME, "C")

def get_current_datetime():
    """Возвращает текущую дату и время с днем недели в формате: 'Monday, 08-02-2025 14:30:00 UTC+4'"""
    now = datetime.now(timezone.utc)
    formatted_datetime = now.strftime("%A, %d-%m-%Y %H:%M:%S UTC%z")
    formatted_datetime = formatted_datetime.replace("UTC+0000", "UTC")
    return formatted_datetime


async def get_weather_for_region(region_name: str) -> Dict[str, Any]:
    """Асинхронно получает прогноз погоды на 5 дней с кэшированием в Redis."""

    redis_key = f"weather:{region_name.lower()}"

    cached_weather = await redis_db.get(redis_key)
    if cached_weather:
        return json.loads(cached_weather)

    params = {
        "q": region_name,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
        "lang": "en",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://api.openweathermap.org/data/2.5/forecast", params=params)
            data = response.json()

            if response.status_code == 200:
                forecast = {}

                for entry in data["list"]:
                    date = entry["dt_txt"].split(" ")[0]  # Дата без времени
                    temp = entry["main"]["temp"]
                    description = entry["weather"][0]["description"].capitalize()

                    if date not in forecast:
                        forecast[date] = {"temp_min": temp, "temp_max": temp, "description": description}
                    else:
                        forecast[date]["temp_min"] = min(forecast[date]["temp_min"], temp)
                        forecast[date]["temp_max"] = max(forecast[date]["temp_max"], temp)

                weather_data = {"forecast": forecast}
                await redis_db.set(redis_key, json.dumps(weather_data), ex=int(settings.WEATHER_CACHE_LIFETIME.total_seconds()))
                return weather_data
            else:
                return {"error": "Weather data unavailable"}
        except Exception as e:
            print(f"Error fetching weather data: {e}")
            return {"error": "Weather data unavailable"}
        




async def get_coordinates(address: str) -> Dict[str, float]:
    """Получает координаты (широта, долгота) для заданного адреса через OpenWeatherMap Geocoding API."""
    geocode_url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": address,
        "limit": 1,
        "appid": settings.WEATHER_API_KEY,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(geocode_url, params=params)
            data = response.json()

            if response.status_code == 200 and data:
                return {"lat": data[0]["lat"], "lon": data[0]["lon"]}
            else:
                print("Ошибка геокодинга:", data)
                return {}
        except Exception as e:
            print(f"Ошибка при получении координат: {e}")
            return {}


async def get_weather_for_location(lat: float, lon: float) -> Dict[str, Any]:
    """Получает прогноз погоды по координатам (широта и долгота)."""

    redis_key = f"weather:{lat},{lon}"
    cached_weather = await redis_db.get(redis_key)
    
    if cached_weather:
        return json.loads(cached_weather)

    weather_url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",  # русский язык
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(weather_url, params=params)
            data = response.json()

            if response.status_code == 200:
                forecast = {}

                for entry in data["list"]:
                    date = entry["dt_txt"].split(" ")[0]  # Дата без времени
                    temp = entry["main"]["temp"]
                    description = entry["weather"][0]["description"].capitalize()

                    if date not in forecast:
                        forecast[date] = {"temp_min": temp, "temp_max": temp, "description": description}
                    else:
                        forecast[date]["temp_min"] = min(forecast[date]["temp_min"], temp)
                        forecast[date]["temp_max"] = max(forecast[date]["temp_max"], temp)

                weather_data = {"forecast": forecast}
                await redis_db.set(redis_key, json.dumps(weather_data), ex=int(settings.WEATHER_CACHE_LIFETIME.total_seconds()))
                return weather_data
            else:
                return {"error": "Погода недоступна"}
        except Exception as e:
            print(f"Ошибка получения погоды: {e}")
            return {"error": "Погода недоступна"}


async def get_weather_by_address(address: str) -> str:
    """Получает прогноз погоды для адреса."""
    coordinates = await get_coordinates(address)

    if not coordinates:
        return {"error": "Не удалось получить координаты"}

    return await get_weather_for_location(coordinates["lat"], coordinates["lon"])