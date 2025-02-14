"""Инициализация БД Redis."""
import aioredis

from infra.settings import REDIS_URL

redis_db = aioredis.from_url(REDIS_URL)
