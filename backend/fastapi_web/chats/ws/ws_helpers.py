"""Вспомогательные сущности для работы с веб-сокетом приложения Чаты."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from fastapi import WebSocket, status
from fastapi_jwt_auth import AuthJWT
from starlette.websockets import WebSocketState

from auth.utils.help_functions import is_token_blacklisted

chat_managers: Dict[str, "ConnectionManager"] = {}


class ConnectionManager:
    """Менеджер соединений веб-сокета."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Принять соединение веб-сокета."""
        try:
            await websocket.accept()
            self.active_connections[user_id] = websocket
            logging.info(f"WebSocket подключён: {user_id}")
        except Exception as e:
            logging.error(f"Ошибка при подключении WebSocket {user_id}: {e}")

    async def disconnect(self, user_id: str) -> None:
        """Отключить пользователя и закрыть соединение, если оно еще активно."""
        websocket = self.active_connections.pop(user_id, None)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
                logging.info(f"WebSocket отключён: {user_id}")
            except Exception as e:
                logging.error(f"Ошибка при закрытии WebSocket {user_id}: {e}")

    async def send_personal_message(self, message: str, user_id: str) -> None:
        """Отправить сообщение конкретному пользователю."""
        websocket = self.active_connections.get(user_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения {user_id}: {e}")
                await self.disconnect(user_id)

    async def broadcast(self, message: str) -> None:
        """Разослать сообщение всем подключенным пользователям."""
        disconnected_users = []
        for user_id, websocket in self.active_connections.items():
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logging.error(f"Ошибка при рассылке {user_id}: {e}")
                    disconnected_users.append(user_id)
            else:
                disconnected_users.append(user_id)

        for user_id in disconnected_users:
            logging.info("Отключаем тех, кого нет")
            await self.disconnect(user_id)


async def get_ws_manager(chat_id: str) -> ConnectionManager:
    """Получить менеджер соединений для чата."""
    return chat_managers.setdefault(chat_id, ConnectionManager())


async def websocket_jwt_required(websocket: WebSocket) -> Optional[str]:
    """Проверка аутентификации пользователя через JWT в веб-сокете."""
    try:
        query_params = parse_qs(urlparse(str(websocket.url)).query)
        token = query_params.get("token", [None])[0]
        if not token:
            return None

        authorize = AuthJWT()
        authorize._token = token

        try:
            authorize.jwt_required()
        except Exception:
            return None

        raw_jwt = authorize.get_raw_jwt()
        jti = raw_jwt["jti"]
        current_user = authorize.get_jwt_subject()

        if await is_token_blacklisted(current_user, "access", jti):
            logging.info("Токен в черном списке")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None

        return current_user
    except Exception:
        return None


class DateTimeEncoder(json.JSONEncoder):
    """Кастомный JSONEncoder для обработки datetime."""

    def default(self, o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def custom_json_dumps(obj: Any) -> str:
    """Функция-обертка для json.dumps с DateTimeEncoder."""
    return json.dumps(obj, cls=DateTimeEncoder)
