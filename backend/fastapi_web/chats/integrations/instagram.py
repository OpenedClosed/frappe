"""Интеграция с Инстаграм."""
import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Query, Request, Response

from chats.db.mongo.enums import ChatSource, SenderRole
from chats.db.mongo.schemas import ChatSession
from chats.routers import handle_chat_creation
from chats.ws.ws_handlers import handle_new_message_wrapper
from chats.ws.ws_helpers import get_ws_manager
from db.mongo.db_init import mongo_db
from infra import settings

instagram_router = APIRouter()


async def verify_instagram_signature(request: Request):
    """
    Проверяет подпись входящего запроса от Instagram.
    """
    signature = request.headers.get(
        "X-Hub-Signature-256")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    raw_body = await request.body()

    expected_signature = hmac.new(
        key=settings.INSTAGRAM_APP_SECRET.encode(),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(f"sha256={expected_signature}", signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    return True


@instagram_router.get("/webhook")
async def verify_instagram_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    """Подтверждение вебхука Instagram"""
    if hub_mode == "subscribe" and hub_verify_token == settings.INSTAGRAM_VERIFY_TOKEN:
        return Response(content=str(hub_challenge), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@instagram_router.post("/webhook")
async def handle_instagram_messages(request: Request):
    """Обрабатывает входящие сообщения из Instagram с проверкой подписи."""
    await verify_instagram_signature(request)

    payload = await request.json()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            messaging_event = change.get("value", {})

            sender_data = messaging_event.get("sender", {})
            recipient_data = messaging_event.get("recipient", {})
            message_data = messaging_event.get("message", {})

            sender_id = sender_data.get("id")
            recipient_id = recipient_data.get("id")
            message_text = message_data.get("text", "")
            message_id = message_data.get("mid")
            if not sender_id or not recipient_id:
                continue
            if sender_id == settings.INSTAGRAM_BOT_ID:
                bot_id = sender_id
                client_id = recipient_id
                sender_role = SenderRole.CONSULTANT
            else:
                bot_id = recipient_id
                client_id = sender_id
                sender_role = SenderRole.CLIENT

            existing_message = await mongo_db.chats.find_one(
                {"external_id": bot_id, "messages.external_id": message_id}
            )
            if existing_message:
                continue

            user_language = request.headers.get("accept-language", "en")

            metadata = {
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

            metadata = {k: v for k, v in metadata.items() if v}

            await process_instagram_message(
                sender_id=sender_id,
                message_text=message_text,
                bot_id=bot_id,
                client_external_id=client_id,
                metadata=metadata,
                sender_role=sender_role,
                external_id=message_id,
                user_language=user_language
            )

    return {"status": "ok"}


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
    """Обрабатывает сообщение из Instagram, используя систему чатов."""

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
    data = {
        "type": "new_message",
        "message": message_text,
        "sender_role": sender_role,
        "external_id": external_id
    }

    redis_session_key = f"chat:{client_id}"
    redis_flood_key = f"flood:{client_id}"

    await handle_new_message_wrapper(
        manager=manager,
        chat_id=chat_id,
        client_id=client_id,
        redis_session_key=redis_session_key,
        redis_flood_key=redis_flood_key,
        data=data,
        is_superuser=(sender_role == SenderRole.CONSULTANT),
        user_language=user_language
    )
