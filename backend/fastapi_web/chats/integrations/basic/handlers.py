from typing import Any, Dict, Optional

from chats.db.mongo.enums import ChatSource, SenderRole
from db.mongo.db_init import mongo_db
from utils.help_functions import get_language_from_locale
from typing import Any, Awaitable, Callable, Dict

from chats.db.mongo.enums import ChatSource
import asyncio
from typing import Any, Dict, Optional

from chats.db.mongo.enums import ChatSource, SenderRole
from chats.db.mongo.schemas import ChatSession
from chats.utils.help_functions import handle_chat_creation
from chats.ws.ws_handlers import handle_message
from chats.ws.ws_helpers import (get_typing_manager, get_ws_manager,
                                 gpt_task_manager)
from db.mongo.db_init import mongo_db
from utils.help_functions import get_language_from_locale

# async def route_incoming_message(
#     *,
#     sender_id: str,
#     recipient_id: str,
#     message_text: str,
#     message_id: str,
#     timestamp: int,
#     metadata: Dict[str, Any],
#     chat_source: ChatSource,
#     settings_bot_id: str,
#     access_token: Optional[str],
#     profile_fetcher: Optional[Callable[[str], Awaitable[Optional[dict]]]] = None,
#     process_fn: Callable[..., Awaitable[None]],
#     skip_locale: bool = False,
# ):
#     """Единый обработчик, одинаковый для Telegram, Instagram, Facebook …"""
#     is_echo = metadata.get("is_echo", False)
#     raw_metadata = metadata.get("raw_metadata")
#     if is_echo and raw_metadata == "broadcast":
#         return

#     if await mongo_db.chats.find_one({"messages.external_id": message_id}, {"_id": 1}):
#         return
#     if chat_source == ChatSource.INSTAGRAM:
#         if is_echo:
#             sender_role = SenderRole.CONSULTANT
#             bot_id = sender_id
#             client_id = recipient_id
#         else:
#             sender_role = SenderRole.CLIENT
#             bot_id = settings_bot_id
#             client_id = sender_id
#     else:
#         if sender_id == settings_bot_id:
#             sender_role = SenderRole.AI
#         else:
#             sender_role = SenderRole.CLIENT
#         bot_id = settings_bot_id
#         client_id = sender_id

#     if not skip_locale and access_token and sender_role == SenderRole.CLIENT:
#         locale = "en_EN"
#         user_language = get_language_from_locale(locale)
#     else:
#         user_language = metadata.get("language_code", "en")[:2]

#     name = " ".join(filter(None, [metadata.get("first_name"), metadata.get("last_name")])).strip()
#     avatar_url = metadata.get("avatar_url")

#     full_metadata = {
#         "sender_id": sender_id,
#         "bot_id": bot_id,
#         "client_id": client_id,
#         "timestamp": timestamp,
#         "message_id": message_id,
#         "name": name if name else None,
#         "avatar_url": avatar_url,
#         "raw_metadata": raw_metadata,
#         "is_echo": is_echo,
#         **{k: v for k, v in metadata.items() if v is not None},
#     }

#     await process_fn(
#         sender_id=sender_id,
#         message_text=message_text,
#         bot_id=bot_id,
#         client_external_id=client_id,
#         metadata=full_metadata,
#         sender_role=sender_role,
#         external_id=message_id,
#         user_language=user_language,
#     )


async def route_incoming_message(
    *,
    sender_id: str,
    recipient_id: str,
    message_text: str,
    message_id: str,
    timestamp: int,
    metadata: Dict[str, Any],
    chat_source: ChatSource,
    settings_bot_id: str,
    access_token: Optional[str],
    profile_fetcher: Optional[Callable[[str], Awaitable[Optional[dict]]]] = None,
    process_fn: Callable[..., Awaitable[None]],
    skip_locale: bool = False,
):
    """Единый обработчик, одинаковый для Telegram, Instagram, Facebook …"""
    is_echo = metadata.get("is_echo", False)
    raw_metadata = metadata.get("raw_metadata")

    if is_echo and raw_metadata == "broadcast":
        return

    if await mongo_db.chats.find_one({"messages.external_id": message_id}, {"_id": 1}):
        return

    # Определение ролей и ID
    if chat_source == ChatSource.INSTAGRAM:
        if is_echo:
            sender_role = SenderRole.CONSULTANT
            bot_id = sender_id
            client_id = recipient_id
        else:
            sender_role = SenderRole.CLIENT
            bot_id = settings_bot_id
            client_id = sender_id
    else:
        if sender_id == settings_bot_id:
            sender_role = SenderRole.AI
        else:
            sender_role = SenderRole.CLIENT
        bot_id = settings_bot_id
        client_id = sender_id

    # Получение профиля пользователя, если передан profile_fetcher
    profile_data = {}
    if profile_fetcher and sender_role == SenderRole.CLIENT:
        profile_data = await profile_fetcher(sender_id) or {}

    # Язык интерфейса
    if not skip_locale and access_token and sender_role == SenderRole.CLIENT:
        locale = profile_data.get("locale") or "en_EN"
        user_language = get_language_from_locale(locale)
    else:
        user_language = metadata.get("language_code", "en")[:2]

    # Имя, аватар — из профиля или metadata
    first_name = profile_data.get("first_name") or metadata.get("first_name")
    last_name = profile_data.get("last_name") or metadata.get("last_name")
    avatar_url = profile_data.get("profile_pic") or metadata.get("avatar_url")

    name = " ".join(filter(None, [first_name, last_name])).strip()

    # Собираем итоговые метаданные
    full_metadata = {
        "sender_id": sender_id,
        "bot_id": bot_id,
        "client_id": client_id,
        "timestamp": timestamp,
        "message_id": message_id,
        "name": name if name else None,
        "avatar_url": avatar_url,
        "raw_metadata": raw_metadata,
        "is_echo": is_echo,
        **{k: v for k, v in metadata.items() if v is not None},
        **{k: v for k, v in profile_data.items() if v is not None},
    }

    # Обработка сообщения
    await process_fn(
        sender_id=sender_id,
        message_text=message_text,
        bot_id=bot_id,
        client_external_id=client_id,
        metadata=full_metadata,
        sender_role=sender_role,
        external_id=message_id,
        user_language=user_language,
    )



async def process_integration_message(
    platform: str,
    chat_source: ChatSource,
    sender_id: str,
    message_text: str,
    bot_id: str,
    client_external_id: str,
    metadata: Dict[str, Any],
    sender_role: SenderRole,
    external_id: str,
    user_language: str,
):
    """Обрабатывает сообщение Meta и передаёт его в систему чатов."""
    chat_data = await handle_chat_creation(
        mode=None,
        chat_source=chat_source,
        chat_external_id=bot_id,
        client_external_id=client_external_id,
        company_name=bot_id,
        bot_id=bot_id,
        metadata=metadata,
        request=None,
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
        "external_id": external_id,
        "metadata": metadata,
    }

    redis_session_key = f"chat:session:{chat_id}"
    redis_flood_key = f"flood:{client_id}"

    user_data = {
        "platform": platform,
        "sender_id": sender_id,
        "external_id": external_id,
        "client_external_id": client_external_id,
        "metadata": metadata,
        "is_superuser": sender_role == SenderRole.CONSULTANT,
    }

    asyncio.create_task(
        handle_message(
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
            user_data=user_data,
        )
    )
