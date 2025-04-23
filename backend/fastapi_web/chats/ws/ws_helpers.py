"""Вспомогательные сущности для работы с веб-сокетом приложения Чаты."""
import json
import logging
from asyncio import Lock, Task
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
        old_ws = self.active_connections.get(user_id)

        # ⚠️ предотвращаем бесконечную перезапись
        if old_ws and old_ws is websocket:
            logging.info(f"ℹ️ WebSocket уже зарегистрирован: {user_id} | ws id={id(websocket)}")
            return

        # # 🔁 отключаем старое соединение, если оно ещё активно
        # if old_ws and old_ws.client_state == WebSocketState.CONNECTED:
        #     logging.info(f"🔁 Заменяем старое соединение для {user_id} (ws id={id(old_ws)})")
        #     try:
        #         await old_ws.close()
        #     except Exception as e:
        #         logging.warning(f"⚠️ Ошибка при закрытии старого WebSocket {user_id}: {e}")

        # ✅ Подключение нового WebSocket
        if websocket.client_state == WebSocketState.CONNECTING:
            try:
                await websocket.accept()
            except Exception as e:
                logging.error(f"❌ Ошибка при accept WebSocket {user_id}: {e}")
                return
        else:
            logging.warning(f"⚠️ WebSocket {user_id} не в состоянии CONNECTING — не вызываем accept()")
            return

        self.active_connections[user_id] = websocket
        logging.info(f"✅ WebSocket подключён: {user_id} | ws id={id(websocket)}")


    async def disconnect(self, user_id: str) -> None:
        websocket = self.active_connections.pop(user_id, None)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
                logging.info(f"🔌 WebSocket отключён: {user_id}")
            except Exception as e:
                logging.error(f"❌ Ошибка при закрытии WebSocket {user_id}: {e}")
        else:
            logging.info(f"ℹ️ Нет активного соединения для {user_id}, ничего не отключено.")

    # async def _safe_send(self, websocket: WebSocket, user_id: str, message: str) -> None:
    #     try:
    #         await websocket.send_text(message)
    #     except RuntimeError as e:
    #         if "Cannot call" in str(e):
    #             logging.warning(f"⚠️ Попытка отправки в закрытый сокет {user_id} (ws id={id(websocket)})")
    #         else:
    #             logging.error(f"❌ Ошибка при отправке сообщения {user_id}: {e}")
    #         await self.disconnect(user_id)
    #     except Exception as e:
    #         logging.error(f"❌ Неизвестная ошибка при отправке {user_id}: {e}")
    #         await self.disconnect(user_id)

    async def _safe_send(self, websocket: WebSocket, user_id: str, message: str) -> None:
        try:
            await websocket.send_text(message)
        except RuntimeError as e:
            if "call 'accept' first" in str(e) or "not connected" in str(e).lower():
                logging.warning(f"⚠️ [send] Висячее соединение: user_id={user_id} | ws id={id(websocket)} | manager id={id(self)}. Закрываем.")
                try:
                    await websocket.close()
                except Exception as close_err:
                    logging.warning(f"⚠️ [send] Ошибка при закрытии висячего WebSocket: {close_err}")
                await self.disconnect(user_id)  # Убираем из активных
            else:
                logging.error(f"❌ [send] Ошибка при отправке данных: {e}")
                await self.disconnect(user_id)
        except Exception as e:
            logging.error(f"❌ [send] Неизвестная ошибка при отправке {user_id}: {e}")
            await self.disconnect(user_id)


    async def send_personal_message(self, message: str, user_id: str) -> None:
        websocket = self.active_connections.get(user_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            await self._safe_send(websocket, user_id, message)
        else:
            logging.warning(f"⚠️ Соединение не активно или не найдено для {user_id}, сообщение не отправлено.")

    async def broadcast(self, message: str) -> None:
        for user_id, websocket in list(self.active_connections.items()):
            if websocket.client_state == WebSocketState.CONNECTED:
                await self._safe_send(websocket, user_id, message)
            else:
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


class GptTaskManager:
    """Менеджер задач GPT и блокировок для последовательной обработки."""

    def __init__(self) -> None:
        self.gpt_tasks: Dict[str, Task] = {}
        self.gpt_locks: Dict[str, Lock] = {}

    def get_lock(self, chat_id: str) -> Lock:
        """Возвращает asyncio.Lock для чата (создаёт, если не существует)."""
        if chat_id not in self.gpt_locks:
            self.gpt_locks[chat_id] = Lock()
        return self.gpt_locks[chat_id]

    def cancel_task(self, chat_id: str) -> None:
        """Отменяет текущую GPT-задачу, если она ещё не завершена."""
        task = self.gpt_tasks.get(chat_id)
        if task and not task.done():
            task.cancel()

    def set_task(self, chat_id: str, task: Task) -> None:
        """Устанавливает новую GPT-задачу для чата."""
        self.gpt_tasks[chat_id] = task

    def get_task(self, chat_id: str) -> Optional[Task]:
        """Возвращает текущую GPT-задачу, если она есть."""
        return self.gpt_tasks.get(chat_id)


gpt_task_manager = GptTaskManager()


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
