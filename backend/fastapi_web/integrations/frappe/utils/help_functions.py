# dantist/integration/frappe/help_functions.py
import hmac
import time
from hashlib import sha256
from fastapi import HTTPException
from typing import Optional

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



# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional

def build_frappe_notification_payload(
    *,
    kind: str,
    html: str,
    title: Dict[str, str],
    entity_type: str,
    entity_id: str,
    route: Optional[str],
    link_url: Optional[str],
    account_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    entity = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "route": route,
        "extra": {},
    }
    if account_id:
        entity["extra"]["account_id"] = account_id

    return {
        "kind": kind,
        "priority": "CRITICAL",
        "title": title,
        "message": html,
        "entity": entity,
        "link_url": link_url,
        "popup": True,
        "sound": True,
        "meta": {},
        "idempotency_key": idempotency_key,
        "recipient_email": None,
    }
