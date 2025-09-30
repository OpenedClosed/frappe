"""Интеграция с Instagram."""
from fastapi import APIRouter, Query, Request

from chats.db.mongo.enums import ChatSource
from chats.integrations.meta.meta import (handle_incoming_meta_messages,
                                          verify_meta_webhook)
from chats.integrations.meta.utils.help_functions import verify_meta_signature
from infra import settings

from .utils.help_functions import (parse_instagram_payload,
                                   process_instagram_message)

instagram_router = APIRouter()


@instagram_router.get("/webhook")
async def verify_instagram_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    """Подтверждение вебхука Instagram."""
    return await verify_meta_webhook(
        hub_mode=hub_mode,
        hub_challenge=hub_challenge,
        hub_verify_token=hub_verify_token,
        expected_token=settings.INSTAGRAM_VERIFY_TOKEN,
    )


@instagram_router.post("/webhook")
async def handle_instagram_messages(request: Request):
    """Обрабатывает входящие сообщения из Instagram с проверкой подписи."""
    await verify_meta_signature(request, settings.INSTAGRAM_APP_SECRET)

    payload = await request.json()
    messages_info = parse_instagram_payload(payload)

    await handle_incoming_meta_messages(
        messages_info=messages_info,
        request=request,
        settings_bot_id=settings.INSTAGRAM_BOT_ID,
        chat_source=ChatSource.INSTAGRAM,
        process_fn=process_instagram_message
    )

    return {"status": "ok"}
