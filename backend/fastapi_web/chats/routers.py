"""Обработчики маршрутов приложения Чаты."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from chats.utils.commands import COMMAND_HANDLERS
from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi_jwt_auth import AuthJWT

from .db.mongo.enums import ChatSource
from .utils.help_functions import (get_active_chats_for_client,
                                   handle_chat_creation, resolve_chat_identity, serialize_active_chat)
from infra import settings
import logging

chat_router = APIRouter()

@chat_router.post("/get_chat")
async def create_or_get_chat(
    request: Request,
    mode: Optional[str] = Query(default=None),
    source: ChatSource = Query(default=ChatSource.INTERNAL),
    chat_external_id: Optional[str] = Query(default=None),
    client_external_id: Optional[str] = Query(default=None),
    company_name: Optional[str] = Query(default=None),
    bot_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    timestamp: Optional[str] = Query(default=None),
    hash: Optional[str] = Query(default=None),
    Authorize: Optional[AuthJWT] = Depends(lambda: None),
) -> dict:
    """API-обработчик получения или создания чата."""
    token_user_id = None
    if Authorize is not None:
        try:
            token_user_id = Authorize.get_jwt_subject()
        except Exception:
            token_user_id = None
    # token_user_id = "6844539b006b0fd6b595ba48" # для теста
    if user_id and timestamp and hash:
        source = ChatSource.TELEGRAM_MINI_APP

    if not user_id:
        user_id = token_user_id

    client_id, external_id = await resolve_chat_identity(
        request, source, client_external_id, user_id, timestamp, hash, Authorize
    )

    metadata = {
        k: v for k, v in request.query_params.items()
        if k not in {
            "mode", "source", "chat_external_id", "client_external_id",
            "company_name", "bot_id", "user_id", "timestamp", "hash"
        }
    }

    return await handle_chat_creation(
        mode=mode,
        chat_source=source,
        chat_external_id=chat_external_id,
        client_external_id=external_id,
        company_name=company_name,
        bot_id=bot_id,
        metadata=metadata,
        request=request,
        token_user_id=token_user_id,
    )


@chat_router.get("/get_chat_by_id/{chat_id}")
async def get_chat_by_id(
    chat_id: str,
    request: Request,
    source: ChatSource = Query(default=ChatSource.INTERNAL),
    client_external_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    timestamp: Optional[str] = Query(default=None),
    hash: Optional[str] = Query(default=None),
    Authorize: Optional[AuthJWT] = Depends(lambda: None),
) -> dict:
    """Получает чат по ID, если он активен и принадлежит вызывающему клиенту."""
    if user_id and timestamp and hash:
        source = ChatSource.TELEGRAM_MINI_APP
    client_id, _ = await resolve_chat_identity(
        request, source, client_external_id, user_id, timestamp, hash, Authorize
    )

    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        raise HTTPException(status_code=404, detail="Chat not found")

    if chat_data.get("client", {}).get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    ttl = await redis_db.ttl(f"chat:session:{chat_id}")
    if ttl is None or ttl <= 0:
        raise HTTPException(status_code=404, detail="Chat session is not active")

    return await serialize_active_chat(chat_data, ttl)


@chat_router.get("/get_active_chats")
async def get_active_chats(
    request: Request,
    source: ChatSource = Query(default=ChatSource.INTERNAL),
    client_external_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    timestamp: Optional[str] = Query(default=None),
    hash: Optional[str] = Query(default=None),
    Authorize: Optional[AuthJWT] = Depends(lambda: None),
) -> list[dict]:
    """Получает список всех активных чатов клиента."""
    if user_id and timestamp and hash:
        source = ChatSource.TELEGRAM_MINI_APP
    client_id, _ = await resolve_chat_identity(
        request, source, client_external_id, user_id, timestamp, hash, Authorize
    )

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
