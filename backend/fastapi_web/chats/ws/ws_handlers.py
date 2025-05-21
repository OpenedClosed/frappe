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
from chats.integrations.constructor_chat.handlers import push_to_constructor
from chats.utils.commands import COMMAND_HANDLERS, command_handler
from chats.utils.help_functions import get_master_client_by_id
from db.mongo.db_init import mongo_client, mongo_db
from db.redis.db_init import redis_db
from gemini_base.gemini_init import gemini_client
from infra import settings
from knowledge.db.mongo.schemas import Answer, Subtopic, Topic
from knowledge.utils.help_functions import (build_messages_for_model,
                                            collect_kb_structures_from_context,
                                            get_knowledge_base,
                                            merge_external_structures,
                                            pick_model_and_client)
from openai_base.openai_init import openai_client
from pydantic import ValidationError
from users.db.mongo.enums import RoleEnum
from utils.help_functions import try_parse_json

from ..db.mongo.enums import ChatSource, ChatStatus, SenderRole
from ..db.mongo.schemas import (BriefAnswer, BriefQuestion, ChatMessage,
                                ChatReadInfo, ChatSession, GptEvaluation)
from ..utils.help_functions import (clean_markdown, find_last_bot_message,
                                    get_bot_context, get_weather_by_address,
                                    send_message_to_bot,
                                    split_text_into_chunks,
                                    update_read_state_for_client, format_chat_history_from_models)
from ..utils.knowledge_base import BRIEF_QUESTIONS
from ..utils.prompts import AI_PROMPTS
from ..utils.translations import TRANSLATIONS
from .ws_helpers import (ConnectionManager, TypingManager, custom_json_dumps,
                         gpt_task_manager)

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
    """Определяем тип сообщения и вызываем нужный handler."""

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

    # 💬 Получаем MasterClient из БД
    doc = await mongo_db.clients.find_one({"client_id": client_id})
    preferred_lang = (
        doc.get("metadata", {}).get("user_language")
        if doc else None
    ) or user_language  # если в БД нет — fallback

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
    update_data = {
        "$push": {"messages": new_msg.model_dump(mode="python")},
        "$set": {"last_activity": new_msg.timestamp}
    }
    await mongo_db.chats.update_one({"chat_id": chat_session.chat_id}, update_data, upsert=True)


