"""Обработчики веб-сокетов приложения Чаты."""
import asyncio
import json
import logging
import random
import re
from asyncio import Lock
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import ValidationError

from chats.integrations.constructor_chat.handlers import push_to_constructor
from chats.utils.commands import COMMAND_HANDLERS, command_handler
from chats.utils.help_functions import get_master_client_by_id
from db.mongo.db_init import mongo_client, mongo_db
from db.redis.db_init import redis_db
from infra import settings
from knowledge.db.mongo.schemas import Answer, Subtopic, Topic
from knowledge.utils.help_functions import (build_messages_for_model,
                                            collect_kb_structures_from_context,
                                            get_knowledge_base,
                                            merge_external_structures)
from users.db.mongo.enums import RoleEnum
from utils.help_functions import try_parse_json
from chats.utils.help_functions import calculate_chat_status

from ..db.mongo.enums import ChatSource, ChatStatus, SenderRole
from ..db.mongo.schemas import (BriefAnswer, BriefQuestion, ChatMessage,
                                ChatReadInfo, ChatSession, GptEvaluation)
from ..utils.help_functions import (chat_generate_any, clean_markdown,
                                    extract_json_from_response,
                                    find_last_bot_message,
                                    format_chat_history_from_models,
                                    get_bot_context, get_weather_by_address,
                                    send_message_to_bot,
                                    split_text_into_chunks,
                                    update_read_state_for_client, get_or_create_master_client, build_sender_data_map)
from ..utils.knowledge_base import BRIEF_QUESTIONS
from ..utils.prompts import AI_PROMPTS
from ..utils.translations import TRANSLATIONS
from .ws_helpers import (ConnectionManager, DateTimeEncoder, TypingManager, custom_json_dumps,
                         gpt_task_manager)

logger = logging.getLogger(__name__)

# ==============================
# БЛОК: Обработка входящих сообщений (router)
# ==============================


async def handle_message(
    manager: ConnectionManager,
    typing_manager: TypingManager,
    data: dict,
    chat_id: str,
    client_id: str,
    redis_session_key: str,
    redis_flood_key: str,
    is_superuser: bool,
    user_language: str,
    gpt_lock: Lock,
    user_data: dict
) -> None:
    """Определяет тип сообщения и вызывает нужный handler."""
    handlers = {
        "status_check": handle_status_check,
        "get_messages": handle_get_messages,
        "new_message": handle_new_message,
        "start_typing": handle_start_typing,
        "stop_typing": handle_stop_typing,
        "get_typing_users": handle_get_typing_users,
        "get_my_id": handle_get_my_id,
    }
    handler = handlers.get(data.get("type"), handle_unknown_type)

    doc = await mongo_db.clients.find_one({"client_id": client_id})
    preferred_lang = (
        doc.get("metadata", {}).get("user_language") if doc else None
    ) or user_language

    if handler == handle_new_message:
        async with await mongo_client.start_session() as session:
            await handler(
                manager, chat_id, client_id, redis_session_key, redis_flood_key,
                data, is_superuser, preferred_lang, typing_manager,
                gpt_lock, user_data
            )
    elif handler == handle_get_messages:
        await handler(manager, chat_id, redis_session_key, data, user_data)
    elif handler in {
        handle_start_typing, handle_stop_typing,
        handle_get_typing_users, handle_get_my_id
    }:
        await handler(typing_manager, chat_id, client_id, manager)
    else:
        await handler(manager, chat_id, redis_session_key)


# ==============================
# БЛОК: Общие функции отправки системных сообщений (error, attention)
# ==============================

async def broadcast_system_message(
    manager: Any, client_id: str, chat_id: str, message: str, msg_type: str
) -> None:
    """Отправляет системное сообщение (ошибка или предупреждение), не сохраняя в БД."""
    system_message = custom_json_dumps({
        "type": msg_type,
        "chat_id": chat_id,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    })
    await manager.send_personal_message(system_message, client_id)


async def broadcast_error(manager: Any, client_id: str,
                          chat_id: str, message: str) -> None:
    """Отправляет сообщение об ошибке."""
    await broadcast_system_message(manager, client_id, chat_id, message, "error")


async def broadcast_attention(
        manager: Any, client_id: str, chat_id: str, message: str) -> None:
    """Отправляет предупреждающее сообщение."""
    await broadcast_system_message(manager, client_id, chat_id, message, "attention")


# ==============================
# БЛОК: Сохранение/загрузка сообщений
# ==============================

async def save_message_to_db(
        chat_session: ChatSession, new_msg: ChatMessage) -> None:
    """Сохраняет новое сообщение в базе данных."""
    chat_session.last_activity = new_msg.timestamp
    chat_session.messages.append(new_msg)
    await mongo_db.chats.update_one(
        {"chat_id": chat_session.chat_id},
        {
            "$push": {"messages": new_msg.model_dump(mode="python")},
            "$set": {"last_activity": new_msg.timestamp}
        },
        upsert=True
    )


async def broadcast_message(
        manager: Any, chat_session: ChatSession, new_msg: ChatMessage) -> None:
    """Отправляет новое сообщение в чат."""

    payload = custom_json_dumps({
        "type": "new_message",
        "id": new_msg.id,
        "chat_id": chat_session.chat_id,
        "sender_role": new_msg.sender_role.value,
        "sender_id": new_msg.sender_id,
        "message": new_msg.message,
        "reply_to": new_msg.reply_to,
        "choice_options": new_msg.choice_options,
        "choice_strict": new_msg.choice_strict,
        "timestamp": new_msg.timestamp.isoformat(),
        "external_id": new_msg.external_id,
        "files": new_msg.files or []
    })
    await manager.broadcast(payload)


async def save_and_broadcast_new_message(
    manager: Any,
    chat_session: ChatSession,
    new_msg: ChatMessage,
    redis_key_session: str,
    user_data: Optional[dict] = {}
) -> None:
    """Сохраняет сообщение, отправляет в чат и Redis, и реплицирует во внешние сервисы."""
    await save_message_to_db(chat_session, new_msg)
    await broadcast_message(manager, chat_session, new_msg)

    await redis_db.set(
        redis_key_session, "1",
        ex=int(settings.CHAT_TIMEOUT.total_seconds())
    )

    if user_data:
        user_id = user_data.get("data", {}).get("user_id")

        if new_msg.sender_role != SenderRole.AI:
            await update_read_state_for_client(
                chat_id=chat_session.chat_id,
                client_id=new_msg.sender_id,
                user_id=user_id,
                last_read_msg=new_msg.id
            )

    if new_msg.sender_role != SenderRole.CLIENT:
        await replicate_message_to_external_channel(chat_session, new_msg)

    try:
        await push_to_constructor(chat_session, [new_msg])
    except Exception:
        pass


# ==============================
# БЛОК: Интеграции чатов
# ==============================


async def replicate_message_to_external_channel(
    chat_session: ChatSession,
    new_msg: ChatMessage
) -> None:
    """Отправляет сообщение во внешний чат (Telegram, Instagram, WhatsApp, Facebook)."""

    source = chat_session.client.source
    client_id = chat_session.client.client_id

    master_client = await get_master_client_by_id(client_id)
    if not master_client:
        return

    external_id = master_client.external_id
    if not external_id:
        return

    is_echo = new_msg.metadata.get("is_echo") if new_msg.metadata else False
    has_external_id = (
        new_msg.metadata.get("message_id") if new_msg.metadata else False
    ) or new_msg.external_id

    en_source_name = json.loads(source).get("en")

    # Loop protection
    if en_source_name in {
        ChatSource.INSTAGRAM.en_value,
        ChatSource.FACEBOOK.en_value,
        ChatSource.WHATSAPP.en_value,
    } and has_external_id:
        return

    send_func_map = {
        ChatSource.INSTAGRAM.en_value: send_instagram_message,
        ChatSource.WHATSAPP.en_value: send_whatsapp_message,
        ChatSource.FACEBOOK.en_value: send_facebook_message,
        ChatSource.TELEGRAM.en_value: send_telegram_message,
    }

    send_func = send_func_map.get(en_source_name)
    if not send_func:
        return

    message_id = await send_func(external_id, new_msg)

    if message_id:
        await mongo_db.chats.update_one(
            {"chat_id": chat_session.chat_id, "messages.id": new_msg.id},
            {"$set": {"messages.$.external_id": message_id}}
        )


