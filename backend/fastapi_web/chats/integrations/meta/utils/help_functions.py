"""Вспомогательные функции интеграции Meta."""
import hashlib
import hmac
import json
import logging
from typing import Optional

import aiohttp
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


async def get_meta_locale(psid: str, access_token: str) -> Optional[str]:
    """Возвращает locale пользователя по его PSID."""
    url = f"https://graph.facebook.com/v22.0/{psid}"
    params = {"fields": "locale", "access_token": access_token}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=5) as resp:
                text = await resp.text()

                if resp.status == 200:
                    data = json.loads(text)
                    return data.get("locale")

                if "Invalid OAuth access token" in text:
                    logging.error(
                        "[IG] Invalid access token — check your settings"
                    )

    except Exception:
        pass

    return None
