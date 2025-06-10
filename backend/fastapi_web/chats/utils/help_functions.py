"""Вспомогательные функции приложения Чаты."""
import asyncio
import base64
import hashlib
import hmac
import json
import locale
import logging
import re
from urllib.parse import parse_qs, urlparse
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from bson import ObjectId
import httpx
from fastapi import HTTPException, Request, WebSocket
from pymongo import DESCENDING
from fastapi import Request, HTTPException, Depends

from fastapi_jwt_auth import AuthJWT, exceptions as jwt_exc


from chats.utils.knowledge_base import BRIEF_QUESTIONS
from users.db.mongo.enums import RoleEnum
from users.db.mongo.schemas import UserWithData
from telegram_bot.infra import settings as bot_settings

from chats.db.mongo.enums import ChatSource, ChatStatus, SenderRole
from chats.db.mongo.schemas import (ChatMessage, ChatReadInfo, ChatSession,
                                    Client, MasterClient)
from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from infra import settings
from knowledge.admin import BotSettingsAdmin
from knowledge.db.mongo.enums import (AIModelEnum, BotColorEnum,
                                      CommunicationStyleEnum,
                                      PersonalityTraitsEnum)
from knowledge.db.mongo.mapping import (COMMUNICATION_STYLE_DETAILS,
                                        FUNCTIONALITY_DETAILS,
                                        PERSONALITY_TRAITS_DETAILS)
from knowledge.db.mongo.schemas import BotSettings
from knowledge.utils.help_functions import pick_model_and_client

# ==============================
# БЛОК: Генерация идентификаторов
# ==============================


def short_uuid_b64() -> str:
    """Возвращает UUID4, закодированный в URL‑безопасный base64 без знаков «=»."""
    uid = uuid.uuid4()
    return base64.urlsafe_b64encode(uid.bytes).rstrip(b"=").decode()


def generate_short_id() -> str:
    """Генерирует короткий уникальный ID."""
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
    client_ip = headers.get("x-forwarded-for",
                            "").split(",")[0].strip() or source.client.host
    user_agent = headers.get("user-agent", "unknown")

    if "PostmanRuntime" in user_agent:
        user_agent = "unknown"

    hash_input = f"{client_ip}-{user_agent}"
    short_hash = base64.urlsafe_b64encode(
        hashlib.sha256(hash_input.encode()).digest()).decode()[:12]

    return f"{chat_source_value.upper()}_{short_hash}"


# async def get_client_id(
#     websocket: WebSocket,
#     chat_id: str,
#     is_superuser: bool,
#     user_id: Optional[str] = None
# ) -> str:
#     """Возвращает client_id для пользователя чата."""
#     chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
#     if not chat_data:
#         raise ValueError("Chat session not found")

#     chat_session = ChatSession(**chat_data)

#     if not is_superuser:
#         return await generate_client_id(websocket)

#     if not chat_session.client:
#         return ""

#     base_client_id = await generate_client_id(websocket)

#     if user_id:
#         return f"{user_id}:{base_client_id}"

#     return base_client_id


async def get_client_id(
    websocket: WebSocket,
    chat_id: str,
    is_superuser: bool,
    user_id: Optional[str] = None
) -> str:
    """
    Возвращает client_id для пользователя чата.
    • Telegram Mini-App → проверяем подпись и делаем такой же client_id, как при REST.
    • JWT-админ → user_id:base_client_id.
    • Обычный клиент → INTERNAL_<…>
    """

    # ---------- 1. Telegram Mini-App ----------
    qs = parse_qs(urlparse(str(websocket.url)).query)
    tg_user_id = qs.get("user_id", [None])[0]
    ts          = qs.get("timestamp", [None])[0]
    tg_hash     = qs.get("hash", [None])[0]

    if tg_user_id and ts and tg_hash:
        base_string = f"user_id={tg_user_id}&timestamp={ts}"
        secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
        expected_hash = hmac.new(secret_key, base_string.encode(), hashlib.sha256).hexdigest()
        result = hmac.compare_digest(expected_hash, tg_hash)
        if result:
            # генерируем ID в том же формате, что и /get_chat
            return await generate_client_id(
                websocket,
                chat_source=ChatSource.TELEGRAM_MINI_APP,
                external_id=tg_user_id
            )

    # ---------- 2. Суперюзер с JWT ----------
    if is_superuser or user_id:
        base_id = await generate_client_id(websocket)
        return f"{user_id}:{base_id}" if user_id else base_id

    # ---------- 3. Обычный клиент ----------
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


