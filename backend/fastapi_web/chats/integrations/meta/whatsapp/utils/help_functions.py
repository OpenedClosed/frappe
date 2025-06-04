"""Вспомогательные функции интеграции WhatsApp."""
from typing import Any, Dict, List

from chats.db.mongo.enums import ChatSource, SenderRole
from chats.integrations.basic.handlers import process_integration_message


def parse_whatsapp_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Разбирает JSON, приходящий от WhatsApp Cloud API."""
    results: List[Dict[str, Any]] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            bot_display_phone = metadata.get("display_phone_number")
            bot_wa_id = metadata.get("phone_number_id")
            contacts = value.get("contacts", [])
            messages = value.get("messages", [])

            for message in messages:
                message_type = message.get("type")
                if message_type not in {
                        "text", "image", "video", "audio", "document"}:
                    continue

                sender_id = message.get("from")
                message_id = message.get("id")
                timestamp = message.get("timestamp")

                message_text = ""
                if message_type == "text":
                    message_text = message.get("text", {}).get("body", "")

                client_id = contacts[0].get("wa_id") if contacts else None

                if sender_id == client_id:
                    actual_sender = sender_id
                    actual_recipient = bot_display_phone
                else:
                    actual_sender = sender_id
                    actual_recipient = client_id

                meta = {
                    "type": message_type,
                    "is_echo": False,
                    "raw_metadata": None,
                    "attachments": message.get(message_type),
                    "profile_name": contacts[0].get("profile", {}).get("name") if contacts else None,
                    "display_phone_number": bot_display_phone,
                    "phone_number_id": bot_wa_id,
                }
                meta = {k: v for k, v in meta.items() if v is not None}

                results.append({
                    "sender_id": actual_sender,
                    "recipient_id": actual_recipient,
                    "message_text": message_text,
                    "message_id": message_id,
                    "timestamp": timestamp,
                    "metadata": meta
                })

    return results


async def process_whatsapp_message(
    sender_id: str,
    message_text: str,
    bot_id: str,
    client_external_id: str,
    metadata: Dict[str, Any],
    sender_role: SenderRole,
    external_id: str,
    user_language: str,
):
    """Обрабатывает сообщение из WhatsApp и передаёт его в систему чатов."""
    await process_integration_message(
        platform="whatsapp",
        chat_source=ChatSource.WHATSAPP,
        sender_id=sender_id,
        message_text=message_text,
        bot_id=bot_id,
        client_external_id=client_external_id,
        metadata=metadata,
        sender_role=sender_role,
        external_id=external_id,
        user_language=user_language,
    )
