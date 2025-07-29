"""Инициализация БД Redis."""
from redis.asyncio import Redis

from infra.settings import REDIS_URL

redis_db = Redis.from_url(REDIS_URL)
