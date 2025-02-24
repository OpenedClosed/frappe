"""Обработчики веб-сокетов приложения Чаты."""
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import requests
from chats.utils.commands import COMMAND_HANDLERS, command_handler
from pydantic import ValidationError

from db.mongo.db_init import mongo_client, mongo_db
from db.redis.db_init import redis_db
from infra import settings
from openai_base.openai_init import openai_client

from ..db.mongo.enums import ChatSource, ChatStatus, SenderRole
from ..db.mongo.schemas import (BriefAnswer, BriefQuestion, ChatMessage,
                                ChatSession, GptEvaluation)
from ..utils.help_functions import find_last_bot_message, get_current_datetime, get_weather_by_address, get_weather_for_region, send_message_to_bot
from ..utils.knowledge_base import BRIEF_QUESTIONS, KNOWLEDGE_BASE
from ..utils.prompts import AI_PROMPTS
from ..utils.translations import TRANSLATIONS
from .ws_helpers import ConnectionManager, custom_json_dumps
from fastapi import HTTPException

async def get_knowledge_base() -> Dict[str, dict]:
    document = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
    if not document:
        raise HTTPException(404, "Knowledge base not found")
    document.pop("_id", None)
    if document["knowledge_base"]:
        return document["knowledge_base"]
    else:
        print('7777')
        return KNOWLEDGE_BASE



# ==============================
# БЛОК: Обработка входящих сообщений (router)
# ==============================


async def handle_message(
    manager: Any,
    data: Dict[str, Any],
    chat_id: str,
    client_id: str,
    redis_session_key: str,
    redis_flood_key: str,
    is_superuser: bool,
    user_language: str
) -> None:
    """Обрабатывает входящее сообщение от клиента."""

    handlers = {
        "status_check": handle_status_check,
        "get_messages": handle_get_messages,
        "new_message": handle_new_message_wrapper,
    }

    handler = handlers.get(data.get("type"), handle_unknown_type)

    if handler == handle_new_message_wrapper:
        async with await mongo_client.start_session() as session:
            await handler(
                manager, chat_id, client_id, redis_session_key, redis_flood_key, data, is_superuser, user_language
            )
    else:
        await handler(manager, chat_id, redis_session_key)


async def handle_new_message_wrapper(
    manager: Any,
    chat_id: str,
    client_id: str,
    redis_session_key: str,
    redis_flood_key: str,
    data: Dict[str, Any],
    is_superuser: bool,
    user_language: str
) -> None:
    """Обертка для обработки нового сообщения с сессией."""
    await handle_new_message(
        manager=manager,
        chat_id=chat_id,
        client_id=client_id,
        redis_key_session=redis_session_key,
        redis_key_flood=redis_flood_key,
        data=data,
        is_superuser=is_superuser,
        user_language=user_language,
    )


# ==============================
# БЛОК: Общие функции отправки системных сообщений (error, attention)
# ==============================


async def broadcast_system_message(
        manager: Any, client_id: str, chat_id: str, message: str, msg_type: str) -> None:
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
    """Отправляет сообщение-предупреждение."""
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
        "$push": {"messages": new_msg.model_dump()},
        "$set": {"last_activity": new_msg.timestamp}
    }
    await mongo_db.chats.update_one({"chat_id": chat_session.chat_id}, update_data, upsert=True)


async def broadcast_message(
        manager: Any, chat_session: ChatSession, new_msg: ChatMessage) -> None:
    """Формирует и отправляет новое сообщение в чат."""
    message_payload = custom_json_dumps({
        "type": "new_message",
        "id": new_msg.id,
        "chat_id": chat_session.chat_id,
        "sender_role": new_msg.sender_role.value,
        "message": new_msg.message,
        "reply_to": new_msg.reply_to,
        "choice_options": new_msg.choice_options,
        "choice_strict": new_msg.choice_strict,
        "timestamp": new_msg.timestamp.isoformat(),
        "external_id": new_msg.external_id
    })
    await manager.broadcast(message_payload)