# async def get_or_create_master_client(
#     source: ChatSource,
#     external_id: str,
#     internal_client_id: str,
#     name: Optional[str] = None,
#     avatar_url: Optional[str] = None,
#     metadata: Optional[Dict[str, Any]] = None,
#     user_id: Optional[str] = None,
# ) -> MasterClient:
#     """Возвращает существующего или создаёт нового MasterClient."""
#     col = mongo_db.clients

#     is_internal = source == ChatSource.INTERNAL
#     is_anonymous = not external_id or external_id == "anonymous"

#     if is_internal and is_anonymous:
#         doc = await col.find_one({"client_id": internal_client_id})
#     else:
#         doc = await col.find_one({"source": source.value, "external_id": external_id})

#     if doc:
#         update_fields: Dict[str, Any] = {}

#         if name and name != doc.get("name"):
#             update_fields["name"] = name
#         if avatar_url and avatar_url != doc.get("avatar_url"):
#             update_fields["avatar_url"] = avatar_url

#         if metadata:
#             current_metadata = doc.get("metadata", {})
#             merged_metadata = {**current_metadata, **metadata}
#             if merged_metadata != current_metadata:
#                 update_fields["metadata"] = merged_metadata

#         if user_id and user_id != doc.get("user_id"):
#             update_fields["user_id"] = user_id

#         if update_fields:
#             await col.update_one({"_id": doc["_id"]}, {"$set": update_fields})
#             doc = await col.find_one({"_id": doc["_id"]})

#         doc.pop("id", None)
#         return MasterClient(**doc)

#     safe_meta: Dict[str, Any] = metadata or {}

#     save_external_id = external_id if external_id and external_id != "anonymous" else "anonymous"

#     client = MasterClient(
#         client_id=internal_client_id,
#         source=source,
#         external_id=save_external_id,
#         name=name,
#         avatar_url=avatar_url,
#         metadata=safe_meta,
#         created_at=datetime.utcnow(),
#         user_id=user_id
#     )

#     await col.insert_one(client.dict(exclude={"id"}))
#     return client


# async def get_or_create_master_client(
#     source: ChatSource,
#     external_id: str,
#     internal_client_id: str,
#     name: Optional[str] = None,
#     avatar_url: Optional[str] = None,
#     metadata: Optional[Dict[str, Any]] = None,
#     user_id: Optional[str] = None,
# ) -> MasterClient:
#     """Возвращает существующего или создаёт нового MasterClient с защитой от гонки."""
#     col = mongo_db.clients
#     metadata = metadata or {}
#     save_external_id = external_id if external_id and external_id != "anonymous" else "anonymous"
#     is_internal = source == ChatSource.INTERNAL
#     is_anonymous = not external_id or external_id == "anonymous"

#     # 🔐 Redis-блокировка от гонки
#     lock_key = f"lock:client:create:{source.value}:{save_external_id}"
#     got_lock = await redis_db.set(lock_key, "1", ex=5, nx=True)

#     try:
#         if is_internal and is_anonymous:
#             doc = await col.find_one({"client_id": internal_client_id})
#         else:
#             doc = await col.find_one({"source": source.value, "external_id": save_external_id})

#         if doc:
#             update_fields: Dict[str, Any] = {}

#             if name and name != doc.get("name"):
#                 update_fields["name"] = name
#             if avatar_url and avatar_url != doc.get("avatar_url"):
#                 update_fields["avatar_url"] = avatar_url
#             if user_id and user_id != doc.get("user_id"):
#                 update_fields["user_id"] = user_id

#             current_metadata = doc.get("metadata", {})
#             merged_metadata = {**current_metadata, **metadata}
#             if merged_metadata != current_metadata:
#                 update_fields["metadata"] = merged_metadata

#             if update_fields:
#                 await col.update_one({"_id": doc["_id"]}, {"$set": update_fields})
#                 doc = await col.find_one({"_id": doc["_id"]})

#             doc.pop("id", None)
#             return MasterClient(**doc)

