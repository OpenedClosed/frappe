from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from db.mongo.db_init import mongo_db
from integrations.frappe.client import get_frappe_client, FrappeError

TIME_FIELDS = [
    "updated_at", "last_message_at", "last_event_at", "last_activity_at",
    "modified_at", "modifiedAt", "updatedAt", "ts",
    "created_at", "createdAt",
]


def normalize_platform(platform: Optional[str]) -> str:
    val = (platform or "").strip().lower()
    mapping = {
        "telegram": "Telegram",
        "telegram mini-app": "Telegram Mini-App",
        "telegram-mini-app": "Telegram Mini-App",
        "instagram": "Instagram",
        "facebook": "Facebook",
        "whatsapp": "WhatsApp",
        "telephony": "Telephony",
        "sms": "SMS",
        "email": "Email",
        "internal": "Internal",
        "web": "Web Form",
        "web form": "Web Form",
        "webform": "Web Form",
    }
    return mapping.get(val, "Internal")


def normalize_channel_type(kind: Optional[str]) -> str:
    val = (kind or "").strip().lower()
    mapping = {
        "chat": "Chat",
        "call": "Call",
        "sms": "SMS",
        "email": "Email",
        "web": "Web Form",
        "web form": "Web Form",
    }
    return mapping.get(val, "Chat")


def to_frappe_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        elif isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return value
        elif isinstance(value, datetime):
            dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        else:
            return None
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def pick_first(*args: Any) -> Optional[str]:
    for v in args:
        if v is None:
            continue
        txt = str(v).strip()
        if txt:
            return txt
    return None


def build_title(chat: Dict[str, Any]) -> str:
    platform = normalize_platform(chat.get("platform") or chat.get("channel") or chat.get("source"))
    display = pick_first(
        chat.get("display_name"),
        (chat.get("client") or {}).get("display_name"),
        (chat.get("user") or {}).get("name"),
        chat.get("username"),
    ) or ""
    short = (str(chat.get("_id") or chat.get("id") or "") or "")[:6]
    parts = ["Chat", "•", platform]
    if display:
        parts += ["•", display]
    elif short:
        parts += ["•", short]
    return " ".join([p for p in parts if p])


def get_collection(name: str):
    try:
        return mongo_db.get_collection(name)
    except Exception:
        return getattr(mongo_db, name, None)


def find_chats_collection() -> Tuple[str, Any]:
    for cname in ["chats", "chat_sessions", "conversations"]:
        col = get_collection(cname)
        if col is not None:
            return cname, col
    return "chats", get_collection("chats")


async def load_chat(chat_id: str) -> Optional[Dict[str, Any]]:
    for cname in ["chats", "chat_sessions", "conversations"]:
        try:
            col = get_collection(cname)
            if col is None:
                continue
            doc = None
            if ObjectId.is_valid(chat_id):
                doc = await col.find_one({"_id": ObjectId(chat_id)})
            if not doc:
                doc = await col.find_one({"id": chat_id})
            if not doc:
                continue
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            print(f"[load_chat] found in collection={cname}")
            return doc
        except Exception as exc:
            print(f"[load_chat] error coll={cname} chat_id={chat_id} err={exc}")
    return None