async def save_and_broadcast_new_message(
    manager: Any,
    chat_session: ChatSession,
    new_msg: ChatMessage,
    redis_key_session: str
) -> None:
    """Сохраняет новое сообщение, отправляет в чат и обновляет TTL в Redis."""

    await save_message_to_db(chat_session, new_msg)
    await broadcast_message(manager, chat_session, new_msg)
    await redis_db.set(redis_key_session, chat_session.chat_id, ex=int(settings.CHAT_TIMEOUT.total_seconds()))

    if chat_session.client.source == ChatSource.INSTAGRAM:
        print('????')
        print(chat_session.client.external_id, chat_session.external_id)
        recipient_id = chat_session.client.external_id
        sender_role = new_msg.sender_role
        if sender_role != SenderRole.CLIENT:
            if recipient_id:
                await send_instagram_message(recipient_id, new_msg.message)



async def send_instagram_message(recipient_id: str, message: str) -> None:
    """Отправляет сообщение пользователю в Instagram Direct через API."""

    url = f"https://graph.instagram.com/v21.0/me/messages"

    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "metadata": "broadcast"
    }
    print(settings.INSTAGRAM_ACCESS_TOKEN)

    headers = {
        "Authorization": f"Bearer {settings.INSTAGRAM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print(f"Ошибка отправки сообщения в Instagram: {response.text}")
    else:
        print(f"Сообщение успешно отправлено в Instagram (ID: {recipient_id})")



# ==============================
# БЛОК: Основные хэндлеры (get_messages, new_message, status_check)
# ==============================


# async def handle_status_check(
#         manager: ConnectionManager, chat_id: str, redis_key_session: str) -> None:
#     """
#     Проверка статуса чата.
#     """
#     remaining_time = max(await redis_db.ttl(redis_key_session), 0)

#     response = custom_json_dumps({
#         "type": "status_check",
#         "message": "Session is active." if remaining_time > 0 else "Session is expired.",
#         "remaining_time": remaining_time
#     })
#     await manager.broadcast(response)

async def handle_status_check(
    manager: ConnectionManager, chat_id: str, redis_key_session: str
) -> None:
    """
    Проверка статуса чата и отправка информации о текущем режиме (авто/ручной).
    """
    remaining_time = max(await redis_db.ttl(redis_key_session), 0)

    # Получаем данные чата
    chat_session = await mongo_db.chats.find_one({"chat_id": chat_id}, {"manual_mode": 1})

    manual_mode = chat_session.get("manual_mode", False) if chat_session else False

    response = custom_json_dumps({
        "type": "status_check",
        "message": "Session is active." if remaining_time > 0 else "Session is expired.",
        "remaining_time": remaining_time,
        "manual_mode": manual_mode  # 🔥 Теперь фронтенд будет получать состояние чата
    })

    await manager.broadcast(response)



async def handle_get_messages(
        manager: ConnectionManager, chat_id: str, redis_key_session: str) -> None:
    """
    Получение истории сообщений чата.
    """
    chat_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_data:
        await manager.broadcast(generate_empty_chat_response())
        return

    chat_session = ChatSession(**chat_data)

    remaining_time = max(await redis_db.ttl(redis_key_session), 0)
    messages = [msg.model_dump() for msg in chat_session.messages]
    messages.sort(key=lambda x: x["timestamp"])

    response = custom_json_dumps({
        "type": "get_messages",
        "messages": messages,
        "remaining_time": remaining_time
    })
    await manager.broadcast(response)
    return messages


async def handle_new_message(
    manager: ConnectionManager,
    chat_id: str,
    client_id: str,
    redis_key_session: str,
    redis_key_flood: str,
    data: dict,
    is_superuser: bool,
    user_language: str,
) -> None:
    """
    Обработка нового сообщения от пользователя.
    """
    msg_text = data.get("message", "")
    reply_to = data.get("reply_to")
    external_id = data.get("external_id")

    if is_superuser:
        await handle_superuser_message(manager, client_id, chat_id, msg_text, reply_to, redis_key_session, user_language)
        return

    chat_session = await load_chat_data(manager, client_id, chat_id, user_language)
    if not chat_session:
        return

    if not await validate_chat_status(manager, client_id, chat_session, redis_key_session, chat_id, user_language):
        return
    
    new_msg = ChatMessage(
        message=msg_text,
        sender_role=SenderRole.CLIENT,
        reply_to=reply_to,
        external_id=external_id
    )
    
    if await handle_command(manager, redis_key_session, client_id, chat_id, chat_session, new_msg, user_language):
        return

    mode = chat_session.calculate_mode(BRIEF_QUESTIONS)

    if not await check_flood_control(manager, client_id, chat_id, redis_key_flood, mode, user_language):
        return

    if not await validate_choice(manager, client_id, chat_session, chat_id, msg_text, user_language):
        return

    await save_and_broadcast_new_message(manager, chat_session, new_msg, redis_key_session)

    if await handle_brief_mode(manager, client_id, chat_session, msg_text, chat_id, redis_key_session, user_language):
        return

    if chat_session.manual_mode:
        return

    await process_user_query_after_brief(manager, new_msg, chat_session, redis_key_session, user_language)


def generate_empty_chat_response() -> str:
    """
    Генерирует ответ, если чат отсутствует в БД.
    """
    return custom_json_dumps({
        "type": "get_messages",
        "messages": [],
        "remaining_time": 0,
        "message": "No chat found."
    })


# ==============================
# БЛОК: Логика загрузки/валидации чата
# ==============================


async def load_chat_data(manager: ConnectionManager, client_id: str,
                         chat_id: str, user_language: str) -> Optional[ChatSession]:
    """
    Загрузка данных чата из базы.
    """
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
    """
    Проверка статуса чата.
    """
    ttl_value = await redis_db.ttl(redis_key_session)
    dynamic_status = chat_session.compute_status(ttl_value)

    if dynamic_status != ChatStatus.IN_PROGRESS:
        await broadcast_error(
            manager,
            client_id,
            chat_id,
            get_translation(
                "errors",
                "chat_status_invalid",
                user_language,
                status=dynamic_status.value)
        )
        return False

    if ttl_value < 0 and not chat_session.messages:
        await redis_db.set(redis_key_session, chat_id, ex=int(settings.CHAT_TIMEOUT.total_seconds()))

    return True


async def handle_command(
    manager: Any,
    redis_key_session: str,
    client_id: str,
    chat_id: str,
    chat_session: ChatSession,
    new_msg: ChatMessage,
    user_language: str
) -> bool:
    """
    Обработка команды от пользователей.
    """
    msg_text = new_msg.message.strip()
    if not msg_text.startswith("/"):
        return False
    
    command_alias = msg_text.split()[0].lower()
    command_data = COMMAND_HANDLERS.get(command_alias)

    if command_data:
        handler = command_data["handler"]
        await save_and_broadcast_new_message(manager, chat_session, new_msg, redis_key_session)
        await handler(manager, chat_session, new_msg, user_language, redis_key_session)
    else:
        unknown_cmd_msg = get_translation("attention", "unknown_command", user_language)
        await broadcast_attention(manager, client_id, chat_id, unknown_cmd_msg)
    
    return True


def get_translation(category: str, key: str, language: str, **kwargs) -> str:
    """
    Получает перевод из `TRANSLATIONS`, подставляя переменные.
    """
    category_data = TRANSLATIONS.get(category, {})

    if isinstance(category_data, dict):
        if key is not None:
            translation_data = category_data.get(key, {})
            if isinstance(translation_data, str):
                template = translation_data
            else:
                template = translation_data.get(
                    language, translation_data.get("en", ""))
        else:
            template = category_data.get(language, category_data.get("en", ""))
    else:
        template = category_data

    return template.format(**kwargs) if isinstance(template,
                                                   str) and kwargs else template

# ==============================
# БЛОК: Flood control и проверка выбора
# ==============================


async def check_flood_control(
    manager: ConnectionManager, client_id: str, chat_id: str, redis_key_flood: str, mode: str, user_language: str
) -> bool:
    """
    Контроль частоты сообщений (flood control), учитывая режим чата (manual/automatic).
    """
    flood_timeout = settings.FLOOD_TIMEOUTS.get(mode)
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
    """
    Обрабатывает логику брифа: если чат в режиме 'brief',
    проверяет релевантность сообщения и задаёт/завершает вопросы.
    """
    if chat_session.calculate_mode(BRIEF_QUESTIONS) != "brief":
        return False

    current_question = chat_session.get_current_question(BRIEF_QUESTIONS)
    if not current_question:
        await complete_brief(manager, chat_session, redis_key_session, user_language)
        return False

    if not await check_relevance_to_brief(current_question.question, msg_text):
        await fill_remaining_brief_questions(chat_id, chat_session)
        return False

    await process_brief_question(client_id, chat_session, msg_text, manager, redis_key_session, user_language)
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
    user_language: str
) -> None:
    """Инициализирует бриф: если вопрос есть — задаём, если нет — завершаем."""
    question = chat_session.get_current_question(BRIEF_QUESTIONS)
    hello_text = get_translation(
        "brief",
        "hello_text",
        user_language,
        default_key="en"
    )
    if hello_text:
        msg = ChatMessage(
            message=f"{hello_text}",
            sender_role=SenderRole.AI,
        )
        await save_and_broadcast_new_message(manager, chat_session, msg, redis_key_session)
    if not question:
        # await complete_brief(manager, chat_session, redis_key_session, user_language)
        return

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
    Обрабатывает текущий вопрос брифа и втоматически задаём следующий вопрос, если он есть.
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
                choices=', '.join(translated_answers))
            await broadcast_error(manager, client_id, chat_session.chat_id, error_msg)
            return

    ans = BriefAnswer(
        question=question.question,
        expected_answers=question.expected_answers,
        user_answer=user_message
    )
    await mongo_db.chats.update_one(
        {"chat_id": chat_session.chat_id},
        {"$push": {"brief_answers": ans.model_dump()}}
    )

    updated_data = await mongo_db.chats.find_one({"chat_id": chat_session.chat_id})
    chat_session.__dict__.update(ChatSession(**updated_data).__dict__)

    next_question = chat_session.get_current_question(BRIEF_QUESTIONS)
    if next_question:
        question = next_question

        translated_q = question.question_translations.get(
            user_language, question.question)

        if question.question_type == "choice" and question.expected_answers:
            msg = ChatMessage(
                # message=f"{please_choose} {translated_q}",
                message=f"{translated_q}",
                sender_role=SenderRole.AI,
                # choice_options=[
                #     question.expected_answers_translations.get(user_language, opt)
                #     for opt in question.expected_answers_translations.get("en", [])
                # ],
                choice_options=question.expected_answers_translations.get(user_language, question.expected_answers_translations.get("en")),
                choice_strict=True
            )
        elif question.question_type == "text" and question.expected_answers:
            msg = ChatMessage(
                # message=f"{please_choose} {translated_q}",
                message=f"{translated_q}",
                sender_role=SenderRole.AI,
                # choice_options=[
                #     question.expected_answers_translations.get(user_language, opt)
                #     for opt in question.expected_answers_translations.get("en", [])
                # ],
                choice_options=question.expected_answers_translations.get(user_language, question.expected_answers_translations.get("en")),
                choice_strict=False
            )
        else:
            msg = ChatMessage(
                message=translated_q,
                sender_role=SenderRole.AI,
                choice_strict=False)

        await save_and_broadcast_new_message(manager, chat_session, msg, redis_key_session)


