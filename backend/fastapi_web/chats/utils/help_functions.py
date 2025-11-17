"""Вспомогательные функции приложения Чаты."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import locale
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qs, urlparse

from notifications.db.mongo.enums import NotificationChannel, Priority
from notifications.utils.help_functions import create_notifications

from .translations import TRANSLATIONS
import httpx
from bson import ObjectId
from fastapi import Depends, HTTPException, Request, WebSocket
from pymongo import DESCENDING

from chats.db.mongo.enums import ChatSource, ChatStatus, SenderRole
from chats.db.mongo.schemas import (
    ChatMessage,
    ChatReadInfo,
    ChatSession,
    Client,
    MasterClient,
)
from chats.utils.knowledge_base import BRIEF_QUESTIONS
from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from infra import settings
from knowledge.admin import BotSettingsAdmin
from knowledge.db.mongo.enums import (
    AIModelEnum,
    BotColorEnum,
    CommunicationStyleEnum,
    PersonalityTraitsEnum,
)
from knowledge.db.mongo.mapping import (
    COMMUNICATION_STYLE_DETAILS,
    FUNCTIONALITY_DETAILS,
    PERSONALITY_TRAITS_DETAILS,
)
from knowledge.db.mongo.schemas import BotSettings
from knowledge.utils.help_functions import pick_model_and_client
from telegram_bot.infra import settings as bot_settings
from users.db.mongo.enums import RoleEnum
from users.db.mongo.schemas import UserWithData

# ==============================
# БЛОК: Генерация идентификаторов
# ==============================

def short_uuid_b64() -> str:
    """UUID4 → urlsafe base64 без '='."""
    uid = uuid.uuid4()
    return base64.urlsafe_b64encode(uid.bytes).rstrip(b"=").decode()


def generate_short_id() -> str:
    """Короткий уникальный ID."""
    return short_uuid_b64()


def generate_chat_id() -> str:
    """Создаёт уникальный chat_id."""
    return f"chat-{generate_short_id()}"


# ==============================
# БЛОК: Работа с client_id
# ==============================

async def generate_client_id(
    source: Union[Request, WebSocket],
    chat_source: ChatSource = ChatSource.INTERNAL,
    external_id: Optional[str] = None,
) -> str:
    """Создаёт client_id, учитывая источник и external_id."""
    chat_source_value = chat_source.value
    try:
        chat_source_dict = json.loads(chat_source_value)
        chat_source_value = chat_source_dict.get("en", chat_source_value)
    except (json.JSONDecodeError, TypeError):
        pass

    if external_id and external_id != "anonymous":
        return f"{chat_source_value.upper()}_{external_id}"

    if not isinstance(source, (Request, WebSocket)):
        raise ValueError("Invalid source type. Must be Request or WebSocket.")

    headers = source.headers
    client_ip = headers.get("x-forwarded-for", "").split(",")[0].strip() or source.client.host
    user_agent = headers.get("user-agent", "unknown")

    if "PostmanRuntime" in user_agent:
        user_agent = "unknown"

    hash_input = f"{client_ip}-{user_agent}"
    short_hash = base64.urlsafe_b64encode(hashlib.sha256(hash_input.encode()).digest()).decode()[:12]

    return f"{chat_source_value.upper()}_{short_hash}"


async def get_client_id(
    websocket: WebSocket,
    chat_id: str,
    is_superuser: bool,
    user_id: Optional[str] = None
) -> str:
    """
    Возвращает client_id пользователя чата.
    • Telegram Mini-App → проверка подписи, формируем ID как в REST.
    • JWT-админ → user_id:base_client_id.
    • Обычный клиент → INTERNAL_<…>
    """
    # Telegram Mini-App
    qs = parse_qs(urlparse(str(websocket.url)).query)
    tg_user_id = qs.get("user_id", [None])[0]
    ts = qs.get("timestamp", [None])[0]
    tg_hash = qs.get("hash", [None])[0]

    if tg_user_id and ts and tg_hash:
        base_string = f"user_id={tg_user_id}&timestamp={ts}"
        secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
        expected_hash = hmac.new(secret_key, base_string.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected_hash, tg_hash):
            return await generate_client_id(
                websocket,
                chat_source=ChatSource.TELEGRAM_MINI_APP,
                external_id=tg_user_id
            )

    # Суперюзер с JWT
    if is_superuser or user_id:
        base_id = await generate_client_id(websocket)
        return f"{user_id}:{base_id}" if user_id else base_id

    # Обычный клиент
    return await generate_client_id(websocket)


# ==============================
# БЛОК: Работа с MasterClient
# ==============================

async def get_master_client_by_id(client_id: str) -> Optional[MasterClient]:
    """Возвращает MasterClient по client_id."""
    doc = await mongo_db.clients.find_one({"client_id": client_id})
    return MasterClient(**doc) if doc else None


def determine_language(accept_language: str) -> str:
    """Определяет язык из заголовка Accept-Language."""
    user_language = accept_language.split(",")[0].split("-")[0]
    return user_language if user_language in settings.SUPPORTED_LANGUAGES else "en"


async def get_or_create_master_client(
    source: ChatSource,
    external_id: str,
    internal_client_id: str,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> MasterClient:
    """Возвращает существующего или создаёт нового MasterClient с защитой от гонки."""
    col = mongo_db.clients
    metadata = metadata or {}
    save_external_id = external_id if external_id and external_id != "anonymous" else "anonymous"
    is_internal = source == ChatSource.INTERNAL
    is_anonymous = not external_id or external_id == "anonymous"

    lock_key = f"lock:client:create:{source.value}:{save_external_id}"
    got_lock = await redis_db.set(lock_key, "1", ex=5, nx=True)

    if user_id and len(internal_client_id.split(":")) < 2:
        internal_client_id = f"{user_id}:{internal_client_id}"

    try:
        # 1) Поищем существующего клиента
        if is_internal and is_anonymous:
            doc = await col.find_one({"client_id": internal_client_id})
        else:
            doc = await col.find_one({"source": source.value, "external_id": save_external_id})
        if doc:
            update_fields: Dict[str, Any] = {}

            if name and name != doc.get("name"):
                update_fields["name"] = name
            if avatar_url and avatar_url != doc.get("avatar_url"):
                update_fields["avatar_url"] = avatar_url
            if user_id and (not doc.get("user_id")):
                update_fields["user_id"] = user_id

            current_metadata = doc.get("metadata", {})
            merged_metadata = {**current_metadata, **metadata}
            if merged_metadata != current_metadata:
                update_fields["metadata"] = merged_metadata

            if update_fields:
                await col.update_one({"_id": doc["_id"]}, {"$set": update_fields})
                doc = await col.find_one({"_id": doc["_id"]})

            doc.pop("id", None)
            return MasterClient(**doc)

        # 2) Fallback при гонке
        if not got_lock:
            await asyncio.sleep(0.2)
            doc = await col.find_one({"client_id": internal_client_id})
            if doc:
                doc.pop("id", None)
                return MasterClient(**doc)
            raise RuntimeError("Race condition: client creation lost")

        # 3) Создаём нового
        client = MasterClient(
            client_id=internal_client_id,
            source=source,
            external_id=save_external_id,
            name=name,
            avatar_url=avatar_url,
            metadata=metadata,
            created_at=datetime.utcnow(),
            user_id=user_id,
        )
        await col.insert_one(client.dict(exclude={"id"}))
        return client

    finally:
        if got_lock:
            await redis_db.delete(lock_key)


# ==============================
# БЛОК: Сообщения / поиск последних
# ==============================

def find_last_bot_message(chat_session: ChatSession) -> Optional[ChatMessage]:
    """Возвращает последнее сообщение бота или консультанта."""
    return next(
        (m for m in reversed(chat_session.messages) if m.sender_role in {SenderRole.AI, SenderRole.CONSULTANT}),
        None,
    )


# ==============================
# БЛОК: Уведомление админ-бота
# ==============================

def format_dt_iso(value: Any) -> str:
    if isinstance(value, datetime):
        value = value.astimezone(timezone.utc).replace(microsecond=0)
        return value.isoformat() + " UTC+0"
    return str(value)


def is_client_sender(m: dict) -> bool:
    try:
        return json.loads(m.get("sender_role", "{}")).get("en") == SenderRole.CLIENT.en_value
    except (json.JSONDecodeError, AttributeError):
        return False


def get_source_label_ru(source_field: Any) -> str:
    try:
        parsed = json.loads(source_field) if isinstance(source_field, str) else source_field
        return parsed.get("ru", "—")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return "—"


def format_new_chat_html(chat_session: Dict[str, Any], *,
                         position: Tuple[int, int] = (-1, -1),
                         master_source_ru: str = "—",
                         last_message_text: str = "—",
                         admin_chat_url: str = "#") -> str:
    pos, total = position
    pos_display = f"{pos} из {total}" if pos > 0 else "не определена"

    manual_mode = "✅ Включен" if chat_session.get("manual_mode") else "❌ Выключен"
    consultant_req = "✅ Да" if chat_session.get("consultant_requested") else "❌ Нет"
    messages = chat_session.get("messages") or []

    return f"""
