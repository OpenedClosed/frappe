from __future__ import annotations

import json
import hashlib
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


# -------------------- helpers: normalize/parse --------------------
def _to_plain_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, dict):
        for k in ("en", "ru", "pl", "uk", "ka", "be", "value", "name"):
            v = val.get(k)
            if isinstance(v, str) and v.strip():
                return v
        for _, v in val.items():
            if isinstance(v, str) and v.strip():
                return v
        return ""
    s = str(val).strip()
    if not s:
        return ""
    if s.startswith("{") and s.endswith("}"):
        try:
            j = json.loads(s)
            return _to_plain_str(j)
        except Exception:
            pass
    return s


def normalize_platform_from_candidates(*candidates: Any) -> str:
    raw_values: List[str] = []
    for c in candidates:
        if c is None:
            continue
        raw = _to_plain_str(c).lower()
        if raw:
            raw_values.append(raw)

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
        "website": "Web Form",
    }

    for raw in raw_values:
        if raw in mapping:
            return mapping[raw]
        for k, v in mapping.items():
            if raw == k or raw.replace("_", " ") == k or raw.replace("-", " ") == k or k in raw:
                return v

    for raw in raw_values:
        if raw.startswith("instagram_"):
            return "Instagram"
        if raw.startswith("telegram_"):
            return "Telegram"
        if raw.startswith("whatsapp_"):
            return "WhatsApp"
        if raw.startswith("facebook_"):
            return "Facebook"
        if raw.startswith("internal_"):
            return "Internal"

    return "Internal"


def normalize_platform(chat: Dict[str, Any]) -> str:
    client = chat.get("client") or {}
    csrc = client.get("source")
    return normalize_platform_from_candidates(
        chat.get("platform"),
        chat.get("channel"),
        chat.get("source"),
        csrc,
        client.get("client_id"),
    )


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


def build_title(chat_id: str) -> str:
    return str(chat_id)


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
                doc = await col.find_one({"chat_id": chat_id}) or await col.find_one({"id": chat_id})
            if not doc:
                continue
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            print(f"[load_chat] found in collection={cname}")
            return doc
        except Exception as exc:
            print(f"[load_chat] error coll={cname} chat_id={chat_id} err={exc}")
    return None