def extract_brief_info(chat_session: ChatSession) -> str:
    """Возвращает строку с ответами брифа для контекста GPT."""
    return "; ".join(
        f"{a.question}: {a.user_answer if a.user_answer else '(Without answer)'}" for a in chat_session.brief_answers)


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
    """Если ответ нерелевантен, помечаем оставшиеся вопросы пустыми ответами."""
    answered = {a.question for a in chat_session.brief_answers}
    unanswered = [q for q in BRIEF_QUESTIONS if q.question not in answered]
    for question in unanswered:
        empty = BriefAnswer(
            question=question.question,
            expected_answers=question.expected_answers,
            user_answer='')
        await mongo_db.chats.update_one(
            {"chat_id": chat_id},
            {"$push": {"brief_answers": empty.model_dump()}}
        )


async def ask_brief_question(
    manager: ConnectionManager,
    chat_session: ChatSession,
    question: BriefQuestion,
    redis_key_session: str,
    user_language: str
) -> None:
    """Задаёт вопрос брифа: если question_type='choice' — выставляем choice_options."""
    # please_choose = get_translation(
    #     "brief",
    #     "please_choose",
    #     user_language,
    #     default_key="en")
    translated_q = question.question_translations.get(
        user_language, question.question)

    if question.question_type == "choice" and question.expected_answers:
        msg = ChatMessage(
            # message=f"{please_choose} {translated_q}",
            message=f"{translated_q}",
            sender_role=SenderRole.AI,
            # choice_options=[
            #     question.expected_answers_translations.get(user_language, opt)
            #     for opt in question.expected_answers_translations.get("en", [])
            # ],
            choice_options=question.expected_answers_translations.get(user_language, question.expected_answers_translations.get("en")),
            choice_strict=True
        )
    elif question.question_type == "text" and question.expected_answers:
        msg = ChatMessage(
            # message=f"{please_choose} {translated_q}",
            message=f"{translated_q}",
            sender_role=SenderRole.AI,
            # choice_options=[
            #     question.expected_answers_translations.get(user_language, opt)
            #     for opt in question.expected_answers_translations.get("en", [])
            # ],
            choice_options=question.expected_answers_translations.get(user_language, question.expected_answers_translations.get("en")),
            choice_strict=False
        )
    else:
        msg = ChatMessage(
            message=translated_q,
            sender_role=SenderRole.AI,
            choice_strict=False)

    await save_and_broadcast_new_message(manager, chat_session, msg, redis_key_session)


