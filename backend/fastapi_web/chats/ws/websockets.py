"""Веб-сокеты приложения Чаты."""
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from starlette.websockets import WebSocketState

from chats.ws.ws_handlers import (broadcast_error, handle_get_messages,
                                  handle_message, start_brief)
from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from main import app

from ..db.mongo.schemas import ChatSession
from ..utils.help_functions import (determine_language, generate_client_id,
                                    get_client_id)
from .ws_helpers import get_ws_manager, websocket_jwt_required

# ==============================
# БЛОК: Основной WebSocket эндпоинт
# ==============================


@app.websocket("/ws/{chat_id}/")
async def websocket_chat_endpoint(websocket: WebSocket, chat_id: str):
    """Основной WebSocket для чата."""
    is_superuser = bool(await websocket_jwt_required(websocket))
    manager = await get_ws_manager(chat_id)

    client_id = await get_client_id(websocket, chat_id, is_superuser)
    id_to_connect = "admin_pass" if (is_superuser and (await generate_client_id(websocket) == client_id)) else await generate_client_id(websocket) if is_superuser else client_id

    await manager.connect(websocket, id_to_connect)

    user_language = determine_language(
        websocket.headers.get(
            "accept-language", "en"))

    redis_session_key = f"chat:{client_id}"
    redis_flood_key = f"flood:{client_id}"

    if not await validate_session(manager, client_id, chat_id, redis_session_key, is_superuser):
        return

    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        return

    chat_session = ChatSession(**chat_data)

    if not await handle_get_messages(manager, chat_id, redis_session_key):
        await start_brief(chat_session, manager, redis_session_key, user_language)

    try:
        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                logging.warning(
                    f"Клиент разорвал соединение: chat_id={chat_id}, client_id={client_id}")
                break
            data = await websocket.receive_json()
            await handle_message(
                manager, data, chat_id, client_id, redis_session_key, redis_flood_key, is_superuser, user_language
            )
    except WebSocketDisconnect:
        logging.error(f"Ошибка WebSocketDisconnect")
        await manager.disconnect(client_id)
    except Exception as e:
        logging.error(f"Ошибка WebSocket: {e}")
        await manager.disconnect(client_id)


# ==============================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================


async def validate_session(manager, client_id: str, chat_id: str,
                           redis_session_key: str, is_superuser: bool) -> bool:
    """Проверяет, соответствует ли текущая сессия чата."""
    stored_chat_id = await redis_db.get(redis_session_key)
    stored_chat_id = stored_chat_id.decode("utf-8") if stored_chat_id else None
    print(stored_chat_id)
    print(chat_id)
    print(is_superuser)

    if not (stored_chat_id == chat_id or is_superuser):
        logging.info("Сессия не прошла валиадцию")
        await manager.disconnect(client_id)
        return False
    return True


async def load_chat_session(manager, client_id: str,
                            chat_id: str) -> Optional[ChatSession]:
    """Загружает и валидирует сессию чата."""
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        await broadcast_error(manager, client_id, chat_id, "Chat does not exist.")
        return None

    try:
        return ChatSession(**chat_data)
    except ValidationError:
        await broadcast_error(manager, client_id, chat_id, "Invalid chat data.")
        return None
