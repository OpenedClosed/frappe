"""Веб-сокеты приложения Чаты."""
import asyncio
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
from users.db.mongo.enums import RoleEnum
from users.utils.help_functions import get_user_by_id

from ..db.mongo.schemas import ChatSession
from ..utils.help_functions import (determine_language, generate_client_id, 
                                    get_client_id)
from .ws_helpers import (get_typing_manager, get_ws_manager, gpt_task_manager, chat_managers,
                         websocket_jwt_required)


import inspect

def print_all_connections():
    print("\n🧠 [DEBUG] Текущее состояние соединений:\n" + "-"*70)
    for chat_id, manager in chat_managers.items():
        print(f"🔹 Чат: {chat_id} | Менеджер id={id(manager)}")
        for user_id, ws in manager.active_connections.items():
            print(f"   └─ 👤 client_id={user_id} | ws id={id(ws)} | статус={ws.client_state}")
    print("-"*70 + "\n")


# ==============================
# Основной WebSocket эндпоинт
# ==============================


@app.websocket("/ws/{chat_id}/")
async def websocket_chat_endpoint(websocket: WebSocket, chat_id: str):
    """WebSocket соединение для чата."""
    print("="*100)
    print("Начало работы с чатом:", chat_id)
    user_data = {}
    user=None
    user_id = await websocket_jwt_required(websocket)
    
    if user_id:
        try:
            user = await get_user_by_id(user_id)
            user_data = await user.get_full_user_data()
        except Exception as e:
            logging.warning(f"Cannot load user from JWT: {e}")

    is_superuser = user and user.role in [RoleEnum.ADMIN, RoleEnum.SUPERADMIN]
    print("Админ?:", is_superuser)


    manager = await get_ws_manager(chat_id)
    typing_manager = await get_typing_manager(chat_id)

    client_id = await get_client_id(websocket, chat_id, is_superuser)
    user_data["client_id"] = client_id

    await manager.connect(websocket, client_id)
    print_all_connections()

    user_language = determine_language(
        websocket.headers.get("accept-language", "en")
    )
    redis_session_key = f"chat:{client_id}"
    redis_flood_key = f"flood:{client_id}"

    chat_session = await load_chat_session(manager, client_id, chat_id)
    if not chat_session:
        return

    if not await validate_session(manager, client_id, chat_id, redis_session_key, is_superuser):
        return

    if not await handle_get_messages(manager=manager, chat_id=chat_id, redis_key_session=redis_session_key, user_data=user_data, data={}):
        await start_brief(chat_session, manager, redis_session_key, user_language)

    try:
        print(f"Статус сокета:", websocket.client_state)
        while websocket.client_state == WebSocketState.CONNECTED:
            data = await websocket.receive_json()

            gpt_lock = gpt_task_manager.get_lock(chat_id)
            print(f"Идет обработка сообщения типа {data.get('type')} в чате:", chat_id)

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
        logging.warning(f"Client disconnected: chat_id={chat_id}, client_id={client_id}")
        await manager.disconnect(client_id)
        await typing_manager.remove_typing(chat_id, client_id, manager)

    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        await manager.disconnect(client_id)


# ==============================
# Вспомогательные функции
# ==============================


async def validate_session(manager, client_id: str, chat_id: str,
                           redis_session_key: str, is_superuser: bool) -> bool:
    """Проверяет, соответствует ли текущая сессия чата."""
    stored_chat_id = await redis_db.get(redis_session_key)
    stored_chat_id = stored_chat_id.decode("utf-8") if stored_chat_id else None
    if not (stored_chat_id == chat_id or is_superuser):
        logging.info("Session validation failed.")
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
