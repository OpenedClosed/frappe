"""Вспомогательные функции интеграции Instagram."""
import json
import logging
from typing import Any, Dict, List

import aiohttp

from chats.integrations.basic.handlers import process_integration_message
from chats.db.mongo.enums import ChatSource, SenderRole
from infra import settings


def parse_instagram_payload(payload: dict) -> List[dict]:
    """Преобразует веб-хук Instagram/Messenger в унифицированный список сообщений."""
    msgs: List[dict] = [] 

    for entry in payload.get("entry", []):
        for ev in entry.get("messaging", []):
            if {"read", "delivery", "reaction"} & ev.keys():
                continue

            msg = ev.get("message")
            if not msg:
                continue

            mid = msg.get("mid")
            is_echo = bool(msg.get("is_echo"))

            if is_echo and msg.get("metadata") == "broadcast":
                continue

            rec = {
                "sender_id": ev["sender"]["id"],
                "recipient_id": ev["recipient"]["id"],
                "message_text": msg.get("text", ""),
                "message_id": mid,
                "timestamp": ev.get("timestamp"),
                "metadata": {
                    "attachments": msg.get("attachments"),
                    "is_echo": is_echo,
                    "raw_metadata": msg.get("metadata"),
                    "referral": ev.get("referral"),
                    "postback": ev.get("postback"),
                    "context": ev.get("context"),
                },
            }
            msgs.append(rec)

    return msgs


async def process_instagram_message(
    sender_id: str,
    message_text: str,
    bot_id: str,
    client_external_id: str,
    metadata: Dict[str, Any],
    sender_role: SenderRole,
    external_id: str,
    user_language: str,
):
    await process_integration_message(
        platform="instagram",
        chat_source=ChatSource.INSTAGRAM,
        sender_id=sender_id,
        message_text=message_text,
        bot_id=bot_id,
        client_external_id=client_external_id,
        metadata=metadata,
        sender_role=sender_role,
        external_id=external_id,
        user_language=user_language,
    )



async def get_instagram_user_profile(psid: str) -> dict:
    """Возвращает имя и аватар пользователя Instagram по PSID."""
    url = f"https://graph.facebook.com/v22.0/{psid}"
    access_token = settings.INSTAGRAM_ACCESS_TOKEN
    params = {
        "fields": "name,profile_pic",
        "access_token": access_token
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=5) as resp:
                text = await resp.text()

                if resp.status == 200:
                    data = json.loads(text)
                    return data

                if "Invalid OAuth access token" in text:
                    logging.error(
                        "[IG] Invalid access token — check settings.INSTAGRAM_ACCESS_TOKEN"
                    )

    except Exception:
        pass

    return {}
