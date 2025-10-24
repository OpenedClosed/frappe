import hashlib
import time

from typing import Any, Dict, Optional


def build_frappe_notification_payload(
    *,
    kind: str,
    html: str,
    title: Optional[Dict[str, str]] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    route: Optional[str] = None,          # зарезервировано
    link_url: Optional[str] = None,
    account_id: Optional[str] = None,     # зарезервировано
    idempotency_key: Optional[str] = None,
    recipient_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Готовит payload для dantist_app.api.integration.create_notification_from_upstream.
    Без document_type/document_name (никаких LinkValidationError).
    """
    title_dict = title or {}

    if not idempotency_key:
        # «минутный» устойчивый ключ, чтобы одинаковые события за минуту не дублировались
        minute_slot = int(time.time() // 60)
        raw = f"{kind}|{(entity_type or '').strip()}|{(entity_id or '').strip()}|{minute_slot}"
        idempotency_key = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    payload: Dict[str, Any] = {
        "title": title_dict,          # {"en": "...", "ru": "..."}
        "message": html,              # HTML или текст
        "link_url": link_url or "",
        "idempotency_key": idempotency_key,
    }
    if recipient_email:
        payload["recipient_email"] = recipient_email

    return payload