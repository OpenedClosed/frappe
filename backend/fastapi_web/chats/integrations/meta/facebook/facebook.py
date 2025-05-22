"""Интеграция с Facebook."""
from fastapi import APIRouter, Query, Request

from chats.db.mongo.enums import ChatSource
from chats.integrations.meta.meta import (handle_incoming_meta_messages,
                                          verify_meta_webhook)
from chats.integrations.meta.utils.help_functions import verify_meta_signature
from infra import settings

from .utils.help_functions import (parse_facebook_payload,
                                   process_facebook_message)

facebook_router = APIRouter(prefix="/facebook")


@facebook_router.get("/webhook")
async def verify_facebook_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    """Подтверждение вебхука Facebook Messenger."""
    return await verify_meta_webhook(
        hub_mode=hub_mode,
        hub_challenge=hub_challenge,
        hub_verify_token=hub_verify_token,
        expected_token=settings.FACEBOOK_VERIFY_TOKEN,
    )


@facebook_router.post("/webhook")
async def handle_facebook_messages(request: Request):
    """Обрабатывает входящие сообщения из Facebook с проверкой подписи."""
    await verify_meta_signature(request, settings.FACEBOOK_APP_SECRET)

    payload = await request.json()
    messages_info = parse_facebook_payload(payload)

    await handle_incoming_meta_messages(
        messages_info=messages_info,
        request=request,
        settings_bot_id=settings.FACEBOOK_PAGE_ID,
        chat_source=ChatSource.FACEBOOK,
        process_fn=process_facebook_message,
    )

    return {"status": "ok"}
