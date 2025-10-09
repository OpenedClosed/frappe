# dantist/integration/frappe/help_functions.py
import hashlib
import hmac
import time
from hashlib import sha256
from fastapi import HTTPException
from typing import Any, Dict, Optional

from db.redis.db_init import redis_db
from infra import settings

def compute_sig(user_id: str, ts: int, nonce: str, secret: str) -> str:
    payload = f"{user_id}|{ts}|{nonce}".encode("utf-8")
    key = secret.encode("utf-8")
    return hmac.new(key, payload, sha256).hexdigest()

async def verify_hmac_request(
    user_id: str, ts: int, nonce: str, sig: str, aud: Optional[str] = None
) -> None:
    """Проверяет подпись, окно времени и одноразовость nonce."""
    secret = settings.FRAPPE_SHARED_SECRET
    if not secret:
        raise HTTPException(500, "Integration secret not configured")

    now = int(time.time())
    try:
        ts = int(ts)
    except Exception:
        raise HTTPException(401, "Invalid timestamp")
    if abs(now - ts) > 300:
        raise HTTPException(401, "Timestamp is not fresh")

    expected = compute_sig(user_id, ts, nonce, secret)
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(401, "Invalid signature")

    nonce_key = f"frappe_integration_nonce:{nonce}"
    if await redis_db.get(nonce_key):
        raise HTTPException(401, "Replay detected")
    await redis_db.set(nonce_key, "1", ex=600)

    configured_aud = getattr(settings, "FRAPPE_AUD", "")
    if configured_aud and aud and aud != configured_aud:
        raise HTTPException(401, "Invalid audience")



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