async def ensure_case_from_chat(chat: Dict[str, Any]) -> Dict[str, Any]:
    client = get_frappe_client()

    chat_id = str(chat.get("_id") or chat.get("id") or "").strip()
    if not chat_id:
        print("[ensure_case_from_chat] skip: chat has no id-like field")
        return {"ok": False, "reason": "chat_has_no_id"}

    platform = normalize_platform(chat.get("platform") or chat.get("channel"))
    channel_type = normalize_channel_type(chat.get("type"))

    display_name = pick_first(
        chat.get("display_name"),
        (chat.get("client") or {}).get("display_name"),
        (chat.get("user") or {}).get("name"),
        chat.get("username"),
    )
    phone = pick_first(chat.get("phone"), (chat.get("client") or {}).get("phone"))
    email = pick_first(chat.get("email"), (chat.get("client") or {}).get("email"))
    preferred_language = pick_first(chat.get("lang"), chat.get("language")) or "ru"
    external_user_id = pick_first(chat.get("external_user_id"), (chat.get("client") or {}).get("external_id"))
    mongo_client_id = pick_first(chat.get("client_id"), (chat.get("client") or {}).get("_id"))

    first_event_at = to_frappe_dt(chat.get("created_at") or chat.get("createdAt"))
    last_event_at = to_frappe_dt(
        chat.get("updated_at") or chat.get("updatedAt")
        or chat.get("last_message_at") or chat.get("last_event_at")
        or chat.get("last_activity_at") or chat.get("modified_at") or chat.get("modifiedAt")
    )
    events_count = int(chat.get("messages_count") or chat.get("events_count") or 0)
    unanswered_count = int(chat.get("unanswered_count") or 0)

    last_actor_role = pick_first(chat.get("last_actor_role"))
    runtime_status = pick_first(chat.get("runtime_status"))

    title = build_title(chat)

    # ищем существующий кейс аккуратно (get_value быстрее и без лишних данных)
    try:
        found = await client.request("get_value", {
            "doctype": "Engagement Case",
            "fieldname": "name",
            "filters": {"mongo_chat_id": chat_id},
        })
    except FrappeError as exc:
        print(f"[ensure_case_from_chat] frappe.get_value error chat_id={chat_id} err={exc}")
        return {"ok": False, "reason": "frappe_get_value_failed"}

    case_name = found.get("name") if isinstance(found, dict) else None
    created = False

    if not case_name:
        doc = {
            "doctype": "Engagement Case",
            "naming_series": "IE-.YYYY.-.#####",
            "title": title,
            "channel_type": channel_type,
            "channel_platform": platform,
            "display_name": display_name,
            "phone": phone,
            "email": email,
            "preferred_language": preferred_language,
            "mongo_chat_id": chat_id,
            "mongo_client_id": mongo_client_id,
            "external_user_id": external_user_id,
            "crm_status": "New",
            "first_event_at": first_event_at,
            "last_event_at": last_event_at,
            "events_count": events_count,
            "unanswered_count": unanswered_count,
            "last_actor_role": last_actor_role,
            "runtime_status": runtime_status,
        }
        try:
            saved = await client.request("insert", {"doc": doc})
            case_name = saved.get("name") if isinstance(saved, dict) else None
            created = True
            print(f"[ensure_case_from_chat] created case name={case_name} chat_id={chat_id}")
        except FrappeError as exc:
            print(f"[ensure_case_from_chat] frappe.insert error chat_id={chat_id} err={exc}")
            return {"ok": False, "reason": "frappe_insert_failed"}

    # апдейт: сначала get, потом save — иначе TimestampMismatch на гонках
    updates = {
        "title": title,
        "channel_type": channel_type,
        "channel_platform": platform,
        "display_name": display_name,
        "phone": phone,
        "email": email,
        "preferred_language": preferred_language,
        "mongo_client_id": mongo_client_id,
        "external_user_id": external_user_id,
        "first_event_at": first_event_at,
        "last_event_at": last_event_at,
        "events_count": events_count,
        "unanswered_count": unanswered_count,
        "last_actor_role": last_actor_role,
        "runtime_status": runtime_status,
    }
    clean_updates = {k: v for k, v in updates.items() if v is not None}

    try:
        existing = await client.request("get", {"doctype": "Engagement Case", "name": case_name})
        if isinstance(existing, dict):
            existing.update(clean_updates)
            _ = await client.request("save", {"doc": existing})
            print(f"[ensure_case_from_chat] saved case name={case_name} created={created} fields={list(clean_updates.keys())}")
        else:
            # фолбэк по одному полю
            for k, v in clean_updates.items():
                try:
                    _ = await client.request("set_value", {
                        "doctype": "Engagement Case",
                        "name": case_name,
                        "fieldname": k,
                        "value": v,
                    })
                except Exception as exc:
                    print(f"[ensure_case_from_chat] set_value failed name={case_name} field={k} err={exc}")
    except FrappeError as exc:
        print(f"[ensure_case_from_chat] frappe.get/save error name={case_name} err={exc}")
        return {"ok": False, "reason": "frappe_save_failed", "case_name": case_name}

    return {"ok": True, "case_name": case_name, "created": created}


async def sync_one_by_chat_id(chat_id: str) -> Dict[str, Any]:
    print(f"[sync_one_by_chat_id] fetch chat chat_id={chat_id}")
    chat = await load_chat(chat_id)
    if not chat:
        print(f"[sync_one_by_chat_id] not found chat_id={chat_id}")
        return {"ok": False, "reason": "chat_not_found"}
    res = await ensure_case_from_chat(chat)
    print(f"[sync_one_by_chat_id] ensured case result={res}")
    return res


async def sync_recent(minutes: int, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Если limit is None → без лимита (проходим все, кто новее порога).
    """
    dt_limit = datetime.now(tz=timezone.utc) - timedelta(minutes=int(minutes))
    ts_limit = dt_limit.timestamp()

    try:
        names = await mongo_db.list_collection_names()
        print(f"[sync_recent] collections={names}")
    except Exception as exc:
        print(f"[sync_recent] list_collection_names failed err={exc}")

    cname, col = find_chats_collection()
    print(f"[sync_recent] using collection={cname} since={dt_limit.isoformat()} limit={'NO_LIMIT' if limit is None else limit}")

    or_conds = []
    for f in TIME_FIELDS:
        or_conds.append({f: {"$gte": ts_limit}})
        or_conds.append({f: {"$gte": dt_limit}})
    query = {"$or": or_conds} if or_conds else {}
    sort_keys = [(f, -1) for f in TIME_FIELDS] + [("_id", -1)]

    chats: List[Dict[str, Any]] = []
    try:
        cursor = col.find(query).sort(sort_keys)
        if isinstance(limit, int) and limit > 0:
            cursor = cursor.limit(int(limit))
        async for c in cursor:
            if "_id" in c:
                c["_id"] = str(c["_id"])
            chats.append(c)
    except Exception as exc:
        print(f"[sync_recent] query failed err={exc}")

    print(f"[sync_recent] fetched recent count={len(chats)}")

    if not chats:
        try:
            fallback = col.find({}).sort(sort_keys)
            if isinstance(limit, int) and limit > 0:
                fallback = fallback.limit(int(limit))
            async for c in fallback:
                if "_id" in c:
                    c["_id"] = str(c["_id"])
                chats.append(c)
            print(f"[sync_recent] fallback count={len(chats)}")
        except Exception as exc:
            print(f"[sync_recent] fallback failed err={exc}")

    created = 0
    updated = 0
    ids: List[str] = []

    for chat in chats:
        try:
            res = await ensure_case_from_chat(chat)
            if res.get("ok"):
                ids.append(res.get("case_name") or "")
                if res.get("created"):
                    created += 1
                else:
                    updated += 1
            else:
                print(f"[sync_recent] ensure failed chat_id={chat.get('_id') or chat.get('id')} reason={res.get('reason')}")
        except Exception as exc:
            print(f"[sync_recent] ensure raised chat_id={chat.get('_id') or chat.get('id')} err={exc}")

    return {"ok": True, "scanned": len(chats), "created": created, "updated": updated, "ids": ids}