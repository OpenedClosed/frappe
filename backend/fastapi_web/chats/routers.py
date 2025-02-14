"""Обработчики маршрутов приложения Чаты."""
from fastapi import Query, Request
from typing import Any, Dict, Optional, Union
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request

from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from infra import settings

from .db.mongo.enums import ChatSource, ChatStatus
from .db.mongo.schemas import ChatSession, Client
from .utils.help_functions import generate_chat_id, generate_client_id

chat_router = APIRouter()


@chat_router.post("/get_chat")
async def create_or_get_chat(
    request: Request,
    mode: Optional[str] = Query(default=None),
    source: Optional[ChatSource] = Query(default=ChatSource.INTERNAL),
    # ID бота (если чат с внешнего сервиса)
    chat_external_id: Optional[str] = Query(default=None),
    # ID пользователя (если чат с внешнего сервиса)
    client_external_id: Optional[str] = Query(default=None),
    company_name: Optional[str] = Query(default=None),
    bot_id: Optional[str] = Query(default=None),
) -> dict:
    """API-обработчик получения или создания чата."""
    metadata = {
        k: v for k,
        v in request.query_params.items() if k not in {
            "mode",
            "source",
            "chat_external_id",
            "client_external_id",
            "company_name",
            "bot_id"}}

    return await handle_chat_creation(
        mode, source, chat_external_id, client_external_id, company_name, bot_id, metadata, request
    )


async def handle_chat_creation(
    mode: Optional[str] = None,
    chat_source: ChatSource = ChatSource.INTERNAL,
    chat_external_id: Optional[str] = None,  # ID чата в внешнем сервисе
    client_external_id: Optional[str] = None,  # ID клиента в внешнем сервисе
    company_name: Optional[str] = None,
    bot_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> dict:
    """Создаёт или получает чат-сессию с приоритетом Redis → MongoDB (для внешних чатов)."""

    metadata = metadata or {}
    chat_data = None
    client_id = await generate_client_id(
        request, chat_source=chat_source, external_id=client_external_id
    ) if request else f"{chat_source.value}_{client_external_id}"

    redis_key = f"chat:{client_id}"

    if mode == "new":
        if old_chat_id := await redis_db.get(redis_key):
            old_chat_id = old_chat_id.decode()
            if chat_data := await mongo_db.chats.find_one({"chat_id": old_chat_id}):
                await mongo_db.chats.update_one(
                    {"chat_id": old_chat_id},
                    {"$set": {"closed_by_request": True,
                              "last_activity": datetime.utcnow()}}
                )
            await redis_db.delete(redis_key)

    if chat_id_from_redis := await redis_db.get(redis_key):
        chat_id_from_redis = chat_id_from_redis.decode()
        if chat_data := await mongo_db.chats.find_one({"chat_id": chat_id_from_redis}):
            remaining_time = max(0, settings.CHAT_TIMEOUT.total_seconds(
            ) - (datetime.utcnow() - chat_data["last_activity"]).total_seconds())
            return {
                "message": "Chat session active.",
                "chat_id": chat_data["chat_id"],
                "client_id": client_id,
                "created_at": chat_data["created_at"],
                "last_activity": chat_data["last_activity"],
                "remaining_time": remaining_time,
                "status": ChatSession(**chat_data).compute_status(remaining_time).value,
            }

    if chat_source != ChatSource.INTERNAL and chat_data:
        chat_session = ChatSession(**chat_data)

        await redis_db.set(redis_key, chat_session.chat_id, ex=int(settings.CHAT_TIMEOUT.total_seconds()))

        return {
            "message": "Chat session restored from MongoDB.",
            "chat_id": chat_session.chat_id,
            "client_id": client_id,
            "status": chat_session.compute_status(settings.CHAT_TIMEOUT.total_seconds()).value,
        }

    client = Client(
        client_id=client_id,
        source=chat_source,
        external_id=client_external_id,
        metadata=metadata)
    chat_id = generate_chat_id()

    chat_session = ChatSession(
        chat_id=chat_id,
        client=client,
        bot_id=bot_id,
        company_name=company_name,
        last_activity=datetime.utcnow(),
        external_id=chat_external_id if chat_source != ChatSource.INTERNAL else None
    )

    await mongo_db.chats.insert_one(chat_session.dict())

    await redis_db.set(redis_key, chat_id, ex=int(settings.CHAT_TIMEOUT.total_seconds()))

    return {
        "message": "New chat session created.",
        "chat_id": chat_id,
        "client_id": client_id,
        "status": ChatStatus.IN_PROGRESS.value,
    }
