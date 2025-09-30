"""Интеграция с Meta."""
import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional

from chats.db.mongo.enums import ChatSource, SenderRole
from chats.db.mongo.schemas import ChatSession
from chats.integrations.basic.handlers import route_incoming_message
from chats.utils.help_functions import handle_chat_creation
from chats.ws.ws_handlers import handle_message
from chats.ws.ws_helpers import (get_typing_manager, get_ws_manager,
                                 gpt_task_manager)
from db.mongo.db_init import mongo_db
from fastapi import HTTPException, Request, Response
from infra import settings
from utils.help_functions import get_language_from_locale

# from .instagram.utils.help_functions import get_instagram_user_profile
# from .utils.help_functions import get_meta_locale


async def verify_meta_webhook(
    hub_mode: str,
    hub_challenge: str,
    hub_verify_token: str,
    expected_token: str,
) -> Response:
    """Универсальная функция, которая проверяет вебхук Meta-сервисов (Instagram, WhatsApp)."""
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        return Response(content=str(hub_challenge), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")




# async def handle_incoming_meta_messages(
#     messages_info: List[Dict[str, Any]],
#     request: Request,
#     settings_bot_id: str,
#     chat_source: ChatSource,
#     process_fn: Callable[..., Awaitable[None]],
#     profile_fetcher: Optional[Callable[[str], Awaitable[Optional[dict]]]] = None,
# ):
#     """Конвертирует Meta-webhook → route_incoming_message."""
#     token_key = f"{chat_source.name.upper()}_ACCESS_TOKEN"
#     access_token = getattr(settings, token_key, None)

#     for raw in messages_info:
#         await route_incoming_message(
#             sender_id=str(raw["sender_id"]),
#             recipient_id=str(raw["recipient_id"]),
#             message_text=raw["message_text"],
#             message_id=str(raw["message_id"]),
#             timestamp=int(raw["timestamp"]),
#             metadata=raw.get("metadata", {}),
#             chat_source=chat_source,
#             settings_bot_id=settings_bot_id,
#             access_token=access_token,
#             profile_fetcher=profile_fetcher,
#             process_fn=process_fn,
#             skip_locale=False,
#         )



async def handle_incoming_meta_messages(
    messages_info: List[Dict[str, Any]],
    request: Request,
    settings_bot_id: str,
    chat_source: ChatSource,
    process_fn: Callable[..., Awaitable[None]],
    profile_fetcher: Optional[Callable[[str], Awaitable[Optional[dict]]]] = None,
):
    """Конвертирует Meta-webhook → route_incoming_message."""

    token_key = f"{chat_source.name.upper()}_ACCESS_TOKEN"
    access_token = getattr(settings, token_key, None)

    for raw in messages_info:
        # --- Если текст пустой, подставим заглушку для вложений ---
        raw_text = raw.get("message_text") or ""
        if not raw_text.strip():
            raw_text = "<Content>"  # или "<Контент не распознан>", если хочешь мягче
        # ----------------------------------------------------------

        await route_incoming_message(
            sender_id=str(raw["sender_id"]),
            recipient_id=str(raw["recipient_id"]),
            message_text=raw_text,
            message_id=str(raw["message_id"]),
            timestamp=int(raw["timestamp"]),
            metadata=raw.get("metadata", {}),
            chat_source=chat_source,
            settings_bot_id=settings_bot_id,
            access_token=access_token,
            profile_fetcher=profile_fetcher,
            process_fn=process_fn,
            skip_locale=False,
        )



def build_meta_metadata(
    sender_id: str,
    bot_id: str,
    client_id: str,
    timestamp: int | str | None,
    message_id: str | None,
    base_meta: Dict[str, Any],
    extra_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Собирает унифицированный словарь метаданных сообщения Meta."""
    meta: Dict[str, Any] = {
        "sender_id": sender_id,
        "bot_id": bot_id,
        "client_id": client_id,
        "timestamp": timestamp,
        "message_id": message_id,
    }
    meta.update({k: v for k, v in base_meta.items() if v is not None})
    if extra_meta:
        meta.update({k: v for k, v in extra_meta.items() if v is not None})
    return {k: v for k, v in meta.items() if v is not None}


# async def process_meta_message(
#     platform: str,
#     chat_source: ChatSource,
#     sender_id: str,
#     message_text: str,
#     bot_id: str,
#     client_external_id: str,
#     metadata: Dict[str, Any],
#     sender_role: SenderRole,
#     external_id: str,
#     user_language: str,
# ):
#     """Обрабатывает сообщение Meta и передаёт его в систему чатов."""
#     chat_data = await handle_chat_creation(
#         mode=None,
#         chat_source=chat_source,
#         chat_external_id=bot_id,
#         client_external_id=client_external_id,
#         company_name=bot_id,
#         bot_id=bot_id,
#         metadata=metadata,
#         request=None,
#     )

#     chat_id = chat_data["chat_id"]
#     client_id = chat_data["client_id"]

#     chat_session_data = await mongo_db.chats.find_one({"chat_id": chat_id})
#     if not chat_session_data:
#         return

#     chat_session = ChatSession(**chat_session_data)
#     manager = await get_ws_manager(chat_id)
#     typing_manager = await get_typing_manager(chat_id)
#     gpt_lock = gpt_task_manager.get_lock(chat_id)

#     data = {
#         "type": "new_message",
#         "message": message_text,
#         "sender_role": sender_role,
#         "external_id": external_id,
#         "metadata": metadata,
#     }

#     redis_session_key = f"chat:session:{chat_id}"
#     redis_flood_key = f"flood:{client_id}"

#     user_data = {
#         "platform": platform,
#         "sender_id": sender_id,
#         "external_id": external_id,
#         "client_external_id": client_external_id,
#         "metadata": metadata,
#         "is_superuser": sender_role == SenderRole.CONSULTANT,
#     }

#     asyncio.create_task(
#         handle_message(
#             manager=manager,
#             typing_manager=typing_manager,
#             chat_id=chat_id,
#             client_id=client_id,
#             redis_session_key=redis_session_key,
#             redis_flood_key=redis_flood_key,
#             data=data,
#             is_superuser=(sender_role == SenderRole.CONSULTANT),
#             user_language=user_language,
#             gpt_lock=gpt_lock,
#             user_data=user_data,
#         )
#     )