async def broadcast_brief_question(
    manager: ConnectionManager,
    question: BriefQuestion,
    user_language: str
) -> None:
    """Отправляет клиенту JSON о новом вопросе брифа (без сохранения в БД)."""
    translated_q = question.question_translations.get(
        user_language, question.question)
    translated_a = question.expected_answers_translations.get(
        user_language, question.expected_answers) if question.expected_answers_translations else None
    payload = {
        "type": "brief_question",
        "question": translated_q,
        "expected_answers": translated_a
    }
    await manager.broadcast(custom_json_dumps(payload))


# ==============================
# БЛОК: Сообщения от суперпользователя
# ==============================


async def handle_superuser_message(
    manager: ConnectionManager,
    client_id: str,
    chat_id: str,
    msg_text: str,
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
        reply_to=reply_to
    )

    chat_session.manual_mode = True
    await save_and_broadcast_new_message(manager, chat_session, new_msg, redis_key_session)

    await mongo_db.chats.update_one({"chat_id": chat_id}, {"$set": {"manual_mode": True}})


# ==============================
# БЛОК: AI-логика (GPT)
# ==============================


async def process_user_query_after_brief(
    manager: Any,
    user_msg: ChatMessage,
    chat_session: ChatSession,
    redis_key_session: str,
    user_language: str
) -> ChatMessage:
    """Обрабатывает пользовательский запрос после брифа с учётом GPT и языка пользователя."""

    user_info = extract_brief_info(chat_session)
    chat_history = chat_session.messages[-25:]
    knowledge_base = await get_knowledge_base()
    gpt_data = await determine_topics_via_gpt(user_msg.message, user_info, knowledge_base)

    topics = gpt_data.get("topics", [])
    confidence = gpt_data.get("confidence", 0.0)
    out_of_scope = gpt_data.get("out_of_scope", False)
    consultant_call = gpt_data.get("consultant_call", False)

    user_msg.gpt_evaluation = GptEvaluation(
        topics=topics,
        confidence=confidence,
        out_of_scope=out_of_scope,
        consultant_call=consultant_call
    )

    await mongo_db.chats.update_one(
        {"chat_id": chat_session.chat_id, "messages.id": user_msg.id},
        {"$set": {"messages.$.gpt_evaluation": user_msg.gpt_evaluation.dict()}}
    )

    ai_msg: Optional[ChatMessage] = None

    if out_of_scope or consultant_call or confidence < 0.3:
        chat_session.manual_mode = True
        await mongo_db.chats.update_one({"chat_id": chat_session.chat_id}, {"$set": {"manual_mode": True}})

        failure_message = get_translation(
            "errors",
            "complex_question",
            user_language,
            phone="+48 733 949 041"
        )

        session_doc = await mongo_db.chats.find_one({"chat_id": chat_session.chat_id})
        session_id = str(session_doc["_id"]) if session_doc else ""
        await send_message_to_bot(session_id, chat_session.model_dump())

        ai_msg = ChatMessage(
            message=failure_message,
            sender_role=SenderRole.AI,
            choice_options=[
                (get_translation("choices", "get_auto_mode", user_language), "/auto"),
            ],
            choice_strict=False
        )

    else:
        snippet_list: List[str] = await extract_knowledge(topics, user_msg.message)

        if 0.3 <= confidence < 0.7:
            partial_text = await generate_ai_answer(
                user_message=user_msg.message,
                snippets=snippet_list,
                user_info=user_info,
                chat_history=chat_history,
                style="partial",
                user_language=user_language
            )

            ai_msg = ChatMessage(
                message=partial_text,
                sender_role=SenderRole.AI,
                choice_options=[
                    get_translation(
                        "choices",
                        "consultant",
                        user_language)
                ],
                choice_strict=False
            )

        else:
            final_text = await generate_ai_answer(
                user_message=user_msg.message,
                snippets=snippet_list,
                user_info=user_info,
                chat_history=chat_history,
                style="confident",
                user_language=user_language
            )

            ai_msg = ChatMessage(message=final_text, sender_role=SenderRole.AI)

    if ai_msg:
        await save_and_broadcast_new_message(manager, chat_session, ai_msg, redis_key_session)

    return ai_msg



