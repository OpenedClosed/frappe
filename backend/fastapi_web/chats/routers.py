"""Обработчики маршрутов приложения Чаты."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from chats.utils.commands import COMMAND_HANDLERS
from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db

from .db.mongo.enums import ChatSource
from .utils.help_functions import (get_active_chats_for_client,
                                   handle_chat_creation, serialize_active_chat)
from infra import settings

chat_router = APIRouter()


# @chat_router.post("/get_chat")
# async def create_or_get_chat(
#     request: Request,
#     mode: Optional[str] = Query(default=None),
#     source: Optional[ChatSource] = Query(default=ChatSource.INTERNAL),
#     chat_external_id: Optional[str] = Query(default=None),
#     client_external_id: Optional[str] = Query(default=None),
#     company_name: Optional[str] = Query(default=None),
#     bot_id: Optional[str] = Query(default=None),
# ) -> dict:
#     """API-обработчик получения или создания чата."""
#     metadata = {
#         k: v for k,
#         v in request.query_params.items() if k not in {
#             "mode",
#             "source",
#             "chat_external_id",
#             "client_external_id",
#             "company_name",
#             "bot_id"}}
#     return await handle_chat_creation(
#         mode, source, chat_external_id, client_external_id, company_name, bot_id, metadata, request
#     )


from chats.integrations.telegram.telegram_bot import verify_telegram_hash

@chat_router.post("/get_chat")
async def create_or_get_chat(
    request: Request,
    mode: Optional[str] = Query(default=None),
    source: Optional[ChatSource] = Query(default=ChatSource.INTERNAL),
    chat_external_id: Optional[str] = Query(default=None),
    client_external_id: Optional[str] = Query(default=None),
    company_name: Optional[str] = Query(default=None),
    bot_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    timestamp: Optional[str] = Query(default=None),
    hash: Optional[str] = Query(default=None),
) -> dict:
    """API-обработчик получения или создания чата."""

    if source == ChatSource.TELEGRAM and user_id and timestamp and hash:
        if not verify_telegram_hash(user_id, timestamp, hash, settings.TELEGRAM_BOT_TOKEN):
            raise HTTPException(status_code=403, detail="Invalid Telegram signature")

        client_external_id = user_id

    metadata = {
        k: v for k, v in request.query_params.items()
        if k not in {
            "mode", "source", "chat_external_id", "client_external_id",
            "company_name", "bot_id", "user_id", "timestamp", "hash"
        }
    }

    return await handle_chat_creation(
        mode, source, chat_external_id, client_external_id, company_name, bot_id, metadata, request
    )



@chat_router.get("/get_chat_by_id/{chat_id}")
async def get_chat_by_id(chat_id: str) -> dict:
    """Получает чат по ID, если он активен. Иначе — 404."""
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        raise HTTPException(status_code=404, detail="Chat not found")

    redis_key = f"chat:session:{chat_id}"
    ttl = await redis_db.ttl(redis_key)
    if ttl <= 0:
        raise HTTPException(
            status_code=404,
            detail="Chat session is not active")

    return await serialize_active_chat(chat_data, ttl)


@chat_router.get("/get_active_chats")
async def get_active_chats(
    client_external_id: str,
    source: ChatSource = Query(default=ChatSource.INTERNAL)
) -> list[dict]:
    """Получает список всех активных чатов пользователя."""
    client_id = f"{source.value}_{client_external_id}"
    active_chats = await get_active_chats_for_client(client_id)

    return [await serialize_active_chat(chat_data, ttl) for chat_data, ttl in active_chats]


@chat_router.get("/commands", summary="Получить список доступных команд")
async def get_available_commands():
    """Возвращает список всех зарегистрированных команд с их описанием."""
    return {
        "commands": [
            {"command": cmd, "description": data["help_text"]}
            for cmd, data in COMMAND_HANDLERS.items()
        ]
    }