<b>🔔 Новый чат</b>

🆔 <b>Chat ID:</b> {chat_session.get("chat_id")}
📡 <b>Источник:</b> {master_source_ru}
🤖 <b>Ручной режим:</b> {manual_mode}
☎️ <b>Вызван консультант:</b> {consultant_req}
💬 <b>Сообщений:</b> {len(messages)}
🕒 <b>Последняя активность:</b> {format_dt_iso(chat_session.get("last_activity"))}
📊 <b>Позиция в очереди:</b> {pos_display}

<b>🗣️ Последнее сообщение клиента:</b>
{last_message_text}

🔗 <a href="{admin_chat_url}">Открыть чат</a>
""".strip()


async def send_message_to_bot(chat_id: str, chat_session: Dict[str, Any]) -> None:
    """
    Обновлённая версия:
    1) Формирует «крутую» HTML-карточку, добавляет "Вызван консультант".
    2) Создаёт 2 уведомления через create_notifications: Web (in-app) + Telegram.
    3) Реальная отправка в Telegram выполняется внутри create_notifications (для Telegram).
    """
    # if settings.HOST == "localhost":
    #     return

    # admin_chat_url = f"https://{settings.HOST}/admin/chats/chat_sessions"
    print("мы тут")

    admin_chat_url = f"https://test.com/admin/chats/chat_sessions"

    client = chat_session.get("client") or {}
    client_id = client.get("client_id") or "—"
    messages = chat_session.get("messages", [])
    last_client_message = next((m for m in reversed(messages) if is_client_sender(m) and m.get("message")), None)
    last_text = (last_client_message or {}).get("message") or "—"

    try:
        position = await get_chat_position(chat_session["chat_id"])  # (pos, total)
    except Exception:
        position = (-1, -1)

    try:
        master_client = await get_master_client_by_id(client_id) if client_id and client_id != "—" else None
        master_source_ru = get_source_label_ru(getattr(master_client, "source", None)) if master_client else "—"
    except Exception:
        master_source_ru = "—"

    html = format_new_chat_html(
        chat_session,
        position=position,
        master_source_ru=master_source_ru,
        last_message_text=last_text,
        admin_chat_url=admin_chat_url,
    )

    # создаём два уведомления; ресурс передаём английским значением из Enum
    result = await create_notifications([
        {
            "resource_en": NotificationChannel.WEB.en_value,       # "Web (in-app)"
            "kind": "chat_new",
            "priority": "high",
            "title": {"en": "New chat", "ru": "Новый чат"},
            "message": html,
            "recipient_user_id": None,  # общий админ-фид; можно подставить user_id
            "entity": {
                "entity_type": "chat",
                "entity_id": chat_session.get("chat_id"),
                "route": "/admin/chats/chat_sessions",
                "extra": {"client_id": client_id},
            },
            "link_url": admin_chat_url,
            "popup": True,
            "sound": True,
            "meta": {"badge": "new-chat"},
        },
        {
            "resource_en": NotificationChannel.TELEGRAM.en_value,  # "Telegram"
            "kind": "chat_new",
            "priority": Priority.HIGH,  # можно и строкой "high"
            "title": {"en": "New chat", "ru": "Новый чат"},
            "message": html,  # HTML
            "recipient_user_id": None,
            "entity": {
                "entity_type": "chat",
                "entity_id": chat_session.get("chat_id"),
                "route": "/admin/chats/chat_sessions",
                "extra": {"client_id": client_id},
            },
            "link_url": admin_chat_url,
            "popup": True,
            "sound": True,
            "telegram": {
                # можно явно задать, а можно оставить пустым — возьмётся bot_settings.ADMIN_CHAT_ID
                # "chat_id": chat_id,
                # "message_thread_id": 123,
            },
            "meta": {"badge": "new-chat"},
        },
    ])
    print(result)


# ─────────────────────────────────────────────────────────────────────────
# СТАРАЯ ВЕРСИЯ
# ─────────────────────────────────────────────────────────────────────────

# async def send_message_to_bot(chat_id: str, chat_session: Dict[str, Any]) -> None:
#     if settings.HOST == "localhost":
#         return

#     bot_webhook_url = "http://bot:9999/webhook/send_message"
#     admin_chat_url = f"https://{settings.HOST}/admin/chats/chat_sessions"

#     def dt_iso(value: Any) -> str:
#         if isinstance(value, datetime):
#             value = value.astimezone(timezone.utc).replace(microsecond=0)
#             return value.isoformat() + " UTC+0"
#         return str(value)

#     def is_client_sender(m: dict) -> bool:
#         try:
#             return json.loads(m.get("sender_role", "{}")).get("en") == SenderRole.CLIENT.en_value
#         except (json.JSONDecodeError, AttributeError):
#             return False

#     def get_ru_source_label(source_field: Any) -> str:
#         try:
#             parsed = json.loads(source_field) if isinstance(source_field, str) else source_field
#             return parsed.get("ru", "—")
#         except (json.JSONDecodeError, TypeError, AttributeError):
#             return "—"

#     client = chat_session.get("client") or {}
#     client_id = client.get("client_id", "❌ Неизвестен")
#     external_id = chat_session.get("external_id") or "—"
#     messages = chat_session.get("messages", [])

#     last_client_message = next((m for m in reversed(messages) if is_client_sender(m) and m.get("message")), None)
#     last_message_text = last_client_message["message"] if last_client_message else "—"

#     try:
#         position, total = await get_chat_position(chat_session["chat_id"])
#     except Exception:
#         position, total = -1, -1

#     position_display = f"{position} из {total}" if position > 0 else "не определена"

#     try:
#         master_client = await get_master_client_by_id(client_id) if client_id else None
#         master_external_id = master_client.external_id if master_client and master_client.external_id else "—"
#         master_source = get_ru_source_label(master_client.source) if master_client and master_client.source else "—"
#     except Exception:
#         master_external_id = master_source = "—"

#     message_text = f\"\"\"
# <b>🆘 Новый чат</b>

# 🆔 <b>Чат ID:</b> {chat_session["chat_id"]}
# 🔗 <b>External ID:</b> {external_id}
# 👤 <b>Клиент ID:</b> {client_id}
# 📡 <b>Источник:</b> {master_source}
# 🤖 <b>Ручной режим:</b> {"✅ Включен" if chat_session.get("manual_mode") else "❌ Выключен"}
# 💬 <b>Сообщений:</b> {len(messages)}
# 📅 <b>Создан:</b> {dt_iso(chat_session.get("created_at"))}
# 🕒 <b>Последняя активность:</b> {dt_iso(chat_session.get("last_activity"))}
# 📊 <b>Позиция в очереди:</b> {position_display}

# 🗣️ <b>Последнее сообщение клиента:</b>
# {last_message_text}

# 🔍 <a href="{admin_chat_url}">Открыть чат в админке</a>
# \"\"\".strip()

#     admin_chat_id = bot_settings.ADMIN_CHAT_ID
#     message_thread_id = None

#     if "/" in admin_chat_id:
#         parts = admin_chat_id.split("/")
#         if len(parts) >= 2:
#             admin_chat_id = parts[0]
#             message_thread_id = int(parts[1]) if parts[1] else None

#     try:
#         async with httpx.AsyncClient() as client_http:
#             payload = {
#                 "chat_id": admin_chat_id,
#                 "text": message_text,
#                 "parse_mode": "HTML",
#             }
#             if message_thread_id:
#                 payload["message_thread_id"] = message_thread_id

#             response = await client_http.post(bot_webhook_url, json=payload, timeout=10.0)
#         response.raise_for_status()
#     except httpx.HTTPStatusError as exc:
#         logging.error(f"Ошибка от бота ({exc.response.status_code}): {exc.response.text}")
#     except Exception:
#         logging.exception("Ошибка при отправке сообщения в бот")


# ==============================
# БЛОК: Работа с чатами клиента
# ==============================

async def get_all_chats_for_client(client_id: str) -> List[dict]:
    """Возвращает все чаты клиента из MongoDB."""
    return [chat async for chat in mongo_db.chats.find({"client.client_id": client_id})]


async def get_active_chats_for_client(client_id: str) -> List[Tuple[dict, int]]:
    """Список активных чатов клиента, отсортированный по created_at (DESC)."""
    all_chats = await get_all_chats_for_client(client_id)
    active_chats: List[Tuple[dict, int]] = []

    for chat in all_chats:
        redis_key = f"chat:session:{chat['chat_id']}"
        ttl = await redis_db.ttl(redis_key)
        if ttl > 0:
            active_chats.append((chat, ttl))

    active_chats.sort(key=lambda x: x[0]["created_at"], reverse=True)
    return active_chats


async def calculate_chat_status(chat_session: ChatSession, redis_key_session: str) -> ChatStatus:
    """
    Вычисляет текущий статус чата через ChatSession.compute_status(...).

    - remaining_time (TTL) читается из Redis по ключу сессии;
    - staff_ids собираются из пользователей с ролями администратора/демо-администратора/суперадмина;
    - brief_questions берутся из BRIEF_QUESTIONS.

    Возвращает ChatStatus. Его .value — i18n-объект со строками статуса.
    """
    remaining_time = max(await redis_db.ttl(redis_key_session), 0)

    staff_roles = [RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.DEMO_ADMIN]
    staff_users_cursor = mongo_db.users.find(
        {"role": {"$in": [role.value for role in staff_roles]}},
        {"_id": 1}
    )
    staff_ids = {str(user["_id"]) async for user in staff_users_cursor}
    brief_questions = BRIEF_QUESTIONS

    return chat_session.compute_status(
        ttl_value=remaining_time,
        staff_ids=staff_ids,
        brief_questions=brief_questions
    )



async def serialize_active_chat(chat_data: dict, ttl: int) -> Dict[str, Any]:
    """Готовит краткое описание активного чата (для REST-ответа)."""
    chat_session = ChatSession(**chat_data)
    redis_key = f"chat:session:{chat_session.chat_id}"
    status = await calculate_chat_status(chat_session, redis_key)

    return {
        "message": "Chat session is active.",
        "chat_id": chat_session.chat_id,
        "client_id": chat_session.client.client_id,
        "created_at": chat_session.created_at,
        "last_activity": chat_session.last_activity,
        "remaining_time": ttl,
        "status": status.value,
    }


async def get_chat_position(chat_id: str) -> tuple[int, int]:
    """Позиция чата в очереди по последнему клиентскому сообщению."""
    query = {"messages": {"$exists": True, "$ne": []}}
    all_chats = [chat async for chat in mongo_db.chats.find(query)]

    def get_updated_at(doc: dict) -> datetime:
        messages = doc.get("messages") or []
        for msg in reversed(messages):
            try:
                sender_role = msg.get("sender_role")
                if isinstance(sender_role, str):
                    sender_role = json.loads(sender_role)
                if isinstance(sender_role, dict) and sender_role.get("en") == SenderRole.CLIENT.en_value:
                    return msg.get("timestamp")
            except Exception:
                continue
        return doc.get("last_activity") or doc.get("created_at")

    all_chats.sort(key=get_updated_at, reverse=True)

    chat_ids = [chat.get("chat_id") for chat in all_chats]
    try:
        position = chat_ids.index(chat_id) + 1
    except ValueError:
        position = -1

    return position, len(chat_ids)


# ==============================
# БЛОК: Создание / восстановление сессии
# ==============================

async def resolve_chat_identity(
    request: Request,
    source: ChatSource,
    client_external_id: Optional[str],
    user_id: Optional[str],
    timestamp: Optional[str],
    hash: Optional[str],
    Authorize: Any = Depends(),  # JWT опционален
) -> Tuple[str, str]:
    """
    Определение (client_id, external_id):
    1) Telegram Mini App → проверка подписи.
    2) JWT → пытаемся найти MasterClient по user_id.
    3) Иначе — external_id || 'anonymous'.
    """
    from chats.integrations.telegram.telegram_bot import verify_telegram_hash

    if source == ChatSource.TELEGRAM_MINI_APP:
        if not (user_id and timestamp and hash):
            raise HTTPException(400, "Telegram auth params missing")
        if not verify_telegram_hash(user_id, timestamp, hash, settings.TELEGRAM_BOT_TOKEN):
            raise HTTPException(403, "Invalid Telegram signature")
        external_id = user_id
    else:
        user_doc = None
        user_id = None
        try:
            user_id = Authorize.get_jwt_subject()
            user_doc = await mongo_db["users"].find_one({"_id": ObjectId(user_id)})
        except Exception:
            user_doc = None

        if user_doc and user_id:
            master = await mongo_db.master_clients.find_one({"user_id": user_id})
            if master:
                return master["client_id"], master.get("external_id") or ""
            external_id = "anonymous" if source == ChatSource.INTERNAL else user_id
        else:
            external_id = "anonymous" if source == ChatSource.INTERNAL else user_id

    client_id = await generate_client_id(request, chat_source=source, external_id=external_id)
    return client_id, external_id


async def handle_chat_creation(
    mode: Optional[str] = None,
    chat_source: ChatSource = ChatSource.INTERNAL,
    chat_external_id: Optional[str] = None,
    client_external_id: Optional[str] = None,
    company_name: Optional[str] = None,
    bot_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
    token_user_id: Optional[str] = None,
) -> dict:
    """Создаёт или получает чат-сессию (Redis + MongoDB)."""
    metadata = metadata or {}

    if not client_external_id:
        client_external_id = "anonymous"

    client_id = await generate_client_id(
        request,
        chat_source=chat_source,
        external_id=client_external_id
    )

    master_client = await get_or_create_master_client(
        source=chat_source,
        external_id=client_external_id,
        internal_client_id=client_id,
        name=metadata.get("name"),
        avatar_url=metadata.get("avatar_url"),
        metadata=metadata,
        user_id=token_user_id,
    )

    client_id = master_client.client_id
    active_chats = await get_active_chats_for_client(client_id)

    if mode != "new" and active_chats:
        chat_data, ttl = active_chats[0]
        return await serialize_active_chat(chat_data, ttl)

    if chat_source not in [ChatSource.INTERNAL, ChatSource.TELEGRAM_MINI_APP]:
        if chat_data := await mongo_db.chats.find_one({"client.client_id": client_id}):
            chat_session = ChatSession(**chat_data)
            await redis_db.set(
                f"chat:session:{chat_session.chat_id}",
                "1",
                ex=int(settings.CHAT_TIMEOUT.total_seconds())
            )
            return {
                "message": "Chat session restored from MongoDB.",
                "chat_id": chat_session.chat_id,
                "client_id": client_id,
                "status": chat_session.compute_status(settings.CHAT_TIMEOUT.total_seconds()).value,
            }

    chat = ChatSession(
        chat_id=generate_chat_id(),
        client=Client(client_id=client_id, source=chat_source),
        bot_id=bot_id,
        company_name=company_name,
        external_id=chat_external_id if chat_source != ChatSource.INTERNAL else client_external_id,
        last_activity=datetime.utcnow()
    )

    await mongo_db.chats.insert_one(chat.dict())
    await redis_db.set(
        f"chat:session:{chat.chat_id}",
        "1",
        ex=int(settings.CHAT_TIMEOUT.total_seconds())
    )

    status = await calculate_chat_status(chat, f"chat:session:{chat.chat_id}")

    return {
        "message": "New chat session created.",
        "chat_id": chat.chat_id,
        "client_id": client_id,
        "status": status.value,
    }


# ==============================
# БЛОК: Валидация/утилиты идентификаторов
# ==============================

def is_valid_object_id(oid: str) -> bool:
    """Проверяет строку на валидный ObjectId."""
    if not isinstance(oid, str):
        return False
    try:
        ObjectId(oid)
        return True
    except Exception:
        return False


# ==============================
# БЛОК: Данные отправителей (мастер-клиент, пользователь)
# ==============================

async def build_sender_data_map(
    messages: list[dict],
    extra_client_id: Optional[str] = None
) -> dict[str, dict[str, Any]]:
    """
    Собирает карту данных отправителей (мастер-клиент + user_data + patient info),
    включая клиента чата даже без сообщений.
    """
    sender_ids = {m.get("sender_id") for m in messages if m.get("sender_id")}
    if extra_client_id:
        sender_ids.add(extra_client_id)
    sender_ids.discard(None)

    if not sender_ids:
        return {}

    # 1) Master clients
    master_docs = await mongo_db.clients.find({"client_id": {"$in": list(sender_ids)}}).to_list(None)
    masters = {d["client_id"]: MasterClient(**d) for d in master_docs}

    # 2) Users
    valid_user_ids = [ObjectId(m.user_id) for m in masters.values() if m.user_id and is_valid_object_id(m.user_id)]
    user_docs = await mongo_db.users.find({"_id": {"$in": valid_user_ids}}).to_list(None)
    users = {str(u["_id"]): u for u in user_docs}

    # 3) Patient main & contact info
    user_ids_str = [str(uid) for uid in valid_user_ids]
    main_infos = await mongo_db["patients_main_info"].find({"user_id": {"$in": user_ids_str}}).to_list(None)
    contact_infos = await mongo_db["patients_contact_info"].find({"user_id": {"$in": user_ids_str}}).to_list(None)
    main_info_map = {doc["user_id"]: doc for doc in main_infos}
    contact_info_map = {doc["user_id"]: doc for doc in contact_infos}

    # 4) Сбор итоговых данных
    sender_data_map: dict[str, dict[str, Any]] = {}

    for client_id, master in masters.items():
        data: dict[str, Any] = {
            "name": master.name,
            "avatar_url": master.avatar_url,
            "source": master.source.en_value,
            "external_id": master.external_id,
            "metadata": dict(master.metadata or {}),
            "client_id": master.client_id,
        }

        if master.user_id and is_valid_object_id(master.user_id):
            user_doc = users.get(master.user_id)
            user_name = None
            if user_doc:
                user_doc["_id"] = str(user_doc["_id"])
                user_data_obj = UserWithData(**user_doc, data={"user_id": str(user_doc["_id"])})
                user_data = await user_data_obj.get_full_user_data()
                data["user"] = user_data
                user_name = user_doc.get("full_name")

            metadata = data.setdefault("metadata", {})

            # main_info (чистый сабсет)
            main_info_raw = main_info_map.get(master.user_id, {})
            main_info = {k: v for k, v in main_info_raw.items() if k in ["first_name", "patronymic", "last_name", "avatar"]}
            contact_info_raw = contact_info_map.get(master.user_id, {})
            contact_info = {k: v for k, v in contact_info_raw.items()}  # <-- фикс: берём из contact_info_map

            main_info_name = None

            if main_info:
                metadata["main_info"] = main_info
                # fallback name
                if not data.get("name"):
                    name_parts = [
                        main_info.get("first_name"),
                        main_info.get("patronymic"),
                        main_info.get("last_name")
                    ]
                    main_info_name = " ".join(filter(None, name_parts)).strip() or None

                # fallback avatar
                avatar = main_info.get("avatar", {})
                if not data["avatar_url"] and avatar and avatar.get("url"):
                    data["avatar_url"] = avatar["url"]

            if contact_info:
                metadata["contact_info"] = contact_info

            data["name"] = main_info_name or user_name

        sender_data_map[client_id] = data

    return sender_data_map


# ==============================
# БЛОК: Read-state
# ==============================

async def update_read_state_for_client(
    chat_id: str,
    client_id: str,
    user_id: Optional[str],
    last_read_msg: str
) -> bool:
    """Обновляет read_state для клиента в чате, если это необходимо."""
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        return False

    read_state_raw = chat_data.get("read_state", [])
    read_state: List[ChatReadInfo] = [
        ChatReadInfo(**ri) if isinstance(ri, dict) else ri
        for ri in read_state_raw
    ]

    now = datetime.utcnow()
    modified = False

    for ri in read_state:
        if ri.client_id == client_id:
            if ri.last_read_msg != last_read_msg:
                ri.last_read_msg = last_read_msg
                ri.last_read_at = now
                modified = True
            break
    else:
        read_state.append(ChatReadInfo(
            client_id=client_id,
            user_id=user_id,
            last_read_msg=last_read_msg,
            last_read_at=now
        ))
        modified = True

    if modified:
        await mongo_db.chats.update_one(
            {"chat_id": chat_id},
            {"$set": {"read_state": [ri.model_dump(mode="python") for ri in read_state]}}
        )

    return modified


# ==============================
# БЛОК: Контекст для ИИ-помощника
# ==============================

locale.setlocale(locale.LC_TIME, "C")


# ==============================
# БЛОК: Форматирование истории / дата-время
# ==============================

def format_chat_history_from_models(chat_history: List[ChatMessage]) -> str:
    """Форматирует историю сообщений для промпта."""
    return "\n".join(
        f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}] "
        f"[{msg.sender_role.name}] {msg.message}"
        for msg in chat_history
    )


def get_current_datetime() -> str:
    """Возвращает текущее время в виде 'Monday, 08-02-2025 14:30:00 UTC'."""
    now = datetime.now(timezone.utc)
    return now.strftime("%A, %d-%m-%Y %H:%M:%S UTC%z").replace("UTC+0000", "UTC")


# ==============================
# БЛОК: Погода
# ==============================

async def fetch_weather(params: Dict[str, Any], redis_key: str) -> Dict[str, Any]:
    """Запрос в OpenWeather с кэшированием (forecast)."""
    cached = await redis_db.get(redis_key)
    if cached:
        return json.loads(cached)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://api.openweathermap.org/data/2.5/forecast", params=params)
            if resp.status_code != 200:
                return {"error": "Weather is not available"}
            data = resp.json()
            forecast = parse_weather_data(data)
            await redis_db.set(
                redis_key,
                json.dumps(forecast),
                ex=int(settings.WEATHER_CACHE_LIFETIME.total_seconds())
            )
            return forecast
        except Exception as e:
            return {"error": f"Weather fetching error: {e}"}


async def get_weather_for_region(region_name: str) -> Dict[str, Any]:
    """Прогноз по названию региона."""
    key = f"weather:{region_name.lower()}"
    params = {"q": region_name, "appid": settings.WEATHER_API_KEY, "units": "metric", "lang": "ru"}
    return await fetch_weather(params, key)


async def get_coordinates(address: str) -> Dict[str, float]:
    """Координаты для адреса."""
    params = {"q": address, "limit": 1, "appid": settings.WEATHER_API_KEY}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://api.openweathermap.org/geo/1.0/direct", params=params)
            if resp.status_code != 200 or not resp.json():
                return {}
            data = resp.json()[0]
            return {"lat": data["lat"], "lon": data["lon"]}
        except Exception as e:
            return {"error": f"Coordinates error: {e}"}


async def get_weather_for_location(lat: float, lon: float) -> Dict[str, Any]:
    """Прогноз по координатам."""
    key = f"weather:{lat},{lon}"
    params = {"lat": lat, "lon": lon, "appid": settings.WEATHER_API_KEY, "units": "metric", "lang": "ru"}
    return await fetch_weather(params, key)


async def get_weather_by_address(address: str) -> Dict[str, Any]:
    """Прогноз погоды по адресу."""
    coords = await get_coordinates(address)
    if not coords:
        return {"error": "Failed to get coordinates"}
    return await get_weather_for_location(coords["lat"], coords["lon"])


def parse_weather_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Группирует прогноз по датам (min/max/desc)."""
    forecast: Dict[str, Any] = {}
    for entry in data["list"]:
        date_key = entry["dt_txt"].split(" ")[0]
        temp = entry["main"]["temp"]
        desc = entry["weather"][0]["description"].capitalize()
        day = forecast.setdefault(date_key, {"temp_min": temp, "temp_max": temp, "description": desc})
        day["temp_min"] = min(day["temp_min"], temp)
        day["temp_max"] = max(day["temp_max"], temp)
    return {"forecast": forecast}


