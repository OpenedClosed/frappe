import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple



from infra import settings
from telegram_bot.infra import settings as bot_settings
import httpx


from db.mongo.db_init import mongo_db
from notifications.db.mongo.schemas import Notification, EntityRef
from notifications.db.mongo.enums import Priority, NotificationChannel

logger = logging.getLogger(__name__)



def channel_from_english(en_name: str) -> NotificationChannel:
    """
    Возвращает Enum-значение канала по английской метке.
    Например: "Telegram" -> NotificationChannel.TELEGRAM
              "Web (in-app)" -> NotificationChannel.WEB
    """
    if not en_name:
        raise ValueError("Empty channel english name")
    en_name = str(en_name).strip()
    for ch in NotificationChannel:
        try:
            if getattr(ch, "en_value", None) == en_name:
                return ch
        except Exception:
            pass
    for ch in NotificationChannel:
        try:
            data = json.loads(ch.value)
            if data.get("en") == en_name:
                return ch
        except Exception:
            continue
    raise ValueError(f"Unknown NotificationChannel by english name: {en_name!r}")


# async def create_notifications(items: List[Dict[str, Any]]) -> Dict[str, Any]:
#     """
#     Универсальный хелпер создания уведомлений.
#     Каждый элемент:
#       {
#         "resource_en": NotificationChannel.TELEGRAM.en_value | "Telegram" | "Web (in-app)" | ...,
#         "message": "<html or text>",
#         # optional:
#         "title": {"en": "...", "ru": "..."},
#         "kind": "chat_new",
#         "priority": "high" | "normal" | "low" | "critical" | Priority.HIGH | ...,
#         "recipient_user_id": "USER_ID or None",
#         "entity": {"entity_type": "...", "entity_id": "...", "route": "/admin/...", "extra": {...}},
#         "link_url": "https://..",
#         "popup": True,
#         "sound": True,
#         "meta": {...},

#         # для Telegram:
#         "telegram": {"chat_id": "...", "message_thread_id": 123}  # опционально
#       }
#     Возвращает: {"ok": bool, "created": N, "ids": [...], "telegram": {"sent": X, "errors": [...]}}.
#     """
#     created = 0
#     created_ids: List[str] = []
#     tg_sent = 0
#     tg_errors: List[str] = []

#     BOT_WEBHOOK_URL = "http://bot:9999/webhook/send_message"
#     print('='*100)
#     print("Вызвана нотификация!")

#     for item in items:
#         try:
#             channel = channel_from_english(item["resource_en"])
#             pr = item.get("priority", Priority.NORMAL)
#             if isinstance(pr, str):
#                 pr = getattr(Priority, pr.strip().upper(), Priority.NORMAL)

#             entity_obj: Optional[EntityRef] = None
#             if item.get("entity"):
#                 entity_obj = EntityRef(**item["entity"])

#             notif = Notification(
#                 kind=item.get("kind") or "generic",
#                 message=item["message"],
#                 title=item.get("title"),
#                 priority=pr,
#                 deliver_to=[channel],
#                 popup=bool(item.get("popup", True)),
#                 sound=bool(item.get("sound", True)),
#                 recipient_user_id=item.get("recipient_user_id"),
#                 entity=entity_obj,
#                 link_url=item.get("link_url"),
#                 meta=item.get("meta") or {},
#                 created_at=datetime.utcnow(),
#             )

#             res = await mongo_db["notifications"].insert_one(notif.model_dump())
#             created += 1
#             created_ids.append(str(res.inserted_id))

#             # --- фактическая отправка в Telegram «как раньше», без вспомогательных хелперов ---
#             print(channel)
#             print(channel == NotificationChannel.TELEGRAM)
#             if channel == NotificationChannel.TELEGRAM:
#                 if "localhost" in BOT_WEBHOOK_URL:
#                     continue
#                 # локально — не шлём (поведение старой версии)
#                 tg_opts = item.get("telegram") or {}
#                 admin_chat_id = tg_opts.get("chat_id") or bot_settings.ADMIN_CHAT_ID
#                 print(admin_chat_id)
#                 message_thread_id = tg_opts.get("message_thread_id")

#                 # поддержка формата "CHATID/THREADID"
#                 if isinstance(admin_chat_id, str) and "/" in admin_chat_id:
#                     parts = admin_chat_id.split("/")
#                     if len(parts) >= 2:
#                         admin_chat_id = parts[0]
#                         if message_thread_id is None and parts[1]:
#                             try:
#                                 message_thread_id = int(parts[1])
#                             except ValueError:
#                                 message_thread_id = None

#                 try:
#                     async with httpx.AsyncClient() as client_http:

#                         payload: Dict[str, Any] = {
#                             "chat_id": admin_chat_id,
#                             "text": notif.message,
#                             "parse_mode": "HTML",
#                         }
#                         if message_thread_id:
#                             payload["message_thread_id"] = message_thread_id

