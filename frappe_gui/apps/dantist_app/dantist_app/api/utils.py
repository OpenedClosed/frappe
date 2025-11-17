# dantist_app/api/utils.py

from __future__ import annotations

import json
from typing import List, Sequence

import frappe


def _to_names_list(names) -> List[str]:
    """Привести вход в список имён."""
    if names is None:
        return []
    if isinstance(names, str):
        # может прийти JSON-строка
        try:
            parsed = frappe.parse_json(names)
            if isinstance(parsed, (list, tuple)):
                names = parsed
            else:
                names = [str(parsed)]
        except Exception:
            names = [names]
    if isinstance(names, (list, tuple, set)):
        return [str(x) for x in names if x]
    return [str(names)]


def cascade_delete_one(doctype: str, name: str) -> None:
    """Удалить документ и связанные записи (жёсткий каскад)."""
    # Спец-кейс: Engagement Case → Call.ticket
    if doctype == "Engagement Case":
        call_names = frappe.get_all(
            "Call",
            filters={"ticket": name},
            pluck="name",
        )
        for call_name in call_names:
            # Жёстко удаляем звонки, игнорируя ссылки
            frappe.delete_doc(
                "Call",
                call_name,
                force=1,
                ignore_permissions=True,
            )

    # Базовый жёсткий delete для самого документа
    frappe.delete_doc(
        doctype,
        name,
        force=1,               # игнорировать ссылки
        ignore_permissions=True,
    )


@frappe.whitelist()
def cascade_delete_bulk(doctype: str, names=None):
    """Каскадное удаление списка документов.

    Вызывается из JS:
      dantist_app.api.utils.cascade_delete_bulk(doctype, names)
    """
    if not doctype:
        frappe.throw("Missing doctype for cascade_delete_bulk")

    names_list = _to_names_list(names)
    if not names_list:
        return {"ok": False, "deleted": [], "errors": ["No names provided"]}

    deleted: List[str] = []
    errors: List[dict] = []

    for name in names_list:
        try:
            cascade_delete_one(doctype, name)
            deleted.append(name)
        except Exception as e:
            frappe.log_error(
                title="Cascade delete failed",
                message=f"{doctype} {name}: {e}",
            )
            errors.append({"name": name, "error": str(e)})

    frappe.db.commit()

    return {
        "ok": True,
        "deleted": deleted,
        "errors": errors,
    }