async def determine_topics_via_gpt(
    user_message: str,
    user_info: str,
    knowledge_base: Dict[str, Any]
) -> Dict[str, Any]:
    """Запрос к GPT для определения тем, подтем, вопросов и вычисления confidence/out_of_scope/consultant_call."""
    topic_lines = []
    for topic_name, topic_data in knowledge_base.items():
        topic_line = f"Topic: {topic_name}"
        subtopics = topic_data.get("subtopics", {})

        if subtopics:
            subtopic_lines = []
            for subtopic_name, subtopic_data in subtopics.items():
                questions = subtopic_data.get("questions", [])
                question_list = ", ".join(questions) if questions else "No specific questions."
                subtopic_lines.append(f"- Subtopic: {subtopic_name}, Questions: {question_list}")

            topic_line += "\n  " + "\n  ".join(subtopic_lines)
        else:
            topic_line += " (No subtopics.)"

        topic_lines.append(topic_line)

    kb_description = "\n".join(topic_lines)

    system_prompt = AI_PROMPTS["system_topics_prompt"].format(
        user_info=user_info,
        kb_description=kb_description
    )

    messages = [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_message.strip()}
    ]

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1
    )

    raw_content = response.choices[0].message.content.strip()

    match = re.search(r"\{.*\}", raw_content, re.DOTALL)
    if not match:
        return {"topics": [], "confidence": 0.0, "out_of_scope": False, "consultant_call": False}

    json_text = match.group(0)
    try:
        result = json.loads(json_text)
        topics = result.get("topics", [])
        confidence = result.get("confidence", 0.0)
        out_of_scope = result.get("out_of_scope", False)
        consultant_call = result.get("consultant_call", False)

        return {
            "topics": topics if isinstance(topics, list) else [],
            "confidence": confidence,
            "out_of_scope": out_of_scope,
            "consultant_call": consultant_call
        }
    except json.JSONDecodeError:
        return {"topics": [], "confidence": 0.0, "out_of_scope": False, "consultant_call": False}


