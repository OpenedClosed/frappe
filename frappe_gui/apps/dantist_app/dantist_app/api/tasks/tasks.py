# dantist_app/api/tasks/tasks.py
from __future__ import annotations
from typing import List, Optional, Tuple
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

F_DUE_DT  = _todo_fieldname("due_datetime")
F_SEND    = _todo_fieldname("send_reminder")
F_SENT_AT = _todo_fieldname("reminder_sent_at")
F_ERR     = _todo_fieldname("reminder_error")

# ========= ASSIGNEES (ONLY Assigned To) =========
def _get_assignees_for(todo_name: str) -> List[str]:
    """Возвращает пользователей из _assign (и только их)."""
    try:
        raw = frappe.db.get_value("ToDo", todo_name, "_assign") or "[]"
        arr = json.loads(raw) if isinstance(raw, str) else (raw or [])
        users = [u for u in arr if u and u != "Guest"]
        print(f"[ASSIGNEES] {todo_name}: {users}", flush=True)
        return users
    except Exception as e:
        print(f"[ASSIGNEES][ERR] {todo_name}: {e}", flush=True)
        return []

# ========= NOTIFY HELPERS =========
def _notify_via_make_logs(users: List[str], docname: str, subject: str, message: str) -> Tuple[int, Optional[str]]:
    """Пытаемся отправить через make_notification_logs (позиционные аргументы)."""
    try:
        from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
        # сигнатура обычно: (recipients, subject, message, doctype, docname, ...),
        # но используем Позиционные аргументы без имён, чтобы не споткнуться об имена.
        make_notification_logs(users, subject, message, "ToDo", docname)
        print(f"[NOTIFY][make_logs] {docname} -> {users}", flush=True)
        return len(users), None
    except Exception as e:
        return 0, str(e)

def _notify_fallback_manual(users: List[str], docname: str, subject: str, message: str) -> Tuple[int, Optional[str]]:
    """Если API отличается — создаём Notification Log вручную на каждого пользователя."""
    sent = 0
    last_err = None
    for u in users:
        try:
            nl = frappe.get_doc({
                "doctype": "Notification Log",
                "subject": subject,
                "email_content": message,
                "for_user": u,
                "document_type": "ToDo",
                "document_name": docname,
                "type": "Alert",
            })
            nl.insert(ignore_permissions=True)
            print(f"[NOTIFY][fallback] {docname} -> {u}", flush=True)
            sent += 1
        except Exception as e:
            last_err = str(e)
            print(f"[NOTIFY][fallback][ERR] {docname} -> {u}: {e}", flush=True)
    return sent, last_err

def _notify_assignees(todo_name: str, subject: str, message: str) -> int:
    users = _get_assignees_for(todo_name)
    if not users:
        print(f"[NOTIFY] {todo_name}: no assignees", flush=True)
        return 0

    sent, err = _notify_via_make_logs(users, todo_name, subject, message)
    if err:
        print(f"[NOTIFY] make_notification_logs failed: {err} — fallback to manual", flush=True)
        sent2, err2 = _notify_fallback_manual(users, todo_name, subject, message)
        if err2:
            print(f"[NOTIFY] manual fallback had errors: {err2}", flush=True)
        return sent2
    return sent

# ========= DUE CHECK =========
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
    print(f"[PICK] due={len(out)} of candidates={len(rows)}", flush=True)
    return out

def _mark_sent(name: str):
    frappe.db.set_value("ToDo", name, {F_SENT_AT: now_datetime(), F_ERR: None}, update_modified=False)
    print(f"[MARK] {name} -> sent", flush=True)

def _mark_error(name: str, msg: str):
    frappe.db.set_value("ToDo", name, {F_ERR: (msg or "")[:1000]}, update_modified=False)
    print(f"[MARK][ERR] {name}: {msg}", flush=True)

# ========= MAIN JOBS =========
# ========= MAIN JOBS =========
@frappe.whitelist()
def process_due_todos(batch_limit: int = 200):
    """Боевой режим: шлём «колокольчик» AssignedTo, когда задача просрочена/наступила, и отмечаем как отправленную."""
    print("========== [CHECK] process_due_todos ==========", flush=True)

    cands = _pick_candidates(limit=int(batch_limit or 200))
    if not cands:
        print("[CHECK] no due todos", flush=True)
        return {"processed": 0}

    processed = 0
    for t in cands:
        name = t["name"]
        desc = (t.get("description") or "").strip() or f"Task {name}"
        subject = "New reminder"
        message = f"New reminder: {desc}"

        print(f"[TODO] {name} | due={t.get('due_datetime')} | date={t.get('date')}", flush=True)
        try:
            sent = _notify_assignees(name, subject, message)
            if sent > 0:
                _mark_sent(name)
                processed += 1
            else:
                _mark_error(name, "No assignees / nothing sent")
        except Exception as e:
            _mark_error(name, str(e))
            print(f"[TODO][ERR] {name}: {e}", flush=True)

    frappe.db.commit()
    print(f"[CHECK] done processed={processed}", flush=True)
    return {"processed": processed}


@frappe.whitelist()
def test_broadcast_todo_notifications(limit: int = 50, include_closed: int = 0):
    """Тестовый режим: шлёт нотификации AssignedTo для первых N задач, игнорируя сроки (без отметки «отправлено»)."""
    print("========== [TEST] broadcast start ==========", flush=True)
    filters = {}
    if not include_closed:
        filters["status"] = "Open"
    base = frappe.get_all(
        "ToDo",
        filters=filters,
        fields=["name", "description"],
        order_by="modified desc",
        limit_page_length=int(limit or 50),
    )
    print(f"[TEST] picked base todos: {len(base)}", flush=True)
    total_sent = 0
    for r in base:
        todo = r["name"]
        desc = (r.get("description") or "").strip() or f"Task {todo}"
        subject = "New reminder"
        message = f"New reminder: {desc}"

        sent = _notify_assignees(todo, subject, message)
        total_sent += sent

    frappe.db.commit()
    print(f"========== [TEST] broadcast done; rows={len(base)} notifications_sent={total_sent} ==========", flush=True)
    return {"rows": len(base), "notifications_sent": total_sent}

@frappe.whitelist()
def scheduler_heartbeat():
    print("========== [HEARTBEAT] scheduler tick at", now_datetime(), "==========", flush=True)