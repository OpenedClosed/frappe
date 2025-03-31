"""Вспомогательные функции интеграции Meta."""
import hashlib
import hmac

from fastapi import HTTPException, Request


async def verify_meta_signature(
    request: Request,
    app_secret: str,
):
    """Проверяет подпись входящего запроса (X-Hub-Signature-256) для сервисов Meta."""
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    raw_body = await request.body()
    expected_signature = hmac.new(
        key=app_secret.encode(),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(f"sha256={expected_signature}", signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    return True