def _stable_hash(payload: Dict[str, Any]) -> str:
    """детерминированный sha1 по стабильным полям (исключаем волатильные вроде last_synced_at)"""
    volatile = {"last_synced_at"}
    stable = {k: v for k, v in payload.items() if k not in volatile}
    s = json.dumps(stable, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _role_en(val: Any) -> str:
    s = _to_plain_str(val).lower()
    if not s:
        return ""
    if s in {"client", "клиент"}:
        return "Client"
    if s in {"ai assistant", "ai", "бот", "assistant", "ии-помощник"}:
        return "AI Assistant"
    if s in {"consultant", "консультант", "operator", "agent", "админ"}:
        return "Consultant"
    return s.title()


def _extract_messages(chat: Dict[str, Any]) -> List[Dict[str, Any]]:
    msgs = chat.get("messages") or []
    if isinstance(msgs, str):
        try:
            msgs = json.loads(msgs)
        except Exception:
            msgs = []
    return msgs if isinstance(msgs, list) else []


def _extract_ts(chat: Dict[str, Any]) -> float:
    for f in TIME_FIELDS:
        v = chat.get(f)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
        if isinstance(v, datetime):
            return (v if v.tzinfo else v.replace(tzinfo=timezone.utc)).timestamp()
    msgs = _extract_messages(chat)
    if msgs:
        try:
            last = msgs[-1].get("timestamp")
            if isinstance(last, (int, float)):
                return float(last)
            if isinstance(last, str):
                return datetime.fromisoformat(last.replace("Z", "+00:00")).timestamp()
            if isinstance(last, datetime):
                return (last if last.tzinfo else last.replace(tzinfo=timezone.utc)).timestamp()
        except Exception:
            pass
    for f in ("last_activity", "created_at", "createdAt"):
        v = chat.get(f)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
        if isinstance(v, datetime):
            return (v if v.tzinfo else v.replace(tzinfo=timezone.utc)).timestamp()
    return 0.0


async def _load_client_by_client_id(client_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not client_id:
        return None
    try:
        col = get_collection("clients")
        if col is None:
            return None
        doc = await col.find_one({"client_id": client_id}) or await col.find_one({"id": client_id})
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
    except Exception:
        return None


def _build_source_avatar_path(platform: str) -> str:
    # имена файлов аватаров — по твоему неймингу
    fname = {
        "Instagram": "insta.png",
        "Facebook": "facebook.png",
        "WhatsApp": "whatsapp.png",
        "Telegram": "telegram.png",
        "Telegram Mini-App": "miniapp.png",
        "Internal": "internal.png",
        "Email": "internal.png",
        "Web Form": "internal.png",
        "Telephony": "internal.png",
        "SMS": "internal.png",
    }.get(platform, "internal.png")
    # важно: без лидирующего слэша, как ты просил → "files/..."
    return f"/files/source_avatars/{fname}"


_ALLOWED_LANGS = {"ru", "en", "pl", "uk", "ka", "be"}


def _coerce_lang(val: Any) -> Optional[str]:
    s = _to_plain_str(val).lower()
    if not s:
        return None
    s = s.replace("_", "-")
    if "-" in s:
        s = s.split("-")[0]
    if s in _ALLOWED_LANGS:
        return s
    return None


def _extract_user_language(*objs: Any) -> Optional[str]:
    keys = ("user_language", "language", "locale")
    for obj in objs:
        if not obj:
            continue
        if isinstance(obj, dict):
            md = obj.get("metadata") or obj
            for k in keys:
                lang = _coerce_lang(md.get(k))
                if lang:
                    return lang
        lang = _coerce_lang(obj)
        if lang:
            return lang
    return None


# -------------------- main upsert --------------------
async def ensure_case_from_chat(chat: Dict[str, Any]) -> Dict[str, Any]:
    client = get_frappe_client()

    chat_id = str(chat.get("_id") or chat.get("id") or chat.get("chat_id") or "").strip()
    if not chat_id:
        print("[ensure_case_from_chat] skip: chat has no id-like field")
        return {"ok": False, "reason": "chat_has_no_id"}

    platform = normalize_platform(chat)
    channel_type = normalize_channel_type(chat.get("type"))

    chat_client = chat.get("client") or {}
    mongo_client_id = pick_first(
        chat_client.get("client_id"),
        chat.get("client_id"),
        chat_client.get("id"),
    )
    client_doc = await _load_client_by_client_id(mongo_client_id)

    display_name = pick_first(
        chat.get("display_name"),
        chat_client.get("display_name"),
        (client_doc or {}).get("name"),
        ((client_doc or {}).get("metadata") or {}).get("name"),
        (chat.get("user") or {}).get("name"),
        chat.get("username"),
    )
    phone = pick_first(chat.get("phone"), chat_client.get("phone"), (client_doc or {}).get("phone"))
    email = pick_first(chat.get("email"), chat_client.get("email"), (client_doc or {}).get("email"))

    preferred_language = (
        _extract_user_language(
            chat,
            chat_client,
            client_doc,
            (client_doc or {}).get("metadata"),
            (chat_client or {}).get("metadata")
        ) or "ru"
    )

    external_user_id = pick_first(
        chat.get("external_user_id"),
        chat_client.get("external_id"),
        (client_doc or {}).get("external_id"),
        ((client_doc or {}).get("metadata") or {}).get("sender_id"),
        ((chat_client.get("metadata") or {}) or {}).get("sender_id"),
    )

    avatar = pick_first(
        chat.get("avatar"),
        chat_client.get("avatar_url"),
        (client_doc or {}).get("avatar_url"),
    ) or _build_source_avatar_path(platform)

    msgs = _extract_messages(chat)
    first_event_at = to_frappe_dt(
        chat.get("created_at")
        or (msgs[0].get("timestamp") if msgs else None)
        or chat.get("createdAt")
    )
    last_event_at = to_frappe_dt(
        chat.get("updated_at") or chat.get("updatedAt") or chat.get("last_message_at")
        or (msgs[-1].get("timestamp") if msgs else None)
        or chat.get("last_activity") or chat.get("last_activity_at")
        or chat.get("modified_at") or chat.get("modifiedAt")
    )
    events_count = int(
        chat.get("messages_count")
        or chat.get("events_count")
        or (len(msgs) if isinstance(msgs, list) else 0)
        or 0
    )

    unanswered_count = 0
    for i in range(len(msgs) - 1, -1, -1):
        role = _role_en(msgs[i].get("sender_role"))
        if role == "Client":
            unanswered_count += 1
        else:
            break

    last_actor_role = _role_en(msgs[-1].get("sender_role")) if msgs else pick_first(chat.get("last_actor_role"))
    runtime_status = pick_first(chat.get("runtime_status"))

    title = build_title(chat_id)

    upstream_payload = {
        "title": title,
        "avatar": avatar,
        "channel_type": channel_type,
        "channel_platform": platform,
        "display_name": display_name,
        "phone": phone,
        "email": email,
        "preferred_language": preferred_language,
        "mongo_chat_id": chat_id,
        "mongo_client_id": mongo_client_id,
        "external_user_id": external_user_id,
        "first_event_at": first_event_at,
        "last_event_at": last_event_at,
        "events_count": events_count,
        "unanswered_count": unanswered_count,
        "last_actor_role": last_actor_role,
        "runtime_status": runtime_status,
    }
    payload_hash = _stable_hash(upstream_payload)

    # ---- state lookup (Mongo cache)
    state_col = get_collection("frappe_sync_state")
    case_name_from_state = None
    try:
        state = await state_col.find_one({"chat_id": chat_id}) if (state_col is not None) else None
        if state and state.get("hash") == payload_hash and state.get("case_name"):
            return {
                "ok": True,
                "case_name": state["case_name"],
                "created": False,
                "skipped": True,
                "reason": "no_changes",
            }
        if state:
            case_name_from_state = state.get("case_name")
    except Exception as exc:
        print(f"[ensure_case_from_chat] state lookup failed err={exc}")

    # ---- find/create case
    frappe_client = client
    case_name = case_name_from_state
    if not case_name:
        try:
            found = await frappe_client.request("get_value", {
                "doctype": "Engagement Case",
                "fieldname": "name",
                "filters": {"mongo_chat_id": chat_id},
            })
            case_name = found.get("name") if isinstance(found, dict) else None
        except FrappeError as exc:
            print(f"[ensure_case_from_chat] frappe.get_value error chat_id={chat_id} err={exc}")
            return {"ok": False, "reason": "frappe_get_value_failed"}

    created = False
    if not case_name:
        try:
            saved = await frappe_client.request("insert", {
                "doc": {
                    "doctype": "Engagement Case",
                    "naming_series": "IE-.YYYY.-.#####",
                    "crm_status": "New",
                    **upstream_payload,
                }
            })
            case_name = saved.get("name") if isinstance(saved, dict) else None
            created = True
            print(f"[ensure_case_from_chat] created case name={case_name} chat_id={chat_id} platform={platform}")
        except FrappeError as exc:
            print(f"[ensure_case_from_chat] frappe.insert error chat_id={chat_id} err={exc}")
            return {"ok": False, "reason": "frappe_insert_failed"}

    # ---- update only changed fields, с уважением к ручным правкам
    try:
        existing = await frappe_client.request("get", {"doctype": "Engagement Case", "name": case_name})
    except FrappeError as exc:
        print(f"[ensure_case_from_chat] frappe.get error name={case_name} err={exc}")
        return {"ok": False, "reason": "frappe_get_failed", "case_name": case_name}

    if not isinstance(existing, dict):
        existing = {}

    def non_empty(v: Any) -> bool:
        return bool(str(v or "").strip())

    def is_default_avatar(val: Any) -> bool:
        # считаем «дефолтом» наши source_avatars независимо от лидирующего слэша
        return str(val or "").lstrip("/").startswith("files/source_avatars/")

    locked_updates = dict(upstream_payload)
    try:
        if non_empty(existing.get("title")) and not str(existing.get("title")).startswith("Chat • "):
            locked_updates.pop("title", None)
        for field in ["display_name", "phone", "email"]:
            if non_empty(existing.get(field)):
                locked_updates.pop(field, None)
        if non_empty(existing.get("preferred_language")) and existing.get("preferred_language") != "ru":
            locked_updates.pop("preferred_language", None)
        if non_empty(existing.get("avatar")) and not is_default_avatar(existing.get("avatar")):
            locked_updates.pop("avatar", None)
    except Exception:
        pass

    changes: Dict[str, Any] = {}
    for k, v in locked_updates.items():
        if k == "avatar":
            # сравнение для аватара — без ведущего слэша, чтобы не триггерить лишние апдейты
            cur = str(existing.get(k) or "")
            if cur.lstrip("/") != str(v or "").lstrip("/"):
                changes[k] = v
        else:
            if existing.get(k) != v:
                changes[k] = v

    if not created and not changes:
        try:
            if state_col is not None:
                await state_col.update_one(
                    {"chat_id": chat_id},
                    {"$set": {
                        "chat_id": chat_id,
                        "case_name": case_name,
                        "hash": payload_hash,
                        "updated_at": datetime.now(timezone.utc),
                    }},
                    upsert=True,
                )
        except Exception as exc:
            print(f"[ensure_case_from_chat] state upsert (no-change) failed err={exc}")
        return {"ok": True, "case_name": case_name, "created": created, "skipped": True, "reason": "no_field_changes"}

    try:
        if changes:
            existing.update(changes)
            _ = await frappe_client.request("save", {"doc": existing})
            print(f"[ensure_case_from_chat] saved case name={case_name} created={created} fields={list(changes.keys())}")
    except FrappeError as exc:
        print(f"[ensure_case_from_chat] frappe.save error name={case_name} err={exc}")
        return {"ok": False, "reason": "frappe_save_failed", "case_name": case_name, "changes": list(changes.keys())}

    try:
        if state_col is not None:
            await state_col.update_one(
                {"chat_id": chat_id},
                {"$set": {
                    "chat_id": chat_id,
                    "case_name": case_name,
                    "hash": payload_hash,
                    "updated_at": datetime.now(timezone.utc),
                }},
                upsert=True,
            )
    except Exception as exc:
        print(f"[ensure_case_from_chat] state upsert failed err={exc}")

    return {"ok": True, "case_name": case_name, "created": created, "updated_fields": list(changes.keys())}


# -------------------- public API --------------------
async def sync_one_by_chat_id(chat_id: str) -> Dict[str, Any]:
    print(f"[sync_one_by_chat_id] fetch chat chat_id={chat_id}")
    chat = await load_chat(chat_id)
    if not chat:
        print(f"[sync_one_by_chat_id] not found chat_id={chat_id}")
        return {"ok": False, "reason": "chat_not_found"}

    platform = normalize_platform(chat)
    client = chat.get("client") or {}
    print(
        "[sync_one_by_chat_id] PREVIEW",
        {
            "chat_id": str(chat.get('_id') or chat.get('id') or chat.get('chat_id')),
            "raw": {
                "chat.platform": chat.get("platform"),
                "chat.channel": chat.get("channel"),
                "chat.source": chat.get("source"),
                "client.source": client.get("source"),
                "client.client_id": client.get("client_id"),
            },
            "normalized_platform": platform,
        }
    )

    res = await ensure_case_from_chat(chat)
    print(f"[sync_one_by_chat_id] ensured case result={res}")
    return res


async def sync_recent(minutes: int, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Берём свежие чаты. Временно форсим limit=50.
    Обрабатываем от старых к новым, чтобы самые новые создавались в конце.
    """
    limit = 50
    dt_limit = datetime.now(tz=timezone.utc) - timedelta(minutes=int(minutes))
    ts_limit = dt_limit.timestamp()

    try:
        names = await mongo_db.list_collection_names()
        print(f"[sync_recent] collections={names}")
    except Exception as exc:
        print(f"[sync_recent] list_collection_names failed err={exc}")

    cname, col = find_chats_collection()
    print(f"[sync_recent] using collection={cname} since={dt_limit.isoformat()} limit={limit}")

    or_conds = []
    for f in TIME_FIELDS:
        or_conds.append({f: {"$gte": ts_limit}})
        or_conds.append({f: {"$gte": dt_limit}})
    query = {"$or": or_conds} if or_conds else {}

    sort_keys = [(f, -1) for f in TIME_FIELDS] + [("_id", -1)]

    chats: List[Dict[str, Any]] = []
    try:
        cursor = col.find(query).sort(sort_keys).limit(int(limit))
        async for c in cursor:
            if "_id" in c:
                c["_id"] = str(c["_id"])
            chats.append(c)
    except Exception as exc:
        print(f"[sync_recent] query failed err={exc}")

    print(f"[sync_recent] fetched recent count={len(chats)}")

    if not chats:
        try:
            fallback = col.find({}).sort(sort_keys).limit(int(limit))
            async for c in fallback:
                if "_id" in c:
                    c["_id"] = str(c["_id"])
                chats.append(c)
            print(f"[sync_recent] fallback count={len(chats)}")
        except Exception as exc:
            print(f"[sync_recent] fallback failed err={exc}")

    # превью первых 5 — чтобы не засорять логи
    preview = []
    for i, ch in enumerate(chats[:5]):
        client = ch.get("client") or {}
        platform = normalize_platform(ch)
        ts = _extract_ts(ch)
        preview.append({
            "i": i,
            "chat_id": str(ch.get("_id") or ch.get("id") or ch.get("chat_id")),
            "raw": {
                "chat.platform": ch.get("platform"),
                "chat.channel": ch.get("channel"),
                "chat.source": ch.get("source"),
                "client.source": client.get("source"),
                "client.client_id": client.get("client_id"),
            },
            "normalized_platform": platform,
            "events": len(_extract_messages(ch)),
            "ts": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
        })
    print("[sync_recent] FIRST5_PREVIEW:", preview)

    to_process = sorted(chats, key=_extract_ts)
    if to_process:
        first_ts = datetime.fromtimestamp(_extract_ts(to_process[0]), tz=timezone.utc).isoformat()
        last_ts = datetime.fromtimestamp(_extract_ts(to_process[-1]), tz=timezone.utc).isoformat()
        print(f"[sync_recent] processing order ASC confirmed (oldest->newest), first_ts={first_ts}, last_ts={last_ts}")

    created = 0
    updated = 0
    ids: List[str] = []

    for chat in to_process:
        try:
            res = await ensure_case_from_chat(chat)
            if res.get("ok"):
                ids.append(res.get("case_name") or "")
                if res.get("created"):
                    created += 1
                elif res.get("skipped"):
                    pass
                else:
                    updated += 1
            else:
                print(f"[sync_recent] ensure failed chat_id={chat.get('_id') or chat.get('id') or chat.get('chat_id')} reason={res.get('reason')}")
        except Exception as exc:
            print(f"[sync_recent] ensure raised chat_id={chat.get('_id') or chat.get('id') or chat.get('chat_id')} err={exc}")

    return {"ok": True, "scanned": len(chats), "created": created, "updated": updated, "ids": ids}