"""Вспомогательные функции проекта."""
import json
import logging
import random
import re
import string
from datetime import datetime
from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, HTTPException, Response, status
import httpx
from infra import settings


def to_snake_case(name: str) -> str:
    """Привести строку в snake_case."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

def get_language_from_locale(locale: str | None) -> str:
    """Извлекает язык из locale, по умолчанию 'en'."""
    if not locale:
        return "en"
    return locale.split("_")[0].lower()


def generate_random_filename(extension: str) -> str:
    """Сгенерировать случайное имя для файла с временной меткой."""
    random_str = ''.join(
        random.choices(
            string.ascii_letters + string.digits,
            k=6
        )
    )
    date_str = datetime.now().strftime("%Y%m%d")
    return f"{random_str}_{date_str}{extension}"


def try_parse_json(text: str) -> Union[Dict[str, Any], str]:
    """Пытается парсить JSON из text. Если неуспешно — возвращает текст как есть."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON", "original": text}
    

def normalize_numbers(phone: str) -> str:
    "Убрать лишние символы, оставив лишь числовые"
    return re.sub(r"\D", "", phone)


async def send_sms(phone: str, text: str) -> dict:
    "Отправляет SMS-сообщение через SMS-Fly."
    test_phone = "48572416005"
    phone = test_phone
    payload = {
        "auth": {
            "key": settings.SMS_API_KEY
        },
        "action": "SENDMESSAGE",
        "data": {
            "recipient": normalize_numbers(phone),
            "channels": ["sms"],
            "sms": {
                "source": settings.SMS_API_SENDER,
                "ttl": 300,
                "text": text
            }
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.post(settings.SMS_API_URL, json=payload)
            response_data = r.json()
            if not response_data.get("success"):
                error_code = response_data.get("error", {}).get("code", "Unknown")
                error_desc = response_data.get("error", {}).get("description", "")
                logging.error(f"SMS-Fly error {error_code}: {error_desc}")
                raise HTTPException(
                    status_code=502,
                    detail=f"SMS error: {error_code} - {error_desc}"
                )
            r.raise_for_status()
            return response_data
        except httpx.HTTPStatusError as exc:
            logging.exception(f"SMS-Fly HTTP error: {exc.response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="SMS provider is unavailable"
            ) from exc
        except Exception as exc:
            logging.exception("Unexpected error in send_sms")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal SMS error"
            ) from exc
