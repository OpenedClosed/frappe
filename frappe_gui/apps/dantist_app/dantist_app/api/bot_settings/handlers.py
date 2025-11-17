import json
import logging
from typing import Any, Dict, List

import frappe
import requests

logger = logging.getLogger(__name__)

BASE_PATH = "/integrations/frappe"


def get_base_url_internal() -> str | None:
    """Получить базовый URL бэкенда из site_config."""
    base_url = frappe.conf.get("dantist_base_url")
    if not base_url:
        return None
    return base_url.rstrip("/")


def extract_multiselect_values(child_table) -> List[str]:
    """Вытащить значения из таблиц-мультиселектов как список строк."""
    values: List[str] = []
    for row in child_table or []:
        for key in ("value", "code", "key", "name"):
            try:
                val = getattr(row, key, None)
            except Exception:
                val = None
            if val:
                values.append(str(val).strip())
                break
    return values


def parse_json_field(raw: str | None) -> Dict[str, str]:
    """Безопасно распарсить JSON-строки (greeting / error_message / и т.п.)."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def serialize_bot_settings_internal(doc) -> Dict[str, Any]:
    """Собрать payload настроек бота для бэкенда."""
    project_name = (doc.project_name or "").strip()
    app_name = (getattr(doc, "app_name", None) or project_name).strip()

    payload: Dict[str, Any] = {
        "project_name": project_name,
        "employee_name": (doc.employee_name or "").strip(),
        "mention_name": bool(getattr(doc, "mention_name", 0)),
        "avatar_url": (doc.avatar or "").strip() or None,
        "bot_color": (doc.bot_color or "").strip(),
        "communication_tone": (doc.communication_tone or "").strip(),
        "personality_traits": (doc.personality_traits or "").strip(),
        "additional_instructions": (getattr(doc, "additional_instructions", "") or ""),
        "role": (getattr(doc, "role", "") or "").strip(),
        "target_action": extract_multiselect_values(getattr(doc, "target_action", [])),
        "core_principles": (getattr(doc, "core_principles", "") or ""),
        "special_instructions": extract_multiselect_values(getattr(doc, "special_instructions", [])),
        "forbidden_topics": extract_multiselect_values(getattr(doc, "forbidden_topics", [])),
        "greeting": parse_json_field(getattr(doc, "greeting", None)),
        "error_message": parse_json_field(getattr(doc, "error_message", None)),
        "farewell_message": parse_json_field(getattr(doc, "farewell_message", None)),
        "fallback_ai_error_message": parse_json_field(getattr(doc, "fallback_ai_error_message", None)),
        "app_name": app_name,
        "ai_model": (doc.ai_model or "").strip(),
        "created_at": str(getattr(doc, "created_at", "") or "") or None,
        "frappe_doctype": doc.doctype,
        "frappe_name": doc.name,
        "frappe_modified": str(getattr(doc, "modified", "") or "") or None,
        "is_active": bool(getattr(doc, "is_active", 0)),
    }
    return payload


def sync_bot_settings_to_backend_internal(doc) -> None:
    """Отправить актуальные настройки бота в backend (Mongo)."""
    base_url = get_base_url_internal()
    if not base_url:
        return

    try:
        payload = serialize_bot_settings_internal(doc)
    except Exception:
        logger.exception("Failed to serialize Bot Settings")
        return

    try:
        r = requests.post(
            f"{base_url}{BASE_PATH}/bot_settings/sync",
            json=payload,
            timeout=8,
        )
    except Exception:
        logger.exception("Failed to sync Bot Settings to backend")
        return

    if r.status_code != 200:
        logger.warning("Bot Settings sync failed: %s %s", r.status_code, r.text)


def deactivate_other_bot_settings(doc) -> None:
    """Снять флаг активности у всех остальных Bot Settings в Frappe."""
    try:
        if not bool(getattr(doc, "is_active", 0)):
            return

        if getattr(frappe.local, "bot_settings_bulk_update", None):
            return

        frappe.local.bot_settings_bulk_update = True
        try:
            others = frappe.get_all(
                "Bot Settings",
                filters={"name": ["!=", doc.name]},
                pluck="name",
                limit_page_length=100000,
            )
            for name in others or []:
                frappe.db.set_value(
                    "Bot Settings",
                    name,
                    "is_active",
                    0,
                    update_modified=False,
                )
        finally:
            frappe.local.bot_settings_bulk_update = False
    except Exception:
        logger.exception("Failed to deactivate other Bot Settings")


@frappe.whitelist()
def on_bot_settings_changed(doc, method=None):
    """Хук: при создании/обновлении Bot Settings пушим в Mongo через backend."""
    try:
        deactivate_other_bot_settings(doc)
        sync_bot_settings_to_backend_internal(doc)
    except Exception:
        logger.exception("on_bot_settings_changed failed")