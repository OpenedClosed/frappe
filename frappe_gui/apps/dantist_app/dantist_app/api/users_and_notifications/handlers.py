import logging
import json
from typing import List, Set, Tuple, Optional

import frappe
import requests

logger = logging.getLogger(__name__)

BASE_PATH = "/integrations/frappe"

# ----------------------------------------------------------------------
#                            NOTIFICATIONS
# ----------------------------------------------------------------------
@frappe.whitelist(methods=["POST"])
def create_notification_from_upstream():
    payload = frappe.local.form_dict or {}
    if "payload" in payload and isinstance(payload["payload"], dict):
        payload = payload["payload"]

    title = payload.get("title") or {}
    subject = title.get("en") or title.get("ru") or "Notification"
    message = payload.get("message") or ""
    link_url = payload.get("link_url") or ""

    recipient_email = (payload.get("recipient_email") or "").strip()

    base_idem = (payload.get("idempotency_key") or "").strip()
    has_idem = frappe.db.has_column("Notification Log", "idempotency_key")

    def _insert_one(for_user: str, idem_suffix: str | None = None) -> str:
        doc_fields = {
            "doctype": "Notification Log",
            "subject": subject,
            "email_content": message,
            "type": "Alert",
            "for_user": for_user,
        }
        # if link_url:
        #     doc_fields["link"] = link_url
        if has_idem and base_idem:
            doc_fields["idempotency_key"] = f"{base_idem}:{idem_suffix or for_user}"
            if frappe.db.exists("Notification Log", {"idempotency_key": doc_fields["idempotency_key"]}):
                return "SKIPPED"
        doc = frappe.get_doc(doc_fields)
        doc.insert(ignore_permissions=True)
        return doc.name

    created = []
    skipped = 0

    if recipient_email:
        name = _insert_one(recipient_email, None)
        if name == "SKIPPED":
            skipped += 1
        else:
            created.append(name)
    else:
        users = frappe.get_all(
            "User",
            filters={"enabled": 1},
            pluck="name",
            limit_page_length=100000
        )
        users = [u for u in users if u and u != "Guest"]
        for u in users:
            name = _insert_one(u, u)
            if name == "SKIPPED":
                skipped += 1
            else:
                created.append(name)

    frappe.db.commit()
    try:
        frappe.publish_realtime("notification_update")
    except Exception:
        pass

    return {"ok": True, "created": len(created), "skipped": skipped, "ids": created}

# ----------------------------------------------------------------------
#                          USER ↔ MONGO LINK
# ----------------------------------------------------------------------
def _current_user_email() -> str:
    user = (frappe.session.user or "").strip()
    if not user or user == "Guest":
        frappe.throw("User is not authenticated", exc=frappe.ValidationError)
    email = (frappe.db.get_value("User", user, "email") or "").strip().lower()
    if not email and "@" in user:
        email = user.lower()
    if not email:
        fallback = (frappe.conf.get("dantist_super_admin_email") or "").strip().lower()
        if fallback:
            email = fallback
    if not email:
        frappe.throw("User has no email", exc=frappe.ValidationError)
    return email


def get_user_id() -> str:
    email = _current_user_email()
    base_url = frappe.conf.get("dantist_base_url")
    if not base_url:
        frappe.throw("Dantist base URL not configured", exc=frappe.ValidationError)
    try:
        r = requests.get(f"{base_url.rstrip('/')}{BASE_PATH}/users/lookup",
                         params={"email": email}, timeout=6)
    except Exception as e:
        frappe.throw(f"Upstream error: {e}", exc=frappe.ValidationError)
    if r.status_code != 200:
        frappe.throw(f"Lookup failed: {r.text}", exc=frappe.ValidationError)
    data = r.json() or {}
    if not data.get("ok"):
        frappe.throw(f"User not linked in Mongo for {email}", exc=frappe.ValidationError)
    return (data.get("user_id") or "").strip()


