"""Обработчики интеграции с Constructor.chat"""
from datetime import timezone

import httpx
from chats.db.mongo.enums import SenderRole
from chats.db.mongo.schemas import ChatMessage, ChatSession
from infra import settings
from . import constants


import logging
from datetime import timezone
from db.mongo.db_init import mongo_db

logger = logging.getLogger(__name__)

def to_constructor_message(msg: ChatMessage) -> dict:
    """Преобразует ChatMessage в формат сообщения для Constructor.chat."""
    return {
        "sentAt": int(msg.timestamp.replace(tzinfo=timezone.utc).timestamp() * 1000),
        "content": msg.message,
        "isInbound": msg.sender_role == SenderRole.CLIENT,
        **({"sender": msg.sender_role.name.replace("_", " ").title()}
           if msg.sender_role not in {SenderRole.CLIENT, SenderRole.AI}
           else {})
    }

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
        logger.error("[Constructor] GraphQL errors: %s", payload["errors"])
        raise RuntimeError(payload["errors"])

    logger.debug("[Constructor] GraphQL ok: %s", payload.get("data"))
    return payload["data"]


async def create_constructor_chat(session: ChatSession):
    """Создаёт чат в Constructor.chat, отправляет всю историю и сохраняет ID в MongoDB с проверкой уникальности."""
    logger.info("[Constructor] Creating chat for %s", session.chat_id)

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

    # 🛡 Проверка на уникальность constructor_chat_id
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
    logger.info("[Constructor] Chat created with id %s for %s", chat_id, session.chat_id)

    # Помечаем все отправленные сообщения
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
        logger.info(
            "[Constructor] Initial sync of %d historical message(s) for chat %s",
            len(unsynced_all),
            session.chat_id,
        )
    else:
        await mongo_db.chats.update_one(
            {"chat_id": session.chat_id},
            {"$set": {"constructor_chat_id": chat_id}},
        )



async def push_to_constructor(session: ChatSession, messages: list[ChatMessage]):
    """
    Отправляет НОВЫЕ (не синхронизированные) сообщения в Constructor.chat.
    Если чат ещё не создан — создаёт его и синхронизирует всю историю.
    """
    unsynced = [m for m in messages if not m.synced_to_constructor]
    if not unsynced:
        logger.debug("[Constructor] Nothing to sync for chat %s", session.chat_id)
        return

    if not session.constructor_chat_id:
        await create_constructor_chat(session)
        return  # ⚠️ ключевой момент — не продолжаем, чтобы не отправить new_msg второй раз

    logger.info(
        "[Constructor] Sending %d new message(s) to Constructor.chat for chat %s",
        len(unsynced),
        session.chat_id,
    )

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

    logger.info(
        "[Constructor] Synced %d message(s) for chat %s",
        len(unsynced),
        session.chat_id,
    )

