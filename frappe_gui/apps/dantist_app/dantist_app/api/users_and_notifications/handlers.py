import logging


import frappe
import requests

logger = logging.getLogger(__name__)

BASE_PATH = "/integrations/frappe"  # ← как ты сказал


@frappe.whitelist(methods=["POST"])
def create_notification_from_upstream():
    """
    Базовое уведомление в Frappe.
    Если payload.recipient_email задан → шлём ОДНО уведомление этому пользователю.
    Если НЕ задан → бродкаст: создаём уведомления для ВСЕХ enabled-пользователей.
    Без document_type/document_name (никаких LinkValidationError).
    Идемпотентность используется только если в Notification Log есть поле idempotency_key.
    """
    payload = frappe.local.form_dict or {}
    if "payload" in payload and isinstance(payload["payload"], dict):
        payload = payload["payload"]

    # Контент
    title = payload.get("title") or {}
    subject = title.get("en") or title.get("ru") or "Notification"
    message = payload.get("message") or ""
    link_url = payload.get("link_url") or ""

    # Адресат(ы)
    recipient_email = (payload.get("recipient_email") or "").strip()

    # Идемпотентность (опционально)
    base_idem = (payload.get("idempotency_key") or "").strip()
    has_idem = frappe.db.has_column("Notification Log", "idempotency_key")

    def _insert_one(for_user: str, idem_suffix: str | None = None) -> str:
        doc_fields = {
            "doctype": "Notification Log",
            "subject": subject,
            "email_content": message,
            "type": "Alert",
            "for_user": for_user,   # Link → User (email / name)
        }
        # Временно уберу, не удалять!
        # if link_url:
        #     doc_fields["link"] = link_url
        if has_idem and base_idem:
            # для бродкаста делаем пер-юзерный ключ, чтобы не «слиплось»
            doc_fields["idempotency_key"] = f"{base_idem}:{idem_suffix or for_user}"

            # если уже есть — пропускаем
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
        # Бродкаст всем включённым, кроме Guest
        # (Administrator включаем; если не нужно — отфильтруй ниже)
        users = frappe.get_all(
            "User",
            filters={"enabled": 1},
            pluck="name",      # name = email
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




def get_user_id() -> str:
    email = (frappe.session.user or "").strip()
    if not email or email == "Guest":
        frappe.throw("User is not authenticated", exc=frappe.ValidationError)

    base_url = frappe.conf.get("dantist_base_url")
    if not base_url:
        frappe.throw("Dantist base URL not configured", exc=frappe.ValidationError)

    try:
        r = requests.get(f"{base_url.rstrip('/')}{BASE_PATH}/users/lookup", params={"email": email}, timeout=6)
    except Exception as e:
        frappe.throw(f"Upstream error: {e}", exc=frappe.ValidationError)

    if r.status_code != 200:
        frappe.throw(f"Lookup failed: {r.text}", exc=frappe.ValidationError)

    data = r.json() or {}
    if not data.get("ok"):
        frappe.throw("User not linked in Mongo", exc=frappe.ValidationError)

    return (data.get("user_id") or "").strip()

@frappe.whitelist()
def on_user_changed(doc, method=None):
    """
    Универсальный хук на создание/изменение User.
    Отправляет в твой FastAPI актуальные данные + список ролей Frappe,
    чтобы endpoint /users/ensure_mongoadmin маппил и «апгрейдил» роль в Mongo.
    """
    try:
        email = (doc.email or "").strip().lower()
        if not email:
            return

        base_url = frappe.conf.get("dantist_base_url")
        if not base_url:
            return

        # соберём роли пользователя из дочерней таблицы
        roles = []
        try:
            roles = [ (r.role or "").strip() for r in (getattr(doc, "roles", []) or []) if (r.role or "").strip() ]
        except Exception:
            roles = []

        payload = {
            "email": email,
            "username": (getattr(doc, "username", None) or doc.name or email.split("@")[0]),
            "full_name": (getattr(doc, "full_name", None) or getattr(doc, "first_name", None) or doc.name),
            "role": None,                    # локальную роль здесь не навязываем — маппинг из frappe_roles
            "frappe_roles": roles,           # <- ключевое: отдаём список ролей Frappe
        }

        try:
            requests.post(
                f"{base_url.rstrip('/')}{BASE_PATH}/users/ensure_mongoadmin",
                json=payload,
                timeout=8,
            )
        except Exception:
            # не валим транзакцию Frappe — просто логируем
            logger.exception("Failed to sync user to MongoAdmin")

    except Exception:
        logger.exception("on_user_changed failed")
