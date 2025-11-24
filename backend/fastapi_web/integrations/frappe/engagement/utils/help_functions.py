# backend/fastapi_web/integrations/frappe/engagement/utils/help_functions.py
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, DefaultDict
from collections import defaultdict

from bson import ObjectId
from db.mongo.db_init import mongo_db
from integrations.frappe.client import get_frappe_client, FrappeError
from chats.utils.help_functions import has_meaningful_client_messages, should_skip_message_for_ai

TIME_FIELDS = [
    "updated_at", "last_message_at", "last_event_at", "last_activity_at",
    "modified_at", "modifiedAt", "updatedAt", "ts",
    "created_at", "createdAt",
]

TARGET_CHAT_ID = "68f6b260070075ebeb464eb2"  # для таргетного дебага


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


def build_title_from_client_id(mongo_client_id: Optional[str], fallback_chat_id: str) -> str:
    """title = client_id (если есть), иначе chat_id"""
    return str(mongo_client_id or fallback_chat_id)


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
            print(f"[load_chat] found in collection={cname}", flush=True)
            return doc
        except Exception as exc:
            print(f"[load_chat] error coll={cname} chat_id={chat_id} err={exc}", flush=True)
    return None


def _stable_hash(payload: Dict[str, Any]) -> str:
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


def _union_participants(a: List[Dict[str, Any]], b: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def _key(p):
        try:
            u = (p.get("sender_info") or {}).get("user") or {}
            return (u.get("email") or "").strip().lower()
        except Exception:
            return ""
    seen = set()
    out: List[Dict[str, Any]] = []
    for arr in (a or []), (b or []):
        for p in (arr or []):
            k = _key(p)
            if not k:
                continue
            if k in seen:
                continue
            seen.add(k)
            out.append(p)
    return out


def _merge_chats_by_client_source(chats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Мердж дублей: ключ = (mongo_client_id, normalized_platform).
    Новый чат переопределяет поля старого. participants_display объединяем по email.
    created_at — самый ранний, updated/last_* — самый поздний, messages — у нового.
    """
    groups: DefaultDict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    def _client_id(c: Dict[str, Any]) -> str:
        cl = c.get("client") or {}
        return str(
            pick_first(
                (cl[0].get("client_id") if isinstance(cl, list) and cl else None),
                cl.get("client_id"),
                c.get("client_id"),
                cl.get("id") if isinstance(cl, dict) else None,
            ) or ""
        )

    for c in chats:
        key = (_client_id(c), normalize_platform(c))
        groups[key].append(c)

    merged: List[Dict[str, Any]] = []
    for key, arr in groups.items():
        if not arr:
            continue
        arr_sorted = sorted(arr, key=_extract_ts)  # старые → новые
        base = dict(arr_sorted[-1])  # новый чат — основа

        def _pick_earliest(*fields):
            vals = []
            for f in fields:
                if base.get(f):
                    vals.append(base.get(f))
                for old in arr_sorted[:-1]:
                    if old.get(f):
                        vals.append(old.get(f))
            if not vals:
                return None
            ts = []
            for v in vals:
                if isinstance(v, (int, float)):
                    ts.append(float(v))
                else:
                    try:
                        ts.append(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
                    except Exception:
                        pass
            if not ts:
                return vals[0]
            return min(ts)

        def _pick_latest(*fields):
            vals = []
            for f in fields:
                if base.get(f):
                    vals.append(base.get(f))
                for old in arr_sorted[:-1]:
                    if old.get(f):
                        vals.append(old.get(f))
            if not vals:
                return None
            ts = []
            raw = []
            for v in vals:
                raw.append(v)
                if isinstance(v, (int, float)):
                    ts.append(float(v))
                else:
                    try:
                        ts.append(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
                    except Exception:
                        ts.append(0.0)
            idx = ts.index(max(ts)) if ts else 0
            return raw[idx]

        earliest_created_ts = _pick_earliest("created_at", "createdAt")
        if earliest_created_ts:
            try:
                base["created_at"] = datetime.fromtimestamp(float(earliest_created_ts), tz=timezone.utc).isoformat()
            except Exception:
                pass

        base["updated_at"] = _pick_latest("updated_at", "updatedAt", "last_message_at", "modified_at", "modifiedAt") or base.get("updated_at")

        merged_participants = []
        for old in arr_sorted:
            merged_participants = _union_participants(merged_participants, (old.get("participants_display") or []))
        base["participants_display"] = merged_participants

        merged.append(base)

    return merged


# -------------------- participants fallback --------------------
async def _compute_participants_fallback(chat: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Если в документе чата нет participants_display, строим его:
    - sender_ids = { messages[].sender_id } ∪ { chat.client.client_id }
    - ищем master clients по client_id, затем user по user_id → берём email/role
    - формируем список участников, пригодный для Frappe-синка ассайни
    """
    try:
        msgs = _extract_messages(chat)
        sender_ids = {m.get("sender_id") for m in msgs if isinstance(m, dict) and m.get("sender_id")}
        # client может быть dict или list (как в твоём примере)
        cl = chat.get("client") or {}
        if isinstance(cl, list) and cl:
            extra_cid = cl[0].get("client_id")
        elif isinstance(cl, dict):
            extra_cid = cl.get("client_id")
        else:
            extra_cid = None
        if extra_cid:
            sender_ids.add(extra_cid)
        sender_ids.discard(None)

        if not sender_ids:
            return []

        # clients -> user_id
        client_docs = await mongo_db.clients.find({"client_id": {"$in": list(sender_ids)}}).to_list(None)
        by_client_id = {d.get("client_id"): d for d in client_docs if d and d.get("client_id")}
        user_ids = []
        for d in client_docs:
            uid = d.get("user_id")
            if uid and ObjectId.is_valid(uid):
                user_ids.append(ObjectId(uid))

        users = []
        if user_ids:
            users = await mongo_db.users.find({"_id": {"$in": user_ids}}).to_list(None)
        by_user_id = {str(u.get("_id")): u for u in users if u and u.get("_id")}

        participants: List[Dict[str, Any]] = []
        for cid in sender_ids:
            m = by_client_id.get(cid) or {}
            uid = m.get("user_id")
            udoc = by_user_id.get(uid or "")
            email = (udoc or {}).get("email")
            role  = ((udoc or {}).get("role") or "").lower()
            source = _to_plain_str((m.get("source") or "internal")).title()
            if not email:
                continue
            participants.append({
                "client_id": cid,
                "sender_info": {
                    "source": source,
                    "client_id": cid,
                    "user": {
                        "email": email,
                        "role": role or "consultant",
                    }
                }
            })
        return participants
    except Exception as e:
        print(f"[participants_fallback][ERR] {e}", flush=True)
        return []


# -------------------- main upsert (CHATS) --------------------
# -------------------- main upsert (CHATS) --------------------
async def ensure_case_from_chat(chat: Dict[str, Any]) -> Dict[str, Any]:
    client = get_frappe_client()

    chat_id = str(chat.get("_id") or chat.get("id") or chat.get("chat_id") or "").strip()
    if not chat_id:
        print("[ensure_case_from_chat] skip: chat has no id-like field", flush=True)
        return {"ok": False, "reason": "chat_has_no_id"}

    # Если в чате нет ни одного осмысленного клиентского сообщения — вообще не создаём кейс
    if not has_meaningful_client_messages(chat):
        return {"ok": False, "reason": "no_meaningful_client_messages"}

    platform = normalize_platform(chat)
    channel_type = normalize_channel_type(chat.get("type"))

    chat_client = None
    # client в твоих примерах приходит иногда массивом
    raw_client = chat.get("client")
    if isinstance(raw_client, list) and raw_client:
        chat_client = raw_client[0]
    elif isinstance(raw_client, dict):
        chat_client = raw_client
    else:
        chat_client = {}

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
        ((chat_client.get("metadata") or {}) or {}).get("sender_id") if isinstance(chat_client, dict) else None,
    )

    avatar = pick_first(
        chat.get("avatar"),
        chat_client.get("avatar_url") if isinstance(chat_client, dict) else None,
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

    title = build_title_from_client_id(mongo_client_id, chat_id)

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

    # participants: берём из чата или строим fallback
    participants = chat.get("participants_display")
    if not participants:
        participants = await _compute_participants_fallback(chat)

    # ---- state lookup (Mongo cache)
    state_col = get_collection("frappe_sync_state")
    case_name_from_state = None
    try:
        state = await state_col.find_one({"chat_id": chat_id}) if (state_col is not None) else None
        if state and state.get("hash") == payload_hash and state.get("case_name"):
            # даже при no_changes — пробуем синкануть ассайни с актуальными участниками
            try:
                fc = get_frappe_client()
                data = {
                    "case_name": state["case_name"],
                    "participants_json": json.dumps(participants or []),
                }
                print(f"[ASSIGNEES_SYNC_CALL] case={state['case_name']} chat={chat_id} parts={len(participants or [])}", flush=True)
                if chat_id == TARGET_CHAT_ID:
                    try:
                        print("*** TARGET CHAT PARTICIPANTS (FASTAPI) ***", json.dumps(participants or [], ensure_ascii=False, indent=2), flush=True)
                    except Exception:
                        pass
                await fc.request("call", "dantist_app.api.users_and_notifications.handlers.sync_case_assignees_from_chat", data)
            except Exception as e:
                print(f"[ensure_case_from_chat] assign sync failed (no_changes path) name={state.get('case_name')} err={e}", flush=True)
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
        print(f"[ensure_case_from_chat] state lookup failed err={exc}", flush=True)

    # ---- find/create case
    frappe_client = get_frappe_client()
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
            print(f"[ensure_case_from_chat] frappe.get_value error chat_id={chat_id} err={exc}", flush=True)
            return {"ok": False, "reason": "frappe_get_value_failed"}

    created = False
    if not case_name:
        try:
            saved = await frappe_client.request("insert", {
                "doc": {
                    "doctype": "Engagement Case",
                    "naming_series": "IE-.YYYY.-.#####",
                    "crm_status": "New",                 # базовый CRM статус
                    "show_board_crm": 1,                 # показать на CRM Board
                    "show_board_leads": 1,               # показать на доске Лидов
                    "status_leads": "Bot Active / New Inquiry",  # колонка на доске Лидов
                    **upstream_payload,
                }
            })
            case_name = saved.get("name") if isinstance(saved, dict) else None
            created = True
            print(f"[ensure_case_from_chat] created case name={case_name} chat_id={chat_id} platform={platform}", flush=True)
        except FrappeError as exc:
            print(f"[ensure_case_from_chat] frappe.insert error chat_id={chat_id} err={exc}", flush=True)
            return {"ok": False, "reason": "frappe_insert_failed"}

    # ---- update only changed fields (уважаем ручные правки)
    try:
        existing = await frappe_client.request("get", {"doctype": "Engagement Case", "name": case_name})
    except FrappeError as exc:
        print(f"[ensure_case_from_chat] frappe.get error name={case_name} err={exc}", flush=True)
        return {"ok": False, "reason": "frappe_get_failed", "case_name": case_name}

    if not isinstance(existing, dict):
        existing = {}

    def non_empty(v: Any) -> bool:
        return bool(str(v or "").strip())

    def is_default_avatar(val: Any) -> bool:
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
            cur = str(existing.get(k) or "")
            if cur.lstrip("/") != str(v or "").lstrip("/"):
                changes[k] = v
        else:
            if existing.get(k) != v:
                changes[k] = v

    if changes:
        try:
            existing.update(changes)
            _ = await frappe_client.request("save", {"doc": existing})
            print(f"[ensure_case_from_chat] saved case name={case_name} created={created} fields={list(changes.keys())}", flush=True)
        except FrappeError as exc:
            print(f"[ensure_case_from_chat] frappe.save error name={case_name} err={exc}", flush=True)
            return {"ok": False, "reason": "frappe_save_failed", "case_name": case_name, "changes": list(changes.keys())}

    # ---- sync assignees (идемпотентно, кеш на карточке в Frappe)
    try:
        data = {
            "case_name": case_name,
            "participants_json": json.dumps(participants or []),
        }
        print(f"[ASSIGNEES_SYNC_CALL] case={case_name} chat={chat_id} parts={len(participants or [])}", flush=True)
        if chat_id == TARGET_CHAT_ID:
            try:
                print("*** TARGET CHAT PARTICIPANTS (FASTAPI) ***", json.dumps(participants or [], ensure_ascii=False, indent=2), flush=True)
            except Exception:
                pass
        await frappe_client.request("call", "dantist_app.api.users_and_notifications.handlers.sync_case_assignees_from_chat", data)
    except Exception as exc:
        print(f"[ensure_case_from_chat] assign sync failed name={case_name} err={exc}", flush=True)

    # ---- update sync state
    try:
        state_col = get_collection("frappe_sync_state")
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
        print(f"[ensure_case_from_chat] state upsert failed err={exc}", flush=True)

    return {"ok": True, "case_name": case_name, "created": created, "updated_fields": list(changes.keys())}

# -------------------- public API (CHATS) --------------------
async def sync_one_by_chat_id(chat_id: str) -> Dict[str, Any]:
    print(f"[sync_one_by_chat_id] fetch chat chat_id={chat_id}", flush=True)
    chat = await load_chat(chat_id)
    if not chat:
        print(f"[sync_one_by_chat_id] not found chat_id={chat_id}", flush=True)
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
                "client.source": (client[0].get("source") if isinstance(client, list) and client else client.get("source")),
                "client.client_id": (client[0].get("client_id") if isinstance(client, list) and client else client.get("client_id")),
            },
            "normalized_platform": platform,
        },
        flush=True
    )

    res = await ensure_case_from_chat(chat)
    print(f"[sync_one_by_chat_id] ensured case result={res}", flush=True)
    return res


