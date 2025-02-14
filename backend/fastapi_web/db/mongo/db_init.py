"""Файл инициализации БД MongoDB."""
from motor.motor_asyncio import AsyncIOMotorClient

from infra import settings

mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
mongo_db = mongo_client[settings.MONGO_DB_NAME]


async def mongo_db_on_startapp():
    """При старте для MongoDB."""
    mongo_db.chats.create_index([("chat_id", 1)])