#         # ⏱ fallback: если гонка, ждём и пытаемся найти
#         if not got_lock:
#             await asyncio.sleep(0.2)
#             doc = await col.find_one({"client_id": internal_client_id})
#             if doc:
#                 doc.pop("id", None)
#                 return MasterClient(**doc)
#             raise RuntimeError("Race condition: client creation lost")

#         # ✅ создаём нового клиента
#         client = MasterClient(
#             client_id=internal_client_id,
#             source=source,
#             external_id=save_external_id,
#             name=name,
#             avatar_url=avatar_url,
#             metadata=metadata,
#             created_at=datetime.utcnow(),
#             user_id=user_id,
#         )
#         await col.insert_one(client.dict(exclude={"id"}))
#         return client

#     finally:
#         if got_lock:
#             await redis_db.delete(lock_key)

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

    # 🔐 Redis-блокировка от гонки
    lock_key = f"lock:client:create:{source.value}:{save_external_id}"
    got_lock = await redis_db.set(lock_key, "1", ex=5, nx=True)

    if user_id and len(internal_client_id.split(":")) < 2:
        internal_client_id = f"{user_id}:{internal_client_id}"

    try:
        # --- 1. Попытка найти существующего клиента ---
        if is_internal and is_anonymous:
            doc = await col.find_one({"client_id": internal_client_id})
        else:
            doc = await col.find_one({"source": source.value, "external_id": save_external_id})
        print("Найден мастер")
        print(doc)
        if doc:
            update_fields: Dict[str, Any] = {}

            if name and name != doc.get("name"):
                update_fields["name"] = name
            if avatar_url and avatar_url != doc.get("avatar_url"):
                update_fields["avatar_url"] = avatar_url
            print('и есть user_id в аргументах' if user_id else None)
            print('и даже user_id в есть в мастере' if doc.get("user_id") else None)
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

        # 🕒 fallback: если гонка, ждём и ищем по client_id
        if not got_lock:
            await asyncio.sleep(0.2)
            doc = await col.find_one({"client_id": internal_client_id})
            if doc:
                doc.pop("id", None)
                return MasterClient(**doc)
            raise RuntimeError("Race condition: client creation lost")

        # --- 2. Создаём нового клиента ---
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
# БЛОК: Работа с сообщениями
# ==============================


def find_last_bot_message(chat_session: ChatSession) -> Optional[ChatMessage]:
    """Возвращает последнее сообщение бота или консультанта."""
    return next(
        (
            msg
            for msg in reversed(chat_session.messages)
            if msg.sender_role in {SenderRole.AI, SenderRole.CONSULTANT}
        ),
        None,
    )

# ==============================
# БЛОК: Уведомление админ‑бота
# ==============================



