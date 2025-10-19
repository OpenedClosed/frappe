# -*- coding: utf-8 -*-
import json
import logging
from typing import Any, Dict, List

import frappe
import requests
from frappe.client import get_list as frappe_get_list
from frappe.client import get as frappe_get

logger = logging.getLogger(__name__)

ENGAGEMENT_DOCTYPE = "Engagement Case"
BASE_PATH = "/integrations/frappe"

# ====================== COMMON ======================
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
    # Убираем служебные ключи, чтобы не ломать core RPC
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
    # Страхуемся от любых наших «служебных» ключей с префиксом __ec_
    for k in list(kwargs.keys()):
        if isinstance(k, str) and k.startswith("__ec_"):
            kwargs.pop(k, None)
    return kwargs


# ====================== UPSTREAM SYNC ======================
def sync_recent_upstream(minutes: int = 5) -> Dict[str, Any]:
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


# ====================== PROXIES: client.get_list / client.get ======================
@frappe.whitelist()
def get_list(doctype: str, **kwargs):
    if doctype == ENGAGEMENT_DOCTYPE and not should_skip_sync():
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


# ====================== HELPERS (для Kanban метрик/превью) ======================
@frappe.whitelist()
def engagement_board_counts(flag_field: str, status_field: str) -> Dict[str, object]:
    hidden = set(frappe.get_all(
        "Engagement Link Item",
        filters={"hide_in_lists": 1},
        pluck="engagement",
        limit_page_length=100000,
        ignore_permissions=True,
    ))
    shown_names = set(frappe.get_all(
        ENGAGEMENT_DOCTYPE,
        filters={flag_field: 1},
        pluck="name",
        limit_page_length=100000,
    ))
    visible = list(shown_names - hidden)

    out = {"__all": len(visible), "by_status": {}}
    if not visible:
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
    return out


@frappe.whitelist()
def engagement_board_preview(flag_field: str, status_field: str, limit: int = 6) -> List[dict]:
    hidden = set(frappe.get_all(
        "Engagement Link Item",
        filters={"hide_in_lists": 1},
        pluck="engagement",
        limit_page_length=100000,
        ignore_permissions=True,
    ))

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

    rows = frappe.get_all(
        ENGAGEMENT_DOCTYPE,
        filters=[["name", "in", parent_names]],
        fields=[
            "name","title","display_name","avatar","channel_platform",
            "priority","status_crm_board","first_event_at","last_event_at"
        ],
        limit_page_length=len(parent_names),
    )
    return rows


# ====================== HELPERS ДЛЯ reportview_get ======================
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
    if flag_field not in {
        "show_board_crm", "show_board_leads", "show_board_deals", "show_board_patients"
    }:
        return []
    names = frappe.get_all(
        ENGAGEMENT_DOCTYPE,
        filters={flag_field: 1},
        pluck="name",
        limit_page_length=100000,
    )
    return names


# ====================== OVERRIDE: frappe.desk.reportview.get (Frappe 15) ======================
from frappe.desk.reportview import get as _core_reportview_get

# Разрешённые ключи, которые можно прокидывать в ядро
_RV_ALLOWED_KEYS = {
    "fields","filters","or_filters","order_by","group_by",
    "start","page_length","view","with_childnames","debug",
    "as_list","with_comment_count","parent","include_metadata",
    "join","distinct"
}