@frappe.whitelist()
def on_user_changed(doc, method=None):
    try:
        email = (doc.email or "").strip().lower()
        if not email:
            return
        base_url = frappe.conf.get("dantist_base_url")
        if not base_url:
            return
        roles = []
        try:
            roles = [ (r.role or "").strip() for r in (getattr(doc, "roles", []) or []) if (r.role or "").strip() ]
        except Exception:
            roles = []
        payload = {
            "email": email,
            "username": (getattr(doc, "username", None) or doc.name or email.split("@")[0]),
            "full_name": (getattr(doc, "full_name", None) or getattr(doc, "first_name", None) or doc.name),
            "role": None,
            "frappe_roles": roles,
        }
        try:
            requests.post(
                f"{base_url.rstrip('/')}{BASE_PATH}/users/ensure_mongoadmin",
                json=payload,
                timeout=8,
            )
        except Exception:
            logger.exception("Failed to sync user to MongoAdmin")
    except Exception:
        logger.exception("on_user_changed failed")

# =====================================================================
#                     CHAT → CASE ASSIGНЕES (ONE-TIME)
# =====================================================================

TARGET_CHAT_ID = "68f6b260070075ebeb464eb2"  # для явной метки в логах

def _seen_get(doc) -> Set[str]:
    try:
        raw = getattr(doc, "custom_chat_assignees_seen", None)
        if raw is None:
            return set()
        arr = json.loads(raw) if isinstance(raw, str) else (raw or [])
        return { (e or "").strip().lower() for e in arr if e }
    except Exception:
        return set()

def _seen_save(doc, seen: Set[str]) -> None:
    if not hasattr(doc, "custom_chat_assignees_seen"):
        return
    try:
        doc.db_set("custom_chat_assignees_seen", json.dumps(sorted(seen)), update_modified=False)
    except Exception:
        frappe.logger("dantist.tasks").warning("Failed to save custom_chat_assignees_seen", exc_info=True)

def _is_non_client_human(p: dict) -> Tuple[bool, str, str]:
    """return (is_candidate, email, role)"""
    try:
        si = p.get("sender_info") or {}
        user = si.get("user") or {}
        email = (user.get("email") or "").strip().lower()
        role = (user.get("role") or "").strip().lower()
        source = (si.get("source") or "").strip().lower()
        if not email:
            return (False, "", "")
        if role in {"client", "customer", "patient"}:
            return (False, "", "")
        if "ai" in role or source in {"ai", "assistant"}:
            return (False, "", "")
        return (True, email, role)
    except Exception:
        return (False, "", "")

def _current_assignees_for_case(case_name: str) -> Set[str]:
    rows = frappe.get_all(
        "ToDo",
        filters={"reference_type": "Engagement Case", "reference_name": case_name, "status": "Open"},
        fields=["allocated_to"],
        limit_page_length=100000,
    )
    return { (r.get("allocated_to") or "").strip() for r in (rows or []) if r.get("allocated_to") }

def _assign_user_to_case(case_name: str, user_name: str) -> None:
    try:
        frappe.desk.form.assign_to.add({
            "assign_to": [user_name],           # ВАЖНО: сюда идёт ИМЯ пользователя (docname), не email
            "doctype": "Engagement Case",
            "name": case_name,
            "notify": 0,
        })
        print(f"[CHAT->ASSIGN] {case_name} <- {user_name}", flush=True)
    except Exception as e:
        print(f"[CHAT->ASSIGN][ERR] {case_name} <- {user_name}: {e}", flush=True)

def _resolve_user(email: str, role: str) -> Optional[str]:
    """
    Возвращает docname пользователя для назначения:
      1) по полю email,
      2) если docname == email,
      3) если роль admin/superadmin/demo → по dantist_super_admin_email или 'Administrator'.
    Только enabled-пользователи.
    """
    email = (email or "").strip().lower()
    role  = (role  or "").strip().lower()

    # 1) поиск по полю email
    try:
        name = frappe.db.get_value("User", {"email": email}, "name")
        if name:
            enabled = frappe.db.get_value("User", name, "enabled")
            if enabled:
                return name
    except Exception:
        pass

    # 2) docname == email
    try:
        if frappe.db.exists("User", email):
            enabled = frappe.db.get_value("User", email, "enabled")
            if enabled:
                return email
    except Exception:
        pass

    # 3) роль-маппинг на суперпользователя
    if role in {"superadmin", "admin", "demo"}:
        cfg = (frappe.conf.get("dantist_super_admin_email") or "").strip().lower()
        if cfg:
            name = frappe.db.get_value("User", {"email": cfg}, "name") or (cfg if frappe.db.exists("User", cfg) else None)
            if name and frappe.db.get_value("User", name, "enabled"):
                return name
        # последний шанс — Administrator
        try:
            if frappe.db.exists("User", "Administrator"):
                # у системного пользователя enabled может быть None → считаем валидным
                return "Administrator"
        except Exception:
            pass

    return None

