# frappe_gui/apps/dantist_app/dantist_app/api/engagement/handlers.py
# -*- coding: utf-8 -*-
import json
import logging
from typing import Any, Dict, List

import frappe
import requests
from frappe.client import get_list as frappe_get_list
from frappe.client import get as frappe_get
from frappe.desk.reportview import get as rv_get
from frappe.desk.reportview import get_count as rv_get_count

logger = frappe.logger("dantist", allow_site=True)

ENGAGEMENT_DOCTYPE = "Engagement Case"
BASE_PATH = "/integrations/frappe"

# ---------- COMMON ----------
def base_url() -> str:
    url = frappe.conf.get("dantist_base_url") or ""
    if not url:
        frappe.throw("dantist_base_url not configured", exc=frappe.ValidationError)
    return url.rstrip("/")

def should_skip_sync() -> bool:
    try:
        hdr = (frappe.get_request_header("X-AIHub-No-Sync") or "").strip()
    except Exception:
        hdr = ""
    if hdr == "1":
        return True
    val = str((frappe.form_dict or {}).get("no_sync", "")).strip().lower()
    return val in {"1", "true", "yes"}

def need_sync(kind: str, seconds: int) -> bool:
    key = f"aihub_sync_cd:{kind}"
    cache = frappe.cache()
    if cache.get_value(key):
        return False
    cache.set_value(key, "1", expires_in_sec=seconds)
    return True

def _coerce_list(maybe_json):
    if isinstance(maybe_json, str):
        try:
            return json.loads(maybe_json)
        except Exception:
            return [maybe_json]
    return maybe_json

def _clean_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    for k in ["cmd", "method", "__ec_internal", "__ec_board_flag"]:
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
    for k in list(kwargs.keys()):
        if isinstance(k, str) and k.startswith("__ec_"):
            kwargs.pop(k, None)
    return kwargs

def _maybe_presync(tag: str, doctype: str) -> None:
    if doctype != ENGAGEMENT_DOCTYPE:
        return
    if should_skip_sync():
        return
    if need_sync(f"{tag}:recent", 5):
        print("-"*100, flush=True)
        print(f"[engagement::{tag}] pre-sync recent (cooldown 5s)", flush=True)
        res = sync_recent_upstream(minutes=5)
        print(f"[engagement::{tag}] pre-sync result={res}", flush=True)
        print("-"*100, flush=True)

# ---------- UPSTREAM SYNC ----------
def sync_recent_upstream(minutes: int = 5) -> Dict[str, Any]:
    url = f"{base_url()}{BASE_PATH}/engagement/sync_recent"
    try:
        r = requests.post(url, json={"minutes": int(minutes)}, timeout=30)
        data = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
        print(f"[frappe.engagement.sync_recent_upstream] status={r.status_code} data={data}", flush=True)
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
        data = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
        print(f"[frappe.engagement.sync_by_chat_id_upstream] status={r.status_code} data={data}", flush=True)
        if r.status_code != 200:
            return {"ok": False, "status": r.status_code}
        return data or {"ok": True}
    except Exception as e:
        logger.exception("sync_by_chat_id_upstream failed")
        return {"ok": False, "error": str(e)}

# ---------- PROXIES: client.get_list / client.get ----------
@frappe.whitelist()
def get_list(doctype: str, **kwargs):
    print("[engagement.get_list] ENTER", flush=True)
    if doctype == ENGAGEMENT_DOCTYPE:
        _maybe_presync("get_list", doctype)
    kw = _clean_kwargs(dict(kwargs))
    out = frappe_get_list(doctype=doctype, **kw)
    print(f"[engagement.get_list] EXIT len={len(out) if isinstance(out, list) else 'n/a'}", flush=True)
    return out

@frappe.whitelist()
def get(doctype: str, name: str, **kwargs):
    print(f"[engagement.get] ENTER doctype={doctype} name={name}", flush=True)
    if doctype == ENGAGEMENT_DOCTYPE and not should_skip_sync():
        chat_id = (frappe.db.get_value(doctype, name, "mongo_chat_id") or "").strip()
        if chat_id:
            key = f"bychat:{chat_id}"
            if need_sync(key, 5):
                print(f"[engagement.get] pre-sync by chat_id={chat_id} (cooldown 5s)", flush=True)
                _ = sync_by_chat_id_upstream(chat_id)
        else:
            _maybe_presync("get_nochat", doctype)
    kw = _clean_kwargs(dict(kwargs))
    out = frappe_get(doctype=doctype, name=name, **kw)
    print("[engagement.get] EXIT", flush=True)
    return out

