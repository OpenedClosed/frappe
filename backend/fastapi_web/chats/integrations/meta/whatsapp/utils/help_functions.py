"""Вспомогательные функции интеграции WhatsApp."""
from typing import Any, Dict, List

from chats.db.mongo.enums import ChatSource, SenderRole
from chats.db.mongo.schemas import ChatSession
from chats.routers import handle_chat_creation
from chats.ws.ws_handlers import handle_message
from chats.ws.ws_helpers import get_typing_manager, get_ws_manager
from db.mongo.db_init import mongo_db

from chats.ws.ws_helpers import gpt_task_manager

def parse_whatsapp_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Разбирает JSON, приходящий от WhatsApp Cloud API.
    """
    results = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            bot_display_phone = metadata.get("display_phone_number")
            bot_wa_id = metadata.get("phone_number_id")
            contacts = value.get("contacts", [])
            messages = value.get("messages", [])

            for message in messages:
                sender_id = message.get("from")
                message_id = message.get("id")
                timestamp = message.get("timestamp")

                message_text = ""
                if message.get("type") == "text":
                    message_text = message.get("text", {}).get("body", "")

                client_id = contacts[0].get("wa_id") if contacts else None

                if sender_id == client_id:
                    actual_sender = sender_id
                    actual_recipient = bot_display_phone
                else:
                    actual_sender = sender_id
                    actual_recipient = client_id

                meta = {
                    "type": message.get("type"),
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
    metadata: dict,
    sender_role: SenderRole,
    external_id: str,
    user_language: str
):
    """
    Обрабатывает сообщение из WhatsApp и передаёт его в систему чатов.
    """
    chat_data = await handle_chat_creation(
        mode=None,
        chat_source=ChatSource.WHATSAPP,
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
        "external_id": external_id
    }

    redis_session_key = f"chat:{client_id}"
    redis_flood_key = f"flood:{client_id}"

    user_data = {
        "platform": "instagram",
        "sender_id": sender_id,
        "external_id": external_id,
        "client_external_id": client_external_id,
        "metadata": metadata,
        "is_superuser": sender_role == SenderRole.CONSULTANT
    }


    await handle_message(
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
