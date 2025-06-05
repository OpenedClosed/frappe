"""Обработчики маршрутов приложения Чаты."""
from aiohttp import web
from fastapi import APIRouter, HTTPException

from bot_conf.create_bot import bot
from infra import settings as bot_settings

router = APIRouter()


# async def send_message(request: web.Request):
#     """Принимает вебхук от backend и отправляет сообщение в Telegram-чат."""

#     client_ip = request.headers.get("X-Real-IP", request.remote)
#     if bot_settings.WEBHOOK_ALLOWED_IPS and client_ip not in bot_settings.WEBHOOK_ALLOWED_IPS:
#         raise HTTPException(status_code=403,
#                             detail="Access forbidden: Unauthorized IP.")

#     payload = await request.json()
#     chat_id = payload.get("chat_id")
#     text = payload.get("text")
#     parse_mode = payload.get("parse_mode")

#     if not chat_id or not text:
#         raise HTTPException(status_code=400, detail="Invalid payload.")

#     try:
#         await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
#         return web.json_response(
#             {"status": "success", "detail": "Message sent successfully"})

#     except Exception as e:
#         print(f"Ошибка обработки запроса: {e}")
#         return web.json_response(
#             {"status": "error", "detail": str(e)}, status=500)


async def send_message(request: web.Request):
    """Принимает вебхук от backend и отправляет сообщение в Telegram-чат, включая топик."""

    client_ip = request.headers.get("X-Real-IP", request.remote)
    if bot_settings.WEBHOOK_ALLOWED_IPS and client_ip not in bot_settings.WEBHOOK_ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="Access forbidden: Unauthorized IP.")

    payload = await request.json()
    chat_id = payload.get("chat_id")
    text = payload.get("text")
    parse_mode = payload.get("parse_mode")
    message_thread_id = payload.get("message_thread_id")  # 🔹 извлекаем топик

    if not chat_id or not text:
        raise HTTPException(status_code=400, detail="Invalid payload.")

    try:
        send_kwargs = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        if message_thread_id:
            send_kwargs["message_thread_id"] = message_thread_id 

        await bot.send_message(**send_kwargs)

        return web.json_response({"status": "success", "detail": "Message sent successfully"})

    except Exception as e:
        print(f"Ошибка обработки запроса: {e}")
        return web.json_response({"status": "error", "detail": str(e)}, status=500)