async def send_message_to_bot(chat_id: str, chat_session: Dict[str, Any]) -> None:
    """Отправляет информацию о чате в админ-бот."""
    if settings.HOST == "localhost":
        return

    bot_webhook_url = "http://bot:9999/webhook/send_message"
    admin_chat_url = f"https://{settings.HOST}/admin/chats/chat_sessions"

    def dt_iso(value: Any) -> str:
        if isinstance(value, datetime):
            value = value.astimezone(timezone.utc).replace(microsecond=0)
            return value.isoformat() + " UTC+0"
        return str(value)

    def is_client_sender(m: dict) -> bool:
        try:
            return json.loads(m.get("sender_role", "{}")).get("en") == SenderRole.CLIENT.en_value
        except (json.JSONDecodeError, AttributeError):
            return False

    def get_ru_source_label(source_field: Any) -> str:
        try:
            parsed = json.loads(source_field) if isinstance(source_field, str) else source_field
            return parsed.get("ru", "—")
        except (json.JSONDecodeError, TypeError, AttributeError):
            return "—"

    client = chat_session.get("client") or {}
    client_id = client.get("client_id", "❌ Неизвестен")
    external_id = chat_session.get("external_id") or "—"
    messages = chat_session.get("messages", [])

    last_client_message = next(
        (m for m in reversed(messages) if is_client_sender(m) and m.get("message")),
        None
    )
    last_message_text = last_client_message["message"] if last_client_message else "—"

    try:
        position, total = await get_chat_position(chat_session["chat_id"])
    except Exception:
        position, total = -1, -1

    position_display = f"{position} из {total}" if position > 0 else "не определена"

    try:
        master_client = await get_master_client_by_id(client_id) if client_id else None
        master_external_id = master_client.external_id if master_client and master_client.external_id else "—"
        master_source = get_ru_source_label(master_client.source) if master_client and master_client.source else "—"
    except Exception:
        master_external_id = master_source = "—"

    message_text = f"""
<b>🆘 Новый чат</b>

🆔 <b>Чат ID:</b> {chat_session["chat_id"]}
🔗 <b>External ID:</b> {external_id}
👤 <b>Клиент ID:</b> {client_id}
📡 <b>Источник:</b> {master_source}
🤖 <b>Ручной режим:</b> {"✅ Включен" if chat_session.get("manual_mode") else "❌ Выключен"}
💬 <b>Сообщений:</b> {len(messages)}
📅 <b>Создан:</b> {dt_iso(chat_session.get("created_at"))}
🕒 <b>Последняя активность:</b> {dt_iso(chat_session.get("last_activity"))}
📊 <b>Позиция в очереди:</b> {position_display}

🗣️ <b>Последнее сообщение клиента:</b>
{last_message_text}

🔍 <a href="{admin_chat_url}">Открыть чат в админке</a>
""".strip()

    # Разбор chat_id и message_thread_id из строки
    admin_chat_id = bot_settings.ADMIN_CHAT_ID
    message_thread_id = None

    
    logging.error(f"📤 URL: {bot_webhook_url}")
    if "/" in admin_chat_id:
        parts = admin_chat_id.split("/")
        if len(parts) >= 2:
            admin_chat_id = parts[0]
            message_thread_id = int(parts[1]) if parts[1] else None

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "chat_id": admin_chat_id,
                "text": message_text,
                "parse_mode": "HTML",
            }
            if message_thread_id:
                payload["message_thread_id"] = message_thread_id
            logging.error(f"📨 Отправка в бота → chat_id: {admin_chat_id}, thread_id: {message_thread_id}")
            logging.error("📦 Payload:")
            logging.error(json.dumps(payload, ensure_ascii=False, indent=2))

            logging.error(f"🛠 Используемый chat_id: {payload['chat_id']}")
            if "message_thread_id" in payload:
                logging.error(f"🧵 Используемый thread_id: {payload.get('message_thread_id', None)}")


            response = await client.post(
                bot_webhook_url,
                json=payload,
                timeout=10.0
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logging.error(f"Ошибка от бота ({exc.response.status_code}): {exc.response.text}")
    except Exception:
        logging.exception("Ошибка при отправке сообщения в бот")




# ==============================
# БЛОК: Работа с чатами клиента
# ==============================


async def get_all_chats_for_client(client_id: str) -> List[dict]:
    """Получает все чаты конкретного клиента из MongoDB."""
    return [chat async for chat in mongo_db.chats.find({"client.client_id": client_id})]


async def get_active_chats_for_client(
        client_id: str) -> List[Tuple[dict, int]]:
    """Возвращает отсортированный список активных чатов клиента (chat_data, ttl)."""
    all_chats = await get_all_chats_for_client(client_id)
    active_chats = []

    for chat in all_chats:
        chat_id = chat["chat_id"]
        redis_key = f"chat:session:{chat_id}"
        ttl = await redis_db.ttl(redis_key)
        if ttl > 0:
            active_chats.append((chat, ttl))

    active_chats.sort(key=lambda x: x[0]["created_at"], reverse=True)
    return active_chats

async def calculate_chat_status(chat_session: ChatSession, redis_key_session: str):
    remaining_time = max(await redis_db.ttl(redis_key_session), 0)

    staff_roles = [RoleEnum.ADMIN, RoleEnum.SUPERADMIN]
    staff_users_cursor = mongo_db.users.find(
        {"role": {"$in": [role.value for role in staff_roles]}},
        {"_id": 1}
    )
    staff_ids = {str(user["_id"]) async for user in staff_users_cursor}
    brief_questions = BRIEF_QUESTIONS

    status = chat_session.compute_status(
        ttl_value=remaining_time,
        staff_ids=staff_ids,
        brief_questions=brief_questions
    )
    return status


async def serialize_active_chat(chat_data: dict, ttl: int) -> Dict[str, Any]:
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
    """Определяет позицию чата в очереди по последнему сообщению клиента без использования админки."""
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
    Authorize: AuthJWT = Depends(),          # ⬅️  JWT опционален
) -> Tuple[str, str]:                       # (client_id, external_id)
    """
    1. Telegram Mini App → валидация подписи.
    2. JWT → пытаемся найти MasterClient по `user_id`.
    3. Иначе — старая схема (external_id || 'anonymous').
    """
    from chats.integrations.telegram.telegram_bot import verify_telegram_hash
    logging.error(f"===== ПОСЛЕ: {user_id} =====")
    logging.error(source)
    logging.error(f"user_id {user_id}")
    logging.error(f"timestamp {timestamp}")
    logging.error(f"hash {hash}")
    if hash:

        res = verify_telegram_hash(user_id, timestamp, hash, settings.TELEGRAM_BOT_TOKEN)
        logging.error(f"res {res}")
    if source == ChatSource.TELEGRAM_MINI_APP:
        if not (user_id and timestamp and hash):
            raise HTTPException(400, "Telegram auth params missing")
        if not verify_telegram_hash(user_id, timestamp, hash, settings.TELEGRAM_BOT_TOKEN):
            raise HTTPException(403, "Invalid Telegram signature")
        external_id = user_id

    else:
        user_doc = None
        if Authorize is not None:
            try:
                user_id = Authorize.get_jwt_subject()
                if not user_id:
                    raise HTTPException(status_code=401, detail="Not authenticated")
                user_doc = await mongo_db["users"].find_one({"_id": ObjectId(user_id)})
            except (jwt_exc.MissingTokenError, jwt_exc.RevokedTokenError):
                user_doc = None
        else:
            user_id = None

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
    """Создаёт или получает чат-сессию, используя Redis и MongoDB."""
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

    # Временно убрал
    # if mode == "new":
    #     for chat_data, _ in active_chats:
    #         await mongo_db.chats.update_one(
    #             {"chat_id": chat_data["chat_id"]},
    #             {
    #                 "$set": {
    #                     "closed_by_request": True,
    #                     "last_activity": datetime.utcnow()
    #                 }
    #             }
    #         )

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


