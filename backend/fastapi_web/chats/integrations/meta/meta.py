"""Интеграция с Meta."""
import json
import logging
from typing import Any, Dict, List

from fastapi import HTTPException, Request, Response

from utils.help_functions import get_language_from_locale

from .instagram.utils.help_functions import get_instagram_user_profile
from .utils.help_functions import get_meta_locale
from chats.db.mongo.enums import ChatSource, SenderRole
from db.mongo.db_init import mongo_db
from infra import settings


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


# async def handle_incoming_meta_messages(
#     messages_info: List[Dict[str, Any]],
#     request: Request,
#     settings_bot_id: str,
#     chat_source: ChatSource,
#     process_fn,
# ):
#     """Проходит по сообщениям Meta и отправляет их в обработку."""

#     token_key = f"{chat_source.name.upper()}_ACCESS_TOKEN"
#     access_token = getattr(settings, token_key, None)
#     logging.debug(f"🛠️ Используется токен {token_key} (начало: {access_token[:12]}...)")

#     for msg in messages_info:
#         sender_id = msg["sender_id"]
#         recipient_id = msg["recipient_id"]
#         message_text = msg["message_text"]
#         message_id = msg["message_id"]
#         timestamp = msg["timestamp"]
#         meta = msg["metadata"] or {}

#         is_echo = meta.get("is_echo")
#         is_broadcast = meta.get("metadata") == "broadcast"

#         logging.debug(
#             f"📨 [Meta] Входящее сообщение:\n"
#             f"  • sender_id: {sender_id}\n"
#             f"  • recipient_id: {recipient_id}\n"
#             f"  • message_id: {message_id}\n"
#             f"  • is_echo: {is_echo} | is_broadcast: {is_broadcast}\n"
#             f"  • text: {message_text}\n"
#             f"  • metadata: {json.dumps(meta, ensure_ascii=False)}"
#         )

#         # 🛡️ КРИТИЧНО: пропускаем любые эхо-сообщения, чтобы не зациклиться
#         if is_echo:
#             logging.debug(f"⛔ [Meta] Пропущено эхо-сообщение (message_id={message_id})")
#             continue

#         # 🧠 Определение ролей
#         if chat_source == ChatSource.INSTAGRAM:
#             if recipient_id == settings_bot_id:
#                 sender_role = SenderRole.CLIENT
#                 bot_id, client_id = recipient_id, sender_id
#             else:
#                 sender_role = SenderRole.CONSULTANT
#                 bot_id, client_id = sender_id, recipient_id
#         else:
#             if sender_id == settings_bot_id:
#                 sender_role = SenderRole.AI
#                 bot_id, client_id = sender_id, recipient_id
#             else:
#                 sender_role = SenderRole.CLIENT
#                 bot_id, client_id = settings_bot_id, sender_id

#         logging.debug(f"🧾 [Meta] Роль определена как {sender_role.name} | bot_id={bot_id} | client_id={client_id}")

#         # 🔁 Дубликат
#         if message_id:
#             duplicate = await mongo_db.chats.find_one({
#                 "external_id": settings_bot_id,
#                 "messages.external_id": message_id
#             })
#             if duplicate:
#                 logging.debug(f"⛔ [Meta] Пропущено дублирующее сообщение message_id={message_id}")
#                 continue
#         else:
#             logging.warning(f"⚠️ [Meta] message_id отсутствует — нет проверки на дубликаты")

#         # 🌍 Определение языка
#         locale = None
#         if access_token and sender_role == SenderRole.CLIENT:
#             locale = await get_meta_locale(sender_id, access_token)
#         user_language = get_language_from_locale(locale) if locale else "en"

#         if not locale:
#             logging.warning(f"🌐 [Meta] locale не получена для {sender_id} — используется язык по умолчанию: en")
#         else:
#             logging.info(f"🌐 [Meta] Язык: {user_language} (locale={locale}) для sender_id={sender_id}")

#         # 👤 Профиль Instagram
#         name = None
#         avatar_url = None
#         if chat_source == ChatSource.INSTAGRAM and sender_role == SenderRole.CLIENT:
#             profile = await get_instagram_user_profile(sender_id)

#             if not profile:
#                 logging.info(f"🙈 [IG] Профиль {sender_id} пуст — возможно пользователь ограничил доступ")
#             else:
#                 name = profile.get("name")
#                 avatar_url = profile.get("profile_pic")

#                 if not name:
#                     logging.info(f"📛 [IG] Имя отсутствует для {sender_id}")
#                 if not avatar_url:
#                     logging.info(f"🖼️ [IG] Аватар отсутствует для {sender_id}")

#         # 💥 Защита от некорректного типа avatar_url
#         if avatar_url is not None and not isinstance(avatar_url, str):
#             logging.warning(f"⚠️ [Meta] avatar_url не строка: {avatar_url}")
#             avatar_url = None

#         # 🧩 Метаданные
#         metadata_dict = {
#             "sender_id": sender_id,
#             "bot_id": bot_id,
#             "client_id": client_id,
#             "timestamp": timestamp,
#             "message_id": message_id,
#             "name": name,
#             "avatar_url": avatar_url
#         }
#         metadata_dict.update(meta)
#         metadata_dict = {k: v for k, v in metadata_dict.items() if v is not None}

#         logging.info(
#             f"🚀 [Meta] Передаём на обработку: sender_role={sender_role.name} | sender_id={sender_id} | "
#             f"message_id={message_id} | язык={user_language}"
#         )

