"""Вспомогательные сущности для работы с веб-сокетом приложения Чаты."""
import json
import logging
from asyncio import Lock, Task
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Optional, Set
from urllib.parse import parse_qs, urlparse

from auth.utils.help_functions import is_token_blacklisted
from fastapi import WebSocket, status
from fastapi_jwt_auth import AuthJWT
from starlette.websockets import WebSocketState
from bson import ObjectId  
from utils.encoders import DateTimeEncoder
from fastapi_jwt_auth.exceptions import JWTDecodeError, MissingTokenError
# ==============================
# Глобальные менеджеры
# ==============================

chat_managers: Dict[str, "ConnectionManager"] = {}
typing_managers: Dict[str, "TypingManager"] = {}


# ==============================
# Менеджеры
# ==============================

class ConnectionManager:
    """Менеджер WebSocket-соединений."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        old_ws = self.active_connections.get(user_id)

        if old_ws is websocket:
            logging.info(f"WebSocket already registered: {user_id}")
            return

        if websocket.client_state == WebSocketState.CONNECTING:
            try:
                await websocket.accept()
            except Exception as e:
                logging.error(f"WebSocket accept error ({user_id}): {e}")
                return
        else:
            logging.warning(
                f"WebSocket not CONNECTING ({user_id}); skip accept()")
            return

        self.active_connections[user_id] = websocket
        logging.info(f"WebSocket connected: {user_id}")
        log_all_connections()

    async def disconnect(self, user_id: str) -> None:
        ws = self.active_connections.pop(user_id, None)
        if ws and ws.client_state == WebSocketState.CONNECTED:
            try:
                await ws.close()
                logging.info(f"WebSocket closed: {user_id}")
            except Exception as e:
                logging.error(f"WebSocket close error ({user_id}): {e}")
        log_all_connections()

    async def safe_send(self, websocket: WebSocket,
                        user_id: str, message: str) -> None:
        try:
            await websocket.send_text(message)
        except RuntimeError as e:
            if "call 'accept' first" in str(
                    e).lower() or "not connected" in str(e).lower():
                logging.warning(f"Stale socket; closing ({user_id})")
                try:
                    await websocket.close()
                except Exception:
                    pass
                await self.disconnect(user_id)
            else:
                logging.error(f"Send error ({user_id}): {e}")
                await self.disconnect(user_id)
        except Exception as e:
            logging.error(f"Unknown send error ({user_id}): {e}")
            await self.disconnect(user_id)

    async def send_personal_message(self, message: str, user_id: str) -> None:
        ws = self.active_connections.get(user_id)
        if ws and ws.client_state == WebSocketState.CONNECTED:
            await self.safe_send(ws, user_id, message)
        else:
            logging.warning(f"No active connection for {user_id}")

    async def broadcast(self, message: str) -> None:
        for user_id, ws in list(self.active_connections.items()):
            if ws.client_state == WebSocketState.CONNECTED:
                await self.safe_send(ws, user_id, message)
            else:
                await self.disconnect(user_id)


class TypingManager:
    """Менеджер печатающих пользователей."""

    def __init__(self) -> None:
        self.typing_users: Dict[str, Set[str]] = defaultdict(set)

    async def add_typing(self, chat_id: str, client_id: str,
                         manager: ConnectionManager) -> None:
        if client_id not in self.typing_users[chat_id]:
            self.typing_users[chat_id].add(client_id)
            await self.broadcast_typing(chat_id, manager)

    async def remove_typing(self, chat_id: str, client_id: str,
                            manager: ConnectionManager) -> None:
        if client_id in self.typing_users.get(chat_id, set()):
            self.typing_users[chat_id].discard(client_id)
            if not self.typing_users[chat_id]:
                del self.typing_users[chat_id]
            await self.broadcast_typing(chat_id, manager)

    async def broadcast_typing(self, chat_id: str,
                               manager: ConnectionManager) -> None:
        message = custom_json_dumps({
            "type": "typing_users",
            "chat_id": chat_id,
            "users": list(self.typing_users.get(chat_id, []))
        })
        await manager.broadcast(message)


class GptTaskManager:
    """Менеджер GPT-задач и блокировок."""

    def __init__(self) -> None:
        self.tasks: Dict[str, Task] = {}
        self.locks: Dict[str, Lock] = {}

    def get_lock(self, chat_id: str) -> Lock:
        if chat_id not in self.locks:
            self.locks[chat_id] = Lock()
        return self.locks[chat_id]

    def cancel_task(self, chat_id: str) -> None:
        task = self.tasks.get(chat_id)
        if task and not task.done():
            task.cancel()

    def set_task(self, chat_id: str, task: Task) -> None:
        self.tasks[chat_id] = task

    def get_task(self, chat_id: str) -> Optional[Task]:
        return self.tasks.get(chat_id)


gpt_task_manager = GptTaskManager()


# ==============================
# Сериализаторы и утилиты
# ==============================

# class DateTimeEncoder(json.JSONEncoder):
#     """JSONEncoder для datetime."""

#     def default(self, o: Any) -> Any:
#         if isinstance(o, datetime):
#             return o.isoformat() 
#         elif isinstance(o, ObjectId):
#             return str(o)

def custom_json_dumps(obj: Any) -> str:
    """Сериализует объект в JSON с поддержкой datetime."""
    return json.dumps(obj, cls=DateTimeEncoder)


def log_all_connections() -> None:
    """Логирует текущее состояние соединений."""
    parts = ["\n[DEBUG] Active WebSocket connections\n" + "-" * 60]
    for chat_id, mgr in chat_managers.items():
        parts.append(f"Chat {chat_id} (manager id={id(mgr)})")
        for uid, ws in mgr.active_connections.items():
            parts.append(
                f"  • {uid} | ws id={id(ws)} | state={ws.client_state}")
    parts.append("-" * 60)
    logging.debug("\n".join(parts))


# ==============================
# Фабрики менеджеров
# ==============================

async def get_ws_manager(chat_id: str) -> ConnectionManager:
    """Возвращает менеджер соединений чата."""
    return chat_managers.setdefault(chat_id, ConnectionManager())


async def get_typing_manager(chat_id: str) -> TypingManager:
    """Возвращает менеджер печатающих пользователей чата."""
    return typing_managers.setdefault(chat_id, TypingManager())


# ==============================
# Аутентификация WebSocket
# ==============================

async def websocket_jwt_required(websocket: WebSocket) -> Optional[str]:
    """Извлекает и валидирует JWT, возвращает user_id или None."""
    try:
        token = parse_qs(urlparse(str(websocket.url)).query).get(
            "token", [None])[0]
        if not token:
            return None

        authorize = AuthJWT()
        authorize._token = token
        authorize.jwt_required()

        raw_jwt = authorize.get_raw_jwt()
        if await is_token_blacklisted(
            authorize.get_jwt_subject(), "access", raw_jwt["jti"]
        ):
            logging.info("Token blacklisted")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        return authorize.get_jwt_subject()

    except (JWTDecodeError, KeyError, Exception):
        return None
