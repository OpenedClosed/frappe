"""Файл инициализации БД MongoDB."""
from motor.motor_asyncio import AsyncIOMotorClient

# from fastapi_web.infra import settings
# from fastapi_web.knowledge.db.mongo.schemas import KnowledgeBase

from infra import settings
from knowledge.db.mongo.schemas import KnowledgeBase

mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
mongo_db = mongo_client[settings.MONGO_DB_NAME]


async def mongo_db_on_startapp():
    """При старте для MongoDB."""
    mongo_db.chats.create_index([("chat_id", 1)])
    kb_doc = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
    if not kb_doc:
        kb = {
            "app_name": "main",
            "knowledge_base": {},
        }
        kb_doc = KnowledgeBase(**kb).model_dump()
        await mongo_db.knowledge_collection.insert_one(kb_doc)
