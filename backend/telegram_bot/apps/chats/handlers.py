import time

import aiohttp
from aiogram import Router
from aiogram.types import Message
from telegram_bot.infra.create_bot import bot, dp
from fastapi_web.infra import settings
from telegram_bot.infra import settings as bot_settings
from telegram_bot.utils.decorators import check_private_chat
from telegram_bot.utils.help_functions import generate_telegram_hash, get_avatar_url

relay_router = Router()


@relay_router.message()
@check_private_chat
async def relay_handler(message: Message):
    """
    Отправляет сообщение на backend от Telegram-бота, включая подпись.
    """
    avatar = await get_avatar_url(message.bot, message.from_user.id)

    payload = {
        "from": {
            "id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "language_code": message.from_user.language_code,
        },
        "message_id": message.message_id,
        "text": message.text,
        "caption": message.caption,
        "date": int(message.date.timestamp()),
        "avatar_url": avatar,
    }

    user_id = str(message.from_user.id)
    timestamp = str(int(time.time()))
    hash_value = generate_telegram_hash(user_id, timestamp, bot_settings.TELEGRAM_BOT_TOKEN)

    base_url = "http://backend:8000/api/chats/telegram/webhook"

    url = (
        f"{base_url}"
        f"?user_id={user_id}&timestamp={timestamp}&hash={hash_value}"
    )

    async with aiohttp.ClientSession() as session:
        await session.post(
            url,
            json=payload,
            headers={"X-Telegram-Token": bot_settings.TELEGRAM_BOT_TOKEN}
        )