def is_valid_object_id(oid: str) -> bool:
    """Получить информацию об отправителях (мастер-клиент + user_data)."""
    if not isinstance(oid, str):
        return False
    try:
        ObjectId(oid)
        return True
    except Exception:
        return False

# async def build_sender_data_map(messages: list[dict], extra_client_id: Optional[str] = None) -> dict[str, dict[str, Any]]:
#     """Получить информацию об отправителях (мастер-клиент + user_data), включая клиента чата даже без сообщений."""
#     sender_ids = {m.get("sender_id") for m in messages if m.get("sender_id")}

#     if extra_client_id:
#         sender_ids.add(extra_client_id)

#     sender_ids.discard(None)
#     if not sender_ids:
#         return {}

#     master_docs = await mongo_db.clients.find({"client_id": {"$in": list(sender_ids)}}).to_list(None)
#     masters = {d["client_id"]: MasterClient(**d) for d in master_docs}

#     valid_user_ids = [ObjectId(m.user_id) for m in masters.values() if m.user_id and is_valid_object_id(m.user_id)]
#     user_docs = await mongo_db.users.find({"_id": {"$in": valid_user_ids}}).to_list(None)
#     users = {str(u["_id"]): u for u in user_docs}

#     sender_data_map = {}

#     for client_id, master in masters.items():
#         data = {
#             "name": master.name,
#             "avatar_url": master.avatar_url,
#             "source": master.source.en_value,
#             "external_id": master.external_id,
#             "metadata": master.metadata,
#             "client_id": master.client_id,
#         }

#         if master.user_id and is_valid_object_id(master.user_id):
#             user_doc = users.get(master.user_id)
#             if user_doc:
#                 user_doc["_id"] = str(user_doc["_id"])
#                 user_data_obj = UserWithData(**user_doc, data={"user_id": str(user_doc["_id"])})
#                 user_data = await user_data_obj.get_full_user_data()
#                 data["user"] = user_data

#         sender_data_map[client_id] = data

