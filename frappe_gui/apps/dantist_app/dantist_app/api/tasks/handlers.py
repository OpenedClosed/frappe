# apps/dantist_app/dantist_app/api/tasks/handlers.py
from __future__ import annotations
import json
from typing import Any, List, Optional, Tuple

import frappe
from frappe.utils import nowdate, get_datetime

LOGGER = frappe.logger("dantist.tasks", allow_site=True)
VALID_PRIORITIES = {"High", "Medium", "Low"}

def _todo_fieldname(base: str) -> str:
    meta = frappe.get_meta("ToDo")
    if meta and meta.get_field(base):
        return base
    custom = f"custom_{base}"
    return custom if (meta and meta.get_field(custom)) else base

F_DUE_DT   = _todo_fieldname("due_datetime")
F_SEND     = _todo_fieldname("send_reminder")
F_SENT_AT  = _todo_fieldname("reminder_sent_at")
F_ERR      = _todo_fieldname("reminder_error")

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

def _effective_user() -> Optional[str]:
    try:
        u = frappe.session.user
    except Exception:
        u = None
    return None if u in (None, "Guest") else u

def _norm_assignees(raw) -> List[str]:
    if not raw: return []
    if isinstance(raw, str):
        try: raw = frappe.parse_json(raw)
        except Exception: raw = [raw]
    if not isinstance(raw, list): raw = [raw]
    seen=set(); out=[]
    for u in raw:
        u=(u or "").strip()
        if not u or u=="Guest": continue
        if u not in seen: seen.add(u); out.append(u)
    return out

def _extract_due(values: frappe._dict) -> Tuple[Optional[str], Optional[str]]:
    raw = values.get("due_datetime") or values.get("due") or values.get(F_DUE_DT)
    if not raw: return None, nowdate()
    try: dt = get_datetime(raw)
    except Exception: return None, nowdate()
    return dt, dt.date().isoformat()

def _assign_users_to_doc(doctype: str, name: str, users: List[str]):
    for u in users:
        try:
            frappe.desk.form.assign_to.add({
                "assign_to": [u],
                "doctype": doctype,
                "name": name,
                "description": None,
                "notify": 0,
            })
            print(f"[ASSIGN] {doctype} {name} -> {u}", flush=True)
        except Exception as e:
            print(f"[ASSIGN][ERR] {doctype} {name} -> {u}: {e}", flush=True)

def _mk_todo_doc(v: frappe._dict, ref_type: str, ref_name: str, source: str = "manual"):
    print(f"[TODO][IN] ref={ref_type}/{ref_name} source={source} values={dict(v)}", flush=True)

    desc = v.get("description") or v.get("subject") or "Task"
    prio_in = (v.get("priority") or "").strip()
    prio = prio_in if prio_in in VALID_PRIORITIES else None
    due_dt, date_iso = _extract_due(v)

    send_raw = v.get("send_reminder")
    if send_raw is None: send_raw = v.get(F_SEND)
    send_on = 1 if str(send_raw).lower() in ("1","true","yes","on") else 0

    data = {
        "doctype": "ToDo",
        "description": desc,
        "date": date_iso,
        "status": "Open",
        "reference_type": ref_type,
        "reference_name": ref_name,
    }
    if prio: data["priority"] = prio
    if due_dt: data[F_DUE_DT] = due_dt
    data[F_SEND] = send_on

    eff = _effective_user()
    if eff: data["assigned_by"] = eff

    doc = frappe.get_doc(data)
    doc.insert(ignore_permissions=True)

    assignees = _norm_assignees(v.get("assignees")) or ([eff] if eff else [])
    if assignees: _assign_users_to_doc("ToDo", doc.name, assignees)

    print(f"[TODO][OK] created {doc.name} ({F_SEND}={send_on})", flush=True)
    LOGGER.info("ToDo created %s for %s/%s", doc.name, ref_type, ref_name)
    return doc

@frappe.whitelist()
def ec_tasks_for_case(name: str, status: Optional[str] = None, limit_start: int = 0, limit_page_length: int = 10):
    flt = {"reference_type": "Engagement Case", "reference_name": name}
    if status: flt["status"] = status

    fields = ["name","description","status","date","priority","allocated_to","assigned_by", F_DUE_DT, F_SEND, F_SENT_AT, F_ERR]
    total = frappe.db.count("ToDo", filters=flt)
    rows = frappe.get_all(
        "ToDo",
        filters=flt,
        fields=fields,
        order_by=f"status asc, COALESCE({F_DUE_DT}, date) asc, name asc",
        limit_start=int(limit_start or 0),
        limit_page_length=int(limit_page_length or 10),
    )

    out=[]
    for r in rows:
        d=dict(r)
        d["due_datetime"]     = d.pop(F_DUE_DT, None)
        d["send_reminder"]    = d.pop(F_SEND, None)
        d["reminder_sent_at"] = d.pop(F_SENT_AT, None)
        d["reminder_error"]   = d.pop(F_ERR, None)
        out.append(d)

    print(f"[EC_TASKS] fetch {name} status={status or 'All'} {limit_start}+{limit_page_length} -> {len(out)}/{total}", flush=True)
    return {"rows": out, "total": total}

@frappe.whitelist()
def create_task_for_case(name: str, values: Any, source: str = "manual"):
    v = _coerce_values(values)
    doc = _mk_todo_doc(v, "Engagement Case", name, source=source)
    return {"name": doc.name}

@frappe.whitelist()
def update_task_status(name: str, status: str):
    if status not in ("Closed", "Cancelled", "Open"):
        frappe.throw("Invalid status")
    doc = frappe.get_doc("ToDo", name)
    doc.status = status
    doc.save(ignore_permissions=True)
    print(f"[TODO][STATUS] {name} -> {status}", flush=True)
    return {"ok": True}