"""Вспомогательные функции проекта."""
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


async def send_sms(phone: str, text: str) -> dict:
    "Отправляет SMS-сообщение через SMS-Fly."
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
                error_code = response_data.get(
                    "error", {}).get(
                    "code", "Unknown")
                error_desc = response_data.get(
                    "error", {}).get(
                    "description", "")
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

# async def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> dict:
#     """Отправляет письмо через SMTP асинхронно, с поддержкой HTML."""
#     message = MIMEMultipart("alternative")
#     message["From"] = settings.SMTP_FROM
#     message["To"] = to_email
#     message["Subject"] = subject
#     if html_body:
#         part = MIMEText(html_body, "html")
#     else:
#         part = MIMEText(body)
#     message.attach(part)

#     try:
#         await aiosmtplib.send(
#             message,
#             hostname=settings.SMTP_HOST,
#             port=settings.SMTP_PORT,
#             username=settings.SMTP_USERNAME,
#             password=settings.SMTP_PASSWORD,
#             start_tls=True,
#             timeout=settings.SMTP_TIMEOUT,
#             recipients=[to_email],  # ВАЖНО: явно указать получателя
#         )
#         return {"success": True}
#     except aiosmtplib.SMTPException as exc:
#         logging.exception("SMTP error")
#         raise HTTPException(
#             status_code=status.HTTP_502_BAD_GATEWAY,
#             detail="SMTP provider is unavailable",
#         ) from exc


async def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> dict:
    """Отправляет письмо через SMTP асинхронно, с поддержкой HTML."""
    
    print("📨 Входящие параметры:")
    print(f"to_email: {to_email}")
    print(f"subject: {subject}")
    print(f"body: {body}")
    print(f"html_body: {html_body}")

    message = MIMEMultipart("alternative")
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email
    message["Subject"] = subject

    html_body = f"""
<html>
<body>
    <p>Here is your verification code: <strong>52</strong></p>
</body>
</html>
"""
    # html_body = None
    # body = "Привет"

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

    # SMTP_FROM: noreply@panamed-aihubworks.com
    # SMTP_HOST: smtp.emaillabs.net.pl
    # SMTP_PORT: 587
    # SMTP_USERNAME: 1.pana.smtp
    # SMTP_PASSWORD: P6ZZvKss
    # SMTP_TIMEOUT: 10.0

    try:
        # await aiosmtplib.send(
        #     message,
        #     hostname=settings.SMTP_HOST,
        #     port=settings.SMTP_PORT,
        #     # port=465,
        #     username=settings.SMTP_USERNAME,
        #     password=settings.SMTP_PASSWORD,
        #     # use_tls=True,
        #     start_tls=True,
        #     timeout=settings.SMTP_TIMEOUT,
        #     recipients=[to_email.lower()],
        # )
        await aiosmtplib.send(
            message,
            hostname="smtp.emaillabs.net.pl",
            port=587,
            username="1.pana.smtp",
            password="P6ZZvKss",
            start_tls=True,
            timeout=10,
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
