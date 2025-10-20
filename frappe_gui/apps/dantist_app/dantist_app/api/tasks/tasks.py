# dantist_app/api/tasks/tasks.py
from __future__ import annotations
from typing import List, Optional
import json
import frappe
from frappe.utils import now_datetime, nowdate, get_datetime, add_to_date


# ========= FIELDS DETECTION =========
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


# ========= HELPERS =========
def _get_assignees_for(name: str) -> List[str]:
    """Возвращает список назначенных пользователей для ToDo."""
    try:
        raw = frappe.db.get_value("ToDo", name, "_assign") or "[]"
        arr = json.loads(raw) if isinstance(raw, str) else (raw or [])
        users = [u for u in arr if u and u != "Guest"]
        if not users:
            alloc = frappe.db.get_value("ToDo", name, "allocated_to")
            if alloc and alloc != "Guest":
                users = [alloc]
        print(f"[ASSIGNEES] {name}: {users}", flush=True)
        return users
    except Exception as e:
        print(f"[ASSIGNEES][ERR] {name}: {e}", flush=True)
        return []


def _mk_notification(to_user: str, docname: str, title: str, body: str):
    """Создает уведомление (колокольчик в Desk)."""
    try:
        from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
        enqueue_create_notification(
            recipients=[to_user],
            doc=frappe._dict(doctype="ToDo", name=docname),
            subject=title,
            message=body,
            email=False,
            indicator="orange",
            type="Alert",
        )
        print(f"[NOTIFY] Sent to {to_user} for {docname}", flush=True)
    except Exception as e:
        print(f"[NOTIFY][ERR] {to_user} for {docname}: {e}", flush=True)


def _is_due(due_dt: Optional[str], date_only: Optional[str]) -> bool:
    now = now_datetime()
    if due_dt:
        try:
            return get_datetime(due_dt) <= now
        except Exception:
            return False
    if date_only:
        try:
            end_of_day = add_to_date(get_datetime(date_only), hours=23, minutes=59)
            return end_of_day <= now or nowdate() >= date_only
        except Exception:
            return nowdate() >= (date_only or "")
    return False


def _pick_candidates(limit: int = 200) -> List[dict]:
    fields = ["name", "description", "status", "date", F_DUE_DT, F_SEND, F_SENT_AT, F_ERR]
    rows = frappe.get_all(
        "ToDo",
        filters={"status": "Open", F_SEND: 1, F_SENT_AT: ["is", "not set"]},
        fields=fields,
        order_by=f"COALESCE({F_DUE_DT}, date) asc, name asc",
        limit_page_length=limit,
    )
    out = []
    for r in rows:
        d = dict(r)
        d["due_datetime"] = d.pop(F_DUE_DT, None)
        d["send_reminder"] = d.pop(F_SEND, None)
        d["reminder_sent_at"] = d.pop(F_SENT_AT, None)
        d["reminder_error"] = d.pop(F_ERR, None)
        if _is_due(d.get("due_datetime"), d.get("date")):
            out.append(d)
    print(f"[PICK] found {len(out)} due of {len(rows)} candidates", flush=True)
    return out


def _mark_sent(name: str):
    frappe.db.set_value("ToDo", name, {
        F_SENT_AT: now_datetime(),
        F_ERR: None,
    }, update_modified=False)
    print(f"[MARK] {name} marked sent", flush=True)


def _mark_error(name: str, msg: str):
    frappe.db.set_value("ToDo", name, {
        F_ERR: (msg or "")[:1000],
    }, update_modified=False)
    print(f"[MARK][ERR] {name}: {msg}", flush=True)


# ========= MAIN JOB =========
@frappe.whitelist()
def process_due_todos(batch_limit: int = 200):
    """Проверка всех задач ToDo: если срок наступил — шлём уведомления."""
    print("========== [CHECK] process_due_todos triggered ==========", flush=True)

    cands = _pick_candidates(limit=int(batch_limit or 200))
    if not cands:
        print("[CHECK] No due ToDos found", flush=True)
        return {"processed": 0}

    processed = 0
    for t in cands:
        name = t["name"]
        print(f"[TODO] Checking {name} | due={t.get('due_datetime')} | date={t.get('date')}", flush=True)
        try:
            users = _get_assignees_for(name)
            if not users:
                _mark_error(name, "No assignees")
                continue

            title = "Task Due"
            body = t.get("description") or f"Task {name} is due"

            for u in users:
                _mk_notification(u, name, title, body)

            _mark_sent(name)
            processed += 1

        except Exception as e:
            _mark_error(name, str(e))
            print(f"[TODO][ERR] {name}: {e}", flush=True)

    frappe.db.commit()
    print(f"[CHECK] Done. Total processed={processed}", flush=True)
    return {"processed": processed}

import frappe
from frappe.utils import now_datetime

@frappe.whitelist()
def scheduler_heartbeat():
    print("========== [HEARTBEAT] scheduler tick at", now_datetime(), "==========", flush=True)