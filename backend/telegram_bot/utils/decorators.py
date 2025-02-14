"""Декораторы функций бота."""
from functools import wraps

from aiogram.types import Message


def check_private_chat(func):
    """Декоратор для проверки, что сообщение отправлено из личного чата, а не из супергруппы."""
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        chat_info = await message.bot.get_chat(message.chat.id)
        if chat_info.type != 'supergroup':
            return await func(message, *args, **kwargs)
        else:
            await message.reply("Эта команда доступна только в личных чатах.")
    return wrapper
