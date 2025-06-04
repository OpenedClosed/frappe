"""Вспомогательные функции интеграции Facebook."""
from typing import Any, Dict, List

from chats.db.mongo.enums import ChatSource, SenderRole
from chats.integrations.meta.meta import process_meta_message
from integrations.basic.handlers import process_integration_message


def parse_facebook_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Разбирает JSON, приходящий от Facebook Messenger Webhook."""
    results: List[Dict[str, Any]] = []

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

            sender_id = ev["sender"]["id"]
            recipient_id = ev["recipient"]["id"]
            timestamp = ev.get("timestamp")

            message_text = msg.get("text", "")

            meta = {
                "attachments": msg.get("attachments"),
                "is_echo": is_echo,
                "raw_metadata": msg.get("metadata"),
                "referral": ev.get("referral"),
                "postback": ev.get("postback"),
                "context": ev.get("context"),
            }
            meta = {k: v for k, v in meta.items() if v is not None}

            results.append(
                {
                    "sender_id": sender_id,
                    "recipient_id": recipient_id,
                    "message_text": message_text,
                    "message_id": mid,
                    "timestamp": timestamp,
                    "metadata": meta,
                }
            )

    return results


async def process_facebook_message(
    sender_id: str,
    message_text: str,
    bot_id: str,
    client_external_id: str,
    metadata: dict,
    sender_role: SenderRole,
    external_id: str,
    user_language: str,
):
    """Обрабатывает сообщение из Facebook и передаёт его в систему чатов."""
    await process_integration_message(
        platform="facebook",
        chat_source=ChatSource.FACEBOOK,
        sender_id=sender_id,
        message_text=message_text,
        bot_id=bot_id,
        client_external_id=client_external_id,
        metadata=metadata,
        sender_role=sender_role,
        external_id=external_id,
        user_language=user_language,
    )
