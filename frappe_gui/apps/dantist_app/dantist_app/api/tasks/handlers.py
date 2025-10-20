# apps/dantist_app/dantist_app/api/tasks/handlers.py
from __future__ import annotations
import json
from typing import Any, Iterable, List, Optional
from datetime import date, timedelta

import frappe
from frappe.utils import nowdate, get_datetime, cint

VALID_PRIORITIES = {"High", "Medium", "Low"}
FALLBACK_ROLES = ["System Manager", "AIHub Super Admin", "AIHub Admin", "AIHub Demo"]  # не используем сейчас

def _coerce_values(values: Any) -> frappe._dict:
    if isinstance(values, str):
        try:
            values = frappe.parse_json(values)
        except Exception:
            try:
                values = json.loads(values)
            except Exception:
                values = {}
    return frappe._dict(values or {})

def _priority_or_none(v: frappe._dict) -> Optional[str]:
    p = (v.get("priority") or "").strip()
    return p if p in VALID_PRIORITIES else None

def _assigned_users_of_case(case_name: str) -> List[str]:
    _assign = frappe.db.get_value("Engagement Case", case_name, "_assign")
    try:
        arr = frappe.parse_json(_assign) if _assign else []
        return [u for u in arr if isinstance(u, str)]
    except Exception:
        return []

def _actor_user(doc) -> str:
    s = (frappe.session.user or "").strip()
    if s and s.lower() not in ("administrator", "guest"):
        return s
    m = (getattr(doc, "modified_by", None) or "").strip()
    if m and m.lower() not in ("administrator", "guest"):
        return m
    o = (getattr(doc, "owner", None) or "").strip()
    return o or "Administrator"

def _notify_user(user: str, title: str, message: str, ref_type: str, ref_name: str):
    try:
        frappe.get_doc({
            "doctype": "Notification Log",
            "type": "Alert",
            "for_user": user,
            "subject": title,
            "email_content": message,
            "document_type": ref_type,
            "document_name": ref_name,
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(f"Notification Log failed for {user}", "to-do notify")

def _mk_single_todo(desc: str, due_dt: Optional[str], allocated_to: Optional[str],
                    ref_type: str, ref_name: str, priority: Optional[str], source: str) -> str:
    date_val = get_datetime(due_dt).date() if due_dt else nowdate()
    data = {
        "doctype": "ToDo",
        "description": desc or "Task",
        "date": date_val,
        "allocated_to": allocated_to,
        "status": "Open",
        "reference_type": ref_type,
        "reference_name": ref_name,
        "assigned_by": frappe.session.user if source == "manual" else _actor_user(frappe.get_doc(ref_type, ref_name)),
    }
    if priority:
        data["priority"] = priority
    doc = frappe.get_doc(data)
    doc.insert(ignore_permissions=True)
    if allocated_to:
        _notify_user(
            allocated_to,
            title=f"New task for {ref_type} {ref_name}",
            message=data["description"],
            ref_type=ref_type, ref_name=ref_name
        )
    return doc.name

def _mk_todos_for_users(desc: str, due: Optional[str], users: Iterable[str],
                        ref_type: str, ref_name: str, priority: Optional[str], source: str) -> List[str]:
    ids = []
    seen = set()
    for u in users or []:
        u = (u or "").strip()
        if not u or u.lower() in ("administrator", "guest") or u in seen:
            continue
        seen.add(u)
        ids.append(_mk_single_todo(desc, due, u, ref_type, ref_name, priority, source))
    if not ids:
        ids.append(_mk_single_todo(desc, due, None, ref_type, ref_name, priority, source))
    return ids

@frappe.whitelist()
def ec_tasks_for_case(name: str, status: Optional[str] = None,
                      limit_start: int = 0, limit_page_length: int = 20):
    filters = {"reference_type": "Engagement Case", "reference_name": name}
    if status and status in ("Open", "Closed", "Cancelled"):
        filters["status"] = status

    rows = frappe.get_all(
        "ToDo",
        filters=filters,
        fields=["name", "description", "status", "date", "allocated_to", "assigned_by", "priority"],
        order_by="status asc, date asc, name asc",
        limit_start=cint(limit_start),
        limit_page_length=cint(limit_page_length)
    )
    total = frappe.db.count("ToDo", filters=filters)
    return {"rows": rows, "total": total}

@frappe.whitelist()
def create_task_for_case(name: str, values: Any, source: str = "manual"):
    """
    values:
      - description (req)
      - due (Datetime)
      - priority (Low/Medium/High)
      - allocated_to (User)          # одиночный
      - assignees (list[str] | CSV)  # множественный
    """
    v = _coerce_values(values)
    desc = v.get("description") or v.get("subject")
    if not desc:
        frappe.throw("Description is required")

    prio = _priority_or_none(v)
    due  = v.get("due")

    # нормализуем assignees → list[str]
    assignees = []
    raw = v.get("assignees")
    if isinstance(raw, list):
        assignees = [str(x) for x in raw]
    elif isinstance(raw, str) and raw.strip():
        assignees = [s.strip() for s in raw.split(",") if s.strip()]

    if assignees:
        ids = _mk_todos_for_users(desc, due, assignees, "Engagement Case", name, prio, source)
        return {"names": ids}

    if v.get("allocated_to"):
        ids = _mk_todos_for_users(desc, due, [v.allocated_to], "Engagement Case", name, prio, source)
        return {"names": ids}

    if source == "manual":
        ids = _mk_todos_for_users(desc, due, [frappe.session.user], "Engagement Case", name, prio, source)
        return {"names": ids}

    doc = frappe.get_doc("Engagement Case", name)
    users = [_actor_user(doc)] + _assigned_users_of_case(name)
    ids = _mk_todos_for_users(desc, due, users, "Engagement Case", name, prio, source)
    return {"names": ids}

@frappe.whitelist()
def update_task_status(name: str, status: str):
    if status not in ("Closed", "Cancelled", "Open"):
        frappe.throw("Invalid status")
    doc = frappe.get_doc("ToDo", name)
    doc.status = status
    doc.save(ignore_permissions=True)
    return {"ok": True}

# ----------- AUTOTASKS (before_save) -----------
def maybe_autotasks_on_status_change(doc, method=None):
    prev = getattr(doc, "_doc_before_save", None) or doc.get_doc_before_save()
    if not prev:
        return

    if prev.status_deals != doc.status_deals and doc.status_deals == "Appointment Scheduled":
        due = date.today() + timedelta(days=1)
        create_task_for_case(
            name=doc.name,
            values={"description": "Next-Day Feedback call", "priority": "Medium", "due": f"{due} 10:00:00"},
            source="auto"
        )

    if prev.status_patients != doc.status_patients and doc.status_patients == "Stage Checked":
        due = date.today() + timedelta(days=3 * 30)
        create_task_for_case(
            name=doc.name,
            values={"description": "Schedule control X-ray", "priority": "High", "due": f"{due} 10:00:00"},
            source="auto"
        )

    if prev.status_deals != doc.status_deals and doc.status_deals == "Treatment Completed":
        due = date.today() + timedelta(days=5 * 30)
        create_task_for_case(
            name=doc.name,
            values={"description": "Recall: schedule prophylaxis", "priority": "Medium", "due": f"{due} 10:00:00"},
            source="auto"
        )