#     return sender_data_map

async def build_sender_data_map(
    messages: list[dict],
    extra_client_id: Optional[str] = None
) -> dict[str, dict[str, Any]]:
    """Получить информацию об отправителях (мастер-клиент + user_data + patient info), включая клиента чата даже без сообщений."""

    sender_ids = {m.get("sender_id") for m in messages if m.get("sender_id")}
    if extra_client_id:
        sender_ids.add(extra_client_id)
    sender_ids.discard(None)

    if not sender_ids:
        return {}

    # --- 1. Master clients ---
    master_docs = await mongo_db.clients.find({"client_id": {"$in": list(sender_ids)}}).to_list(None)
    masters = {d["client_id"]: MasterClient(**d) for d in master_docs}

    # --- 2. Users ---
    valid_user_ids = [ObjectId(m.user_id) for m in masters.values() if m.user_id and is_valid_object_id(m.user_id)]
    user_docs = await mongo_db.users.find({"_id": {"$in": valid_user_ids}}).to_list(None)
    users = {str(u["_id"]): u for u in user_docs}

    # --- 3. Main info & Contact info ---
    user_ids_str = [str(uid) for uid in valid_user_ids]

    main_infos = await mongo_db["patients_main_info"].find({"user_id": {"$in": user_ids_str}}).to_list(None)
    contact_infos = await mongo_db["patients_contact_info"].find({"user_id": {"$in": user_ids_str}}).to_list(None)

    main_info_map = {doc["user_id"]: doc for doc in main_infos}
    contact_info_map = {doc["user_id"]: doc for doc in contact_infos}

    # --- 4. Сбор итоговых данных ---
    sender_data_map = {}

    for client_id, master in masters.items():
        data = {
            "name": master.name,
            "avatar_url": master.avatar_url,
            "source": master.source.en_value,
            "external_id": master.external_id,
            "metadata": dict(master.metadata or {}),
            "client_id": master.client_id,
        }

        if master.user_id and is_valid_object_id(master.user_id):
            user_doc = users.get(master.user_id)
            if user_doc:
                user_doc["_id"] = str(user_doc["_id"])
                user_data_obj = UserWithData(**user_doc, data={"user_id": str(user_doc["_id"])})
                user_data = await user_data_obj.get_full_user_data()
                data["user"] = user_data

            metadata = data.setdefault("metadata", {})

            main_info = main_info_map.get(master.user_id)
            main_info = {key: value for key, value in main_info.items() if key in ["first_name", "patronymic", "last_name", "avatar"]}
            contact_info = contact_info_map.get(master.user_id)
            contact_info = {key: value for key, value in main_info.items() if key in []}

            if main_info:
                metadata["main_info"] = main_info
                # fallback name
                if not data["name"]:
                    name_parts = [
                        main_info.get("first_name"),
                        main_info.get("patronymic"),
                        main_info.get("last_name")
                    ]
                    data["name"] = " ".join(filter(None, name_parts)).strip() or None

                # fallback avatar
                avatar = main_info.get("avatar", {})
                if not data["avatar_url"] and avatar and avatar.get("url"):
                    data["avatar_url"] = avatar["url"]

            if contact_info:
                metadata["contact_info"] = contact_info

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
            {"$set": {"read_state": [ri.model_dump(
                mode="python") for ri in read_state]}}
        )

    return modified


# ==============================
# БЛОК: Контекст для ИИ-помощника
# ==============================

locale.setlocale(locale.LC_TIME, "C")


# ==============================
# БЛОК: Форматирование истории
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
    return now.strftime(
        "%A, %d-%m-%Y %H:%M:%S UTC%z").replace("UTC+0000", "UTC")


# ==============================
# БЛОК: Погода
# ==============================

async def fetch_weather(
        params: Dict[str, Any], redis_key: str) -> Dict[str, Any]:
    """Базовый запрос в OpenWeather с кэшированием."""
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
    """Возвращает прогноз погоды по названию региона."""
    key = f"weather:{region_name.lower()}"
    params = {
        "q": region_name,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }
    return await fetch_weather(params, key)


async def get_coordinates(address: str) -> Dict[str, float]:
    """Возвращает координаты для адреса."""
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
    """Возвращает прогноз погоды по координатам."""
    key = f"weather:{lat},{lon}"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
        "lang": "ru",
    }
    return await fetch_weather(params, key)