@frappe.whitelist(methods=["POST"])
def sync_case_assignees_from_chat():
    """
    Идемпотентно добавляет Assigned To на карточку Engagement Case для всех участников чата
    с НЕклиентской ролью (и не ИИ). Используем participants_json (из FastAPI).
    """
    form = frappe.local.form_dict or {}
    case_name = (form.get("case_name") or "").strip()
    if not case_name:
        frappe.throw("case_name is required", exc=frappe.ValidationError)

    # participants_json может прийти строкой
    participants = None
    if isinstance(form.get("participants"), list):
        participants = form.get("participants")
    else:
        pj = form.get("participants_json")
        if pj is None and isinstance(form.get("participants"), str):
            pj = form.get("participants")
        try:
            participants = json.loads(pj or "[]")
        except Exception:
            participants = []

    # подтянем chat_id для логов
    chat_id = (frappe.db.get_value("Engagement Case", case_name, "mongo_chat_id") or "").strip()

    # Вербоз — только если 1 участник, как просил
    if len(participants or []) == 1:
        print(f"[ASSIGNEES_SYNC][VERBOSE] case={case_name} chat_id={chat_id} raw_participants=1", flush=True)
        p0 = (participants or [])[0] or {}
        si = p0.get("sender_info") or {}
        u  = si.get("user") or {}
        print(f"[ASSIGNEES_SYNC][VERBOSE] p#0: email={(u.get('email') or '').strip().lower()} role={(u.get('role') or '').strip().lower()} source={(si.get('source') or '').strip()}", flush=True)
        if chat_id == TARGET_CHAT_ID:
            try:
                dump = json.dumps(participants or [], ensure_ascii=False, indent=2)
            except Exception:
                dump = str(participants)
            print("*** TARGET CHAT MATCHED ***", flush=True)
            print(f"[ASSIGNEES_SYNC][TARGET] participants_dump= {dump}", flush=True)
    else:
        # сводка-коротышка для остальных случаев
        print(f"[ASSIGNEES_SYNC] case={case_name} chat_id={chat_id} raw_participants={len(participants or [])}", flush=True)

    case = frappe.get_doc("Engagement Case", case_name)

    # кандидаты по роли
    candidates: List[Tuple[str, str]] = []  # (email, role)
    skipped_by_role = 0
    for p in (participants or []):
        ok, email, role = _is_non_client_human(p)
        if ok and email:
            candidates.append((email, role))
        else:
            skipped_by_role += 1

    print(f"[ASSIGNEES_SYNC] candidates_by_role={len(candidates)} skipped_by_role={skipped_by_role}", flush=True)

    # seen / current
    seen = _seen_get(case)
    current = _current_assignees_for_case(case.name)
    print(f"[ASSIGNEES_SYNC] seen={sorted(seen)}", flush=True)
    print(f"[ASSIGNEES_SYNC] current={sorted(current)}", flush=True)

    to_add: List[str] = []
    skipped_no_user = 0
    skipped_seen = 0
    skipped_current = 0

    for email, role in candidates:
        if email in seen:
            skipped_seen += 1
            continue

        user_docname = _resolve_user(email, role)
        if not user_docname:
            print(f"[ASSIGNEES_SYNC] skip_no_user e={email}", flush=True)
            skipped_no_user += 1
            continue

        if user_docname in current:
            seen.add(email)
            skipped_current += 1
            continue

        to_add.append(user_docname)

    # назначаем
    for user_name in to_add:
        _assign_user_to_case(case.name, user_name)

    # обновляем seen (храним по email-ам для идемпотентности)
    for email, _ in candidates:
        if email not in seen:
            seen.add(email)
    _seen_save(case, seen)
    frappe.db.commit()

    print(f"[ASSIGNEES_SYNC] to_add={to_add}", flush=True)
    print(f"[ASSIGNEES_SYNC] result added={len(to_add)} skipped_no_user={skipped_no_user} skipped_seen={skipped_seen} skipped_current={skipped_current}", flush=True)

    return {
        "ok": True,
        "added": len(to_add),
        "skipped_no_user": skipped_no_user,
        "skipped_seen": skipped_seen,
        "skipped_current": skipped_current,
        "case": case_name
    }