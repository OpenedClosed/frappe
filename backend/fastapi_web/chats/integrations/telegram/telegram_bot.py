"""Интеграция с Telegram."""
import hashlib
import hmac
from typing import Any, Awaitable, Callable, Dict, List, Optional
from urllib.parse import parse_qsl

from chats.db.mongo.enums import ChatSource
from chats.integrations.basic.handlers import route_incoming_message
from fastapi import APIRouter, HTTPException, Query, Request
from infra import settings

from .utils.help_functions import process_telegram_message

telegram_router = APIRouter()

# def verify_telegram_hash(user_id: str, timestamp: str, hash_value: str, bot_token: str) -> bool:
#     """
#     Проверяет подпись по user_id и timestamp.
#     """
#     base_string = f"user_id={user_id}&timestamp={timestamp}"
#     secret_key = hashlib.sha256(bot_token.encode()).digest()
#     expected_hash = hmac.new(secret_key, base_string.encode(), hashlib.sha256).hexdigest()
#     return hmac.compare_digest(expected_hash, hash_value)

def verify_telegram_hash(user_id: str, timestamp: str, hash_value: str, bot_token: str) -> bool:
    """
    Проверяет подпись по user_id и timestamp и выводит отладочную информацию.
    """
    base_string = f"user_id={user_id}&timestamp={timestamp}"
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    expected_hash = hmac.new(secret_key, base_string.encode(), hashlib.sha256).hexdigest()
    result = hmac.compare_digest(expected_hash, hash_value)

    return result

@telegram_router.post("/webhook")
async def handle_telegram_messages(request: Request):
    """Принимает запросы от контейнера бота Telegram и валидирует токен и подпись."""
    token = request.headers.get("X-Telegram-Token")
    if token != settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

    user_id = request.query_params.get("user_id")
    timestamp = request.query_params.get("timestamp")
    hash_value = request.query_params.get("hash")

    if not all([user_id, timestamp, hash_value]):
        raise HTTPException(status_code=400, detail="Missing hash parameters")

    is_valid = verify_telegram_hash(
        user_id=user_id,
        timestamp=timestamp,
        hash_value=hash_value,
        bot_token=settings.TELEGRAM_BOT_TOKEN,
    )


    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid hash signature")

    payload = await request.json()
    messages_info = [payload]


    await handle_incoming_telegram_messages(
        messages_info=messages_info,
        request=request,
        settings_bot_id=settings.TELEGRAM_BOT_ID,
        chat_source=ChatSource.TELEGRAM,
        process_fn=process_telegram_message,
    )

    return {"status": "ok"}



async def handle_incoming_telegram_messages(
    messages_info: List[Dict[str, Any]],
    request: Request,
    settings_bot_id: str,
    chat_source: ChatSource,
    process_fn: Callable[..., Awaitable[None]],
):
    """Подготовка данных Telegram → универсальный роутер."""
    for msg in messages_info:
        sender_id = str(msg["from"]["id"])
        recipient_id = str(settings_bot_id)
        message_text = msg.get("text") or msg.get("caption", "")
        message_id = str(msg["message_id"])
        timestamp = int(msg["date"]) * 1000

        from_data = msg["from"]
        avatar_url = msg.get("avatar_url")

        metadata: Dict[str, Any] = {
            "username": from_data.get("username"),
            "first_name": from_data.get("first_name"),
            "last_name": from_data.get("last_name"),
            "language_code": from_data.get("language_code"),
            "avatar_url": avatar_url,
        }

        await route_incoming_message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_text=message_text,
            message_id=message_id,
            timestamp=timestamp,
            metadata=metadata,
            chat_source=chat_source,
            settings_bot_id=settings_bot_id,
            access_token=None,
            profile_fetcher=None,
            process_fn=process_fn,
            skip_locale=True,
        )