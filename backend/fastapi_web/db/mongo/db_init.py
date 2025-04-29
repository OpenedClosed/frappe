"""Файл инициализации БД MongoDB."""
from motor.motor_asyncio import AsyncIOMotorClient

from infra import settings
from knowledge.db.mongo.schemas import KnowledgeBase

mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
mongo_db = mongo_client[settings.MONGO_DB_NAME]


async def mongo_db_on_startapp():
    """При старте для MongoDB."""
    mongo_db.chats.create_index([("chat_id", 1)])
    kb_doc = await mongo_db.knowledge_collection.find_one({"app_name": settings.APP_NAME})
    print(f"База знаний {'найдена' if kb_doc else 'не найдена'}")
    if not kb_doc:
        kb = {
            "app_name": settings.APP_NAME,
            "knowledge_base": {},
        }
        kb_doc = KnowledgeBase(**kb).model_dump(mode="python")
        await mongo_db.knowledge_collection.insert_one(kb_doc)