#                         resp = await client_http.post(BOT_WEBHOOK_URL, json=payload, timeout=10.0)
#                         resp.raise_for_status()
#                     tg_sent += 1
#                 except httpx.HTTPStatusError as exc:
#                     err = f"Ошибка от бота ({exc.response.status_code}): {exc.response.text}"
#                     logger.error(err)
#                     tg_errors.append(err)
#                 except Exception as exc:
#                     logger.exception("Ошибка при отправке сообщения в бот")
#                     tg_errors.append(str(exc))

#         except Exception as exc:
#             logger.exception("create_notifications item failed")
#             tg_errors.append(str(exc))

#     ok = (created > 0) and (not tg_errors)
#     return {"ok": ok, "created": created, "ids": created_ids, "telegram": {"sent": tg_sent, "errors": tg_errors}}



async def create_notifications(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    created = 0
    created_ids: List[str] = []
    tg_sent = 0
    tg_errors: List[str] = []

    BOT_WEBHOOK_URL = "http://bot:9999/webhook/send_message"

    for item in items:
        try:
            channel = channel_from_english(item["resource_en"])
            pr = item.get("priority", Priority.NORMAL)
            if isinstance(pr, str):
                pr = getattr(Priority, pr.strip().upper(), Priority.NORMAL)

            entity_obj: Optional[EntityRef] = None
            if item.get("entity"):
                entity_obj = EntityRef(**item["entity"])

            notif = Notification(
                kind=item.get("kind") or "generic",
                message=item["message"],
                title=item.get("title"),
                priority=pr,
                deliver_to=[channel],
                popup=bool(item.get("popup", True)),
                sound=bool(item.get("sound", True)),
                recipient_user_id=item.get("recipient_user_id"),
                entity=entity_obj,
                link_url=item.get("link_url"),
                meta=item.get("meta") or {},
                created_at=datetime.utcnow(),
            )

            res = await mongo_db.notifications.insert_one(notif.model_dump())
            created += 1
            created_ids.append(str(res.inserted_id))

            # === Пролив в Frappe (идемпотентно, один в один контент) ===
            try:
                entity_id = (notif.entity.entity_id if notif.entity else "") or "-"
                idem = (
                    item.get("idempotency_key")
                    or (item.get("meta") or {}).get("idem")
                    or f"{notif.kind}:{entity_id}"
                )
                frappe_payload = build_frappe_notification_payload(
                    kind=notif.kind,
                    html=notif.message,
                    title=notif.title or {},
                    entity_type=(notif.entity.entity_type if notif.entity else "generic"),
                    entity_id=entity_id,
                    route=(notif.entity.route if notif.entity else None),
                    link_url=notif.link_url,
                    account_id=(notif.entity.extra.get("account_id") if (notif.entity and notif.entity.extra) else None),
                    idempotency_key=idem,
                )
                await get_frappe_client().create_notification_from_upstream(frappe_payload)
            except Exception:
                logger.exception("Frappe notification proxy failed")

            # --- отправка в Telegram как раньше ---
            if channel == NotificationChannel.TELEGRAM:
                if "localhost" in BOT_WEBHOOK_URL:
                    continue
                tg_opts = item.get("telegram") or {}
                admin_chat_id = tg_opts.get("chat_id") or bot_settings.ADMIN_CHAT_ID
                message_thread_id = tg_opts.get("message_thread_id")

                if isinstance(admin_chat_id, str) and "/" in admin_chat_id:
                    parts = admin_chat_id.split("/")
                    if len(parts) >= 2:
                        admin_chat_id = parts[0]
                        if message_thread_id is None and parts[1]:
                            try:
                                message_thread_id = int(parts[1])
                            except ValueError:
                                message_thread_id = None

                try:
                    async with httpx.AsyncClient() as client_http:
                        payload: Dict[str, Any] = {
                            "chat_id": admin_chat_id,
                            "text": notif.message,
                            "parse_mode": "HTML",
                        }
                        if message_thread_id:
                            payload["message_thread_id"] = message_thread_id

                        resp = await client_http.post(BOT_WEBHOOK_URL, json=payload, timeout=10.0)
                        resp.raise_for_status()
                    tg_sent += 1
                except httpx.HTTPStatusError as exc:
                    err = f"Ошибка от бота ({exc.response.status_code}): {exc.response.text}"
                    logger.error(err)
                    tg_errors.append(err)
                except Exception as exc:
                    logger.exception("Ошибка при отправке сообщения в бот")
                    tg_errors.append(str(exc))

        except Exception as exc:
            logger.exception("create_notifications item failed")
            tg_errors.append(str(exc))

    ok = (created > 0) and (not tg_errors)
    return {"ok": ok, "created": created, "ids": created_ids, "telegram": {"sent": tg_sent, "errors": tg_errors}}


async def create_simple_notifications(resources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Упрощённый алиас: [{"resource_en": "Web (in-app)", "message": "..."}, ...]"""
    return await create_notifications(resources)