# ==============================
# Meta
# ==============================

# ==============================
# Instagram
# ==============================


async def send_instagram_message(
    recipient_id: str, message_obj: ChatMessage
) -> Optional[str]:
    """Отправляет сообщение в Instagram Direct, разбивая текст и убирая Markdown."""
    url = "https://graph.instagram.com/v22.0/me/messages"
    headers = {
        "Authorization": f"Bearer {settings.INSTAGRAM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    raw_text = (message_obj.message or "").strip()
    files = message_obj.files or []
    first_file = None  # files[0] if files else None

    cleaned_text = clean_markdown(raw_text)

    text_chunks = split_text_into_chunks(cleaned_text)

    async with httpx.AsyncClient() as client:
        try:
            if first_file:
                payload_image = {
                    "recipient": {"id": recipient_id},
                    "message": {
                        "attachment": {
                            "type": "image",
                            "payload": {"url": first_file, "is_reusable": False}
                        },
                        "metadata": "broadcast"
                    }
                }
                resp = await client.post(url, headers=headers, json=payload_image)
                resp.raise_for_status()

            message_id = None
            for i, chunk in enumerate(text_chunks):
                payload_text = {
                    "recipient": {"id": recipient_id},
                    "message": {
                        "text": chunk,
                        "metadata": "broadcast"
                    }
                }
                response = await client.post(url, json=payload_text, headers=headers)
                response.raise_for_status()
                message_id = response.json().get("message_id")

            return message_id
        except Exception as exc:
            logging.exception(f"❌ Ошибка при отправке сообщения в Instagram: {exc}")
            return None


# Вторая (будущая) версия отправки

# async def send_instagram_message(recipient_id: str, message_obj: ChatMessage) -> Optional[str]:
#     """
#     Отправляет фото (если есть) и текст (если есть) в Instagram Direct через Facebook Graph API.
#     Фото и подпись отправляются отдельными сообщениями. Markdown очищается, текст разбивается.
#     """
#     url = f"https://graph.facebook.com/v22.0/{settings.APPLICATION_PAGE_ID}/messages"
#     access_token = settings.APPLICATION_ACCESS_TOKEN
#
#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }
#
#     raw_text = message_obj.message.strip()
#     files = message_obj.files or []
#     image_url = files[0] if files else None
#
#     cleaned_text = clean_markdown(raw_text)
#     text_chunks = split_text_into_chunks(cleaned_text)
#
#     async with httpx.AsyncClient() as client:
#         try:
#             if image_url:
#                 payload_image = {
#                     "recipient": {"id": recipient_id},
#                     "message": {
#                         "attachment": {
#                             "type": "image",
#                             "payload": {
#                                 "url": image_url,
#                                 "is_reusable": False
#                             }
#                         }
#                     }
#                 }
#                 await client.post(url, headers=headers, json=payload_image)
#
#             message_id = None
#             for chunk in text_chunks:
#                 payload_text = {
#                     "recipient": {"id": recipient_id},
#                     "message": {
#                         "text": chunk
#                     }
#                 }
#                 response = await client.post(url, headers=headers, json=payload_text)
#                 response.raise_for_status()
#                 message_id = response.json().get("message_id")
#
#             return message_id
#         except Exception as exc:
#             logging.error(f"IG send error: {exc}")
#     return None



# ==============================
# WhatsApp
# ==============================

async def send_whatsapp_message(
        recipient_phone_id: str, message_obj: ChatMessage) -> Optional[str]:
    """Отправляет сообщение в WhatsApp через Cloud API."""
    url = f"https://graph.facebook.com/v22.0/{settings.WHATSAPP_BOT_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone_id,
        "type": "text",
        "text": {"body": message_obj.message.strip()},
        "metadata": "broadcast"
    }
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("messages", [{}])[0].get("id")
        except Exception as exc:
            logging.error(f"WhatsApp send error: {exc}")
            return None


# ==============================
# Facebook
# ==============================

async def send_facebook_message(
        recipient_id: str, message_obj: ChatMessage) -> Optional[str]:
    """Отправляет сообщение в Facebook Messenger."""
    url = f"https://graph.facebook.com/v22.0/{settings.FACEBOOK_PAGE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.FACEBOOK_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    text = message_obj.message.strip()
    files = message_obj.files or []
    first_file = None  # files[0] if files else None

    if first_file:
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": "image",
                    "payload": {"url": first_file, "is_reusable": False}
                },
                "text": text,
                "metadata": "broadcast"
            }
        }
    else:
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text, "metadata": "broadcast"}
        }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message_id") or data.get(
                "messages", [{}])[0].get("id")
        except Exception as exc:
            logging.error(f"Facebook send error: {exc}")
            return None

# ==============================
# Telegram
# ==============================

