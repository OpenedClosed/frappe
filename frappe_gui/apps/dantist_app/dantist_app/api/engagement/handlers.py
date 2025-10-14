import json
import logging
from typing import Any, Dict

import frappe
import requests
from frappe.client import get_list as frappe_get_list
from frappe.client import get as frappe_get

logger = logging.getLogger(__name__)

ENGAGEMENT_DOCTYPE = "Engagement Case"
BASE_PATH = "/integrations/frappe"


def base_url() -> str:
    url = frappe.conf.get("dantist_base_url") or ""
    if not url:
        frappe.throw("dantist_base_url not configured", exc=frappe.ValidationError)
    return url.rstrip("/")


def should_skip_sync() -> bool:
    """Если пришли из FastAPI — пропускаем предсинк, чтобы не было рекурсии."""
    try:
        hdr = (frappe.get_request_header("X-AIHub-No-Sync") or "").strip()
    except Exception:
        hdr = ""
    if hdr == "1":
        return True
    val = str((frappe.form_dict or {}).get("no_sync", "")).strip().lower()
    return val in {"1", "true", "yes"}


def need_sync(kind: str, seconds: int) -> bool:
    """Простой cooldown через Redis — не чаще, чем раз в seconds."""
    key = f"aihub_sync_cd:{kind}"
    cache = frappe.cache()
    if cache.get_value(key):
        return False
    cache.set_value(key, "1", expires_in_sec=seconds)
    return True


def sync_recent_upstream(minutes: int = 5) -> Dict[str, Any]:
    """Без limit → FastAPI трактует как «без лимита»."""
    url = f"{base_url()}{BASE_PATH}/engagement/sync_recent"
    payload = {"minutes": int(minutes)}
    try:
        r = requests.post(url, json=payload, timeout=30)
        try:
            data = r.json()
        except Exception:
            data = {}
        print(f"[frappe.engagement.get_list] upstream status={r.status_code} data={data}")
        if r.status_code != 200:
            return {"ok": False, "status": r.status_code}
        return data or {"ok": True}
    except Exception as e:
        logger.exception("sync_recent_upstream failed")
        return {"ok": False, "error": str(e)}


def sync_by_chat_id_upstream(chat_id: str) -> Dict[str, Any]:
    url = f"{base_url()}{BASE_PATH}/engagement/sync_by_chat_id"
    try:
        r = requests.post(url, json={"chat_id": chat_id}, timeout=30)
        try:
            data = r.json()
        except Exception:
            data = {}
        print(f"[frappe.engagement.get] upstream status={r.status_code} data={data}")
        if r.status_code != 200:
            return {"ok": False, "status": r.status_code}
        return data or {"ok": True}
    except Exception as e:
        logger.exception("sync_by_chat_id_upstream failed")
        return {"ok": False, "error": str(e)}


def _coerce_list(maybe_json):
    if isinstance(maybe_json, str):
        try:
            return json.loads(maybe_json)
        except Exception:
            return [maybe_json]
    return maybe_json


def _clean_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    # frappe.handler пушит служебные ключи — убираем
    for k in ["cmd", "method"]:
        kwargs.pop(k, None)
    if "fields" in kwargs:
        kwargs["fields"] = _coerce_list(kwargs["fields"])
    if isinstance(kwargs.get("filters"), str):
        try:
            kwargs["filters"] = json.loads(kwargs["filters"])
        except Exception:
            pass
    if isinstance(kwargs.get("or_filters"), str):
        try:
            kwargs["or_filters"] = json.loads(kwargs["or_filters"])
        except Exception:
            pass
    return kwargs


@frappe.whitelist()
def get_list(doctype: str, **kwargs):
    if doctype == ENGAGEMENT_DOCTYPE and not should_skip_sync():
        # лёгкий предсинк с антидребезгом — раз в 5 секунд
        if need_sync("recent", 5):
            print("[frappe.engagement.get_list] pre-sync recent (cooldown 5s, NO LIMIT)")
            _ = sync_recent_upstream(minutes=5)

    kw = _clean_kwargs(dict(kwargs))
    return frappe_get_list(doctype=doctype, **kw)


@frappe.whitelist()
def get(doctype: str, name: str, **kwargs):
    if doctype == ENGAGEMENT_DOCTYPE and not should_skip_sync():
        chat_id = (frappe.db.get_value(doctype, name, "mongo_chat_id") or "").strip()
        if chat_id:
            key = f"bychat:{chat_id}"
            if need_sync(key, 5):
                print(f"[frappe.engagement.get] pre-sync by chat_id={chat_id} (cooldown 5s)")
                _ = sync_by_chat_id_upstream(chat_id)
        else:
            if need_sync("recent_fallback", 5):
                print("[frappe.engagement.get] no chat_id — fallback recent (cooldown 5s)")
                _ = sync_recent_upstream(minutes=3)

    kw = _clean_kwargs(dict(kwargs))
    return frappe_get(doctype=doctype, name=name, **kw)