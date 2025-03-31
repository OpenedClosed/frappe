"""Интеграция с Whatsapp."""
from fastapi import APIRouter, Query, Request

from chats.db.mongo.enums import ChatSource
from chats.integrations.meta.meta import (handle_incoming_meta_messages,
                                          verify_meta_webhook)
from chats.integrations.meta.utils.help_functions import verify_meta_signature
from infra import settings

from .utils.help_functions import (parse_whatsapp_payload,
                                   process_whatsapp_message)

whatsapp_router = APIRouter()


@whatsapp_router.get("/webhook")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    """Подтверждение вебхука WhatsApp."""
    return await verify_meta_webhook(
        hub_mode=hub_mode,
        hub_challenge=hub_challenge,
        hub_verify_token=hub_verify_token,
        expected_token=settings.WHATSAPP_VERIFY_TOKEN,
    )


@whatsapp_router.post("/webhook")
async def handle_whatsapp_messages(request: Request):
    """
    Обрабатывает входящие сообщения из WhatsApp с проверкой подписи.
    """
    print(await request.json())
    await verify_meta_signature(request, settings.WHATSAPP_APP_SECRET)

    payload = await request.json()
    messages_info = parse_whatsapp_payload(payload)

    await handle_incoming_meta_messages(
        messages_info=messages_info,
        request=request,
        settings_bot_id=settings.WHATSAPP_BOT_NUMBER,
        chat_source=ChatSource.WHATSAPP,
        process_fn=process_whatsapp_message
    )

    return {"status": "ok"}