# ---------- NEW: PROXIES для ReportView ----------
@frappe.whitelist()
def reportview_get(**kwargs):
    """
    Обёртка для frappe.desk.reportview.get — именно её дёргает список (List View).
    Здесь форсим sync_recent перед выдачей списка для Engagement Case.
    """
    doctype = (kwargs.get("doctype") or "").strip()
    print(f"[engagement.reportview_get] ENTER doctype={doctype}", flush=True)
    if doctype == ENGAGEMENT_DOCTYPE:
        _maybe_presync("reportview_get", doctype)
    out = rv_get(**kwargs)
    print(f"[engagement.reportview_get] EXIT", flush=True)
    return out

@frappe.whitelist()
def reportview_get_count(**kwargs):
    """
    Обёртка для frappe.desk.reportview.get_count — чтобы счётчик тоже запускал пресинк.
    """
    doctype = (kwargs.get("doctype") or "").strip()
    print(f"[engagement.reportview_get_count] ENTER doctype={doctype}", flush=True)
    if doctype == ENGAGEMENT_DOCTYPE:
        _maybe_presync("reportview_get_count", doctype)
    out = rv_get_count(**kwargs)
    print(f"[engagement.reportview_get_count] EXIT count={out}", flush=True)
    return out

# ---------- HELPERS для виджета/предпросмотра/инжектора ----------
@frappe.whitelist()
def engagement_hidden_children() -> List[str]:
    names = frappe.get_all(
        "Engagement Link Item",
        filters={"hide_in_lists": 1},
        pluck="engagement",
        limit_page_length=100000,
        ignore_permissions=True,
    )
    return sorted({n for n in names if n})

@frappe.whitelist()
def engagement_allowed_for_board(flag_field: str) -> List[str]:
    if flag_field not in {"show_board_crm", "show_board_leads", "show_board_deals", "show_board_patients"}:
        return []
    return frappe.get_all(
        ENGAGEMENT_DOCTYPE,
        filters={flag_field: 1},
        pluck="name",
        limit_page_length=100000,
    )

@frappe.whitelist()
def engagement_board_counts(flag_field: str, status_field: str) -> Dict[str, object]:
    print("[engagement_board_counts] ENTER", flush=True)
    hidden = set(engagement_hidden_children())
    shown  = set(engagement_allowed_for_board(flag_field))
    visible = list(shown - hidden)
    out = {"__all": len(visible), "by_status": {}}
    if not visible:
        print("[engagement_board_counts] EXIT empty", flush=True)
        return out
    rows = frappe.get_all(
        ENGAGEMENT_DOCTYPE,
        filters=[["name", "in", visible]],
        fields=["name", status_field],
        limit_page_length=len(visible),
    )
    by = {}
    for r in rows:
        st = r.get(status_field) or ""
        by[st] = by.get(st, 0) + 1
    out["by_status"] = by
    print("[engagement_board_counts] EXIT ok", flush=True)
    return out

@frappe.whitelist()
def engagement_board_preview(flag_field: str, status_field: str, limit: int = 6) -> List[dict]:
    hidden = set(engagement_hidden_children())
    rows = frappe.get_all(
        ENGAGEMENT_DOCTYPE,
        filters={flag_field: 1},
        fields=[
            "name","title","display_name","avatar","channel_platform",
            "preferred_language","priority", status_field,
            "first_event_at","last_event_at","modified"
        ],
        order_by="ifnull(last_event_at, modified) desc, modified desc",
        limit_page_length=limit * 3,
    )
    out = []
    for r in rows:
        if r["name"] in hidden:
            continue
        out.append(r)
        if len(out) >= int(limit):
            break
    return out

@frappe.whitelist()
def parents_of_engagement(name: str) -> List[dict]:
    if not name:
        return []
    parent_names = frappe.get_all(
        "Engagement Link Item",
        filters={"engagement": name},
        pluck="parent",
        limit_page_length=100000,
        ignore_permissions=True,
    )
    parent_names = sorted({p for p in parent_names if p})
    if not parent_names:
        return []
    fields = [
        "name","title","display_name","avatar","channel_platform","priority",
        "status_crm_board","status_leads","status_deals","status_patients",
        "show_board_crm","show_board_leads","show_board_deals","show_board_patients",
        "first_event_at","last_event_at"
    ]
    return frappe.get_all(
        ENGAGEMENT_DOCTYPE,
        filters=[["name","in", parent_names]],
        fields=fields,
        limit_page_length=len(parent_names),
    )