async def broadcast_message(
        manager: Any, chat_session: ChatSession, new_msg: ChatMessage) -> None:
    """Отправляет новое сообщение в чат."""
    message_payload = custom_json_dumps({
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
    await manager.broadcast(message_payload)


async def save_and_broadcast_new_message(
    manager: Any,
    chat_session: ChatSession,
    new_msg: ChatMessage,
    redis_key_session: str
) -> None:
    """Сохраняет сообщение, отправляет в чат и Redis, и отправляет в интеграции."""
    await save_message_to_db(chat_session, new_msg)
    await broadcast_message(manager, chat_session, new_msg)
    await redis_db.set(redis_key_session, "1", ex=int(settings.CHAT_TIMEOUT.total_seconds()))
    if new_msg.sender_role != SenderRole.AI:
        await update_read_state_for_client(
            chat_id=chat_session.chat_id,
            client_id=new_msg.sender_id,
            user_id=None,
            last_read_msg=new_msg.id
        )


    if new_msg.sender_role != SenderRole.CLIENT:
        await send_message_to_external_meta_channel(chat_session, new_msg)


    try:
        await push_to_constructor(chat_session, [new_msg])
    except Exception as exc:
        logging.warning(
            f"Ошибка отправки в конструктор {chat_session.chat_id} {exc}"
        )


# ==============================
# БЛОК: Интеграция с Meta
# ==============================

async def send_message_to_external_meta_channel(
    chat_session: ChatSession,
    new_msg: ChatMessage
) -> None:
    """
    Отправляет сообщение в стороннюю интеграцию (Instagram / WhatsApp).
    """

    # 🔒 Защита от лупа: не слать назад Instagram-echo консультанта без external_id
    if (
        chat_session.client.source == ChatSource.INSTAGRAM
        and new_msg.metadata
        and new_msg.metadata.get("is_echo")
    ):
        external_id = new_msg.metadata.get("message_id") or new_msg.external_id
        if not external_id:
            logging.debug("⛔ IG: echo-сообщение без external_id — не отправляем в Instagram")
            return

        logging.debug("⛔ IG: consultant echo — не отправляем в Instagram (защита от лупа)")
        return

    # 📤 Debug — полное содержимое сообщения перед отправкой
    logging.debug(f"📤 Message dict перед отправкой:\n{new_msg.dict()}")

    source = chat_session.client.source
    client_id = chat_session.client.client_id

    master_client = await get_master_client_by_id(client_id)
    if not master_client:
        logging.warning(f"Не удалось найти master-клиента для {client_id}")
        return

    external_id = master_client.external_id
    message = new_msg.message

    # === Отправка в Instagram ===
    if source == ChatSource.INSTAGRAM:
        message_id = await send_instagram_message(external_id, new_msg)
        if message_id:
            # 💾 Обновляем external_id сообщения в базе
            await mongo_db.chats.update_one(
                {"chat_id": chat_session.chat_id, "messages.id": new_msg.id},
                {"$set": {"messages.$.external_id": message_id}}
            )
    # === Отправка в WhatsApp ===
    elif source == ChatSource.WHATSAPP:
        await send_whatsapp_message(external_id, message)
    else:
        logging.warning(f"Интеграция для источника {source} не реализована")


# ==============================
# Instagram
# ==============================


async def send_instagram_message(recipient_id: str, message_obj: ChatMessage) -> Optional[str]:
    """
    Отправляет сообщение в Instagram Direct:
    - Если есть хотя бы один файл — отправляет его как фото с подписью.
    - Иначе — просто текст.
    """
    url = "https://graph.instagram.com/v22.0/me/messages"
    headers = {
        "Authorization": f"Bearer {settings.INSTAGRAM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    text = message_obj.message.strip()
    files = message_obj.files or []

    # Берём только первую картинку
    # first_file = files[0] if files else None
    first_file = None

    if first_file:
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": "image",
                    "payload": {
                        "url": first_file,
                        "is_reusable": False
                    }
                },
                "text": text,
                "metadata": "broadcast"
            }
        }
    else:
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "text": text,
                "metadata": "broadcast"
            }
        }

    logging.debug(f"📤 IG payload: {json.dumps(payload, ensure_ascii=False)}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            logging.info(f"Отправлено в Instagram: {recipient_id}")
            return response_data.get("message_id")
        except httpx.HTTPError as exc:
            logging.error(f"Ошибка отправки в Instagram: {exc} — {response.text if 'response' in locals() else 'нет ответа'}")
            return None


import logging

import httpx

# async def send_instagram_message(recipient_id: str, message_obj: ChatMessage) -> Optional[str]:
#     """
#     Отправляет фото (если есть) и текст (если есть) в Instagram Direct.
#     Фото и подпись отправляются отдельными сообщениями.
#     """
#     import json

#     # url = f"https://graph.facebook.com/v22.0/{settings.INSTAGRAM_BOT_ID}/messages"
#     # access_token = settings.INSTAGRAM_ACCESS_TOKEN

#     url = f"https://graph.facebook.com/v22.0/{settings.APPLICATION_PAGE_ID}/messages"
#     access_token = settings.APPLICATION_ACCESS_TOKEN

#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }

#     text = message_obj.message.strip()
#     files = message_obj.files or []
#     image_url = files[0] if files else None

#     logging.debug(f"💬 Подготовка отправки Instagram-сообщения:")
#     logging.debug(f"↪ recipient_id = {recipient_id}")
#     logging.debug(f"↪ text = {text!r}")
#     logging.debug(f"↪ image_url = {image_url}")
#     logging.debug(f"↪ total files = {len(files)}")

#     async with httpx.AsyncClient() as client:
#         try:
#             # if image_url:
#             #     payload_image = {
#             #         "recipient": {"id": recipient_id},
#             #         "message": {
#             #             "attachment": {
#             #                 "type": "image",
#             #                 "payload": {
#             #                     "url": image_url,
#             #                     "is_reusable": False
#             #                 }
#             #             }
#             #         }
#             #     }

#             #     logging.debug("📤 Отправка изображения в Instagram...")
#             #     logging.debug(f"📦 payload_image: {json.dumps(payload_image, ensure_ascii=False)}")

#             #     response = await client.post(url, headers=headers, json=payload_image)
#             #     logging.debug(f"📥 Ответ на изображение: {response.status_code} — {response.text}")
#             #     response.raise_for_status()

#             if text:
#                 payload_text = {
#                     "recipient": {"id": recipient_id},
#                     "message": {
#                         "text": text
#                     }
#                 }

#                 logging.debug("📤 Отправка текста в Instagram...")
#                 logging.debug(f"📦 payload_text: {json.dumps(payload_text, ensure_ascii=False)}")

#                 response = await client.post(url, headers=headers, json=payload_text)
#                 logging.debug(f"📥 Ответ на текст: {response.status_code} — {response.text}")
#                 response.raise_for_status()

#             logging.info(f"📨 Успешно отправлено в Instagram: {recipient_id}")
#             return "ok"

#         except httpx.HTTPError as exc:
#             logging.error(f"❌ Ошибка при отправке в Instagram: {exc}")
#             if 'response' in locals():
#                 logging.error(f"🧾 Тело ответа: {response.status_code} — {response.text}")
#             return None



# ==============================
# WhatsApp
# ==============================

async def send_whatsapp_message(recipient_phone_id: str, message: str) -> None:
    """Отправляет сообщение в WhatsApp через Cloud API."""

    # Рабочий вариант с `me` (если токен привязан к номеру напрямую)
    # url = "https://graph.facebook.com/v22.0/me/messages"

    # Официальный вариант через phone_number_id
    url = f"https://graph.facebook.com/v22.0/{settings.WHATSAPP_BOT_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone_id,
        "type": "text",
        "text": {
            "body": message
        },
        "metadata": "broadcast"
    }

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                logging.info(f"Отправлено в WhatsApp: {recipient_phone_id}")
            else:
                logging.error(
                    f"Ошибка WhatsApp: {response.status_code} {response.text}"
                )
        except httpx.HTTPError as e:
            logging.error(f"HTTP ошибка при отправке в WhatsApp: {e}")


# ==============================
# БЛОК: Основные хэндлеры (статус, идентификация)
# ==============================

async def handle_status_check(
    manager: ConnectionManager,
    chat_id: str,
    redis_key_session: str
) -> None:
    """Проверяет статус чата, режим работы и прочитан ли чат хотя бы одним сотрудником."""

    remaining_time = max(await redis_db.ttl(redis_key_session), 0)

    chat_data = await mongo_db.chats.find_one(
        {"chat_id": chat_id},
        {"chat_id": 1, "manual_mode": 1, "read_state": 1, "messages": 1}
    )
    if not chat_data:
        return

    chat_session = ChatSession(**chat_data)

    staff_roles = [RoleEnum.ADMIN, RoleEnum.SUPERADMIN]
    staff_users_cursor = mongo_db.users.find(
        {"role": {"$in": [role.value for role in staff_roles]}}, {"_id": 1})
    staff_ids = {str(user["_id"]) async for user in staff_users_cursor}

    read_by_staff = chat_session.is_read_by_any_staff(staff_ids)

    response = custom_json_dumps({
        "type": "status_check",
        "message": "Session is active." if remaining_time > 0 else "Session is expired.",
        "remaining_time": remaining_time,
        "manual_mode": chat_session.manual_mode,
        "read_by_staff": read_by_staff
    })
    await manager.broadcast(response)


