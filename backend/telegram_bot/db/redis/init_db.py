"""Инициализация БД Redis."""
from aioredis.client import Redis

from infra import settings as bot_settings

redis = Redis.from_url(bot_settings.REDIS_STORAGE_URL)