async def get_weather_by_address(address: str) -> Dict[str, Any]:
    """Возвращает прогноз погоды по адресу."""
    coords = await get_coordinates(address)
    if not coords:
        return {"error": "Failed to get coordinates"}
    return await get_weather_for_location(coords["lat"], coords["lon"])


def parse_weather_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Парсит прогноз погоды и группирует по датам."""
    forecast: Dict[str, Any] = {}
    for entry in data["list"]:
        date_key = entry["dt_txt"].split(" ")[0]
        temp = entry["main"]["temp"]
        desc = entry["weather"][0]["description"].capitalize()
        day = forecast.setdefault(
            date_key, {"temp_min": temp, "temp_max": temp, "description": desc}
        )
        day["temp_min"] = min(day["temp_min"], temp)
        day["temp_max"] = max(day["temp_max"], temp)
    return {"forecast": forecast}


# ==============================
# БЛОК: Контекст бота
# ==============================

async def get_bot_context() -> Dict[str, Any]:
    """Загружает настройки бота или берёт значения по умолчанию."""
    data = await mongo_db.bot_settings.find_one({}, sort=[("_id", DESCENDING)])
    bot_settings = BotSettings(**data) if data else BotSettings(
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
            "ka": "გამარჯობა! რით შემ 가능합니다?"
        },
        error_message={
            "en": "Please wait for a consultant.",
            "pl": "Proszę poczekać na konsultanta.",
            "uk": "Будь ласка, зачекайте на консультанта.",
            "ru": "Пожалуйста, подождите, консультант скоро ответит.",
            "ka": "გთხოვთ, დაელოდოთ კონსულტანტს."
        },
        farewell_message={
            "en": "Goodbye! Feel free to ask anything else.",
            "pl": "Do widzenia! Jeśli masz pytania, śmiało pytaj.",
            "uk": "До побачення! Звертайтесь, якщо виникнуть питання.",
            "ru": "До свидания! Если вам что-то понадобится, обращайтесь.",
            "ka": "ნახვამდის! თავისუფლად შეგიძლიათ კიდევ რაღაც მკითხოთ."
        },
        fallback_ai_error_message={
            "en": "Unfortunately, I'm having trouble generating a response right now. Please try again later.",
            "pl": "Niestety, mam teraz problem z wygenerowaniem odpowiedzi. Spróbuj ponownie później.",
            "uk": "На жаль, зараз виникла проблема з генерацією відповіді. Спробуйте пізніше.",
            "ru": "К сожалению, я не могу сейчас сгенерировать ответ. Пожалуйста, попробуйте позже.",
            "ka": "სამწუხაროდ, ახლა ვერ ვქმნი პასუხს. გთხოვთ, სცადეთ მოგვიანებით."
        },
        ai_model=AIModelEnum.GPT_4_O,
        created_at=datetime.utcnow()
    )
    return build_bot_settings_context(bot_settings, BotSettingsAdmin(mongo_db))


def build_bot_settings_context(
    settings: BotSettings,
    admin_model: BotSettingsAdmin
) -> Dict[str, Any]:
    """Формирует контекст бота из настроек."""
    bot_config = {
        "ai_model": settings.ai_model.value if settings.ai_model else "gpt-4o",
        "temperature": PERSONALITY_TRAITS_DETAILS.get(settings.personality_traits, 0.1),
        "welcome_message": settings.greeting,
        "redirect_message": settings.error_message,
        "farewell_message": settings.farewell_message,
        "fallback_ai_error_message": settings.fallback_ai_error_message,
        "app_name": settings.project_name,
        "app_description": settings.additional_instructions,
        "forbidden_topics": settings.forbidden_topics,
        "avatar": settings.avatar.url if settings.avatar else None,
        "bot_color": settings.bot_color.value,
        "postprocessing_instruction": settings.postprocessing_instruction or (
            "Do not invent facts. Do not generate placeholder links. "
            "Do not provide addresses, phones, or prices unless clearly present in the snippets or chat history."
        ),
        "language_instruction": settings.language_instruction or (
            "Always respond in the language of the user's latest messages. "
            "If it is unclear, use the language of the recent chat context or interface."
        ),
    }
    bot_config["prompt_text"] = generate_prompt_text(settings, admin_model)
    return bot_config


# ==============================
# БЛОК: Генерация промпта
# ==============================

def generate_prompt_text(
    settings: BotSettings,
    admin_model: BotSettingsAdmin
) -> str:
    """Создаёт текст промпта на основе настроек."""
    excluded = {"greeting", "error_message", "farewell_message", "ai_model",
                "personality_traits", "created_at", "avatar"}

    all_fields = set(admin_model.detail_fields) | set(admin_model.list_display)
    lines = ["You are AI Assistant. REMEMBER!:",
             "SYSTEM PROMPT:", "=" * 50]

    for field in all_fields:
        if field in excluded:
            continue
        field_title = admin_model.field_titles.get(field, {}).get("en", field)
        raw_value = getattr(settings, field, None)
        if not raw_value:
            continue
        processed = extract_value(raw_value)
        formatted = format_value(field, processed)
        if field == "employee_name":
            field_title = "Your (Bot) name (Not user name!!! Don`t to be confused with the username of the user being conversating)"
        lines += [f"{field_title.upper()}: {formatted}", "-" * 10]

    lines += ["IMPORTANT: FOLLOW ALL RULES STRICTLY!", "=" * 50]
    return "\n".join(lines)


def extract_value(value: Any) -> Any:
    """Преобразует значение для промпта."""
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
    """Форматирует значение для промпта."""
    if isinstance(value, list):
        return ", ".join(str(item.value if hasattr(
            item, "value") else item) for item in value)
    if hasattr(value, "value"):
        return value.value
    return str(value)


# ==============================
# БЛОК: Вспомогательный текст
# ==============================


def split_text_into_chunks(text: str, max_length: int = 998) -> List[str]:
    """Делит текст на части по предложениям, не обрывая числовые списки и не теряя хвост."""

    pattern = re.compile(
        r"""
        (            # начало группы
            (?:      # не захватываем вложенную группу
                (?!\d+\.\s)  # НЕ числовой список (например, 1. пункт)
                .*?
            )
            [.!?…:;]+           # финальный знак окончания предложения
            [)\]"»”’\s\w]*      # возможные закрывающие символы и пробелы
        )
        (?=\s+|$)    # за которым идёт пробел или конец строки
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
    """Удаляет Markdown и преобразует ссылки в текст (url), если текст ≠ url."""
    if not text:
        return ""

    def link_replacer(match):
        label, url = match.group(1).strip(), match.group(2).strip()
        if not url.startswith("http"):
            return label
        if not label:
            return url
        if label == url:
            return url
        return f"{label} ({url})"


    text = re.sub(
        r"\[\s*([^\]]*?)\s*\]\s*\(\s*(https?:\/\/[^\s)]+)\s*\)",
        link_replacer,
        text,
    )

    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*\*([^*]+)\*\*\*", r"\1", text)
    text = re.sub(r"___([^_]+)___", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"~+([^~]+?)~+", r"\1", text)

    text = re.sub(r"^\s*[-*+•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(
        r"(?<!\w)([a-zA-Z0-9\-._~:/?#@!$&'()*+,;=]{5,})\s*\(\s*(https?://[^\s)]+)\s*\)",
        lambda m: m.group(2)
        if m.group(1).rstrip('/').lower() in m.group(2).rstrip('/').lower()
        else m.group(0),
        text,
    )

    return text.strip()




# ==============================
# БЛОК: Обработка сообщения пользователя
# ==============================


def extract_json_from_response(resp: dict) -> dict[str, Any]:
    """Извлекает первый JSON-блок из ответа модели."""
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
    """Единый вызов генерации текста для OpenAI и Gemini."""
    client, real_model = pick_model_and_client(model_name)

    if real_model.startswith("gpt"):
        response = await client.chat.completions.create(
            model=real_model,
            messages=messages,
            temperature=temperature
        )
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": response.choices[0].message.content.strip()
                    }]
                }
            }]
        }

    elif real_model.startswith("gemini"):
        response = await client.chat_generate(
            model=real_model,
            messages=messages,
            temperature=temperature,
            system_instruction=system_instruction
        )
        return response

    raise ValueError(f"Unsupported model: {real_model}")