async def handle_get_my_id(manager: ConnectionManager,
                           chat_id: str, client_id: str) -> None:
    """Отправляет клиенту его идентификатор."""
    response = custom_json_dumps({"type": "my_id_info", "user_id": client_id})
    await manager.broadcast(response)


# ==============================
# БЛОК: Хэндлеры сообщений
# ==============================

# ==============================
# Получение всех сообщений
# ==============================

async def handle_get_messages(
    manager,
    chat_id: str,
    redis_key_session: str,
    data: dict,
    user_data: dict
) -> bool:
    """Отдаёт историю чата и, при наличии with_enter=True, фиксирует прочтение текущим клиентом."""
    chat_data: Dict[str, Any] | None = await mongo_db.chats.find_one({"chat_id": chat_id})

    if not chat_data:
        await manager.broadcast(custom_json_dumps({
            "type": "get_messages",
            "messages": [],
            "remaining_time": 0,
            "message": "No chat found."
        }))
        return False

    messages: List[dict] = chat_data.get("messages", [])
    messages.sort(key=lambda m: m.get("timestamp"))
    if not messages:
        remaining = max(await redis_db.ttl(redis_key_session), 0)
        await manager.broadcast(custom_json_dumps({
            "type": "get_messages",
            "messages": [],
            "remaining_time": remaining
        }))
        return messages

    last_id = messages[-1]["id"]
    client_id = user_data["client_id"]
    user_id = user_data.get("user_id")

    if data.get("with_enter"):
        await update_read_state_for_client(
            chat_id=chat_id,
            client_id=client_id,
            user_id=user_id,
            last_read_msg=last_id
        )

    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    read_state_raw = chat_data.get("read_state", [])
    read_state: List[ChatReadInfo] = [
        ChatReadInfo(**ri) if isinstance(ri, dict) else ri
        for ri in read_state_raw
    ]

    idx = {m["id"]: i for i, m in enumerate(messages)}
    enriched: List[dict] = []

    for m in messages:
        readers = [
            ri.client_id
            for ri in read_state
            if idx.get(ri.last_read_msg, -1) >= idx[m["id"]]
        ]
        m["read_by"] = readers
        enriched.append(m)

    remaining = max(await redis_db.ttl(redis_key_session), 0)
    await manager.broadcast(custom_json_dumps({
        "type": "get_messages",
        "messages": enriched,
        "remaining_time": remaining
    }))
    print('+'*100)
    print(enriched)

    return enriched


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
    metadata=data.get("metadata")

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

    await save_and_broadcast_new_message(manager, chat_session, new_msg, redis_key_session)

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