# ==============================
# БЛОК: Контекст бота
# ==============================
def get_default_bot_settings(app_name: str) -> BotSettings:
    """Дефолтные настройки бота для указанного app_name."""
    return BotSettings(
        app_name=app_name,
        project_name="Default Project",
        employee_name="Default Employee",
        mention_name=False,
        avatar=None,
        bot_color=BotColorEnum.RED,
        communication_tone=CommunicationStyleEnum.CASUAL,
        personality_traits=PersonalityTraitsEnum.BALANCED,
        additional_instructions="",
        role="Default Role",
        target_action=[],
        core_principles=None,
        special_instructions=[],
        forbidden_topics=[],
        greeting={
            "en": "Hello! How can I assist you?",
            "pl": "Cześć! W czym mogę pomóc?",
            "uk": "Вітаю! Чим я можу допомогти?",
            "ru": "Здравствуйте! Чем могу помочь?",
            "ka": "გამარჯობა! რით შემიძლია დაგეხმაროთ?",
        },
        error_message={
            "en": "Please wait for a consultant.",
            "pl": "Proszę poczekać на konsultанта.",
            "uk": "Будь ласка, зачекайте на консультанта.",
            "ru": "Пожалуйста, подождите, консультант скоро ответит.",
            "ka": "გთხოვთ, დაელოდოთ კონსულტანტს.",
        },
        farewell_message={
            "en": "Goodbye! Feel free to ask anything else.",
            "pl": "Do widzenia! Jeśli masz pytania, śmiało pytaj.",
            "uk": "До побачення! Звертайтесь, якщо виникнуть питання.",
            "ru": "До свидания! Если вам что-то понадобится, обращайтесь.",
            "ka": "ნახვამდис! თავისუფლად შეგიძლიათ კიდევ რაღაც მკითხოთ.",
        },
        fallback_ai_error_message={
            "en": "Unfortunately, I'm having trouble generating a response right now. Please try again later.",
            "pl": "Niestety, mam teraz problem z wygenerowaniem odpowiedzi. Spróbuj ponownie później.",
            "uk": "На жаль, зараз виникла проблема з генерацією відповіді. Спробуйте пізніше.",
            "ru": "К сожалению, я не могу сейчас сгенерировать ответ. Пожалуйста, попробуйте позже.",
            "ka": "სამწუხაროდ, ახლა ვერ ვქმნი პასუხს. გთხოვთ, სცადეთ მოგვიანებით.",
        },
        ai_model=AIModelEnum.GPT_4_O,
        created_at=datetime.utcnow(),
        is_active=False,
    )