async def send_telegram_message(
    recipient_id: str,
    message_obj: ChatMessage
) -> Optional[str]:
    """Отправляет сообщение в Telegram через вебхук в контейнере bot."""
    url = "http://bot:9999/webhook/send_message"
    # url = "http://0.0.0.0:9999/webhook/send_message"
    payload = {
        "chat_id": recipient_id,
        "text": message_obj.message,
        "parse_mode": "HTML",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            return data.get("message_id")
    except Exception as e:
        logging.exception(f"❌ Ошибка при отправке в Telegram: {e}")
        return None


# ==============================
# БЛОК: Основные хэндлеры (статус, идентификация)
# ==============================

async def handle_status_check(
    manager: ConnectionManager,
    chat_id: str,
    redis_key_session: str
) -> None:
    chat_data = await mongo_db.chats.find_one(
        {"chat_id": chat_id},
        {
            "chat_id": 1,
            "manual_mode": 1,
            "read_state": 1,
            "messages": 1,
            "brief_answers": 1
        }
    )
    if not chat_data:
        return

    chat_session = ChatSession(**chat_data)
    remaining_time = max(await redis_db.ttl(redis_key_session), 0)
    read_by_staff = chat_session.is_read_by_any_staff({
        str(user["_id"]) async for user in mongo_db.users.find(
            {"role": {"$in": [RoleEnum.ADMIN.value, RoleEnum.SUPERADMIN.value]}},
            {"_id": 1}
        )
    })

    status = await calculate_chat_status(chat_session, redis_key_session)

    response = custom_json_dumps({
        "type": "status_check",
        "message": "Session is active." if remaining_time > 0 else "Session is expired.",
        "remaining_time": remaining_time,
        "manual_mode": chat_session.manual_mode,
        "read_by_staff": read_by_staff,
        "status": status.value
    })

    await manager.broadcast(response)




async def handle_get_my_id(
    manager: ConnectionManager,
    chat_id: str,
    client_id: str
) -> None:
    """Отправляет клиенту его идентификатор."""
    response = custom_json_dumps({
        "type": "my_id_info",
        "user_id": client_id
    })
    await manager.broadcast(response)


# ==============================
# БЛОК: Хэндлеры сообщений
# ==============================

# ==============================
# Получение всех сообщений
# ==============================

# async def handle_get_messages(
#     manager: ConnectionManager,
#     chat_id: str,
#     redis_key_session: str,
#     data: dict,
#     user_data: dict
# ) -> bool:
#     """Отдаёт историю чата и, при наличии with_enter=True, фиксирует прочтение текущим клиентом."""
#     chat_data: dict | None = await mongo_db.chats.find_one({"chat_id": chat_id})
#     if not chat_data:
#         await manager.broadcast(custom_json_dumps({
#             "type": "get_messages",
#             "messages": [],
#             "remaining_time": 0,
#             "message": "No chat found."
#         }))
#         return False

#     messages: list[dict] = chat_data.get("messages", [])
#     messages.sort(key=lambda m: m.get("timestamp"))

#     if not messages:
#         remaining = max(await redis_db.ttl(redis_key_session), 0)
#         await manager.broadcast(custom_json_dumps({
#             "type": "get_messages",
#             "messages": [],
#             "remaining_time": remaining
#         }))
#         return False

#     last_id = messages[-1]["id"]
#     client_id = user_data["client_id"]
#     user_id = user_data.get("user_id")

#     if data.get("with_enter"):
#         await update_read_state_for_client(
#             chat_id=chat_id,
#             client_id=client_id,
#             user_id=user_id,
#             last_read_msg=last_id
#         )

#     chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
#     read_state_raw = chat_data.get("read_state", [])
#     read_state: list[ChatReadInfo] = [
#         ChatReadInfo(**ri) if isinstance(ri, dict) else ri
#         for ri in read_state_raw
#     ]

#     idx = {m["id"]: i for i, m in enumerate(messages)}
#     enriched: list[dict] = []

#     for m in messages:
#         readers = [
#             ri.client_id
#             for ri in read_state
#             if idx.get(ri.last_read_msg, -1) >= idx[m["id"]]
#         ]
#         m["read_by"] = readers
#         enriched.append(m)

#     remaining = max(await redis_db.ttl(redis_key_session), 0)
#     await manager.broadcast(custom_json_dumps({
#         "type": "get_messages",
#         "messages": enriched,
#         "remaining_time": remaining
#     }))

#     return True

async def handle_get_messages(
    manager: ConnectionManager,
    chat_id: str,
    redis_key_session: str,
    data: dict,
    user_data: dict
) -> bool:
    """Отдаёт историю чата и, при наличии with_enter=True, фиксирует прочтение текущим клиентом."""
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        await manager.broadcast(custom_json_dumps({
            "type": "get_messages",
            "messages": [],
            "remaining_time": 0,
            "message": "No chat found."
        }))
        return False

    messages = sorted(chat_data.get("messages", []), key=lambda m: m.get("timestamp"))
    if not messages:
        remaining = max(await redis_db.ttl(redis_key_session), 0)
        await manager.broadcast(custom_json_dumps({
            "type": "get_messages",
            "messages": [],
            "remaining_time": remaining
        }))
        return False

    last_id = messages[-1]["id"]
    client_id = user_data.get("client_id")
    user_id = user_data.get("data", {}).get("user_id")

    print("===== USER DATA ====")
    print(user_data)

    if data.get("with_enter"):
        await update_read_state_for_client(
            chat_id=chat_id,
            client_id=client_id,
            user_id=user_id,
            last_read_msg=last_id
        )

    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    read_state_raw = chat_data.get("read_state", [])
    read_state: list[ChatReadInfo] = [
        ChatReadInfo(**ri) if isinstance(ri, dict) else ri
        for ri in read_state_raw
    ]
    idx = {m["id"]: i for i, m in enumerate(messages)}

    sender_data_map = await build_sender_data_map(messages)

    enriched: list[dict] = []
    for m in messages:
        readers = [
            ri.client_id
            for ri in read_state
            if idx.get(ri.last_read_msg, -1) >= idx[m["id"]]
        ]
        m["read_by"] = readers

        sender_id = m.get("sender_id")
        if sender_id and sender_id in sender_data_map:
            m["sender_data"] = sender_data_map[sender_id]

        enriched.append(m)

    remaining = max(await redis_db.ttl(redis_key_session), 0)
    await manager.broadcast(custom_json_dumps({
        "type": "get_messages",
        "messages": enriched,
        "remaining_time": remaining
    }))
    return True



# ==============================
# Обработка нового сообщения
# ==============================

async def handle_new_message(
    manager: ConnectionManager,
    chat_id: str,
    client_id: str,
    redis_key_session: str,
    redis_key_flood: str,
    data: dict,
    is_superuser: bool,
    user_language: str,
    typing_manager: TypingManager,
    gpt_lock: Lock,
    user_data: dict
) -> None:
    """Обрабатывает новое сообщение от пользователя."""

    msg_text = data.get("message", "")
    reply_to = data.get("reply_to")
    external_id = data.get("external_id")
    metadata = data.get("metadata", {})

    if is_superuser:
        await handle_superuser_message(manager, client_id, chat_id, msg_text, metadata, reply_to, redis_key_session, user_language)
        return

    chat_session = await load_chat_data(manager, client_id, chat_id, user_language)
    if not chat_session:
        return

    if not await validate_chat_status(manager, client_id, chat_session, redis_key_session, chat_id, user_language):
        return

    if not msg_text.strip():
        return

    try:
        new_msg = ChatMessage(
            message=msg_text,
            sender_role=SenderRole.CLIENT,
            sender_id=client_id,
            reply_to=reply_to,
            external_id=external_id,
            metadata=metadata,
        )
    except ValidationError as e:
        await broadcast_error(
            manager,
            client_id,
            chat_id,
            get_translation("errors", "message_too_long", user_language)
        )
        return

    if await handle_command(manager, redis_key_session, client_id, chat_id, chat_session, new_msg, user_language):
        return

    if not await check_flood_control(manager, client_id, chat_session, redis_key_flood,
                                     chat_session.calculate_mode(BRIEF_QUESTIONS), user_language):
        return

    if not await validate_choice(manager, client_id, chat_session, chat_id, msg_text, user_language):
        return

    await save_and_broadcast_new_message(manager, chat_session, new_msg, redis_key_session, user_data)

    if await handle_brief_mode(manager, client_id, chat_session, msg_text, chat_id, redis_key_session, user_language):
        return

    if not chat_session.manual_mode:
        gpt_task_manager.cancel_task(chat_id)

        new_task = asyncio.create_task(
            process_user_query_after_brief(
                manager=manager,
                chat_id=chat_id,
                user_msg=new_msg,
                chat_session=chat_session,
                redis_key_session=redis_key_session,
                user_language=user_language,
                typing_manager=typing_manager,
                gpt_lock=gpt_lock,
                user_data=user_data
            )
        )
        gpt_task_manager.set_task(chat_id, new_task)


# ==============================
# БЛОК: Хэндлеры печати (start/stop typing, get_typing_users)
# ==============================

async def handle_start_typing(typing_manager: TypingManager,
                              chat_id: str, client_id: str, manager: ConnectionManager) -> None:
    """Обрабатывает начало печати пользователя."""
    await typing_manager.add_typing(chat_id, client_id, manager)


async def handle_stop_typing(typing_manager: TypingManager,
                             chat_id: str, client_id: str, manager: ConnectionManager) -> None:
    """Обрабатывает окончание печати пользователя."""
    await typing_manager.remove_typing(chat_id, client_id, manager)
    await send_typing_update(typing_manager, chat_id, manager)


async def handle_get_typing_users(
        typing_manager: TypingManager, chat_id: str, client_id: str, manager: ConnectionManager) -> None:
    """Отправляет текущий список печатающих пользователей в чат."""
    await send_typing_update(typing_manager, chat_id, manager)


async def send_typing_update(
        typing_manager: TypingManager, chat_id: str, manager: ConnectionManager) -> None:
    """Отправляет обновленный список печатающих пользователей в чат."""
    response = custom_json_dumps(
        {"type": "typing_update", "typing_users": typing_manager.get_typing_users(chat_id)})
    await manager.broadcast(response)


# ==============================
# БЛОК: Логика загрузки/валидации чата
# ==============================

async def load_chat_data(manager: ConnectionManager, client_id: str,
                         chat_id: str, user_language: str) -> Optional[ChatSession]:
    """Загружает данные чата из базы."""
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})

    if not chat_data:
        await broadcast_error(manager, client_id, chat_id, get_translation("errors", "chat_not_exist", user_language))
        return None

    try:
        return ChatSession(**chat_data)
    except ValidationError:
        await broadcast_error(manager, client_id, chat_id, get_translation("errors", "invalid_chat_data", user_language))
        return None




