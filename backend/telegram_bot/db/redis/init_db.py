"""Инициализация БД Redis."""
from redis.asyncio import Redis

from telegram_bot.infra import settings as bot_settings

redis = Redis.from_url(bot_settings.REDIS_STORAGE_URL)