async def sync_recent(minutes: int, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Берём свежие чаты. Временно форсим limit=50.
    Обрабатываем от старых к новым; перед обработкой мерджим дубли по (client_id, platform).
    """
    # limit = 50
    dt_limit = datetime.now(tz=timezone.utc) - timedelta(minutes=int(minutes))
    ts_limit = dt_limit.timestamp()

    try:
        names = await mongo_db.list_collection_names()
        print(f"[sync_recent] collections={names}", flush=True)
    except Exception as exc:
        print(f"[sync_recent] list_collection_names failed err={exc}", flush=True)

    cname, col = find_chats_collection()
    print(f"[sync_recent] using collection={cname} since={dt_limit.isoformat()} limit={limit}", flush=True)

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
        print(f"[sync_recent] query failed err={exc}", flush=True)

    print(f"[sync_recent] fetched recent count={len(chats)}", flush=True)

    if not chats:
        try:
            fallback = col.find({}).sort(sort_keys).limit(int(limit))
            async for c in fallback:
                if "_id" in c:
                    c["_id"] = str(c["_id"])
                chats.append(c)
            print(f"[sync_recent] fallback count={len(chats)}", flush=True)
        except Exception as exc:
            print(f"[sync_recent] fallback failed err={exc}", flush=True)

    merged_chats = _merge_chats_by_client_source(chats)
    print(f"[sync_recent] merged groups: in={len(chats)} out={len(merged_chats)}", flush=True)

    preview = []
    for i, ch in enumerate(merged_chats[:5]):
        client = ch.get("client") or {}
        if isinstance(client, list) and client:
            c0 = client[0]
        else:
            c0 = client if isinstance(client, dict) else {}
        platform = normalize_platform(ch)
        ts = _extract_ts(ch)
        preview.append({
            "i": i,
            "chat_id": str(ch.get("_id") or ch.get("id") or ch.get("chat_id")),
            "raw": {
                "chat.platform": ch.get("platform"),
                "chat.channel": ch.get("channel"),
                "chat.source": ch.get("source"),
                "client.source": c0.get("source"),
                "client.client_id": c0.get("client_id"),
            },
            "normalized_platform": platform,
            "events": len(_extract_messages(ch)),
            "ts": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
        })
    print("[sync_recent] FIRST5_PREVIEW:", preview, flush=True)

    to_process = sorted(merged_chats, key=_extract_ts)
    if to_process:
        first_ts = datetime.fromtimestamp(_extract_ts(to_process[0]), tz=timezone.utc).isoformat()
        last_ts = datetime.fromtimestamp(_extract_ts(to_process[-1]), tz=timezone.utc).isoformat()
        print(f"[sync_recent] processing order ASC confirmed (oldest->newest), first_ts={first_ts}, last_ts={last_ts}", flush=True)

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
                print(f"[sync_recent] ensure failed chat_id={chat.get('_id') or chat.get('id') or chat.get('chat_id')} reason={res.get('reason')}", flush=True)
        except Exception as exc:
            print(f"[sync_recent] ensure raised chat_id={chat.get('_id') or chat.get('id') or chat.get('chat_id')} err={exc}", flush=True)

    return {"ok": True, "scanned": len(chats), "merged": len(merged_chats), "created": created, "updated": updated, "ids": ids}


# =====================================================================
#                           USERS → DEALS
# =====================================================================

def _users_collection():
    return get_collection("users")

async def _iter_recent_users(minutes: int, limit: Optional[int]) -> List[Dict[str, Any]]:
    """
    Берём пользователей с ролью client и (updated_at >= T) ИЛИ (created_at >= T).
    Если updated_at/created_at отсутствуют — не попадают в выборку (как и просил).
    """
    col = _users_collection()
    if col is None:
        print("[users-sync] no `users` collection", flush=True)
        return []

    dt_limit = datetime.now(tz=timezone.utc) - timedelta(minutes=int(minutes))
    flt = {
        "role": {"$in": ["client", "CLIENT", "Client"]},
        "is_active": {"$ne": False},
        # "$or": [
        #     {"updated_at": {"$gte": dt_limit}},
        #     {"created_at": {"$gte": dt_limit}},
        # ]
    }

    cursor = col.find(flt).sort([("updated_at", -1), ("created_at", -1), ("_id", -1)])
    if limit:
        cursor = cursor.limit(int(limit))

    out: List[Dict[str, Any]] = []
    async for u in cursor:
        if "_id" in u:
            u["_id"] = str(u["_id"])
        out.append(u)
    return out

# ======================================================================
#                         USERS → ENGAGEMENT (DEALS)
# ======================================================================

async def ensure_case_from_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Создаёт/обновляет карточку Engagement Case для пользователя с ролью 'client'.
    ВАЖНО: статусы досок выставляются ТОЛЬКО при создании. На апдейтах не трогаем.
    """
    role = str(user.get("role") or "").strip().lower()
    if role != "client":
        return {"ok": False, "reason": "not_client"}

    client = get_frappe_client()

    # идентификатор для связки
    user_id = str(user.get("_id") or user.get("id") or "").strip()
    if ObjectId.is_valid(user_id) and isinstance(user.get("_id"), ObjectId):
        user_id = str(user["_id"])
    if not user_id:
        return {"ok": False, "reason": "no_user_id"}

    email = (user.get("email") or "").strip().lower() or None
    display_name = (
        (user.get("full_name") or "").strip()
        or (user.get("username") or "").strip()
        or (email.split("@")[0] if email else None)
        or f"User {user_id}"
    )

    avatar = (user.get("avatar") or None)
    if isinstance(avatar, dict):
        avatar = avatar.get("url") or avatar.get("path") or None
    avatar = avatar or "/files/source_avatars/internal.png"

    created_at = user.get("created_at")
    updated_at = user.get("updated_at") or created_at

    # Поля, которые мы СИНКАЕМ ВСЕГДА (без статусов и show_* — чтобы не откатывать вручную изменённое)
    payload_base = {
        "title": display_name,
        "display_name": display_name,
        "email": email,
        "avatar": avatar,
        "channel_type": "Personal Account",
        "channel_platform": "Internal",
        "mongo_user_id": user_id,
        "first_event_at": to_frappe_dt(created_at),
        "last_event_at": to_frappe_dt(updated_at),
    }
    # Хеш тоже БЕЗ статусов/флагов — чтобы изменения статусов в Frappe не приводили к «обновлениям»
    payload_hash = _stable_hash(payload_base)

    # state cache по user_id
    state_col = mongo_db.get_collection("frappe_sync_state")
    cache_key = {"user_id": user_id}
    try:
        st = await state_col.find_one(cache_key)
        if st and st.get("hash") == payload_hash and st.get("case_name"):
            return {"ok": True, "case_name": st["case_name"], "created": False, "skipped": True, "reason": "no_changes"}
    except Exception:
        pass

    # поиск карточки по mongo_user_id
    case_name = None
    try:
        found = await client.request("get_value", {
            "doctype": "Engagement Case",
            "fieldname": "name",
            "filters": {"mongo_user_id": user_id},
        })
        case_name = found.get("name") if isinstance(found, dict) else None
    except FrappeError:
        pass

    created = False
    if not case_name:
        # При СОЗДАНИИ выставляем флаги/статусы на досках ОДИН РАЗ
        insert_doc = {
            "doctype": "Engagement Case",
            "naming_series": "IE-.YYYY.-.#####",
            **payload_base,
            # deals/CRM — первичная раскладка
            "show_board_deals": 1,
            "status_deals": "Appointment Scheduled",
            "show_board_crm": 1,
            # поддержим оба поля CRM
            "crm_status": "Scheduled",
            "status_crm_board": "Scheduled",
        }
        try:
            saved = await client.request("insert", {"doc": insert_doc})
            case_name = saved.get("name") if isinstance(saved, dict) else None
            created = True
            print(f"[ensure_case_from_user] created case={case_name} for user={user_id}", flush=True)
        except FrappeError as e:
            print(f"[ensure_case_from_user][ERR insert] user={user_id} err={e}", flush=True)
            return {"ok": False, "reason": "frappe_insert_failed"}

    # update only changed (НО: статусы и show_* НЕ ТРОГАЕМ)
    try:
        existing = await client.request("get", {"doctype": "Engagement Case", "name": case_name})
    except FrappeError as e:
        print(f"[ensure_case_from_user][ERR get] {case_name} {e}", flush=True)
        return {"ok": False, "reason": "frappe_get_failed", "case_name": case_name}

    locked_updates = dict(payload_base)  # тут уже нет статусных полей
    changes = {}
    for k, v in locked_updates.items():
        cur = existing.get(k)
        if k == "avatar":
            cur_norm = str(cur or "").lstrip("/")
            v_norm = str(v or "").lstrip("/")
            if cur_norm != v_norm:
                changes[k] = v
        else:
            if cur != v:
                changes[k] = v

    if changes:
        try:
            existing.update(changes)
            _ = await client.request("save", {"doc": existing})
            print(f"[ensure_case_from_user] updated {case_name} fields={list(changes.keys())}", flush=True)
        except FrappeError as e:
            print(f"[ensure_case_from_user][ERR save] {case_name} {e}", flush=True)
            return {"ok": False, "reason": "frappe_save_failed", "case_name": case_name, "changes": list(changes.keys())}

    # обновим кеш
    try:
        await state_col.update_one(
            cache_key,
            {"$set": {"case_name": case_name, "hash": payload_hash, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    except Exception:
        pass

    return {"ok": True, "case_name": case_name, "created": created, "updated_fields": list(changes.keys())}

async def sync_recent_users(minutes: Optional[int] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Users sync:
      - minutes == None → БЕЗ фильтра по времени (как просил).
      - minutes задан → фильтруем по created_at/updated_at >= now - minutes.
      - limit опционален.
    """
    col = mongo_db.get_collection("users")
    q: Dict[str, Any] = {"role": "client"}

    if minutes is not None:
        dt_limit = datetime.now(tz=timezone.utc) - timedelta(minutes=int(minutes))
        or_conds = [{"updated_at": {"$gte": dt_limit}}, {"created_at": {"$gte": dt_limit}}]
        q = {"$and": [q, {"$or": or_conds}]}

    cursor = col.find(q).sort([("updated_at", -1), ("created_at", -1), ("_id", -1)])
    if limit is not None:
        cursor = cursor.limit(int(limit))

    scanned = created = updated = 0
    ids: List[str] = []

    async for u in cursor:
        scanned += 1
        if "_id" in u and isinstance(u["_id"], ObjectId):
            u["_id"] = str(u["_id"])
        try:
            res = await ensure_case_from_user(u)
            if res.get("ok"):
                ids.append(res.get("case_name") or "")
                if res.get("created"):
                    created += 1
                elif res.get("skipped"):
                    pass
                else:
                    updated += 1
        except Exception as e:
            print(f"[sync_recent_users][ERR] id={u.get('_id')} {e}", flush=True)

    return {"ok": True, "scanned": scanned, "created": created, "updated": updated, "ids": ids}