async def validate_chat_status(
    manager: ConnectionManager,
    client_id: str,
    chat_session: ChatSession,
    redis_key_session: str,
    chat_id: str,
    user_language: str
) -> bool:
    """Проверяет статус чата перед обработкой сообщений."""

    ttl_value = await redis_db.ttl(redis_key_session)
    brief_questions = BRIEF_QUESTIONS
    dynamic_status = chat_session.compute_status(ttl_value)
    status_en = json.loads(dynamic_status.value)["en"]
    print(status_en)


    NEGATIVE_STATUSES = {
        ChatStatus.CLOSED_NO_MESSAGES.en_value,
        ChatStatus.CLOSED_BY_TIMEOUT.en_value,
        ChatStatus.CLOSED_BY_OPERATOR.en_value
    }
    print(NEGATIVE_STATUSES)

    if status_en in NEGATIVE_STATUSES:
        await broadcast_error(
            manager,
            client_id,
            chat_id,
            get_translation(
                "errors", "chat_status_invalid", user_language,
                status=dynamic_status.value
            )
        )
        return False

    if ttl_value < 0 and chat_session.messages:
        await redis_db.set(
            redis_key_session,
            "1",
            ex=int(settings.CHAT_TIMEOUT.total_seconds())
        )

    return True



# ==============================
# БЛОК: Обработка команд
# ==============================

async def handle_command(manager: ConnectionManager, redis_key_session: str, client_id: str,
                         chat_id: str, chat_session: ChatSession, new_msg: ChatMessage, user_language: str) -> bool:
    """Обрабатывает команду пользователя (начинается с `/`)."""
    command_alias = new_msg.message.strip().split()[0].lower()

    if not command_alias.startswith("/"):
        return False

    command_data = COMMAND_HANDLERS.get(command_alias)

    if command_data:
        await save_and_broadcast_new_message(manager, chat_session, new_msg, redis_key_session)
        await command_data["handler"](manager, chat_session, new_msg, user_language, redis_key_session)
    else:
        await broadcast_attention(manager, client_id, chat_id, get_translation("attention", "unknown_command", user_language))

    return True


# ==============================
# БЛОК: Функция перевода сообщений
# ==============================

def get_translation(category: str, key: str, language: str, **kwargs) -> str:
    """Возвращает перевод из `TRANSLATIONS`, подставляя переменные."""
    template = TRANSLATIONS.get(
        category,
        {}).get(
        key,
        {}).get(
            language,
            TRANSLATIONS.get(
                category,
                {}).get(
                    key,
                    {}).get(
                        "en",
                ""))
    return template.format(**kwargs) if isinstance(template, str) else template


# ==============================
# БЛОК: Flood control и проверка выбора
# ==============================


async def check_flood_control(
    manager: ConnectionManager,
    client_id: str,
    chat_session: ChatSession,
    redis_key_flood: str,
    mode: str,
    user_language: str
) -> bool:
    """Контроль частоты сообщений (flood control), учитывая режим чата (manual/automatic)."""
    source = chat_session.client.source

    en_source_name = json.loads(source).get("en")

    if any(en_source_name == s.en_value for s in [
        ChatSource.INSTAGRAM, ChatSource.FACEBOOK, ChatSource.WHATSAPP
    ]):
        return True

    flood_timeout = settings.FLOOD_TIMEOUTS.get(mode)
    chat_id = chat_session.chat_id

    if flood_timeout:
        redis_key_mode_flood = f"{redis_key_flood}:{mode}"
        current_ts = datetime.utcnow().timestamp()
        last_sent_ts = safe_float(await redis_db.get(redis_key_mode_flood))

        if (current_ts - last_sent_ts) < flood_timeout.total_seconds():
            await broadcast_attention(
                manager, client_id, chat_id,
                get_translation("attention", "too_fast", user_language)
            )
            return False

        await redis_db.set(redis_key_mode_flood, str(current_ts), ex=int(flood_timeout.total_seconds()))

    return True



async def validate_choice(
    manager: ConnectionManager, client_id: str, chat_session: ChatSession, chat_id: str, msg_text: str, user_language: str
) -> bool:
    """
    Проверка корректности выбора пользователя (strict choice).
    """
    last_bot_msg = find_last_bot_message(chat_session)
    if not last_bot_msg or not last_bot_msg.choice_options or (
            last_bot_msg.choice_options and not last_bot_msg.choice_strict):
        return True

    translated_choices = chat_session.get_current_question(BRIEF_QUESTIONS).expected_answers_translations.get(
        user_language, []
    )

    if msg_text not in translated_choices:
        await broadcast_error(
            manager, client_id, chat_id, get_translation(
                "errors", "invalid_choice", user_language, choices=', '.join(translated_choices))
        )
        return False

    return True


def safe_float(value: Optional[Union[str, bytes]]) -> float:
    """
    Безопасное преобразование значения в `float`.
    """
    try:
        return float(value) if value else 0.0
    except ValueError:
        return 0.0


# ==============================
# БЛОК: Работа с брифами
# ==============================

async def handle_brief_mode(
    manager: ConnectionManager,
    client_id: str,
    chat_session: ChatSession,
    msg_text: str,
    chat_id: str,
    redis_key_session: str,
    user_language: str
) -> bool:
    """Обрабатывает логику брифа, если чат в режиме `brief`."""

    if chat_session.calculate_mode(BRIEF_QUESTIONS) != "brief":
        return False

    current_question = chat_session.get_current_question(BRIEF_QUESTIONS)
    if not current_question:
        await complete_brief(manager, chat_session, redis_key_session, user_language)
        return False

    if not await check_relevance_to_brief(current_question.question, msg_text):
        await fill_remaining_brief_questions(chat_id, chat_session)
        return False

    await process_brief_question(
        client_id, chat_session, msg_text,
        manager, redis_key_session, user_language
    )

    updated_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    updated_session = ChatSession(**updated_data)

    next_question = updated_session.get_current_question(BRIEF_QUESTIONS)
    if not next_question:
        await complete_brief(manager, updated_session, redis_key_session, user_language)
    else:
        await broadcast_brief_question(manager, next_question, user_language)

    return True


async def start_brief(
    chat_session: ChatSession,
    manager: ConnectionManager,
    redis_key_session: str,
    user_language: str,
) -> None:
    """
    Инициализирует бриф.
    """
    welcome_flag_key = f"chat:welcome:{chat_session.chat_id}"

    if len(chat_session.messages) > 0 or not await redis_db.set(welcome_flag_key, "1", ex=60, nx=True):
        return

    bot_context = await get_bot_context()
    hello_text = bot_context.get(
        "welcome_message",
        {}).get(
        user_language,
        None)

    if isinstance(hello_text, str):
        msg = ChatMessage(message=hello_text, sender_role=SenderRole.AI)
        await save_and_broadcast_new_message(manager, chat_session, msg, redis_key_session)

    question = chat_session.get_current_question(BRIEF_QUESTIONS)
    if question:
        await ask_brief_question(manager, chat_session, question, redis_key_session, user_language)


async def process_brief_question(
    client_id: str,
    chat_session: ChatSession,
    user_message: str,
    manager: ConnectionManager,
    redis_key_session: str,
    user_language: str
) -> None:
    """
    Обрабатывает текущий вопрос брифа и, при необходимости, задаёт следующий.
    """
    question = chat_session.get_current_question(BRIEF_QUESTIONS)
    if not question:
        return

    if question.question_type == "choice" and question.expected_answers:
        translated_answers = question.expected_answers_translations.get(
            user_language, question.expected_answers
        )
        if user_message not in translated_answers:
            error_msg = get_translation(
                "errors",
                "invalid_answer",
                user_language,
                choices=', '.join(translated_answers)
            )
            await broadcast_error(manager, client_id, chat_session.chat_id, error_msg)
            return

    ans = BriefAnswer(
        question=question.question,
        expected_answers=question.expected_answers,
        user_answer=user_message
    )
    await mongo_db.chats.update_one(
        {"chat_id": chat_session.chat_id},
        {"$push": {"brief_answers": ans.model_dump(mode="python")}}
    )

    updated_data = await mongo_db.chats.find_one({"chat_id": chat_session.chat_id})
    chat_session.__dict__.update(ChatSession(**updated_data).__dict__)

    next_question = chat_session.get_current_question(BRIEF_QUESTIONS)
    if next_question:
        msg = build_brief_question_message(next_question, user_language)
        await save_and_broadcast_new_message(manager, chat_session, msg, redis_key_session)


