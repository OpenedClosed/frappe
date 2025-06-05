from aiogram import Bot
from aiogram.types import User
import asyncio
import logging
import sys
from pathlib import Path
import hmac
import hashlib
from datetime import datetime
from urllib.parse import urlencode

from aiogram.types import MenuButtonWebApp, WebAppInfo
from bot_conf.create_bot import bot
from infra import settings as bot_settings
from fastapi_web.infra import settings


import hashlib
import hmac

def generate_telegram_hash(user_id: str, timestamp: str, bot_token: str) -> str:
    """
    Генерирует HMAC-хэш для подписи сообщения от Telegram WebApp или бота.
    """
    base_string = f"user_id={user_id}&timestamp={timestamp}"
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret_key, base_string.encode(), hashlib.sha256).hexdigest()


async def generate_secure_webapp_url(user: User, bot: Bot) -> str:
    """
    Генерирует WebApp URL с подписью и дополнительной информацией о пользователе.
    """
    base_url = f"{settings.HOST_URL}/chats/telegram-chat"
    timestamp = int(datetime.utcnow().timestamp())
    user_id = user.id

    # Хэш только по user_id и timestamp
    data = f"user_id={user_id}&timestamp={timestamp}"
    secret_key = hashlib.sha256(bot_settings.TELEGRAM_BOT_TOKEN.encode()).digest()
    signature = hmac.new(secret_key, data.encode(), hashlib.sha256).hexdigest()

    # Дополнительные данные
    avatar_url = await get_avatar_url(bot, user.id)

    query = urlencode({
        "user_id": user_id,
        "timestamp": timestamp,
        "hash": signature,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "language_code": user.language_code or "",
        "avatar_url": avatar_url or "",
    })

    return f"{base_url}?{query}"


async def set_menu_webapp_for_user(user: User, bot: Bot):
    """
    Назначает WebApp-кнопку с безопасной ссылкой.
    """
    url = await generate_secure_webapp_url(user, bot)
    logging.error(url)
    await bot.set_chat_menu_button(
        chat_id=user.id,
        menu_button=MenuButtonWebApp(
            text="💬",
            web_app=WebAppInfo(url=url)
        )
    )


async def get_avatar_url(bot: Bot, user_id: int) -> str | None:
    photos = await bot.get_user_profile_photos(user_id, limit=1)
    if not photos.total_count:
        return None
    file_id = photos.photos[0][-1].file_id 
    f = await bot.get_file(file_id)
    return f"https://api.telegram.org/file/bot{bot.token}/{f.file_path}"
