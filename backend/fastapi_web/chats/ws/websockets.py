"""Веб-сокеты приложения Чаты."""
import asyncio
import logging
from typing import Optional
from urllib.parse import parse_qs, urlparse

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from starlette.websockets import WebSocketState

from chats.ws.ws_handlers import (broadcast_error, handle_get_messages,
                                  handle_message, start_brief)
from db.mongo.db_init import mongo_db
from main import app
from users.db.mongo.enums import RoleEnum
from users.utils.help_functions import get_user_by_id

from ..db.mongo.schemas import ChatSession
from ..utils.help_functions import (determine_language,
                                    get_active_chats_for_client, get_chat_position, get_client_id)
from .ws_helpers import (chat_managers, get_typing_manager, get_ws_manager,
                         gpt_task_manager, websocket_jwt_required)

# ==============================
# Основной WebSocket эндпоинт
# ==============================


@app.websocket("/ws/{chat_id}/")
async def websocket_chat_endpoint(websocket: WebSocket, chat_id: str):
    """WebSocket соединение для чата."""
    user_data = {}
    user = None
    user_id = await websocket_jwt_required(websocket)

    if user_id:
        try:
            user = await get_user_by_id(user_id)
            user_data = await user.get_full_user_data()
        except Exception as e:
            logging.warning(f"Cannot load user from JWT: {e}")

    qs = parse_qs(urlparse(str(websocket.url)).query)
    as_admin = qs.get("as_admin", [None])[0]
    is_superuser = bool(
        user and user.role in [
            RoleEnum.ADMIN,
            RoleEnum.SUPERADMIN, RoleEnum.DEMO_ADMIN] and as_admin)


    # is_superuser = bool(
    #     user and user.role in [
    #         RoleEnum.ADMIN,
    #         RoleEnum.SUPERADMIN])

    manager = await get_ws_manager(chat_id)
    typing_manager = await get_typing_manager(chat_id)

    client_id = await get_client_id(websocket, chat_id, is_superuser, user_id=user_id)
    user_data["client_id"] = client_id

    await manager.connect(websocket, client_id)

    user_language = determine_language(
        websocket.headers.get("accept-language", "en")
    )
    redis_session_key = f"chat:session:{chat_id}"
    redis_flood_key = f"flood:{client_id}"

    chat_session = await load_chat_session(manager, client_id, chat_id)
    if not chat_session:
        return

    if not await validate_session(manager, client_id, chat_id, is_superuser):
        return

    if not await handle_get_messages(
        manager=manager,
        chat_id=chat_id,
        redis_key_session=redis_session_key,
        user_data=user_data,
        data={}
    ):
        await start_brief(chat_session, user_data, manager, redis_session_key, user_language)

    try:
        while websocket.client_state == WebSocketState.CONNECTED:
            data = await websocket.receive_json()

            gpt_lock = gpt_task_manager.get_lock(chat_id)

            asyncio.create_task(
                handle_message(
                    manager=manager,
                    typing_manager=typing_manager,
                    data=data,
                    chat_id=chat_id,
                    client_id=client_id,
                    redis_session_key=redis_session_key,
                    redis_flood_key=redis_flood_key,
                    is_superuser=is_superuser,
                    user_language=user_language,
                    gpt_lock=gpt_lock,
                    user_data=user_data
                )
            )

    except WebSocketDisconnect:
        logging.warning(
            f"Client disconnected: chat_id={chat_id}, client_id={client_id}")
        await manager.disconnect(client_id)
        await typing_manager.remove_typing(chat_id, client_id, manager)

    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        await manager.disconnect(client_id)


# ==============================
# Вспомогательные функции
# ==============================

async def validate_session(
    manager,
    client_id: str,
    chat_id: str,
    is_superuser: bool
) -> bool:
    """Проверяет, что чат активен у клиента."""
    if is_superuser:
        return True

    active_chats = await get_active_chats_for_client(client_id)
    active_chat_ids = {chat["chat_id"] for chat, _ in active_chats}

    if chat_id not in active_chat_ids:
        logging.info(
            f"Session validation failed: client_id={client_id}, chat_id={chat_id}")
        await manager.disconnect(client_id)
        return False

    return True


async def load_chat_session(manager, client_id: str,
                            chat_id: str) -> Optional[ChatSession]:
    """Загружает сессию чата из базы данных."""
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        await broadcast_error(manager, client_id, chat_id, "Chat does not exist.")
        return None

    try:
        return ChatSession(**chat_data)
    except ValidationError:
        await broadcast_error(manager, client_id, chat_id, "Invalid chat data.")
        return None


def log_all_connections():
    """Логирует текущее состояние всех соединений."""
    parts = ["\n🧠 [DEBUG] Current WebSocket connections:\n" + "-" * 70]
    for chat_id, manager in chat_managers.items():
        parts.append(f"🔹 Chat: {chat_id} | Manager id={id(manager)}")
        for user_id, ws in manager.active_connections.items():
            parts.append(
                f"   └─ 👤 client_id={user_id} | ws id={id(ws)} | state={ws.client_state}"
            )
    parts.append("-" * 70 + "\n")
    logging.debug("\n".join(parts))