# def extract_knowledge(
#         topics: List[Dict[str, Optional[str]]], user_message: str) -> List[str]:
#     """Извлекает ответы из knowledge_base для списка тем/подтем."""
#     snippets: List[str] = []
#     for item in topics:
#         topic = item.get("topic", "")
#         subtopic = item.get("subtopic", "")
#         if topic not in knowledge_base:
#             continue
#         topic_data = knowledge_base[topic]
#         subs = topic_data.get("subtopics", {})

#         if subtopic and subtopic in subs:
#             for q_text, ans_text in subs[subtopic].get(
#                     "questions", {}).items():
#                 snippets.append(f"Q: {q_text}\nA: {ans_text}")
#         elif not subtopic:
#             for _, st_data in subs.items():
#                 for q_text, ans_text in st_data.get("questions", {}).items():
#                     snippets.append(f"Q: {q_text}\nA: {ans_text}")

#     return snippets if snippets else ["No relevant data found."]


from typing import List, Dict, Optional

async def extract_knowledge(topics: List[Dict[str, Optional[str]]], user_message: Optional[str]=None, knowledge_base: Optional[Dict[str, dict]]={}) -> List[str]:
    """Извлекает ответы из knowledge_base для списка тем, подтем и вопросов."""
    snippets: List[str] = []
    print('===========================TOPICS===========================')
    print(topics)
    print()
    if not knowledge_base:
        knowledge_base = await get_knowledge_base()
    for item in topics:
        topic_name = item.get("topic", "")
        subtopics = item.get("subtopics", [])

        if topic_name not in knowledge_base:
            continue

        topic_data = knowledge_base[topic_name]
        subs = topic_data.get("subtopics", {})

        if subtopics:
            for subtopic_item in subtopics:
                subtopic_name = subtopic_item.get("subtopic", None)
                questions = subtopic_item.get("questions", [])

                if subtopic_name and subtopic_name in subs:
                    subtopic_data = subs[subtopic_name]

                    if questions:
                        for q_text in questions:
                            if q_text in subtopic_data.get("questions", {}):
                                ans_text = subtopic_data["questions"][q_text]
                                snippets.append(f"Q: {q_text}\nA: {ans_text}")
                    
                    else:
                        for q_text, ans_text in subtopic_data.get("questions", {}).items():
                            snippets.append(f"Q: {q_text}\nA: {ans_text}")

        else:
            for _, subtopic_data in subs.items():
                for q_text, ans_text in subtopic_data.get("questions", {}).items():
                    snippets.append(f"Q: {q_text}\nA: {ans_text}")

    return snippets if snippets else ["No relevant data found."]


