"""Обработчики интеграции с Constructor.chat"""
import logging
from datetime import timezone
from typing import List

import httpx

from chats.db.mongo.enums import SenderRole
from chats.db.mongo.schemas import ChatMessage, ChatSession
from db.mongo.db_init import mongo_db
from infra import settings

from . import constants

logger = logging.getLogger(__name__)


def to_constructor_message(msg: ChatMessage) -> dict:
    """Преобразует ChatMessage в формат сообщения для Constructor.chat."""
    base = {
        "sentAt": int(msg.timestamp.replace(tzinfo=timezone.utc).timestamp() * 1000),
        "content": msg.message,
        "isInbound": msg.sender_role == SenderRole.CLIENT,
    }
    if msg.sender_role not in {SenderRole.CLIENT, SenderRole.AI}:
        base["sender"] = msg.sender_role.name.replace("_", " ").title()
    return base


async def constructor_query(query: str, variables: dict):
    """Выполняет GraphQL-запрос к Constructor.chat; ошибки отлавливаются по полю `errors`."""
    headers = {
        "Authorization": f"Bearer {settings.CONSTRUCTOR_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            settings.CONSTRUCTOR_URL,
            json={"query": query, "variables": variables},
            headers=headers,
        )
        resp.raise_for_status()

    payload = resp.json()
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])

    return payload["data"]


async def create_constructor_chat(session: ChatSession):
    """Создаёт чат в Constructor.chat, отправляет всю историю и сохраняет ID в MongoDB с проверкой уникальности."""
    unsynced_all = [m for m in session.messages if not m.synced_to_constructor]

    data = await constructor_query(
        constants.CREATE_CHAT,
        {
            "assistantId": settings.CONSTRUCTOR_ASSISTANT_ID,
            "name": f"Chat {session.chat_id}",
            "messages": [to_constructor_message(m) for m in unsynced_all],
        },
    )
    chat_id = data["createApiChat"]["id"]

    existing = await mongo_db.chats.find_one({
        "constructor_chat_id": chat_id,
        "chat_id": {"$ne": session.chat_id}
    })
    if existing:
        logger.critical(
            "[Constructor] COLLISION: constructor_chat_id %s уже назначен чату %s (конфликт с %s)",
            chat_id, existing["chat_id"], session.chat_id
        )
        raise RuntimeError("Constructor chat ID collision detected")

    session.constructor_chat_id = chat_id

    if unsynced_all:
        for m in unsynced_all:
            m.synced_to_constructor = True

        await mongo_db.chats.update_one(
            {"chat_id": session.chat_id},
            {
                "$set": {
                    "constructor_chat_id": chat_id,
                    "messages.$[msg].synced_to_constructor": True,
                }
            },
            array_filters=[{"msg.id": {"$in": [m.id for m in unsynced_all]}}],
        )
    else:
        await mongo_db.chats.update_one(
            {"chat_id": session.chat_id},
            {"$set": {"constructor_chat_id": chat_id}},
        )


async def push_to_constructor(
        session: ChatSession, messages: List[ChatMessage]):
    """
    Отправляет НОВЫЕ (не синхронизированные) сообщения в Constructor.chat.
    Если чат ещё не создан — создаёт его и синхронизирует всю историю.
    """
    unsynced = [m for m in messages if not m.synced_to_constructor]
    if not unsynced:
        return

    if not session.constructor_chat_id:
        await create_constructor_chat(session)
        return

    await constructor_query(
        constants.CREATE_MESSAGES,
        {
            "chatId": session.constructor_chat_id,
            "messages": [to_constructor_message(m) for m in unsynced],
        },
    )

    for m in unsynced:
        m.synced_to_constructor = True

    await mongo_db.chats.update_one(
        {"chat_id": session.chat_id},
        {
            "$set": {
                "messages.$[msg].synced_to_constructor": True,
            }
        },
        array_filters=[{"msg.id": {"$in": [m.id for m in unsynced]}}],
    )
