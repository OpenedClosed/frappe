"""Вспомогательные функции интеграции Instagram."""
import hashlib
import hmac

from fastapi import HTTPException, Request

from chats.db.mongo.enums import ChatSource, SenderRole
from chats.db.mongo.schemas import ChatSession
from chats.routers import handle_chat_creation
from chats.ws.ws_handlers import handle_new_message_wrapper
from chats.ws.ws_helpers import get_ws_manager
from db.mongo.db_init import mongo_db
from infra import settings


async def verify_instagram_signature(request: Request):
    """Проверяет подпись входящего запроса от Instagram."""
    signature = request.headers.get("X-Hub-Signature-256")
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