def extract_brief_info(chat_session: ChatSession) -> str:
    """Возвращает строку с ответами брифа для контекста GPT."""
    return "; ".join(
        f"{a.question}: {a.user_answer if a.user_answer else '(Without answer)'}"
        for a in chat_session.brief_answers
    )


async def complete_brief(
    manager: ConnectionManager,
    chat_session: ChatSession,
    redis_key_session: str,
    user_language: str
) -> None:
    """Завершает бриф и отправляет пользователю сообщение о завершении."""
    done_text = get_translation(
        "brief",
        "brief_completed",
        user_language,
        default_key="en")
    msg = ChatMessage(message=done_text, sender_role=SenderRole.AI)
    await save_and_broadcast_new_message(manager, chat_session, msg, redis_key_session)


async def fill_remaining_brief_questions(
        chat_id: str, chat_session: ChatSession) -> None:
    """Заполняет оставшиеся вопросы брифа пустыми ответами, если ответ нерелевантен."""
    answered = {a.question for a in chat_session.brief_answers}
    unanswered = [q for q in BRIEF_QUESTIONS if q.question not in answered]
    for question in unanswered:
        empty = BriefAnswer(
            question=question.question,
            expected_answers=question.expected_answers,
            user_answer=''
        )
        await mongo_db.chats.update_one(
            {"chat_id": chat_id},
            {"$push": {"brief_answers": empty.model_dump(mode="python")}}
        )


async def ask_brief_question(
    manager: ConnectionManager,
    chat_session: ChatSession,
    question: BriefQuestion,
    redis_key_session: str,
    user_language: str
) -> None:
    """
    Задаёт первый вопрос брифа при инициализации чата.
    """
    msg = build_brief_question_message(question, user_language)
    await save_and_broadcast_new_message(manager, chat_session, msg, redis_key_session)


async def broadcast_brief_question(
    manager: ConnectionManager,
    question: BriefQuestion,
    user_language: str
) -> None:
    """
    Отправляет клиенту JSON с новым вопросом брифа
    (без сохранения этого сообщения в БД).
    """
    translated_q = question.question_translations.get(
        user_language, question.question)
    translated_a = None
    if question.expected_answers_translations:
        translated_a = question.expected_answers_translations.get(
            user_language, question.expected_answers
        )

    payload = {
        "type": "brief_question",
        "question": translated_q,
        "expected_answers": translated_a
    }
    await manager.broadcast(custom_json_dumps(payload))


def build_brief_question_message(
        question: BriefQuestion, user_language: str) -> ChatMessage:
    """
    Формирует ChatMessage с учётом типа вопроса (choice/text) и ожидаемых ответов.
    """
    translated_q = question.question_translations.get(
        user_language, question.question)
    if question.question_type == "choice" and question.expected_answers:
        return ChatMessage(
            message=translated_q,
            sender_role=SenderRole.AI,
            choice_options=question.expected_answers_translations.get(
                user_language, question.expected_answers_translations.get("en")
            ),
            choice_strict=True
        )
    elif question.question_type == "text" and question.expected_answers:
        return ChatMessage(
            message=translated_q,
            sender_role=SenderRole.AI,
            choice_options=question.expected_answers_translations.get(
                user_language, question.expected_answers_translations.get("en")
            ),
            choice_strict=False
        )
    return ChatMessage(message=translated_q,
                       sender_role=SenderRole.AI, choice_strict=False)


# ==============================
# БЛОК: Сообщения от суперпользователя
# ==============================


async def handle_superuser_message(
    manager: ConnectionManager,
    client_id: str,
    chat_id: str,
    msg_text: str,
    metadata: dict,
    reply_to: Optional[str],
    redis_key_session: str,
    user_language: str
) -> None:
    """
    Обработка сообщения от суперпользователя (консультанта).
    """
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        await broadcast_error(manager, client_id, chat_id, get_translation("errors", "chat_not_exist", user_language))
        return

    try:
        chat_session = ChatSession(**chat_data)
    except ValidationError:
        await broadcast_error(manager, client_id, chat_id, get_translation("errors", "invalid_chat_data", user_language))
        return

    if ":" in client_id:
        user_id, base_id = client_id.split(":", 1)
    else:
        user_id, base_id = client_id, client_id

    await get_or_create_master_client(
        source=ChatSource.INTERNAL,
        external_id=client_id,
        internal_client_id=client_id,
        name=metadata.get("name"),
        avatar_url=metadata.get("avatar_url"),
        metadata=metadata,
        user_id=user_id
    )

    new_msg = ChatMessage(
        message=msg_text,
        sender_role=SenderRole.CONSULTANT,
        sender_id=client_id,
        reply_to=reply_to,
        metadata=metadata,
    )

    chat_session.manual_mode = True
    await save_and_broadcast_new_message(manager, chat_session, new_msg, redis_key_session)
    await mongo_db.chats.update_one({"chat_id": chat_id}, {"$set": {"manual_mode": True}})

# ==============================
# БЛОК: AI-логика (GPT)
# ==============================

async def process_user_query_after_brief(
    manager: Any,
    chat_id: str,
    user_msg: ChatMessage,
    chat_session: ChatSession,
    redis_key_session: str,
    user_language: str,
    typing_manager: TypingManager,
    gpt_lock: Lock,
    user_data: dict
) -> Optional[ChatMessage]:
    """Обрабатывает запрос после брифа двухшаговой GPT-логикой."""
    try:
        async with gpt_lock:
            user_data = user_data or {}
            user_data["brief_info"] = extract_brief_info(chat_session)

            chat_history = chat_session.messages[-25:]
            print('5-???')
            kb_doc, kb_model = await get_knowledge_base()
            print('4-???')
            external_structs, _ = await collect_kb_structures_from_context(kb_model.context)
            merged_kb = merge_external_structures(
                kb_doc["knowledge_base"],
                external_structs
            )
            print('3-???')

            client_id = chat_session.client.client_id if chat_session.client else None
            print('3.1-???')
            gpt_data = await determine_topics_via_ai(
                user_message=user_msg.message,
                user_info=user_data,
                knowledge_base=merged_kb,
                chat_history=chat_history,
                client_id=client_id
            )
            
            user_msg.gpt_evaluation = GptEvaluation(
                topics=gpt_data["topics"],
                confidence=gpt_data["confidence"],
                out_of_scope=gpt_data["out_of_scope"],
                consultant_call=gpt_data["consultant_call"]
            )
            print('3.2-???')
            await update_gpt_evaluation_in_db(chat_session.chat_id, user_msg.id, user_msg.gpt_evaluation)

            lang = gpt_data.get("user_language") or user_language
            print('2-???')
            ai_msg = await build_ai_response(
                manager=manager,
                chat_session=chat_session,
                user_msg=user_msg,
                user_data=user_data,
                chat_history=chat_history,
                redis_key_session=redis_key_session,
                user_language=lang,
                typing_manager=typing_manager,
                chat_id=chat_id,
            )
            print('1-???')

            if ai_msg:
                await save_and_broadcast_new_message(manager, chat_session, ai_msg, redis_key_session)

            return ai_msg

    except asyncio.CancelledError:
        return None

    except Exception as e:
        logger.critical(
            f"[AI]: {e}",
        )
        fallback = (await get_bot_context()).get("fallback_ai_error_message", {}).get(
            user_language, "The assistant is currently unavailable."
        )
        fallback_msg = ChatMessage(message=fallback, sender_role=SenderRole.AI)
        await save_and_broadcast_new_message(manager, chat_session, fallback_msg, redis_key_session)
        return None


