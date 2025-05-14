"""Вспомогательные функции интеграции Instagram."""
import asyncio
import json
import logging
from typing import Any, Dict, List

import aiohttp

from chats.db.mongo.enums import ChatSource, SenderRole
from chats.db.mongo.schemas import ChatSession
from chats.routers import handle_chat_creation
from chats.ws.ws_handlers import handle_message
from chats.ws.ws_helpers import (get_typing_manager, get_ws_manager,
                                 gpt_task_manager)
from db.mongo.db_init import mongo_db
from infra import settings


# ---------------------------------------------------------------------------
# 1. instagram_router.utils.parse_instagram_payload
# ---------------------------------------------------------------------------
def parse_instagram_payload(payload: dict) -> list[dict]:
    """
    Преобразует веб-хук Instagram/Messenger в унифицированный список сообщений.
    Системные события (read / delivery / reaction) и echo-broadcast пропускаются.
    """
    logging.debug("📦 [IG] RAW payload:\n%s",
                  json.dumps(payload, indent=2, ensure_ascii=False))

    msgs: list[dict] = []

    for entry in payload.get("entry", []):
        for ev in entry.get("messaging", []):
            # 1️⃣ Системные события — skip
            if {"read", "delivery", "reaction"} & ev.keys():
                logging.debug("↪️  [IG] Skip system event keys=%s", list(ev.keys()))
                continue

            msg = ev.get("message")
            if not msg:
                logging.debug("↪️  [IG] Skip event without 'message': %s", ev)
                continue

            mid        = msg.get("mid")
            is_echo    = bool(msg.get("is_echo"))

            # 2️⃣ echo-broadcast (наши исходящие) — skip
            #    broadcast-метка появится далее в meta["raw_metadata"]
            if is_echo and msg.get("metadata") == "broadcast":
                logging.debug("⛔  [IG] Skip echo-broadcast mid=%s", mid)
                continue

            # 3️⃣ формируем результат
            rec = {
                "sender_id":    ev["sender"]["id"],
                "recipient_id": ev["recipient"]["id"],
                "message_text": msg.get("text", ""),
                "message_id":   mid,
                "timestamp":    ev.get("timestamp"),
                "metadata": {
                    "attachments": msg.get("attachments"),
                    "is_echo":     is_echo,
                    "raw_metadata": msg.get("metadata"),    # <-- важно
                    "referral":    ev.get("referral"),
                    "postback":    ev.get("postback"),
                    "context":     ev.get("context"),
                },
            }
            msgs.append(rec)

            logging.info("🔍 [IG] Parsed mid=%s is_echo=%s text='%s'",
                         mid, is_echo, rec["message_text"][:40])

    logging.info("✅ [IG] Parsed %d inbound message(s)", len(msgs))
    return msgs




async def process_instagram_message(
    sender_id: str,
    message_text: str,
    bot_id: str,
    client_external_id: str,
    metadata: dict,
    sender_role: SenderRole,
    external_id: str,
    user_language: str
):
    """Обрабатывает сообщение из Instagram и передаёт его в систему чатов."""

    chat_data = await handle_chat_creation(
        mode=None,
        chat_source=ChatSource.INSTAGRAM,
        chat_external_id=bot_id,
        client_external_id=client_external_id,
        company_name=bot_id,
        bot_id=bot_id,
        metadata=metadata,
        request=None
    )

    chat_id = chat_data["chat_id"]
    client_id = chat_data["client_id"]

    chat_session_data = await mongo_db.chats.find_one({"chat_id": chat_id})
    if not chat_session_data:
        return

    chat_session = ChatSession(**chat_session_data)
    manager = await get_ws_manager(chat_id)
    typing_manager = await get_typing_manager(chat_id)
    gpt_lock = gpt_task_manager.get_lock(chat_id)

    data = {
        "type": "new_message",
        "message": message_text,
        "sender_role": sender_role,
        "external_id": external_id,
        "metadata": metadata
    }

    redis_session_key = f"chat:session:{chat_id}"
    redis_flood_key = f"flood:{client_id}"

    user_data = {
        "platform": "instagram",
        "sender_id": sender_id,
        "external_id": external_id,
        "client_external_id": client_external_id,
        "metadata": metadata,
        "is_superuser": sender_role == SenderRole.CONSULTANT
    }

    asyncio.create_task(
        handle_message(
            manager=manager,
            typing_manager=typing_manager,
            chat_id=chat_id,
            client_id=client_id,
            redis_session_key=redis_session_key,
            redis_flood_key=redis_flood_key,
            data=data,
            is_superuser=(sender_role == SenderRole.CONSULTANT),
            user_language=user_language,
            gpt_lock=gpt_lock,
            user_data=user_data
        )
    )

async def get_instagram_user_profile(psid: str) -> dict:
    """Возвращает имя и аватар пользователя Instagram по PSID."""
    url = f"https://graph.facebook.com/v22.0/{psid}"
    access_token = settings.INSTAGRAM_ACCESS_TOKEN
    params = {
        "fields": "name,profile_pic",
        "access_token": access_token
    }

    logging.debug(f"[IG] Запрос профиля пользователя psid={psid} (access_token starts with: {access_token[:10]}...)")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=5) as resp:
                text = await resp.text()

                logging.debug(f"[IG] Ответ профиля для psid={psid}: status={resp.status}, body={text[:300]}")

                if resp.status == 200:
                    data = json.loads(text)
                    if not data:
                        logging.info(f"[IG] Профиль {psid} пуст — возможно пользователь ограничил доступ")
                    else:
                        if not data.get("name"):
                            logging.info(f"[IG] Имя отсутствует для {psid}")
                        if not data.get("profile_pic"):
                            logging.info(f"[IG] Аватар отсутствует для {psid}")
                    return data

                logging.warning(f"[IG] Ошибка получения профиля {psid}: {resp.status} {text}")

                if "Invalid OAuth access token" in text:
                    logging.error(f"[IG] ❌ Неверный access token — проверь settings.INSTAGRAM_ACCESS_TOKEN")

    except Exception as e:
        logging.exception(f"[IG] Исключение при запросе профиля {psid}: {e}")

    return {}

