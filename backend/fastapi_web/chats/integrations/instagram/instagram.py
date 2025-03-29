"""Интеграция с Instagram."""
from fastapi import APIRouter, HTTPException, Query, Request, Response

from chats.db.mongo.enums import SenderRole
from db.mongo.db_init import mongo_db
from infra import settings

from .utils.help_functions import (process_instagram_message,
                                   verify_instagram_signature)

instagram_router = APIRouter()


@instagram_router.get("/webhook")
async def verify_instagram_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    """Подтверждение вебхука Instagram."""
    if hub_mode == "subscribe" and hub_verify_token == settings.INSTAGRAM_VERIFY_TOKEN:
        return Response(content=str(hub_challenge), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@instagram_router.post("/webhook")
async def handle_instagram_messages(request: Request):
    """Обрабатывает входящие сообщения из Instagram с проверкой подписи."""
    await verify_instagram_signature(request)
    payload = await request.json()

    for entry in payload.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            sender_data = messaging_event.get("sender", {})
            recipient_data = messaging_event.get("recipient", {})
            message_data = messaging_event.get("message", {})

            sender_id = sender_data.get("id")
            recipient_id = recipient_data.get("id")
            message_text = message_data.get("text", "")
            message_id = message_data.get("mid")
            metadata = messaging_event.get("metadata", "")

            if metadata == "broadcast" or sender_id == settings.INSTAGRAM_BOT_ID:
                continue

            if recipient_id == settings.INSTAGRAM_BOT_ID:
                bot_id, client_id, sender_role = recipient_id, sender_id, SenderRole.CLIENT
            else:
                bot_id, client_id, sender_role = sender_id, recipient_id, SenderRole.CONSULTANT

            existing_message = await mongo_db.chats.find_one(
                {"external_id": bot_id, "messages.external_id": message_id}
            )
            if existing_message:
                continue

            user_language = request.headers.get("accept-language", "en")

            metadata_dict = {
                "sender_id": sender_id,
                "bot_id": bot_id,
                "client_id": client_id,
                "timestamp": messaging_event.get("timestamp"),
                "message_id": message_id,
                "attachments": message_data.get("attachments"),
                "referral": messaging_event.get("referral"),
                "postback": messaging_event.get("postback"),
                "context": messaging_event.get("context"),
            }
            metadata_dict = {k: v for k, v in metadata_dict.items() if v}

            await process_instagram_message(
                sender_id=sender_id,
                message_text=message_text,
                bot_id=bot_id,
                client_external_id=client_id,
                metadata=metadata_dict,
                sender_role=sender_role,
                external_id=message_id,
                user_language=user_language
            )

    return {"status": "ok"}