async def generate_ai_answer(
    user_message: str,
    snippets: List[str],
    user_info: str,
    chat_history: List[ChatMessage],
    user_language: str,
    style: str = "confident",
    return_json: bool = False
) -> Union[str, Dict[str, Any]]:
    """Генерирует ответ через GPT с учётом истории чата и языка."""
    joined_snippets = "\n- " + "\n- ".join(snippets) if snippets else ""
    style_description = "Please provide a short partial answer." if style == "partial" else "Please provide a thorough, confident answer."
    if return_json:
        style_description += "\nReturn valid JSON only. Do not include extra text."

    system_language_instruction = f"Language settings:\n- The interface language for the user is '{user_language}'.\n- You should prioritize responding in the language of the user's message.\n"

    current_datetime = get_current_datetime()
    weather_info = {
        # "Tbilisi": await get_weather_for_region("Tbilisi, Georgia"),
        # "Batumi": await get_weather_for_region("Batumi, Georgia")
        # "Nika Hotel & Club": await get_weather_by_address(address="Chanchkhalo, Adjara, Georgia"),

        # "Nika Hotel & Club": await get_weather_by_address(address="деревня Чанчхало, Аджария, Грузия"),
        # "Moscow": await get_weather_by_address(address="Москва")
    }
    print('+'*100)
    print(weather_info)
    # weather_info = {}

    system_prompt = AI_PROMPTS["system_ai_answer"].format(
        current_datetime=current_datetime,
        weather_info=weather_info,
        user_info=user_info,
        joined_snippets=joined_snippets,
        style_description=style_description,
        system_language_instruction=system_language_instruction
    ).strip()

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt}]
    for msg in chat_history:
        if msg.sender_role == SenderRole.CLIENT:
            messages.append({"role": "user", "content": msg.message})
        elif msg.sender_role == SenderRole.AI:
            messages.append({"role": "assistant", "content": msg.message})
    messages.append({"role": "user", "content": user_message})

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7
    )
    gpt_text = response.choices[0].message.content.strip()

    if not return_json:
        return gpt_text

    try:
        return json.loads(gpt_text)
    except json.JSONDecodeError:
        return {"error": "GPT returned invalid JSON", "original": gpt_text}


