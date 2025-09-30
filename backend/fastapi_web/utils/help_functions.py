"""Вспомогательные функции проекта."""
import asyncio
from email.mime.text import MIMEText
import json
import logging
import random
import re
import string
from datetime import datetime
from typing import Any, Dict, Union
from email.message import EmailMessage
import aiosmtplib
import asyncio
from aiosmtplib import send
import smtplib
from email.mime.multipart import MIMEMultipart
import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status

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


# async def send_sms(phone: str, text: str) -> dict:
#     "Отправляет SMS-сообщение через SMS-Fly."
#     payload = {
#         "auth": {
#             "key": settings.SMS_API_KEY
#         },
#         "action": "SENDMESSAGE",
#         "data": {
#             "recipient": normalize_numbers(phone),
#             "channels": ["sms"],
#             "sms": {
#                 "source": settings.SMS_API_SENDER,
#                 "ttl": 300,
#                 "text": text
#             }
#         }
#     }

#     async with httpx.AsyncClient(timeout=10.0) as client:
#         try:
#             r = await client.post(settings.SMS_API_URL, json=payload)
#             response_data = r.json()
#             if not response_data.get("success"):
#                 error_code = response_data.get(
#                     "error", {}).get(
#                     "code", "Unknown")
#                 error_desc = response_data.get(
#                     "error", {}).get(
#                     "description", "")
#                 logging.error(f"SMS-Fly error {error_code}: {error_desc}")
#                 raise HTTPException(
#                     status_code=502,
#                     detail=f"SMS error: {error_code} - {error_desc}"
#                 )
#             r.raise_for_status()
#             return response_data
#         except httpx.HTTPStatusError as exc:
#             logging.exception(f"SMS-Fly HTTP error: {exc.response.text}")
#             raise HTTPException(
#                 status_code=status.HTTP_502_BAD_GATEWAY,
#                 detail="SMS provider is unavailable"
#             ) from exc
#         except Exception as exc:
#             logging.exception("Unexpected error in send_sms")
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="Internal SMS error"
#             ) from exc


# async def send_sms(phone: str, text: str) -> dict:
#     """Отправляет SMS через SMSAPI.pl."""
#     print('here')
#     payload = {
#         "to": normalize_numbers(phone),
#         "message": text,
#         "from": settings.SMS_API_SENDER,  # имя отправителя
#     }
#     payload = {
#         "to": "79639229335",
#         "message": text,
#         "from": settings.SMS_API_SENDER,  # имя отправителя
#     }

#     headers = {
#         "Authorization": f"Bearer {settings.SMS_API_KEY}"
#     }

#     async with httpx.AsyncClient(timeout=10.0) as client:
#         try:
#             r = await client.post(settings.SMS_API_URL, json=payload, headers=headers)
#             r.raise_for_status()
#             response_data = r.json()

#             if "error" in response_data:
#                 error_code = response_data["error"].get("message", "Unknown")
#                 logging.error(f"SMSAPI error: {error_code}")
#                 raise HTTPException(
#                     status_code=502,
#                     detail=f"SMS error: {error_code}"
#                 )
#             return response_data

#         except httpx.HTTPStatusError as exc:
#             logging.exception(f"SMSAPI HTTP error: {exc.response.text}")
#             raise HTTPException(
#                 status_code=status.HTTP_502_BAD_GATEWAY,
#                 detail="SMS provider is unavailable"
#             ) from exc
#         except Exception as exc:
#             logging.exception("Unexpected error in send_sms")
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="Internal SMS error"
#             ) from exc


async def send_sms(phone: str, text: str) -> dict:
    """
    Отправляет SMS через SMSAPI (LINK Mobility).
    Требуются:
      settings.SMS_API_URL     -> "https://api.smsapi.pl/sms.do"
      settings.SMS_API_KEY     -> OAuth token (Bearer)
      settings.SMS_API_SENDER  -> Подтверждённое имя отправителя (опц.)
    """
    url = (settings.SMS_API_URL or "").rstrip("/") or "https://api.smsapi.pl/sms.do"
    # phone = "+7(963)9229335"
    to = normalize_numbers(phone)
    print(to)
    # to = "79639229335"
    if not to:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    # В SMSAPI form-encoded, не JSON
    data = {
        "to": to,
        "message": text,
        "format": "json",         # чтобы получать JSON, а не текст
        "encoding": "utf-8",
    }
    # if getattr(settings, "SMS_API_SENDER", None):
    #     data["from"] = settings.SMS_API_SENDER

    headers = {
        "Authorization": f"Bearer {settings.SMS_API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.post(url, data=data, headers=headers)
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logging.error(f"SMSAPI HTTP error: {exc.response.text}")
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

    try:
        payload = r.json()
    except Exception:
        logging.error("SMSAPI returned non-JSON response")
        raise HTTPException(status_code=502, detail="Invalid SMS provider response")

    # У SMSAPI при ошибке в JSON может прийти ключ 'error' / 'message'
    if isinstance(payload, dict) and payload.get("error"):
        desc = payload.get("message") or payload.get("error_description") or str(payload)
        raise HTTPException(status_code=502, detail=f"SMS error: {desc}")
    print(payload)
    return payload


async def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> dict:
    """Отправляет письмо через SMTP асинхронно, с поддержкой HTML."""
    
    print("📨 Входящие параметры:")
    print(f"to_email: {to_email}")
    print(f"subject: {subject}")
    print(f"body: {body}")
    print(f"html_body: {html_body}")

    message = MIMEMultipart("alternative")
    # message["From"] = settings.SMTP_FROM
    message["From"] = "noreply@panamed-aihubworks.com"
    message["To"] = to_email
    message["Subject"] = subject
    if html_body:
        part = MIMEText(html_body, "html")
    else:
        part = MIMEText(body)

    message.attach(part)

    print("📦 Сформировано сообщение:")
    print(f"From: {message['From']}")
    print(f"To: {message['To']}")
    print(f"Subject: {message['Subject']}")
    print(f"Message payload:\n{message.as_string()}")

    print("🔧 SMTP конфигурация:")
    print(f"SMTP_FROM: {settings.SMTP_FROM}")
    print(f"SMTP_HOST: {settings.SMTP_HOST}")
    print(f"SMTP_PORT: {settings.SMTP_PORT}")
    print(f"SMTP_USERNAME: {settings.SMTP_USERNAME}")
    print(f"SMTP_PASSWORD: {settings.SMTP_PASSWORD}")
    print(f"SMTP_TIMEOUT: {settings.SMTP_TIMEOUT}")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            # port=465,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            # use_tls=True,
            start_tls=True,
            timeout=settings.SMTP_TIMEOUT,
            recipients=[to_email.lower()],
        )
        print("✅ Письмо успешно отправлено.")
        return {"success": True}
    except aiosmtplib.SMTPException as exc:
        logging.exception("SMTP error")
        print(f"❌ Ошибка SMTP: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="SMTP provider is unavailable",
        ) from exc


def split_prompt_parts(full_prompt: str) -> tuple[str, str]:
    """Делит prompt на static- и dynamic-части."""
    if "<<<STATIC>>>" in full_prompt and "<<<DYNAMIC>>>" in full_prompt:
        static_part = (
            full_prompt.split("<<<DYNAMIC>>>")[0]
            .replace("<<<STATIC>>>", "")
            .strip()
        )
        dynamic_part = full_prompt.split("<<<DYNAMIC>>>")[1].strip()
    else:
        static_part, dynamic_part = full_prompt.strip(), ""
    return static_part, dynamic_part
