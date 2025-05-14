"""Вспомогательные функции интеграции Meta."""
import hashlib
import hmac
import json
import logging

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



async def get_meta_locale(psid: str, access_token: str) -> str | None:
    """Возвращает locale пользователя по его PSID."""
    url = f"https://graph.facebook.com/v22.0/{psid}"
    params = {"fields": "locale", "access_token": access_token}

    logging.debug(f"[IG] Запрос locale для psid={psid} (token starts with: {access_token[:10]}...)")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=5) as resp:
                text = await resp.text()
                logging.debug(f"[IG] Ответ locale для psid={psid}: status={resp.status}, body={text[:300]}")

                if resp.status == 200:
                    data = json.loads(text)
                    locale = data.get("locale")
                    logging.info(f"[IG] locale={locale} получен для psid={psid}")
                    if not locale:
                        logging.warning(f"[IG] locale отсутствует в ответе: {data}")
                    return locale

                logging.warning(f"[IG] Ошибка при запросе locale {psid}: {resp.status} {text}")
                if "Invalid OAuth access token" in text:
                    logging.error(f"[IG] ❌ Неверный access token — проверь настройки")

    except Exception as e:
        logging.exception(f"[IG] Исключение при запросе locale для psid={psid}: {e}")

    return None

