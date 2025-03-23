"""Вспомогательные сущности для работы с веб-сокетом приложения Чаты."""
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Optional, Set
from urllib.parse import parse_qs, urlparse

from fastapi import WebSocket, status
from fastapi_jwt_auth import AuthJWT
from starlette.websockets import WebSocketState

from auth.utils.help_functions import is_token_blacklisted

chat_managers: Dict[str, "ConnectionManager"] = {}
typing_managers: Dict[str, "TypingManager"] = {}


class ConnectionManager:
    """Менеджер соединений веб-сокета."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Принимает соединение веб-сокета."""
        try:
            await websocket.accept()
            self.active_connections[user_id] = websocket
            logging.info(f"WebSocket подключён: {user_id}")
        except Exception as e:
            logging.error(f"Ошибка при подключении WebSocket {user_id}: {e}")

    async def disconnect(self, user_id: str) -> None:
        """Отключает пользователя и закрывает соединение, если оно активно."""
        websocket = self.active_connections.pop(user_id, None)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
                logging.info(f"WebSocket отключён: {user_id}")
            except Exception as e:
                logging.error(f"Ошибка при закрытии WebSocket {user_id}: {e}")

    async def send_personal_message(self, message: str, user_id: str) -> None:
        """Отправляет сообщение конкретному пользователю."""
        websocket = self.active_connections.get(user_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения {user_id}: {e}")
                await self.disconnect(user_id)

    async def broadcast(self, message: str) -> None:
        """Разослать сообщение всем подключенным пользователям."""
        active_connections_copy = list(self.active_connections.items())

        disconnected_users = [
            user_id
            for user_id, ws in active_connections_copy
            if ws.client_state != WebSocketState.CONNECTED
        ]
        for user_id in disconnected_users:
            await self.disconnect(user_id)

        active_connections_copy = list(self.active_connections.items())
        for user_id, websocket in active_connections_copy:
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logging.error(f"Ошибка при рассылке {user_id}: {e}")
                    await self.disconnect(user_id)


class TypingManager:
    """Менеджер печатающих пользователей."""

    def __init__(self) -> None:
        self.typing_users: Dict[str, Set[str]] = defaultdict(set)

    async def add_typing(self, chat_id: str, client_id: str,
                         manager: ConnectionManager) -> None:
        """Добавляет пользователя в список печатающих и обновляет чат."""
        if client_id not in self.typing_users[chat_id]:
            self.typing_users[chat_id].add(client_id)
            await self.broadcast_typing(chat_id, manager)

    async def remove_typing(self, chat_id: str, client_id: str,
                            manager: ConnectionManager) -> None:
        """Удаляет пользователя из списка печатающих и обновляет чат."""
        if client_id in self.typing_users.get(chat_id, set()):
            self.typing_users[chat_id].discard(client_id)
            if not self.typing_users[chat_id]:
                del self.typing_users[chat_id]
            await self.broadcast_typing(chat_id, manager)

    async def broadcast_typing(self, chat_id: str,
                               manager: ConnectionManager) -> None:
        """Отправляет обновленный список печатающих пользователей в чат."""
        message = custom_json_dumps({
            "type": "typing_users",
            "chat_id": chat_id,
            "users": list(self.typing_users.get(chat_id, []))
        })
        await manager.broadcast(message)


class DateTimeEncoder(json.JSONEncoder):
    """Кастомный JSONEncoder для обработки datetime."""

    def default(self, o: Any) -> Any:
        return o.isoformat() if isinstance(o, datetime) else super().default(o)


def custom_json_dumps(obj: Any) -> str:
    """Функция-обертка для json.dumps с DateTimeEncoder."""
    return json.dumps(obj, cls=DateTimeEncoder)


# ==============================
# Вспомогательные функции
# ==============================

async def get_ws_manager(chat_id: str) -> ConnectionManager:
    """Возвращает менеджер соединений для чата, создавая новый при необходимости."""
    return chat_managers.setdefault(chat_id, ConnectionManager())


async def get_typing_manager(chat_id: str) -> TypingManager:
    """Возвращает менеджер печатающих пользователей для чата, создавая новый при необходимости."""
    return typing_managers.setdefault(chat_id, TypingManager())


# ==============================
# Аутентификация WebSocket
# ==============================

async def websocket_jwt_required(websocket: WebSocket) -> Optional[str]:
    """Проверяет аутентификацию пользователя через JWT."""
    try:
        token = parse_qs(urlparse(str(websocket.url)).query).get(
            "token", [None])[0]
        if not token:
            return None

        authorize = AuthJWT()
        authorize._token = token

        try:
            authorize.jwt_required()
        except Exception:
            return None

        raw_jwt = authorize.get_raw_jwt()
        if await is_token_blacklisted(authorize.get_jwt_subject(), "access", raw_jwt["jti"]):
            logging.info("Токен в черном списке")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        return authorize.get_jwt_subject()
    except Exception:
        return None