async def validate_chat_status(manager: ConnectionManager, client_id: str, chat_session: ChatSession,
                               redis_key_session: str, chat_id: str, user_language: str) -> bool:
    """Проверяет статус чата перед обработкой сообщений."""
    ttl_value = await redis_db.ttl(redis_key_session)
    dynamic_status = chat_session.compute_status(ttl_value)

    if dynamic_status != ChatStatus.IN_PROGRESS:
        await broadcast_error(manager, client_id, chat_id, get_translation("errors", "chat_status_invalid", user_language, status=dynamic_status.value))
        return False

    if ttl_value < 0 and chat_session.messages:
        await redis_db.set(redis_key_session, "1", ex=int(settings.CHAT_TIMEOUT.total_seconds()))

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
    manager: ConnectionManager, client_id: str, chat_session: ChatSession, redis_key_flood: str, mode: str, user_language: str
) -> bool:
    """
    Контроль частоты сообщений (flood control), учитывая режим чата (manual/automatic).
    """
    source = chat_session.client.source
    if source in {ChatSource.INSTAGRAM, ChatSource.WHATSAPP}:
        return True
    flood_timeout = settings.FLOOD_TIMEOUTS.get(mode)
    chat_id = chat_session.chat_id
    if flood_timeout:
        redis_key_mode_flood = f"{redis_key_flood}:{mode}"
        current_ts = datetime.utcnow().timestamp()
        last_sent_ts = safe_float(await redis_db.get(redis_key_mode_flood))

        if (current_ts - last_sent_ts) < flood_timeout.seconds:
            await broadcast_attention(manager, client_id, chat_id, get_translation("attention", "too_fast", user_language))
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
    Безопасное преобразование значения в `float`, возвращает 0.0 в случае ошибки.
    """
    try:
        return float(value) if value else 0.0
    except ValueError:
        return 0.0


# ==============================
# БЛОК: Работа с брифами (Brief)
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
    """Обрабатывает логику брифа, если чат в режиме 'brief'."""

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
    Инициализирует бриф:
    - Блокируем двойную отправку приветствия через Redis-флаг.
    - Проверяем, что в чате ещё нет сообщений.
    """
    welcome_flag_key = f"chat:welcome:{chat_session.chat_id}"

    if len(chat_session.messages) > 0 or not await redis_db.set(welcome_flag_key, "1", ex=60, nx=True):
        return

    bot_context = await get_bot_context()
    hello_text = bot_context.get(
        "welcome_message",
        "Hello!").get(
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
    """
    Обрабатывает пользовательский запрос после брифа, используя двухшаговую GPT-логику.
    Выполняется строго последовательно с помощью gpt_lock.
    Может быть отменена, если пришло новое сообщение.
    """
    try:
        async with gpt_lock:
            if not user_data:
                user_data = {}

            brief_info = extract_brief_info(chat_session)
            user_data["brief_info"] = brief_info

            chat_history = chat_session.messages[-25:]

            kb_doc, knowledge_base_model = await get_knowledge_base()
            knowledge_base = kb_doc["knowledge_base"]

            external_structs, _ = await collect_kb_structures_from_context(knowledge_base_model.context)
            merged_kb = merge_external_structures(knowledge_base, external_structs)

            # 💬 Получаем client_id, если доступен
            client_id = (
                chat_session.client.client_id
                if chat_session.client else None
            )

            gpt_data = await determine_topics_via_gpt(
                user_message=user_msg.message,
                user_info=user_data,
                knowledge_base=merged_kb,
                chat_history=chat_history,
                client_id=client_id
            )

            user_msg.gpt_evaluation = GptEvaluation(
                topics=gpt_data.get("topics", []),
                confidence=gpt_data.get("confidence", 0.0),
                out_of_scope=gpt_data.get("out_of_scope", False),
                consultant_call=gpt_data.get("consultant_call", False)
            )

            await update_gpt_evaluation_in_db(
                chat_session.chat_id,
                user_msg.id,
                user_msg.gpt_evaluation
            )

            # 💬 Приоритет: язык из gpt_data -> входной user_language
            lang = gpt_data.get("user_language") or user_language

            ai_msg = await build_ai_response(
                manager=manager,
                chat_session=chat_session,
                user_msg=user_msg,
                user_data=user_data,
                chat_history=chat_history,
                redis_key_session=redis_key_session,
                user_language=lang,
                typing_manager=typing_manager,
                chat_id=chat_id
            )

            if ai_msg:
                await save_and_broadcast_new_message(manager, chat_session, ai_msg, redis_key_session)

            return ai_msg

    except asyncio.CancelledError:
        logging.info(f"[GPT] Задача GPT для чата {chat_id} отменена.")
        return None

    except Exception as e:
        logging.error(f"[GPT] Ошибка обработки сообщения в чате {chat_id}: {e}")
        bot_context = await get_bot_context()
        fallback_text = bot_context.get("fallback_ai_error_message", {}).get(
            user_language, "The assistant is currently unavailable."
        )
        fallback_msg = ChatMessage(
            message=fallback_text,
            sender_role=SenderRole.AI,
        )
        if fallback_msg:
            await save_and_broadcast_new_message(manager, chat_session, fallback_msg, redis_key_session)
        return None


async def determine_topics_via_gpt(
    user_message: str,
    user_info: dict,
    knowledge_base: dict[str, Any],
    chat_history: list[ChatMessage] = None,
    model_name: str = "gemini-2.0-flash",
    history_tail: int = 5,
    client_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Двухэтапный анализ:
    1. Определение тем и confidence.
    2. Выявление out_of_scope, consultant_call и языка пользователя.
    """
    bot_context = await get_bot_context()

    topics_data = await detect_topics_gpt(
        user_message=user_message,
        chat_history=chat_history,
        user_info=user_info,
        knowledge_base=knowledge_base,
        model_name=model_name,
        bot_context=bot_context
    )

    outcome_data = await detect_outcome_gpt(
        user_message=user_message,
        topics=topics_data.get("topics", []),
        knowledge_base=knowledge_base,
        chat_history=chat_history,
        model_name=model_name,
        history_tail=history_tail,
        bot_context=bot_context,
        client_id=client_id  # 💬 для сохранения языка
    )

    return {
        "topics": topics_data.get("topics", []),
        "confidence": topics_data.get("confidence", 0.0),
        "out_of_scope": outcome_data.get("out_of_scope", False),
        "consultant_call": outcome_data.get("consultant_call", False),
        "user_language": outcome_data.get("user_language")  # 💬 возвращаем язык
    }


async def detect_topics_gpt(
    user_message,
    chat_history: List[ChatMessage],
    user_info: dict,
    knowledge_base: Dict[str, Any],
    model_name: str,
    bot_context: dict
) -> Dict[str, Any]:

    formatted_history = format_chat_history_from_models(chat_history)

    full_prompt = AI_PROMPTS["system_topics_prompt"].format(
        user_info=json.dumps(user_info, ensure_ascii=False, indent=2),
        chat_history=formatted_history,
        kb_description=knowledge_base,
        app_description=bot_context["app_description"],
    )

    if "<<<STATIC>>>" in full_prompt and "<<<DYNAMIC>>>" in full_prompt:
        static_part = full_prompt.split("<<<DYNAMIC>>>")[0].replace("<<<STATIC>>>", "").strip()
        dynamic_part = full_prompt.split("<<<DYNAMIC>>>")[1].strip()
    else:
        static_part = full_prompt.strip()
        dynamic_part = ""

    client, real_model = pick_model_and_client(model_name)
    temperature = 0.1

    if real_model.startswith("gpt"):
        messages = [{"role": "system", "content": static_part}]
        if dynamic_part:
            messages.append({"role": "system", "content": dynamic_part})
    elif real_model.startswith("gemini"):
        merged_prompt = f"{static_part}\n\n{dynamic_part}".strip()
        messages = [{"role": "user", "parts": [{"text": merged_prompt}]}]
    else:
        messages = [{"role": "system", "content": full_prompt}]

    print('*2*'*100)
    print(messages)
    print('*2*'*100)

    response = await client.chat_generate(
        model=real_model,
        messages=messages,
        temperature=temperature,
    )

    raw = response["candidates"][0]["content"]["parts"][0]["text"]
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    result = json.loads(match.group(0).replace("None", "null")) if match else {}

    return {
        "topics": result.get("topics", []),
        "confidence": result.get("confidence", 0.0)
    }



async def detect_outcome_gpt(
    user_message: str,
    topics: list[dict[str, Any]],
    knowledge_base: dict[str, Any],
    chat_history: list[ChatMessage],
    model_name: str,
    history_tail: int,
    bot_context: dict,
    client_id: Optional[str] = None,
) -> dict[str, Any]:
    """Возвращает признаки out_of_scope, consultant_call и сохраняет язык пользователя."""

    forbidden_topics = bot_context.get("forbidden_topics", [])
    snippets = await extract_knowledge(topics, user_message, knowledge_base)
    last_messages = chat_history[-history_tail:] if chat_history else []

    history_text = "\n".join(
        f"- {m.timestamp.isoformat()} {m.sender_role.value}: {m.message}"
        for m in last_messages
    )

    prompt = AI_PROMPTS["system_outcome_analysis_prompt"].format(
        forbidden_topics=json.dumps(forbidden_topics, ensure_ascii=False),
        snippets=json.dumps(snippets, ensure_ascii=False),
        additional_instructions=bot_context.get("app_description"),
        chat_history=history_text,
    )
    print(prompt)
    

    response = await gemini_client.chat_generate(
        model=model_name,
        messages=[{"role": "user", "parts": [{"text": prompt}]}],
        temperature=0.1,
        system_instruction=prompt,
    )

    raw = response["candidates"][0]["content"]["parts"][0]["text"]
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    result = json.loads(match.group(0)) if match else {}

    user_language = result.get("user_language")
    if client_id and user_language:
        await mongo_db.clients.update_one(
            {"client_id": client_id},
            {"$set": {"metadata.user_language": user_language}}
        )

    return {
        "out_of_scope": result.get("out_of_scope", False),
        "consultant_call": result.get("consultant_call", False),
        "user_language": user_language,
    }




# ==============================
# Вспомогательные функции
# ==============================

async def update_gpt_evaluation_in_db(
        chat_id: str, message_id: str, gpt_eval: GptEvaluation) -> None:
    """Обновляет поля GPT-оценки в документе сообщения."""
    await mongo_db.chats.update_one(
        {"chat_id": chat_id, "messages.id": message_id},
        {"$set": {"messages.$.gpt_evaluation": gpt_eval.dict()}}
    )


def build_kb_description(knowledge_base: Dict[str, Any]) -> str:
    """Формирует текстовое описание базы знаний для GPT."""
    lines = []
    for topic_name, topic_data in knowledge_base.items():
        line = f"Topic: {topic_name}"
        subtopics = topic_data.get("subtopics", {})
        if subtopics:
            sub_lines = []
            for subtopic_name, subtopic_data in subtopics.items():
                questions = subtopic_data.get("questions", [])
                question_list = ", ".join(
                    questions) if questions else "No specific questions."
                sub_lines.append(
                    f"- Subtopic: {subtopic_name}, Questions: {question_list}")
            line += "\n  " + "\n  ".join(sub_lines)
        else:
            line += " (No subtopics.)"
        lines.append(line)
    return "\n".join(lines)


# async def build_ai_response(
#     manager: Any,
#     chat_session: ChatSession,
#     user_msg: ChatMessage,
#     user_data: dict,
#     chat_history: List[ChatMessage],
#     redis_key_session: str,
#     user_language: str,
#     typing_manager: TypingManager,
#     chat_id: str
# ) -> Optional[ChatMessage]:
#     """
#     На основе результатов GPT (out_of_scope, confidence, consultant_call) формирует итоговое сообщение бота.
#     """
#     confidence = user_msg.gpt_evaluation.confidence
#     out_of_scope = user_msg.gpt_evaluation.out_of_scope
#     consultant_call = user_msg.gpt_evaluation.consultant_call

#     if out_of_scope or consultant_call or confidence < 0.2:
#         chat_session.manual_mode = True
#         await mongo_db.chats.update_one({"chat_id": chat_session.chat_id}, {"$set": {"manual_mode": True}})

#         bot_context = await get_bot_context()
#         redirect_msg = bot_context.get(
#             "redirect_message", "Bye!").get(
#             user_language, None)
#         session_doc = await mongo_db.chats.find_one({"chat_id": chat_session.chat_id})
#         if session_doc:
#             await send_message_to_bot(str(session_doc["_id"]), chat_session.model_dump(mode="python"))

#         return ChatMessage(
#             message=redirect_msg,
#             sender_role=SenderRole.AI,
#             choice_options=[
#                 (get_translation(
#                     "choices",
#                     "get_auto_mode",
#                     user_language),
#                     "/auto")],
#             choice_strict=False
#         )
#     snippet_data: Dict[str, Any] = await extract_knowledge(
#         user_msg.gpt_evaluation.topics, user_msg.message
#     )

#     files: List[str] = []
#     remove_files_from_snippets(snippet_data, files)

#     final_text = await generate_ai_answer(
#         user_message=user_msg.message,
#         snippets=snippet_data,
#         user_info=str(user_data),
#         chat_history=chat_history,
#         style="",
#         user_language=user_language,
#         typing_manager=typing_manager,
#         manager=manager,
#         chat_id=chat_id
#     )

#     if 0.3 <= confidence < 0.7:
#         return ChatMessage(
#             message=final_text,
#             sender_role=SenderRole.AI,
#             files=list(set(files)),
#             choice_options=[
#                 get_translation(
#                     "choices",
#                     "consultant",
#                     user_language)],
#             choice_strict=False
#         )

#     return ChatMessage(
#         message=final_text,
#         sender_role=SenderRole.AI,
#         files=list(set(files))
#     )

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
    """
    На основе результатов GPT (out_of_scope, confidence, consultant_call) формирует итоговое сообщение бота.
    """
    confidence = user_msg.gpt_evaluation.confidence
    out_of_scope = user_msg.gpt_evaluation.out_of_scope
    consultant_call = user_msg.gpt_evaluation.consultant_call

    if out_of_scope or consultant_call or confidence < 0.2:
        chat_session.manual_mode = True
        await mongo_db.chats.update_one({"chat_id": chat_session.chat_id}, {"$set": {"manual_mode": True}})

        bot_context = await get_bot_context()
        redirect_msg = bot_context.get(
            "redirect_message", "Bye!").get(
            user_language, None)
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

    # 🧠 Новый вызов: с источниками
    snippets_by_source: Dict[str, Dict[str, Topic]] = await extract_knowledge_with_sources(
        user_msg.gpt_evaluation.topics, user_msg.message
    )

    # 🧩 Сбор всех файлов (из всех источников)
    files: List[str] = []
    for topic_dict in snippets_by_source.values():
        for topic in topic_dict.values():
            for subtopic in topic.subtopics.values():
                for answer in subtopic.questions.values():
                    files.extend(answer.files or [])

    # 📦 Слияние всех тем в одну общую структуру (для передачи в генератор)
    merged_snippet_tree: Dict[str, Topic] = {}
    for topic_dict in snippets_by_source.values():
        for topic_name, topic in topic_dict.items():
            if topic_name not in merged_snippet_tree:
                merged_snippet_tree[topic_name] = topic
            else:
                # слияние подтем
                merged_snippet_tree[topic_name].subtopics.update(topic.subtopics)

    print("^"*100)
    print(files)
    print("^"*100)

    # 🤖 Генерация текста
    final_text = await generate_ai_answer(
        user_message=user_msg.message,
        snippets=merged_snippet_tree,
        user_info=str(user_data),
        chat_history=chat_history,
        style="",
        user_language=user_language,
        typing_manager=typing_manager,
        manager=manager,
        chat_id=chat_id
    )

    # 📌 Создаём итоговое сообщение ИИ с добавлением snippets_by_source
    ai_msg = ChatMessage(
        message=final_text,
        sender_role=SenderRole.AI,
        files=list(set(files)),
        snippets_by_source=snippets_by_source
    )

    # 🔘 Вариант с выбором консультанта при средней уверенности
    if 0.3 <= confidence < 0.7:
        ai_msg.choice_options = [
            get_translation("choices", "consultant", user_language)
        ]
        ai_msg.choice_strict = False

    return ai_msg



def remove_files_from_snippets(data: Any, files: List[str]) -> None:
    """Рекурсивно извлекает файлы из структуры snippet_data, удаляя их из исходных данных."""
    if isinstance(data, dict):
        if "files" in data:
            files.extend(data["files"])
            del data["files"]
        for key, value in data.items():
            remove_files_from_snippets(value, files)
    elif isinstance(data, list):
        for item in data:
            remove_files_from_snippets(item, files)


# ==============================
# БЛОК: Извлечение знаний из knowledge_base
# ==============================

async def extract_knowledge(
    topics: List[Dict[str, Optional[str]]],
    user_message: Optional[str] = None,
    knowledge_base: Optional[Dict[str, dict]] = None
) -> Dict[str, Any]:
    """
    Извлекает релевантную информацию из `knowledge_base` для списка тем, подтем и вопросов.
    Возвращает структуру вида:
    {
      "topics": [
        {
          "topic": ...,
          "subtopics": [
            {
              "subtopic": ...,
              "questions": {
                "Q1 Q2": { ... },  # склеенные дубликаты через пробел
                "Q3": { ... }
              }
            }
          ]
        }
      ]
    }
    Если ничего не найдено, возвращается {"topics": []}.
    """
    if not knowledge_base:
        kb_doc, knowledge_base_model = await get_knowledge_base()

        knowledge_base = kb_doc["knowledge_base"]

        external_structs, _ = await collect_kb_structures_from_context(knowledge_base_model.context)
        merged_kb = merge_external_structures(knowledge_base, external_structs)
        knowledge_base = merged_kb

    extracted_data = {"topics": []}

    for item in topics:
        topic_name = item.get("topic", "")
        subtopics = item.get("subtopics", [])

        if topic_name not in knowledge_base:
            continue

        topic_data = knowledge_base[topic_name]
        topic_entry = extract_topic_data(topic_name, subtopics, topic_data)

        if topic_entry["subtopics"]:
            extracted_data["topics"].append(topic_entry)

    return extracted_data if extracted_data["topics"] else {"topics": []}


def extract_topic_data(
    topic_name: str,
    subtopics: List[Dict[str, Any]],
    topic_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Формирует структуру данных по конкретной теме, включая подтемы и вопросы.
    """
    result = {"topic": topic_name, "subtopics": []}
    subs = topic_data.get("subtopics", {})

    if subtopics:
        for subtopic_item in subtopics:
            subtopic_name = subtopic_item.get("subtopic", "")
            questions = subtopic_item.get("questions", [])

            if subtopic_name and subtopic_name in subs:
                extracted_sub = extract_subtopic_data(
                    subtopic_name, questions, subs[subtopic_name]
                )
                if extracted_sub["questions"]:
                    result["subtopics"].append(extracted_sub)
    else:
        for sub_name, sub_data in subs.items():
            extracted_sub = extract_subtopic_data(sub_name, [], sub_data)
            if extracted_sub["questions"]:
                result["subtopics"].append(extracted_sub)

    return result


def extract_subtopic_data(
    subtopic_name: str,
    questions: List[str],
    subtopic_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    - Ищет частичное совпадение вопроса (lower/strip) в ключе базы знаний (или наоборот).
    - Если ответ уже есть, добавляет новый вопрос в ключ (склеивает через пробел).
    - Если questions=[] (нет уточнённых вопросов), возвращает все имеющиеся в подтеме.
    """
    result = {"subtopic": subtopic_name, "questions": {}}
    sub_q = subtopic_data.get("questions", {})

    answer_to_questions = {}

    if questions:
        for user_q_raw in questions:
            user_q_clean = user_q_raw.lower().strip()

            for kb_key, kb_value in sub_q.items():
                kb_key_clean = kb_key.lower().strip()

                if user_q_clean in kb_key_clean or kb_key_clean in user_q_clean:
                    answer_text = kb_value.get("text", "").strip()

                    if answer_text in answer_to_questions:
                        answer_to_questions[answer_text].append(user_q_raw)
                    else:
                        answer_to_questions[answer_text] = [user_q_raw]

                    break
    else:
        for kb_key, kb_value in sub_q.items():
            answer_text = kb_value.get("text", "").strip()
            if answer_text not in answer_to_questions:
                answer_to_questions[answer_text] = [kb_key]

    for answer_text, question_list in answer_to_questions.items():
        combined_question_key = " ".join(sorted(set(question_list)))
        result["questions"][combined_question_key] = {
            "text": answer_text,
            "files": sub_q.get(combined_question_key, {}).get("files", [])
        }

    return result


async def extract_knowledge_with_sources(
    topics: List[Dict[str, Optional[str]]],
    user_message: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Возвращает словарь структур знаний, сгруппированных по источнику:
    {
        "kb": { "Тема": Topic(...) },
        "65abc123": { "Доставка": Topic(...) },  # ID ContextEntry
    }
    """
    kb_doc, knowledge_base_model = await get_knowledge_base()
    base_kb = kb_doc["knowledge_base"]
    context_entries = knowledge_base_model.context or []

    context_map = {}  # topic -> source_ref (если из контекста)
    external_structs = []

    for ctx in context_entries:
        if ctx.kb_structure:
            ctx_topics = ctx.kb_structure.keys()
            for topic in ctx_topics:
                context_map[topic] = str(ctx.id)
            external_structs.append(ctx.kb_structure)

    merged_kb = merge_external_structures(base_kb, external_structs)

    result_by_source: Dict[str, Dict[str, Topic]] = {}

    for item in topics:
        topic_name = item.get("topic", "")
        subtopics = item.get("subtopics", [])

        if topic_name not in merged_kb:
            continue

        topic_data = merged_kb[topic_name]
        subtopics_data = topic_data.get("subtopics", {})
        extracted_subtopics = {}

        source_ref = context_map.get(topic_name, "kb")
        if source_ref not in result_by_source:
            result_by_source[source_ref] = {}

        for subtopic_item in subtopics:
            subtopic_name = subtopic_item.get("subtopic", "")
            questions = subtopic_item.get("questions", [])

            if subtopic_name not in subtopics_data:
                continue

            sub_data = subtopics_data[subtopic_name]["questions"]
            matched_questions = {}

            for user_q in questions:
                user_q_clean = user_q.lower().strip()
                for kb_q, ans in sub_data.items():
                    kb_q_clean = kb_q.lower().strip()
                    if user_q_clean in kb_q_clean or kb_q_clean in user_q_clean:
                        matched_questions[user_q] = Answer(
                            text=ans.get("text", ""),
                            files=ans.get("files", []),
                            source_ref=source_ref
                        )
                        break

            if matched_questions:
                extracted_subtopics[subtopic_name] = Subtopic(
                    questions=matched_questions
                )

        if extracted_subtopics:
            result_by_source[source_ref][topic_name] = Topic(
                subtopics=extracted_subtopics
            )

    return result_by_source



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
    chat_id: str,
    manager: ConnectionManager,
    style: str = "confident",
    return_json: bool = False,
) -> Union[str, Dict[str, Any]]:
    """
    Генерирует ответ от AI, учитывая историю чата, язык пользователя,
    сниппеты знаний и настройки бота из MongoDB, с последующей постобработкой.
    """
    print("*"*100)
    print(snippets)
    print("*"*100)
    bot_context = await get_bot_context()
    chosen_model = bot_context["ai_model"]
    chosen_temp = bot_context["temperature"]

    weather_info = {}
    for weather_address in settings.LOCATION_INFO:
        weather_info[weather_address["name"]] = await get_weather_by_address(address=weather_address["address"])

    system_prompt = assemble_system_prompt(
        bot_context, snippets, user_info, user_language, weather_info
    )

    msg_bundle = build_messages_for_model(
        system_prompt=system_prompt,
        messages_data=chat_history,
        user_message=user_message,
        model=chosen_model
    )

    await typing_manager.add_typing(chat_id, "ai_bot", manager)
    # Пока отключу фейк-задержу
    # await simulate_delay()

    client, real_model = pick_model_and_client(chosen_model)

    try:
        if real_model.startswith("gpt"):
            response = await client.chat.completions.create(
                model=real_model,
                messages=msg_bundle["messages"],
                temperature=chosen_temp
            )
            ai_text = response.choices[0].message.content.strip()

        elif real_model.startswith("gemini"):
            response = await client.chat_generate(
                model=real_model,
                messages=msg_bundle["messages"],
                temperature=chosen_temp,
                system_instruction=msg_bundle.get("system_instruction")
            )
            ai_text = response["candidates"][0]["content"]["parts"][0]["text"].strip()

        else:
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=msg_bundle["messages"],
                temperature=chosen_temp
            )
            ai_text = response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"AI generation failed: {e}")
        ai_text = bot_context.get("fallback_ai_error_message", {}).get(
            user_language, "The assistant is currently unavailable."
        )
        await typing_manager.remove_typing(chat_id, "ai_bot", manager)
        return ai_text
    
    print("===== Ответ до обработки =====")
    print(ai_text)
    

    ai_text = await postprocess_ai_response(
        raw_text=ai_text,
        chat_history=chat_history,
        snippets=snippets,
        bot_context=bot_context,
        user_interface_language=user_language,

    )
    

    print("===== Ответ после обработки =====")
    print(ai_text)

    await typing_manager.remove_typing(chat_id, "ai_bot", manager)

    if return_json:
        return try_parse_json(ai_text)

    return ai_text


async def postprocess_ai_response(
    *,
    raw_text: str,
    chat_history: List[ChatMessage],
    snippets: List[str],
    bot_context: dict,
    user_interface_language: str
) -> str:
    """
    Проверяет, соответствует ли ответ языку пользователя, не содержит ли он фейковые ссылки
    или вымышленные факты. Исправляет, если требуется.
    """
    admin_instruction = bot_context.get("postprocessing_instruction", "").strip()
    language_instruction = bot_context.get("language_instruction", "").strip()

    conversation_history = "\n".join(
        f"{msg.sender_role.name.upper()}: {msg.message.strip()}"
        for msg in chat_history[-10:]
    )

    full_prompt = AI_PROMPTS["postprocess_ai_answer"].format(
        ai_generated_response=raw_text.strip(),
        joined_snippets=snippets,
        user_interface_language=user_interface_language,
        postprocessing_instruction=admin_instruction or "None",
        language_instruction=language_instruction or "Always reply in the same language as the user's last message.",
        conversation_history=conversation_history
    )

    static_part, dynamic_part = "", ""
    if "<<<STATIC>>>" in full_prompt and "<<<DYNAMIC>>>" in full_prompt:
        static_part = full_prompt.split("<<<DYNAMIC>>>")[0].replace("<<<STATIC>>>", "").strip()
        dynamic_part = full_prompt.split("<<<DYNAMIC>>>")[1].strip()
    else:
        static_part = full_prompt.strip()

    model_name = bot_context.get("ai_model", "gpt-4o")
    temperature = 0.2
    client, real_model = pick_model_and_client(model_name)

    try:
        if real_model.startswith("gpt"):
            messages = [{"role": "system", "content": static_part}]
            if dynamic_part:
                messages.append({"role": "system", "content": dynamic_part})

        elif real_model.startswith("gemini"):
            merged_prompt = f"{static_part}\n\n{dynamic_part}".strip()
            messages = [{"role": "user", "parts": [{"text": merged_prompt}]}]

        else:
            # fallback: всё в одном system
            messages = [{"role": "system", "content": full_prompt}]

        if real_model.startswith("gpt"):
            result = await client.chat.completions.create(
                model=real_model,
                messages=messages,
                temperature=temperature
            )
            return result.choices[0].message.content.strip()

        elif real_model.startswith("gemini"):
            result = await client.chat_generate(
                model=real_model,
                messages=messages,
                temperature=temperature
            )
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()

        else:
            result = await openai_client.chat.completions.create(
                model=real_model,
                messages=messages,
                temperature=temperature
            )
            return result.choices[0].message.content.strip()

    except Exception as e:
        logging.warning(f"Ошибка постобработки: {e}")
        return raw_text





def assemble_system_prompt(
    bot_context: Dict[str, Any],
    snippets: List[str],
    user_info: str,
    user_language: str,
    weather_info: Dict[str, Any]
) -> str:
    """Формирует system-промпт, включая дату, погоду и инструкции для AI."""
    current_datetime = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    system_language_instruction = (
        f"Language settings:\n"
        f"IMPORTANT!!!:\n"
        f"- use THE SAME LANGUAGE the user used in their message (NOT EQUAL interface language)**.\n"
        f"- Always respond in the last user's (NOT BOT) message language. PLEASE!!!\n"
    )

    print(":"*100)
    print(AI_PROMPTS["system_ai_answer"].format(
        settings_context=bot_context["prompt_text"],
        current_datetime=current_datetime,
        weather_info=weather_info,
        user_info=user_info,
        joined_snippets=snippets,
        system_language_instruction=system_language_instruction
    ))
    print(":"*100)

    return AI_PROMPTS["system_ai_answer"].format(
        settings_context=bot_context["prompt_text"],
        current_datetime=current_datetime,
        weather_info=weather_info,
        user_info=user_info,
        joined_snippets=snippets,
        system_language_instruction=system_language_instruction
    )


async def simulate_delay() -> None:
    """Имитирует задержку от 5 до 15 секунд перед вызовом AI."""
    delay = random.uniform(3, 7)
    logging.info(f"⏳ Artificial delay {delay:.2f}s before AI generation...")
    await asyncio.sleep(delay)


async def check_relevance_to_brief(question: str, user_message: str) -> bool:
    """Проверяет, связано ли сообщение пользователя с вопросом брифа (через GPT)."""
    full_prompt = AI_PROMPTS["system_brief_relevance"].format(
        question=question,
        user_message=user_message
    )

    static_part, dynamic_part = "", ""
    if "<<<STATIC>>>" in full_prompt and "<<<DYNAMIC>>>" in full_prompt:
        static_part = full_prompt.split("<<<DYNAMIC>>>")[0].replace("<<<STATIC>>>", "").strip()
        dynamic_part = full_prompt.split("<<<DYNAMIC>>>")[1].strip()
    else:
        static_part = full_prompt.strip()

    messages = [{"role": "system", "content": static_part}]
    if dynamic_part:
        messages.append({"role": "system", "content": dynamic_part})

    response = await openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.1
    )
    return response.choices[0].message.content.strip().lower() == "yes"



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