async def determine_topics_via_ai(
    user_message: str,
    user_info: dict,
    knowledge_base: dict[str, Any],
    chat_history: list[ChatMessage] | None = None,
    model_name: str | None = None,
    history_tail: int = 5,
    client_id: Optional[str] = None,
) -> dict[str, Any]:
    """Возвращает темы, оффтоп, вызов консультанта и язык пользователя."""
    bot_context = await get_bot_context()
    model_name = model_name or bot_context["ai_model"]
    print('0.1-???')
    kb_outline = build_kb_structure_outline(knowledge_base)
    print('0.2-???')
    topics_data = await detect_topics_ai(
        user_message=user_message,
        chat_history=chat_history,
        user_info=user_info,
        knowledge_base=kb_outline,
        model_name=model_name,
        bot_context=bot_context
    )
    print('0.3-???')
    outcome_data = await detect_outcome_ai(
        user_message=user_message,
        topics=topics_data["topics"],
        knowledge_base=knowledge_base,
        chat_history=chat_history,
        model_name=model_name,
        history_tail=history_tail,
        bot_context=bot_context,
        client_id=client_id
    )

    return {**topics_data, **outcome_data}


async def detect_topics_ai(
    user_message: str,
    chat_history: List[ChatMessage],
    user_info: dict,
    knowledge_base: Dict[str, Any],
    model_name: str,
    bot_context: dict
) -> Dict[str, Any]:
    """Определяет темы и confidence сообщения."""
    formatted_history = format_chat_history_from_models(chat_history)

    system_prompt = AI_PROMPTS["system_topics_prompt"].format(
        user_info=json.dumps(user_info, ensure_ascii=False, indent=2, cls=DateTimeEncoder),
        chat_history=formatted_history,
        kb_description=knowledge_base,
        app_description=bot_context["app_description"],
    )
    bundle = build_messages_for_model(
        system_prompt=system_prompt,
        messages_data=[],
        user_message="",
        model=model_name
    )

    resp = await chat_generate_any(
        model_name,
        bundle["messages"],
        system_instruction=bundle["system_instruction"]
    )
    res = extract_json_from_response(resp)

    return {
        "topics": res.get("topics", []),
        "confidence": res.get("confidence", 0.0)
    }



async def detect_outcome_ai(
    user_message: str,
    topics: list[dict[str, Any]],
    knowledge_base: dict[str, Any],
    chat_history: list[ChatMessage],
    model_name: str,
    history_tail: int,
    bot_context: dict,
    client_id: Optional[str] = None,
) -> dict[str, Any]:
    """Определяет оффтоп, вызов консультанта и язык ответа."""
    snippets = await extract_knowledge(topics, user_message, knowledge_base)
    last_messages = chat_history[-history_tail:] if chat_history else []

    formatted_history = format_chat_history_from_models(last_messages)

    system_prompt = AI_PROMPTS["system_outcome_analysis_prompt"].format(
        forbidden_topics=json.dumps(
            bot_context.get(
                "forbidden_topics",
                []),
            ensure_ascii=False),
        snippets=json.dumps(snippets, ensure_ascii=False),
        additional_instructions=bot_context.get("app_description"),
        chat_history=formatted_history
    )
    print("===== СИСТЕМНЫЙ ПРОМПТ ОПРЕДЕЛНИЯ =====")
    print(system_prompt)
    print("==========")

    bundle = build_messages_for_model(
        system_prompt=system_prompt,
        messages_data=[],
        user_message="",
        model=model_name
    )

    resp = await chat_generate_any(
        model_name,
        bundle["messages"],
        system_instruction=bundle["system_instruction"]
    )
    res = extract_json_from_response(resp)

    user_lang = res.get("user_language")
    if client_id and user_lang:
        await mongo_db.clients.update_one(
            {"client_id": client_id},
            {"$set": {"metadata.user_language": user_lang}}
        )

    print("===== РЕЗУЛЬТАТ =====")
    print(res)
    print("==========")

    return {
        "out_of_scope": res.get("out_of_scope", False),
        "consultant_call": res.get("consultant_call", False),
        "user_language": user_lang,
    }

# ==============================
# БЛОК: Вспомогательные функции
# ==============================

async def update_gpt_evaluation_in_db(
    chat_id: str,
    message_id: str,
    gpt_eval: GptEvaluation
) -> None:
    """Сохраняет оценку GPT в сообщении БД."""
    await mongo_db.chats.update_one(
        {"chat_id": chat_id, "messages.id": message_id},
        {"$set": {"messages.$.gpt_evaluation": gpt_eval.dict()}}
    )


def build_kb_description(knowledge_base: Dict[str, Any]) -> str:
    """Формирует текстовое описание базы знаний."""
    lines: list[str] = []
    for topic_name, topic_data in knowledge_base.items():
        subtopics = topic_data.get("subtopics", {})
        if subtopics:
            sub_lines = [
                f"- Subtopic: {sub_name}, Questions: "
                f'{", ".join(sd.get("questions", [])) or "No specific questions."}'
                for sub_name, sd in subtopics.items()
            ]
            lines.append(f"Topic: {topic_name}\n  " + "\n  ".join(sub_lines))
        else:
            lines.append(f"Topic: {topic_name} (No subtopics.)")
    return "\n".join(lines)


def build_kb_structure_outline(knowledge_base: dict[str, Any]) -> dict[str, Any]:
    """
    Строит компактное описание базы знаний без текста ответов.
    Только topic → subtopics → questions.
    """
    result: dict[str, Any] = {}

    for topic_name, topic_data in knowledge_base.items():
        topic_outline: dict[str, Any] = {}
        subtopics = topic_data.get("subtopics", {})

        if subtopics:
            sub_outline: dict[str, Any] = {}
            for sub_name, sub_data in subtopics.items():
                questions = list(sub_data.get("questions", {}).keys())
                sub_outline[sub_name] = {
                    "questions": questions
                }

            topic_outline["subtopics"] = sub_outline

        result[topic_name] = topic_outline

    return result


# ==============================
# БЛОК: Обработка ответа ИИ
# ==============================

async def build_ai_response(
    manager: Any,
    chat_session: ChatSession,
    user_msg: ChatMessage,
    user_data: dict,
    chat_history: List[ChatMessage],
    redis_key_session: str,
    user_language: str,
    typing_manager: TypingManager,
    chat_id: str
) -> Optional[ChatMessage]:
    """Формирует финальный ответ бота с учётом confidence и snippets."""
    confidence = user_msg.gpt_evaluation.confidence
    if (
        user_msg.gpt_evaluation.out_of_scope
        or user_msg.gpt_evaluation.consultant_call
        or confidence < 0.2
    ):
        chat_session.manual_mode = True
        await mongo_db.chats.update_one(
            {"chat_id": chat_session.chat_id},
            {"$set": {"manual_mode": True}}
        )

        bot_context = await get_bot_context()
        redirect_msg = bot_context.get("redirect_message", {}).get(
            user_language,
            "Please wait for a consultant."
        )
        session_doc = await mongo_db.chats.find_one({"chat_id": chat_session.chat_id})
        if session_doc:
            await send_message_to_bot(str(session_doc["_id"]), chat_session.model_dump(mode="python"))

        return ChatMessage(
            message=redirect_msg,
            sender_role=SenderRole.AI,
            choice_options=[
                (get_translation(
                    "choices",
                    "get_auto_mode",
                    user_language),
                    "/auto")],
            choice_strict=False
        )

    snippets_by_source = await extract_knowledge_with_sources(
        user_msg.gpt_evaluation.topics, user_msg.message
    )

    files: list[str] = []
    for topic_dict in snippets_by_source.values():
        for topic in topic_dict.values():
            for sub in topic.subtopics.values():
                for answer in sub.questions.values():
                    files.extend(answer.files or [])
    files = list(set(files))

    merged_snippet_tree: Dict[str, Topic] = {}
    for topic_dict in snippets_by_source.values():
        for name, topic in topic_dict.items():
            merged_snippet_tree.setdefault(
                name, topic).subtopics.update(
                topic.subtopics)

    message_before_postprocessing, final_text = await generate_ai_answer(
        user_message=user_msg.message,
        snippets=merged_snippet_tree,
        user_info=str(user_data),
        chat_history=chat_history,
        style="",
        user_language=user_language,
        typing_manager=typing_manager,
        manager=manager,
        chat_session=chat_session
    )

    ai_msg = ChatMessage(
        message=final_text if final_text else message_before_postprocessing,
        message_before_postprocessing=message_before_postprocessing,
        sender_role=SenderRole.AI,
        files=files,
        snippets_by_source=snippets_by_source
    )

    if 0.3 <= confidence < 0.7:
        ai_msg.choice_options = [
            get_translation(
                "choices",
                "consultant",
                user_language)]
        ai_msg.choice_strict = False

    return ai_msg


