"""Обработчики маршрутов приложения Чаты."""
from typing import Optional

from fastapi import APIRouter, Query, Request

from chats.utils.commands import COMMAND_HANDLERS

from .db.mongo.enums import ChatSource
from .utils.help_functions import handle_chat_creation

chat_router = APIRouter()


@chat_router.post("/get_chat")
async def create_or_get_chat(
    request: Request,
    mode: Optional[str] = Query(default=None),
    source: Optional[ChatSource] = Query(default=ChatSource.INTERNAL),
    chat_external_id: Optional[str] = Query(default=None),
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


@chat_router.get("/commands", summary="Получить список доступных команд")
async def get_available_commands():
    """Возвращает список всех зарегистрированных команд с их описанием."""
    return {
        "commands": [
            {"command": cmd, "description": data["help_text"]}
            for cmd, data in COMMAND_HANDLERS.items()
        ]
    }