def _rv_sanitize(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    clean = {}
    for k, v in kwargs.items():
        if isinstance(k, str) and k.startswith("__ec_"):
            continue
        if k in _RV_ALLOWED_KEYS:
            clean[k] = v
    return clean


@frappe.whitelist()
def reportview_get(doctype: str, **kwargs):
    """
    Фильтруем ТОЛЬКО Kanban по Engagement Case.
    Клиент добавляет __ec_board_flag=<show_board_*> — по нему собираем allowlist/denylist.
    В ядро передаём только «белый список» аргументов.
    """
    flag_field = kwargs.pop("__ec_board_flag", None)

    # не наш случай — отдаём в ядро, НО с санитизацией (на всякий)
    if doctype != ENGAGEMENT_DOCTYPE or not flag_field:
        safe_kwargs = _rv_sanitize(kwargs)
        print(f"[EC rv.get passthrough] doctype={doctype} kwargs={list(safe_kwargs.keys())}")
        return _core_reportview_get(doctype=doctype, **safe_kwargs)

    # наша фильтрация
    hidden = set(engagement_hidden_children())
    allowed = set(engagement_allowed_for_board(flag_field))

    filters = kwargs.get("filters")
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = []
    filters = filters or []

    # только карточки, отмеченные галкой текущей доски
    filters.append([ENGAGEMENT_DOCTYPE, "name", "in", list(allowed) if allowed else []])
    # исключаем «дочерние, скрытые»
    if hidden:
        filters.append([ENGAGEMENT_DOCTYPE, "name", "not in", list(hidden)])

    kwargs["filters"] = json.dumps(filters)

    safe_kwargs = _rv_sanitize(kwargs)
    print(f"[EC rv.get] board_flag={flag_field} filters_applied={len(filters)} pass_keys={list(safe_kwargs.keys())}")
    return _core_reportview_get(doctype=doctype, **safe_kwargs)

# ====================== OVERRIDE: frappe.desk.reportview.get (Frappe 15) ======================
from frappe.desk.reportview import get as _core_reportview_get

_RV_ALLOWED_KEYS = {
    "fields","filters","or_filters","order_by","group_by",
    "start","page_length","view","with_childnames","debug",
    "as_list","with_comment_count","parent","include_metadata",
    "join","distinct"
}

def _rv_sanitize(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    clean = {}
    for k, v in kwargs.items():
        if isinstance(k, str) and k.startswith("__ec_"):
            continue
        if k in _RV_ALLOWED_KEYS:
            clean[k] = v
    return clean

@frappe.whitelist()
def reportview_get(doctype: str, **kwargs):
    """
    Фильтруем ТОЛЬКО Kanban по Engagement Case.
    Клиент добавляет __ec_board_flag=<show_board_*> — по нему собираем allowlist/denylist.
    В ядро передаём только «белый список» аргументов, и ОБЯЗАТЕЛЬНО чистим frappe.form_dict.
    """
    flag_field = kwargs.pop("__ec_board_flag", None)

    # соберём фильтры, если это наш кейс
    if doctype == ENGAGEMENT_DOCTYPE and flag_field:
        hidden = set(engagement_hidden_children())
        allowed = set(engagement_allowed_for_board(flag_field))

        filters = kwargs.get("filters")
        if isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except Exception:
                filters = []
        filters = filters or []

        # 1) только отмеченные для текущей доски
        filters.append([ENGAGEMENT_DOCTYPE, "name", "in", list(allowed) if allowed else []])
        # 2) исключаем «дочерние, скрытые»
        if hidden:
            filters.append([ENGAGEMENT_DOCTYPE, "name", "not in", list(hidden)])

        kwargs["filters"] = json.dumps(filters)
        print(f"[EC rv.get] board_flag={flag_field} filters_applied={len(filters)}")
    else:
        print(f"[EC rv.get passthrough] doctype={doctype} (not our case)")

    # --- КРИТИЧЕСКОЕ: убрать служебный ключ из frappe.form_dict, чтобы НЕ утёк в DatabaseQuery.execute ---
    # (ядро может считывать параметры прямо из form_dict, игнорируя наши очищенные kwargs)
    fd = getattr(frappe, "form_dict", None)
    had_flag_in_fd = False
    saved_flag_value = None
    try:
        if isinstance(fd, dict) and "__ec_board_flag" in fd:
            had_flag_in_fd = True
            saved_flag_value = fd.get("__ec_board_flag")
            fd.pop("__ec_board_flag", None)

        safe_kwargs = _rv_sanitize(kwargs)
        return _core_reportview_get(doctype=doctype, **safe_kwargs)

    finally:
        # аккуратно восстановим, чтобы ничего другого в запросе не сломать
        if had_flag_in_fd and isinstance(fd, dict):
            fd["__ec_board_flag"] = saved_flag_value

@frappe.whitelist()
def get(doctype: str, name: str, **kwargs):
    # 1) Обычный пред-синк для Engagement Case (ваш код — как был)
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
    doc = frappe_get(doctype=doctype, name=name, **kw)

    # 2) Доп. обработка ТОЛЬКО когда это Kanban Board по Engagement Case:
    if doctype == "Kanban Board":
        try:
            ref_dt = (doc.get("reference_doctype") or "").strip()
            board_name = (doc.get("kanban_board_name") or "").strip()
            if ref_dt == ENGAGEMENT_DOCTYPE and board_name:
                # определяем нужный флаг доски
                BOARD_FLAGS = {
                    "CRM Board":                  "show_board_crm",
                    "Leads – Contact Center":     "show_board_leads",
                    "Deals – Contact Center":     "show_board_deals",
                    "Patients – Care Department": "show_board_patients",
                }
                flag_field = BOARD_FLAGS.get(board_name)
                if flag_field:
                    # наборы для фильтрации
                    hidden = set(frappe.get_all(
                        "Engagement Link Item",
                        filters={"hide_in_lists": 1},
                        pluck="engagement",
                        limit_page_length=100000,
                        ignore_permissions=True,
                    ))
                    allowed = set(frappe.get_all(
                        ENGAGEMENT_DOCTYPE,
                        filters={flag_field: 1},
                        pluck="name",
                        limit_page_length=100000,
                    ))

                    # подчистим order в каждой колонке
                    cols = doc.get("columns") or []
                    changed = 0
                    for col in cols:
                        order_raw = col.get("order") or "[]"
                        try:
                            names = json.loads(order_raw) if isinstance(order_raw, str) else (order_raw or [])
                        except Exception:
                            names = []
                        if not isinstance(names, list):
                            names = []

                        # фильтр: только allowed и не hidden
                        filtered = [n for n in names if n in allowed and n not in hidden]

                        # если что-то поменялось — записываем обратно JSON-ом
                        if filtered != names:
                            col["order"] = json.dumps(filtered)
                            changed += 1

                    if changed:
                        print(f"[EC Kanban get] board={board_name} columns_order_pruned={changed}")
        except Exception as e:
            # не ломаем выдачу борды, просто логируем
            logger.exception("post-process Kanban Board failed")

    return doc

# ====================== OVERRIDE: frappe.desk.reportview.get (Frappe 15) ======================
from frappe.desk.reportview import get as _core_reportview_get

_RV_ALLOWED_KEYS = {
    "fields","filters","or_filters","order_by","group_by",
    "start","page_length","view","with_childnames","debug",
    "as_list","with_comment_count","parent","include_metadata",
    "join","distinct"
}

def _rv_sanitize(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    clean = {}
    for k, v in kwargs.items():
        if isinstance(k, str) and k.startswith("__ec_"):
            continue
        if k in _RV_ALLOWED_KEYS:
            clean[k] = v
    return clean

@frappe.whitelist()
def reportview_get(doctype: str, **kwargs):
    """
    Сужаем выдачу Kanban по Engagement Case к allowlist (show_board_*) и исключаем скрытых "детей".
    Критично: передавать filters как list, НЕ как JSON-строку.
    """
    flag_field = kwargs.pop("__ec_board_flag", None)
    is_ec_kanban = (doctype == ENGAGEMENT_DOCTYPE and bool(flag_field))

    if not is_ec_kanban:
        safe_kwargs = _rv_sanitize(kwargs)
        print(f"[EC rv.get passthrough] doctype={doctype} pass_keys={list(safe_kwargs.keys())}")
        return _core_reportview_get(doctype=doctype, **safe_kwargs)

    # --- наши наборы ---
    hidden = set(frappe.get_all(
        "Engagement Link Item",
        filters={"hide_in_lists": 1},
        pluck="engagement",
        limit_page_length=100000,
        ignore_permissions=True,
    ))
    allowed = set(frappe.get_all(
        ENGAGEMENT_DOCTYPE,
        filters={flag_field: 1},
        pluck="name",
        limit_page_length=100000,
    ))

    # возьмём исходные filters как list
    filters = kwargs.get("filters")
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = []
    if not isinstance(filters, list):
        filters = []

    # только карточки, отмеченные галкой текущей доски
    filters.append([ENGAGEMENT_DOCTYPE, "name", "in", list(allowed) if allowed else []])
    # исключаем «дочерние, скрытые»
    if hidden:
        filters.append([ENGAGEMENT_DOCTYPE, "name", "not in", list(hidden)])

    # ВАЖНО: передать list, НЕ json-строку
    kwargs["filters"] = filters

    # убрать служебный ключ из form_dict, чтобы не протёк ниже
    fd = getattr(frappe, "form_dict", None)
    had_flag_in_fd = False
    saved_flag_value = None
    try:
        if isinstance(fd, dict) and "__ec_board_flag" in fd:
            had_flag_in_fd = True
            saved_flag_value = fd.get("__ec_board_flag")
            fd.pop("__ec_board_flag", None)

        safe_kwargs = _rv_sanitize(kwargs)
        print(
            f"[EC rv.get] board_flag={flag_field} "
            f"allowed={len(allowed)} hidden={len(hidden)} "
            f"filters_sent={len(filters)} "
            f"sample_allowed={list(sorted(allowed))[:3]}"
        )
        return _core_reportview_get(doctype=doctype, **safe_kwargs)
    finally:
        if had_flag_in_fd and isinstance(fd, dict):
            fd["__ec_board_flag"] = saved_flag_value

# -*- coding: utf-8 -*-
import json
import logging
from typing import Any, Dict, List

import frappe
from frappe.client import get_list as frappe_get_list
from frappe.client import get as frappe_get
from frappe.desk.reportview import get as _core_reportview_get

logger = logging.getLogger(__name__)
ENGAGEMENT_DOCTYPE = "Engagement Case"

# ------------- утилиты -------------
def _coerce_list(maybe_json):
    if isinstance(maybe_json, str):
        try:
            return json.loads(maybe_json)
        except Exception:
            return [maybe_json]
    return maybe_json

def _rv_sanitize(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {
        "fields","filters","or_filters","order_by","group_by",
        "start","page_length","view","with_childnames","debug",
        "as_list","with_comment_count","parent","include_metadata",
        "join","distinct"
    }
    clean = {}
    for k, v in kwargs.items():
        if isinstance(k, str) and k.startswith("__ec_"):
            continue
        if k in allowed:
            clean[k] = v
    return clean

# ------------- вспомогательные выборки -------------
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
    if flag_field not in {
        "show_board_crm","show_board_leads","show_board_deals","show_board_patients"
    }:
        return []
    return frappe.get_all(
        ENGAGEMENT_DOCTYPE,
        filters={flag_field: 1},
        pluck="name",
        limit_page_length=100000,
    )

# ------------- ПЕРЕОПРЕДЕЛЕНИЕ reportview.get -------------
@frappe.whitelist()
def reportview_get(doctype: str, **kwargs):
    """
    Единая точка для Kanban. Если прилетел __ec_board_flag и doctype = Engagement Case —
    добавляем фильтры (allowlist + not-in hidden), чистим form_dict и проксируем в ядро.
    Для всех остальных случаев — прозрачный прокси в ядро с санитизацией аргументов.
    """
    flag_field = kwargs.pop("__ec_board_flag", None)

    # не наш случай → просто ядро
    if doctype != ENGAGEMENT_DOCTYPE or not flag_field:
        safe = _rv_sanitize(kwargs)
        print(f"[EC rv.get passthrough] doctype={doctype} keys={list(safe.keys())}")
        return _core_reportview_get(doctype=doctype, **safe)

    # наш случай → собираем фильтры
    hidden  = set(engagement_hidden_children())
    allowed = set(engagement_allowed_for_board(flag_field))

    filters = kwargs.get("filters")
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = []
    filters = filters or []

    # только отмеченные для текущей доски
    filters.append([ENGAGEMENT_DOCTYPE, "name", "in", list(allowed) if allowed else []])
    # исключаем «скрытые»
    if hidden:
        filters.append([ENGAGEMENT_DOCTYPE, "name", "not in", list(hidden)])

    # передаём в ядро СПИСКОМ (а не JSON-строкой), ядро это принимает
    kwargs["filters"] = filters

    # критично: убрать служебный ключ из form_dict, чтобы не утёк в DatabaseQuery
    fd = getattr(frappe, "form_dict", None)
    had_flag, saved_val = False, None
    try:
        if isinstance(fd, dict) and "__ec_board_flag" in fd:
            had_flag, saved_val = True, fd.get("__ec_board_flag")
            fd.pop("__ec_board_flag", None)

        safe = _rv_sanitize(kwargs)
        print(f"[EC rv.get] board_flag={flag_field} allowed={len(allowed)} hidden={len(hidden)} filters_sent={len(filters)}")
        return _core_reportview_get(doctype=doctype, **safe)
    finally:
        if had_flag and isinstance(fd, dict):
            fd["__ec_board_flag"] = saved_val