def remove_files_from_snippets(data: Any, files: List[str]) -> None:
    """Извлекает файлы из структуры snippets без изменения сигнатур."""
    if isinstance(data, dict):
        if "files" in data:
            files.extend(data["files"])
            del data["files"]
        for value in data.values():
            remove_files_from_snippets(value, files)
    elif isinstance(data, list):
        for item in data:
            remove_files_from_snippets(item, files)


# ==============================
# БЛОК: Извлечение знаний из базы
# ==============================

async def extract_knowledge(
    topics: List[Dict[str, Optional[str]]],
    user_message: Optional[str] = None,
    knowledge_base: Optional[Dict[str, dict]] = None
) -> Dict[str, Any]:
    """Возвращает релевантные фрагменты базы знаний по темам."""
    if knowledge_base is None:
        kb_doc, kb_model = await get_knowledge_base()
        merged = merge_external_structures(
            kb_doc["knowledge_base"],
            (await collect_kb_structures_from_context(kb_model.context))[0]
        )
        knowledge_base = merged

    result = {"topics": []}
    for item in topics:
        topic_name = item.get("topic", "")
        if topic_name not in knowledge_base:
            continue
        topic_entry = extract_topic_data(
            topic_name,
            item.get("subtopics", []),
            knowledge_base[topic_name]
        )
        if topic_entry["subtopics"]:
            result["topics"].append(topic_entry)

    return result if result["topics"] else {"topics": []}


