# apps/dantist_app/dantist_app/api/tasks/tasks.py
from __future__ import annotations
import frappe
from frappe.utils import now_datetime

LOGGER = frappe.logger("dantist.reminders", allow_site=True)

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

def _notify_user(user: str, todo_name: str, desc: str):
    try:
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": "ToDo Reminder",
            "email_content": desc,
            "for_user": user,
            "document_type": "ToDo",
            "document_name": todo_name,
            "type": "Alert",
        }).insert(ignore_permissions=True)
        print(f"[REMIND] {todo_name} -> {user}", flush=True)
    except Exception as e:
        print(f"[REMIND][ERR] {todo_name} -> {user}: {e}", flush=True)

def _assigned_users_for_todo(todo_name: str):
    # Assignments хранятся в ToDo как отдельные строки ToDo со ссылкой? Нет.
    # В Frappe назначение — в таблице ToDo Assignment (используется API assign_to).
    # Упростим: возьмём из assign_to API представление:
    rows = frappe.get_all("ToDo",  # это безопасный fallback на случай использования allocated_to
                          filters={"name": todo_name},
                          fields=["allocated_to"])
    out = []
    if rows and rows[0].get("allocated_to"):
        out.append(rows[0]["allocated_to"])

    # дополнительно вытащим assign_log (узлы Assign To)
    alog = frappe.get_all("Assignment Rule", fields=["name"], limit=0)  # заглушка, если нет — ок
    # Прямого API для чтения «Assign To» нет в ORM — пойдём через таблицу `ToDo`? В 15-ке
    # назначенные пользователи хранятся в `ToDo`-assignements через `Assignment` doctype:
    assignees = frappe.get_all(
        "Assignment",
        filters={"reference_doctype": "ToDo", "reference_name": todo_name, "status": "Open"},
        fields=["owner"]
    )
    for a in assignees:
        u = a.get("owner")
        if u and u not in out:
            out.append(u)
    return out

def scan_todo_reminders():
    now = now_datetime()
    # Ищем открытые с включённым флагом и НЕ отправленные
    todos = frappe.get_all(
        "ToDo",
        filters={
            "status": "Open",
            F_SEND: 1,
            F_SENT_AT: ["is", "not set"],
            F_DUE_DT: ["<=", now],
        },
        fields=["name","description","allocated_to"],
        order_by=f"{F_DUE_DT} asc",
        limit=200
    )
    if not todos:
        return

    for row in todos:
        try:
            # Кого пинговать:
            users = _assigned_users_for_todo(row.name)
            if not users and row.allocated_to:
                users = [row.allocated_to]
            if not users:
                frappe.db.set_value("ToDo", row.name, F_ERR, "No assignees")
                print(f"[REMIND][SKIP] {row.name} no users", flush=True)
                continue

            for u in users:
                _notify_user(u, row.name, row.description or row.name)

            frappe.db.set_value("ToDo", row.name, {
                F_SENT_AT: now,
                F_ERR: None
            })
        except Exception as e:
            frappe.db.set_value("ToDo", row.name, F_ERR, str(e))
            print(f"[REMIND][ERR] {row.name}: {e}", flush=True)
            frappe.log_error(title="scan_todo_reminders", message=frappe.get_traceback())