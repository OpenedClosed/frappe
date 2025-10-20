# apps/dantist_app/dantist_app/api/tasks/tasks.py
from datetime import timedelta
import frappe
from frappe.utils import now_datetime

# Флаги:
# - custom_send_reminder (Check) — включить ли напоминание (по умолчанию 1)
# - custom_reminder_sent (Check) — уже отправляли?
# - custom_due_datetime (Datetime) — когда напомнить

def _notify(users: list[str], title: str, message: str, ref_type: str, ref_name: str):
    if not users:
        return
    try:
        from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
        enqueue_create_notification(users=users, subject=title, email_content=message, reference_doctype=ref_type, reference_name=ref_name)
    except Exception as e:
        print("[REMINDER][NOTIFY][ERROR]", e, flush=True)


def _get_assignees(todo_name: str) -> list[str]:
    # читаем стандартные Assignments
    rows = frappe.get_all("ToDo",
                          filters={"name": todo_name},
                          fields=["allocated_to"])
    users = set()
    for r in rows:
        if r.get("allocated_to"):
            users.add(r["allocated_to"])

    # дополнительно из Assignment Doc (если используется)
    try:
        ass = frappe.get_all("Assignment",
                             filters={"reference_type": "ToDo", "reference_name": todo_name, "status": ["!=", "Cancelled"]},
                             fields=["owner", "assigned_to"])
        for a in ass:
            if a.get("assigned_to"):
                users.add(a["assigned_to"])
            if a.get("owner"):
                users.add(a["owner"])
    except Exception:
        pass

    return [u for u in users if u and u != "Guest"]


def scan_todo_reminders():
    now = now_datetime()
    print(f"[REMINDER][SCAN] {now}", flush=True)

    rows = frappe.get_all(
        "ToDo",
        filters={
            "status": "Open",
            "custom_send_reminder": 1,
            "custom_reminder_sent": 0,
            "custom_due_datetime": ["<=", now + timedelta(seconds=1)]
        },
        fields=["name", "description", "reference_type", "reference_name", "custom_due_datetime"]
    )

    print(f"[REMINDER][FOUND] {len(rows)}", flush=True)

    for r in rows:
        users = _get_assignees(r.name)
        print(f"[REMINDER][ITEM] {r.name} -> users={users}", flush=True)
        _notify(
            users=users,
            title=f"ToDo reminder",
            message=f"{r.description or r.name}",
            ref_type=r.reference_type,
            ref_name=r.reference_name
        )
        # помечаем отправленным
        frappe.db.set_value("ToDo", r.name, {"custom_reminder_sent": 1})


@frappe.whitelist()
def run_scan_now():
    print("[REMINDER][RUN_SCAN_NOW] called", flush=True)
    scan_todo_reminders()
    return {"ok": True}