async def get_bot_context(app_name: Optional[str] = None) -> Dict[str, Any]:
    """Загружает настройки бота по app_name, либо активного/последнего."""
    app_name = app_name or settings.APP_NAME

    data = await mongo_db.bot_settings.find_one({"is_active": True})

    if not data:
        if app_name.startswith("demo_"):
            bot_settings_obj = get_default_bot_settings(app_name)
        else:
            data = await mongo_db.bot_settings.find_one({"is_active": True})
            if not data:
                data = await mongo_db.bot_settings.find_one({}, sort=[("_id", DESCENDING)])
            bot_settings_obj = BotSettings(**data) if data else get_default_bot_settings(app_name)
    else:
        bot_settings_obj = BotSettings(**data)

    return build_bot_settings_context(bot_settings_obj, BotSettingsAdmin(mongo_db))


def build_bot_settings_context(
    settings_model: BotSettings,
    admin_model: BotSettingsAdmin
) -> Dict[str, Any]:
    """Формирует словарь настроек бота из модели BotSettings."""
    bot_config = {
        "ai_model": settings_model.ai_model.value if settings_model.ai_model else "gpt-4o",
        "temperature": PERSONALITY_TRAITS_DETAILS.get(settings_model.personality_traits, 0.1),
        "welcome_message": settings_model.greeting,
        "redirect_message": settings_model.error_message,
        "farewell_message": settings_model.farewell_message,
        "fallback_ai_error_message": settings_model.fallback_ai_error_message,
        "app_name": settings_model.project_name,
        "app_description": settings_model.additional_instructions,
        "forbidden_topics": settings_model.forbidden_topics,
        "avatar": settings_model.avatar.url if settings_model.avatar else None,
        "bot_color": settings_model.bot_color.value,
        "postprocessing_instruction": settings_model.postprocessing_instruction or (
            "Do not invent facts. Do not generate placeholder links. "
            "Do not provide addresses, phones, or prices unless clearly present in the snippets or chat history."
        ),
        "language_instruction": settings_model.language_instruction or (
            "Always respond in the language of the user's latest messages. "
            "If it is unclear, use the language of the recent chat context or interface."
        ),
    }
    bot_config["prompt_text"] = generate_prompt_text(settings_model, admin_model)
    return bot_config