#         # 🔄 Передаём в обработку
#         await process_fn(
#             sender_id=sender_id,
#             message_text=message_text,
#             bot_id=bot_id,
#             client_external_id=client_id,
#             metadata=metadata_dict,
#             sender_role=sender_role,
#             external_id=message_id,
#             user_language=user_language
#         )




async def handle_incoming_meta_messages(
    messages_info: List[Dict[str, Any]],
    request: Request,
    settings_bot_id: str,
    chat_source: ChatSource,
    process_fn,
):
    """Проходит по сообщениям Meta и отправляет их в обработку."""

    token_key = f"{chat_source.name.upper()}_ACCESS_TOKEN"
    access_token = getattr(settings, token_key, None)
    logging.debug(f"🛠️ Используется токен {token_key} (начало: {access_token[:12]}...)")

    for msg in messages_info:
        sender_id     = msg["sender_id"]
        recipient_id  = msg["recipient_id"]
        message_text  = msg["message_text"]
        message_id    = msg["message_id"]
        timestamp     = msg["timestamp"]
        meta          = msg.get("metadata") or {}

        # Принудительно восстанавливаем важные поля
        meta.setdefault("is_echo", msg.get("is_echo", True))  # echo по умолчанию True, если пришёл с is_echo
        meta.setdefault("message_id", message_id)
        meta.setdefault("raw_metadata", None)

        is_echo       = meta.get("is_echo")
        raw_metadata  = meta.get("raw_metadata")
        is_broadcast  = raw_metadata == "broadcast"

        logging.debug(
            f"📨 [Meta] Входящее сообщение:\n"
            f"  • sender_id: {sender_id}\n"
            f"  • recipient_id: {recipient_id}\n"
            f"  • message_id: {message_id}\n"
            f"  • is_echo: {is_echo} | is_broadcast: {is_broadcast}\n"
            f"  • text: {message_text}\n"
            f"  • metadata: {json.dumps(meta, ensure_ascii=False)}"
        )

        # ─── Защита от лупов ────────────────────────────────────────────────
        if message_id:
            duplicate = await mongo_db.chats.find_one(
                {"messages.external_id": message_id},
                {"_id": 1}
            )
            if duplicate:
                logging.debug(f"⛔ [Meta] Loop-protect: duplicate message_id={message_id} — skip")
                continue
        else:
            logging.warning("⚠️ [Meta] message_id отсутствует — нет проверки на дубликаты")

        if is_echo and is_broadcast:
            logging.debug(f"⛔ [Meta] echo+broadcast — skip message_id={message_id}")
            continue
        # ────────────────────────────────────────────────────────────────────

        # ─── Определение роли ───────────────────────────────────────────────
        if chat_source == ChatSource.INSTAGRAM:
            if is_echo:
                sender_role = SenderRole.CONSULTANT
                bot_id      = sender_id
                client_id   = recipient_id
            else:
                sender_role = SenderRole.CLIENT
                bot_id      = settings_bot_id
                client_id   = sender_id
        else:
            if sender_id == settings_bot_id:
                sender_role = SenderRole.AI
                bot_id      = sender_id
                client_id   = recipient_id
            else:
                sender_role = SenderRole.CLIENT
                bot_id      = settings_bot_id
                client_id   = sender_id

        logging.debug(f"🧾 [Meta] Роль определена как {sender_role.name} | bot_id={bot_id} | client_id={client_id}")

        # ─── Определение языка ──────────────────────────────────────────────
        locale = None
        if access_token and sender_role == SenderRole.CLIENT:
            # Потом включу не удаляй!
            # locale = await get_meta_locale(sender_id, access_token)
            locale = "en_EN"
        user_language = get_language_from_locale(locale) if locale else "en"

        if not locale:
            logging.warning(f"🌐 [Meta] locale не получена для {sender_id} — используется язык по умолчанию: en")
        else:
            logging.info(f"🌐 [Meta] Язык: {user_language} (locale={locale}) для sender_id={sender_id}")

        # ─── Профиль пользователя IG (только для клиента) ───────────────────
        name = None
        avatar_url = None
        if chat_source == ChatSource.INSTAGRAM and sender_role == SenderRole.CLIENT:
            # Потом включу не удаляй!
            # profile = await get_instagram_user_profile(sender_id)
            profile = None
            if profile:
                name = profile.get("name")
                avatar_url = profile.get("profile_pic")

        if avatar_url is not None and not isinstance(avatar_url, str):
            logging.warning(f"⚠️ [Meta] avatar_url не строка: {avatar_url}")
            avatar_url = None

        # ─── Финальные метаданные ───────────────────────────────────────────
        metadata_dict = {
            "sender_id": sender_id,
            "bot_id": bot_id,
            "client_id": client_id,
            "timestamp": timestamp,
            "message_id": message_id,
            "name": name,
            "avatar_url": avatar_url,
            "raw_metadata": raw_metadata,
            "is_echo": is_echo
        }
        metadata_dict.update({k: v for k, v in meta.items() if v is not None})
        metadata_dict = {k: v for k, v in metadata_dict.items() if v is not None}

        logging.info(
            f"🚀 [Meta] Передаём на обработку: sender_role={sender_role.name} | sender_id={sender_id} | "
            f"message_id={message_id} | язык={user_language}"
        )

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
