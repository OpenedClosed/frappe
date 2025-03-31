"""Интеграция с Meta."""
from typing import Any, Dict, List

from fastapi import HTTPException, Request, Response

from chats.db.mongo.enums import ChatSource, SenderRole
from db.mongo.db_init import mongo_db


async def verify_meta_webhook(
    hub_mode: str,
    hub_challenge: str,
    hub_verify_token: str,
    expected_token: str,
) -> Response:
    """
    Универсальная функция, которая проверяет вебхук Meta-сервисов (Instagram, WhatsApp).
    """
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        return Response(content=str(hub_challenge), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


async def handle_incoming_meta_messages(
    messages_info: List[Dict[str, Any]],
    request: Request,
    settings_bot_id: str,
    chat_source: ChatSource,
    process_fn,
):
    """
    Универсальная функция, которая проходится по списку сообщений в едином формате.
    """
    for msg in messages_info:
        sender_id = msg["sender_id"]
        recipient_id = msg["recipient_id"]
        message_text = msg["message_text"]
        message_id = msg["message_id"]
        timestamp = msg["timestamp"]
        meta = msg["metadata"] or {}

        existing = await mongo_db.chats.find_one(
            {"external_id": settings_bot_id, "messages.external_id": message_id}
        )
        if existing:
            continue

        if chat_source == ChatSource.INSTAGRAM:
            if recipient_id == settings_bot_id:
                bot_id, client_id, sender_role = recipient_id, sender_id, SenderRole.CLIENT
            else:
                bot_id, client_id, sender_role = sender_id, recipient_id, SenderRole.CONSULTANT

            if meta.get(
                    "metadata") == "broadcast" or sender_id == settings_bot_id:
                continue
        else:
            if sender_id == settings_bot_id:
                bot_id, client_id, sender_role = sender_id, recipient_id, SenderRole.CONSULTANT
            else:
                bot_id, client_id, sender_role = settings_bot_id, sender_id, SenderRole.CLIENT

        metadata_dict = {
            "sender_id": sender_id,
            "bot_id": bot_id,
            "client_id": client_id,
            "timestamp": timestamp,
            "message_id": message_id,
        }
        metadata_dict.update(meta)
        metadata_dict = {
            k: v for k,
            v in metadata_dict.items() if v is not None}

        user_language = request.headers.get("accept-language", "en")

        await process_fn(
            sender_id=sender_id,
            message_text=message_text,
            bot_id=bot_id,
            client_external_id=client_id,
            metadata=metadata_dict,
            sender_role=sender_role,
            external_id=message_id,
            user_language=user_language
        )