# ==============================
# БЛОК: Генерация промпта
# ==============================

def generate_prompt_text(
    settings_model: BotSettings,
    admin_model: BotSettingsAdmin
) -> str:
    """Создаёт текст system-prompt из настроек."""
    excluded = {"greeting", "error_message", "farewell_message", "ai_model",
                "personality_traits", "created_at", "avatar"}

    all_fields = set(admin_model.detail_fields) | set(admin_model.list_display)
    lines = ["You are AI Assistant. REMEMBER!:",
             "SYSTEM PROMPT:", "=" * 50]

    for field in all_fields:
        if field in excluded:
            continue
        field_title = admin_model.field_titles.get(field, {}).get("en", field)
        raw_value = getattr(settings_model, field, None)
        if not raw_value:
            continue
        processed = extract_value(raw_value)
        formatted = format_value(field, processed)
        if field == "employee_name":
            field_title = "Your (Bot) name (Not user name!!! Don`t be confused with the username of the user being conversating)"
        lines += [f"{field_title.upper()}: {formatted}", "-" * 10]

    lines += ["IMPORTANT: FOLLOW ALL RULES STRICTLY!", "=" * 50]
    return "\n".join(lines)


def extract_value(value: Any) -> Any:
    """Преобразует значение для промпта (enum/JSON/список/строка)."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            value = parsed.get("en", value)
        except (json.JSONDecodeError, TypeError):
            pass
        if value in COMMUNICATION_STYLE_DETAILS:
            return f"\n{value}:\n{COMMUNICATION_STYLE_DETAILS[value]}"
        if value in FUNCTIONALITY_DETAILS:
            return f"\n{value}:\n{FUNCTIONALITY_DETAILS[value]}"
        return value

    if isinstance(value, dict):
        return value.get("en", str(value))

    if isinstance(value, list):
        return [extract_value(item) for item in value]

    return value


def format_value(field_name: str, value: Any) -> str:
    """Форматирует значение для промпта в строку."""
    if isinstance(value, list):
        return ", ".join(str(item.value if hasattr(item, "value") else item) for item in value)
    if hasattr(value, "value"):
        return value.value
    return str(value)


# ==============================
# БЛОК: Текстовые утилиты (чистка/разбиение/переводы)
# ==============================

def split_text_into_chunks(text: str, max_length: int = 998) -> List[str]:
    """Делит текст на части по предложениям, не обрывая числовые списки и не теряя хвост."""
    pattern = re.compile(
        r"""
        (                               # одна законченная фраза
            (?: (?!\d+\.\s) .*? )       # не начинать с '1. '
            [.!?…:;]+                   # конечный знак
            [)\]"»”’\s\w]*              # закрывающие символы/пробелы
        )
        (?=\s+|$)
        """,
        re.VERBOSE | re.DOTALL,
    )

    matches = pattern.findall(text)
    unmatched_tail = text[len("".join(matches)):]
    if unmatched_tail.strip():
        matches.append(unmatched_tail)

    chunks, chunk = [], ""
    for sentence in matches:
        if len(chunk) + len(sentence) <= max_length:
            chunk += sentence
        else:
            if chunk.strip():
                chunks.append(chunk.rstrip())
            chunk = sentence
    if chunk.strip():
        chunks.append(chunk.rstrip())

    return chunks


def clean_markdown(text: str) -> str:
    """Удаляет Markdown; `[label](url)` → `label (url)` если label≠url."""
    if not text:
        return ""

    def link_replacer(match: re.Match) -> str:
        label, url = match.group(1).strip(), match.group(2).strip()
        if not url.startswith("http"):
            return label
        if not label or label == url:
            return url
        return f"{label} ({url})"

    text = re.sub(r"\[\s*([^\]]*?)\s*\]\s*\(\s*(https?:\/\/[^\s)]+)\s*\)", link_replacer, text)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*\*([^*]+)\*\*\*|___([^_]+)___", r"\1\2", text)
    text = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", r"\1\2", text)
    text = re.sub(r"\*([^*]+)\*|_([^_]+)_", r"\1\2", text)
    text = re.sub(r"~+([^~]+?)~+", r"\1", text)
    text = re.sub(r"^\s*[-*+•]\s+|\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # Если встречается "метка (url)" и метка == домен урла — оставить только url.
    text = re.sub(
        r"(?<!\w)([a-zA-Z0-9\-._~:/?#@!$&'()*+,;=]{5,})\s*\(\s*(https?://[^\s)]+)\s*\)",
        lambda m: m.group(2)
        if m.group(1).rstrip("/").lower() in m.group(2).rstrip("/").lower()
        else m.group(0),
        text,
    )

    return text.strip()

# ==============================
# БЛОК: Перевод
# ==============================

def get_translation(category: str, key: str, language: str, **kwargs) -> str:
    """Возвращает перевод из TRANSLATIONS с подстановкой переменных (fallback на en)."""
    template = (
        TRANSLATIONS.get(category, {})
        .get(key, {})
        .get(language, TRANSLATIONS.get(category, {}).get(key, {}).get("en", ""))
    )
    return template.format(**kwargs) if isinstance(template, str) else template

# ==============================
# БЛОК: Интеграция с моделями ИИ
# ==============================

def extract_json_from_response(resp: dict) -> dict[str, Any]:
    """Извлекает первый JSON-блок из ответа модели (fallback на пустой dict)."""
    try:
        text = resp["candidates"][0]["content"]["parts"][0]["text"]
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(match.group(0)) if match else {}
    except Exception:
        return {}


async def chat_generate_any(
    model_name: str,
    messages: list[dict],
    temperature: float = 0.1,
    system_instruction: str | None = None
) -> dict:
    """Единый вызов генерации для OpenAI и Gemini (асинхронный)."""
    client, real_model = pick_model_and_client(model_name)

    if real_model.startswith("gpt"):
        response = await client.chat.completions.create(
            model=real_model,
            messages=messages,
            temperature=temperature
        )
        return {
            "candidates": [{
                "content": {"parts": [{"text": response.choices[0].message.content.strip()}]}
            }]
        }

    if real_model.startswith("gemini"):
        response = await client.chat_generate(
            model=real_model,
            messages=messages,
            temperature=temperature,
            system_instruction=system_instruction
        )
        return response

    raise ValueError(f"Unsupported model: {real_model}")

# ==============================
# БЛОК: Остальное
# ==============================

def safe_float(value: Optional[Union[str, bytes]]) -> float:
    """Безопасно преобразует значение к float (для flood-control и т.п.)."""
    try:
        return float(value) if value else 0.0
    except (ValueError, TypeError):
        return 0.0