def extract_topic_data(
    topic_name: str,
    subtopics: List[Dict[str, Any]],
    topic_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Формирует данные по теме для ответа бота."""
    result = {"topic": topic_name, "subtopics": []}
    subs = topic_data.get("subtopics", {})

    if subtopics:
        for sub in subtopics:
            name = sub.get("subtopic", "")
            if name in subs:
                sub_entry = extract_subtopic_data(
                    name, sub.get("questions", []), subs[name])
                if sub_entry["questions"]:
                    result["subtopics"].append(sub_entry)
    else:
        for name, data in subs.items():
            sub_entry = extract_subtopic_data(name, [], data)
            if sub_entry["questions"]:
                result["subtopics"].append(sub_entry)

    return result


def extract_subtopic_data(
    subtopic_name: str,
    questions: List[str],
    subtopic_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Возвращает ответы и файлы по подтеме."""
    sub_q = subtopic_data.get("questions", {})
    collected: Dict[str, Answer] = {}

    if questions:
        for user_q in questions:
            q_clean = user_q.lower().strip()
            for kb_q, ans in sub_q.items():
                if q_clean in kb_q.lower() or kb_q.lower() in q_clean:
                    text = ans.get("text", "").strip()
                    collected.setdefault(text, []).append(user_q)
                    break
    else:
        for kb_q, ans in sub_q.items():
            text = ans.get("text", "").strip()
            collected.setdefault(text, []).append(kb_q)

    result_q = {
        " ".join(sorted(set(q_list))): {
            "text": text,
            "files": sub_q.get("files", [])
        }
        for text, q_list in collected.items()
    }

    return {"subtopic": subtopic_name, "questions": result_q}


async def extract_knowledge_with_sources(
    topics: List[Dict[str, Optional[str]]],
    user_message: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """Группирует найденные знания по источникам (kb / context)."""
    kb_doc, kb_model = await get_knowledge_base()
    base_kb = kb_doc["knowledge_base"]
    context_entries = kb_model.context or []

    context_map: dict[str, str] = {}
    externals = []
    for ctx in context_entries:
        if ctx.kb_structure:
            for topic in ctx.kb_structure:
                context_map[topic] = str(ctx.id)
            externals.append(ctx.kb_structure)

    merged_kb = merge_external_structures(base_kb, externals)
    by_source: Dict[str, Dict[str, Topic]] = {}

    for item in topics:
        topic_name = item.get("topic", "")
        subs = item.get("subtopics", [])
        if topic_name not in merged_kb:
            continue

        topic_data = merged_kb[topic_name]
        sub_dict = topic_data.get("subtopics", {})
        extracted_subs: Dict[str, Subtopic] = {}

        for sub in subs:
            sub_name = sub.get("subtopic", "")
            if sub_name in sub_dict:
                questions = sub.get("questions", [])
                matched_q: dict[str, Answer] = {}
                for user_q in questions:
                    q_clean = user_q.lower().strip()
                    for kb_q, ans in sub_dict[sub_name]["questions"].items():
                        if q_clean in kb_q.lower() or kb_q.lower() in q_clean:
                            cleaned_files = [
                                f for f in (ans.get("files") or [])
                                if isinstance(f, str) and f.strip()
                            ]
                            matched_q[user_q] = Answer(
                                text=ans.get("text", ""),
                                files=cleaned_files,
                                source_ref=context_map.get(topic_name, "kb")
                            )
                            break
                if matched_q:
                    extracted_subs[sub_name] = Subtopic(questions=matched_q)

        if extracted_subs:
            source = context_map.get(topic_name, "kb")
            by_source.setdefault(source, {})[topic_name] = Topic(subtopics=extracted_subs)

    return by_source



# ==============================
# БЛОК: Генерация ответа AI
# ==============================

async def generate_ai_answer(
    user_message: str,
    snippets: List[str],
    user_info: str,
    chat_history: List[ChatMessage],
    user_language: str,
    typing_manager: TypingManager,
    chat_session: ChatSession,
    manager: ConnectionManager,
    style: str = "confident",
    return_json: bool = False,
) -> Union[str, Dict[str, Any]]:
    """Генерирует ответ бота, учитывая историю, язык и сниппеты."""
    bot_ctx = await get_bot_context()
    model_name = bot_ctx["ai_model"]
    temperature = bot_ctx["temperature"]
    chat_id = chat_session.chat_id

    weather_info = {
        loc["name"]: await get_weather_by_address(loc["address"])
        for loc in settings.LOCATION_INFO
    }

    system_prompt = assemble_system_prompt(
        bot_ctx, snippets, user_info, user_language, weather_info, chat_session
    )

    msg_bundle = build_messages_for_model(
        system_prompt=system_prompt,
        messages_data=chat_history,
        user_message=user_message,
        model=model_name
    )

    await typing_manager.add_typing(chat_id, "ai_bot", manager)

    try:
        resp = await chat_generate_any(
            model_name=model_name,
            messages=msg_bundle["messages"],
            temperature=temperature,
            system_instruction=msg_bundle.get("system_instruction")
        )
        message_before_postprocessing = extract_json_from_response(resp).get("text") or \
            resp["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        logging.error(f"AI generation failed: {e}")
        await typing_manager.remove_typing(chat_id, "ai_bot", manager)
        fallback_ai_text = bot_ctx.get("fallback_ai_error_message", {}).get(
            user_language, "The assistant is currently unavailable."
        )
        return fallback_ai_text, None

    ai_text = await postprocess_ai_response(
        raw_text=message_before_postprocessing,
        chat_history=chat_history,
        snippets=snippets,
        bot_context=bot_ctx,
        user_interface_language=user_language,
        chat_session=chat_session,
    )
    print("===== ДО =====")
    print(message_before_postprocessing)
    print("===== ПОСЛЕ =====")
    print(ai_text)

    await typing_manager.remove_typing(chat_id, "ai_bot", manager)
    final_ai_text = try_parse_json(ai_text) if return_json else ai_text
    return message_before_postprocessing, final_ai_text


async def postprocess_ai_response(
    *,
    raw_text: str,
    chat_history: List[ChatMessage],
    snippets: List[str],
    bot_context: dict,
    user_interface_language: str,
    chat_session: ChatSession,
) -> str:
    """Пост-обработка: проверка ссылок/медиа в зависимости от канала."""

    POSTPROCESS_INTERNAL = """
**Unrequested file links**
- If the AI inserted a Markdown or HTML link to a file (e.g., an image) from the `files` field, but the user **did not explicitly request a link**, remove the link.
- Preserve any leading sentence (e.g., “See attached photo”) but remove the clickable part — files are delivered automatically.
"""

    POSTPROCESS_EXTERNAL = """
**Photo link formatting**
- The assistant must NOT mention attached images; instead, include a Markdown link `[caption](URL)` when a file is available.
- If text contains phrases like “see attached photo/image”, replace them with the Markdown link; if no link is available, delete the phrase.
- Validate every Markdown link: it must contain a full URL with protocol (`https://`).
"""

    try:
        en_source = json.loads(chat_session.client.source).get("en")
    except Exception:
        en_source = "Unknown"

    dynamic_postprocess_rules = (
        POSTPROCESS_INTERNAL
        if en_source in {ChatSource.INTERNAL.en_value,
                         ChatSource.TELEGRAM_MINI_APP.en_value}
        else POSTPROCESS_EXTERNAL
    )

    system_prompt = AI_PROMPTS["postprocess_ai_answer"].format(
        ai_generated_response=raw_text.strip(),
        joined_snippets=snippets,
        user_interface_language=user_interface_language,
        postprocessing_instruction=bot_context.get("postprocessing_instruction", "None"),
        language_instruction="",
        conversation_history="\n".join(
            f"{m.sender_role.name.upper()}: {m.message.strip()}"
            for m in chat_history[-10:]
        ),
        dynamic_postprocess_rules=dynamic_postprocess_rules,
    )
    print(system_prompt)

    model_name = bot_context["ai_model"]
    bundle = build_messages_for_model(
        system_prompt=system_prompt,
        messages_data=[],
        user_message="",
        model=model_name
    )

    try:
        resp = await chat_generate_any(
            model_name,
            bundle["messages"],
            temperature=0.2,
            system_instruction=bundle["system_instruction"]
        )
        return (
            extract_json_from_response(resp).get("text")
            or resp["candidates"][0]["content"]["parts"][0]["text"].strip()
        )
    except Exception as e:
        logging.warning(f"Postprocess failed: {e}")
        return raw_text


def assemble_system_prompt(
    bot_context: Dict[str, Any],
    snippets: List[str],
    user_info: str,
    user_language: str,
    weather_info: Dict[str, Any],
    chat_session: ChatSession,
) -> str:
    """Собирает system-prompt с учётом канала и правил для медиа."""

    INTERNAL_IMAGE_RULE = """
**Image & file request**
- Mention (only sentences, not links) attached images/files only if entries exist in `files`, but **do not include links**, even if a URL is present.
- Never include Markdown or HTML links unless the user **explicitly asks for a link**.
- Do not reject user requests for photos — if files exist, they will be sent automatically; your task is to reference them naturally (e.g., “See attached image”, “Photo is included above”) without inserting a link.
"""

    EXTERNAL_IMAGE_RULE = """
**Photo request limitations**
- This channel does not support sending media directly.
- If the user asks for a photo, politely explain that images cannot be sent here, but you can share a direct link instead.
- When a file is available in `files`, include a Markdown link like `[photo-caption](https://example.com/image.jpg)` **inside the answer**.
- Never use phrases such as “See attached photo” or “Photo is included above”.
"""

    try:
        en_source = json.loads(chat_session.client.source).get("en")
    except Exception:
        en_source = "Unknown"

    if en_source in {ChatSource.INTERNAL.en_value,
                     ChatSource.TELEGRAM_MINI_APP.en_value}:
        dynamic_rules = INTERNAL_IMAGE_RULE
    else:
        dynamic_rules = EXTERNAL_IMAGE_RULE

    system_prompt = AI_PROMPTS["system_ai_answer"].format(
        settings_context=bot_context["prompt_text"],
        current_datetime=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        weather_info=weather_info,
        user_info=user_info,
        joined_snippets=snippets,
        system_language_instruction=(
            "Language settings:\n"
            "- Always respond in the language of the user's last message.\n"
        ),
        dynamic_rules=dynamic_rules,
    )

    return system_prompt


async def simulate_delay() -> None:
    """Имитирует задержку перед вызовом AI."""
    await asyncio.sleep(random.uniform(3, 7))


async def check_relevance_to_brief(question: str, user_message: str) -> bool:
    """Проверяет связь сообщения с вопросом брифа."""
    system_prompt = AI_PROMPTS["system_brief_relevance"].format(
        question=question,
        user_message=user_message
    )

    bundle = build_messages_for_model(
        system_prompt=system_prompt,
        messages_data=[],
        user_message="",
        model="gpt-3.5-turbo"
    )

    resp = await chat_generate_any(
        "gpt-3.5-turbo",
        bundle["messages"],
        temperature=0.1,
        system_instruction=bundle["system_instruction"]
    )
    answer = extract_json_from_response(resp).get("text") or \
        resp["candidates"][0]["content"]["parts"][0]["text"].strip()
    return answer.lower() == "yes"


# ==============================
# БЛОК: Обработка неизвестного типа сообщения
# ==============================

async def handle_unknown_type(
        manager: Any, chat_id: str, redis_session_key: str) -> None:
    """Обрабатывает неизвестный тип сообщения, отправляя ошибку в чат и лог."""
    logging.warning(f"Received unknown message type in chat {chat_id}.")
    response = custom_json_dumps(
        {"type": "error", "message": "Unknown type of message."})
    await manager.broadcast(response)


# ==============================
# БЛОК: Команды переключения режима чата
# ==============================

@command_handler("/manual")
async def set_manual_mode(manager: Any, chat_session: ChatSession, new_msg: ChatMessage,
                          user_language: str, redis_key_session: str):
    """Переключает чат в ручной режим."""
    await toggle_chat_mode(manager, chat_session, redis_key_session, manual_mode=True)
    await send_mode_change_message(manager, chat_session, user_language, redis_key_session, "manual_mode_enabled")


@command_handler("/auto")
async def set_auto_mode(manager: Any, chat_session: ChatSession, new_msg: ChatMessage,
                        user_language: str, redis_key_session: str):
    """Переключает чат в автоматический режим."""
    await toggle_chat_mode(manager, chat_session, redis_key_session, manual_mode=False)
    await send_mode_change_message(manager, chat_session, user_language, redis_key_session, "auto_mode_enabled")


# ==============================
# Вспомогательные функции для смены режима
# ==============================

async def toggle_chat_mode(manager: Any, chat_session: ChatSession,
                           redis_key_session: str, manual_mode: bool) -> None:
    """Переключает чат в указанный режим (ручной/автоматический)."""
    chat_session.manual_mode = manual_mode
    await mongo_db.chats.update_one({"chat_id": chat_session.chat_id}, {"$set": {"manual_mode": manual_mode}})
    await fill_remaining_brief_questions(chat_session.chat_id, chat_session)


async def send_mode_change_message(manager: Any, chat_session: ChatSession,
                                   user_language: str, redis_key_session: str, message_key: str) -> None:
    """Отправляет пользователю сообщение о смене режима."""
    response_text = get_translation("info", message_key, user_language)
    ai_msg = ChatMessage(message=response_text, sender_role=SenderRole.AI)
    await save_and_broadcast_new_message(manager, chat_session, ai_msg, redis_key_session)