async def check_relevance_to_brief(question: str, user_message: str) -> bool:
    """Проверяет, связано ли сообщение пользователя с вопросом брифа (через GPT)."""
    system_prompt = AI_PROMPTS["system_brief_relevance"].format(
        question=question,
        user_message=user_message
    )

    response = await openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": system_prompt.strip()}],
        temperature=0.1
    )
    return response.choices[0].message.content.strip().lower() == "yes"


# ==============================
# БЛОК: Неизвестный тип сообщения
# ==============================


async def handle_unknown_type(
    manager: Any,
    chat_id: str,
    redis_session_key: str,
) -> None:
    """Обрабатывает неизвестный тип сообщения."""
    response = custom_json_dumps(
        {"type": "error", "message": "Unknown type of message."})
    await manager.broadcast(response)

# ==============================
# БЛОК: Команды
# ==============================


@command_handler("/manual")
async def set_manual_mode(
    manager: Any,
    chat_session: ChatSession,
    new_msg: ChatMessage,
    user_language: str,
    redis_key_session: str,
):
    """Переключает чат в ручной режим."""
    chat_session.manual_mode = True
    await mongo_db.chats.update_one(
        {"chat_id": chat_session.chat_id},
        {"$set": {"manual_mode": True}}
    )

    response_text = get_translation("info", "manual_mode_enabled", user_language)
    await fill_remaining_brief_questions(chat_session.chat_id, chat_session)

    ai_msg = ChatMessage(message=response_text, sender_role=SenderRole.AI)
    await save_and_broadcast_new_message(manager, chat_session, ai_msg, redis_key_session)

@command_handler("/auto")
async def set_auto_mode(
    manager: Any,
    chat_session: ChatSession,
    new_msg: ChatMessage,
    user_language: str,
    redis_key_session: str,
):
    """Переключает чат в автоматический режим."""
    chat_session.manual_mode = False
    await mongo_db.chats.update_one(
        {"chat_id": chat_session.chat_id},
        {"$set": {"manual_mode": False}}
    )

    response_text = get_translation("info", "auto_mode_enabled", user_language)
    await fill_remaining_brief_questions(chat_session.chat_id, chat_session)

    ai_msg = ChatMessage(message=response_text, sender_role=SenderRole.AI)
    await save_and_broadcast_new_message(manager, chat_session, ai_msg, redis_key_session)

