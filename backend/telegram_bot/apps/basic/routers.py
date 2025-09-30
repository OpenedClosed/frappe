"""Базовые маршруты."""
import html
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs  # импорт вверху файла

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove)
from aiohttp import web
from fastapi import HTTPException

from telegram_bot.ai.utils.help_functions import (build_messages_for_model,
                                                  chat_generate_any,
                                                  extract_json_from_response)
from telegram_bot.ai.utils.mappings import FUNCTION_MAP
from telegram_bot.ai.utils.prompts import PROMPTS
from telegram_bot.apps.fashion.db.postgres.models import Subscription
from telegram_bot.apps.fashion.handlers import handle_send_digest
from telegram_bot.apps.knowledge.utils.help_functions import get_bot_context
from telegram_bot.infra import settings as bot_settings
from telegram_bot.infra.create_bot import bot

# ===== ВНУТРЕННИЕ =====

basic_router = Router()


import logging

logger = logging.getLogger(__name__)

@basic_router.message(
    F.from_user.id != F.bot.id,
    F.chat.type == "private",
)
async def dispatch_user_message(message: Message):
    user_txt = message.text or ""
    logger.info(f"🔹 New message from {message.from_user.id}: {user_txt!r}")

    # ---------- Stage 1: определение функции ----------------------------------
    prompt1 = PROMPTS["function_detection"].format(
        user_message=user_txt,
        # function_spec=json.dumps(FUNCTION_MAP, ensure_ascii=False, indent=2),
        function_spec = "\n".join(f"- {k}: {v['description']}" for k, v in FUNCTION_MAP.items())
    )
    bundle1 = build_messages_for_model(prompt1, [], "", "gpt-3.5-turbo")
    resp1 = await chat_generate_any(
        "gpt-3.5-turbo",
        bundle1["messages"],
        temperature=0.0,
        system_instruction=bundle1.get("system_instruction"),
    )
    parsed1 = extract_json_from_response(resp1, model="gpt") or {}
    func_name = parsed1.get("function", "none")
    hint1 = parsed1.get("hint", "")
    logger.info(f"🧠 Detected function: {func_name!r}; hint={hint1!r}")

    if func_name == "none":
        await message.answer(
            hint1 or "❌ Не смог распознать действие.",
            parse_mode=ParseMode.HTML,
            show_alert=True,
        )
        return

    handler_name = f"handle_{func_name}"
    handler = globals().get(handler_name)
    if not (callable(handler) and func_name in FUNCTION_MAP):
        logger.warning(f"❌ Unknown or unsupported function: {func_name}")
        await message.answer(
            hint1 or "❌ Действие не поддерживается.",
            parse_mode=ParseMode.HTML,
            show_alert=True,
        )
        return

    # ---------- Stage 2: генерация аргументов ---------------------------------
    bot_ctx = await get_bot_context()
    subs = await Subscription.filter(user__telegram_id=message.from_user.id).prefetch_related("channel")
    user_ctx = {"subscriptions": [s.channel.title for s in subs]}

    func_meta = FUNCTION_MAP[func_name]
    prompt2 = PROMPTS["args_generation"].format(
        function_name=func_name,
        function_description=func_meta["description"],
        params_schema=json.dumps(func_meta["params_schema"], ensure_ascii=False, indent=2),
        user_context=json.dumps(user_ctx, ensure_ascii=False),
        user_message=user_txt,
    )
    bundle2 = build_messages_for_model(prompt2, [], "", bot_ctx["ai_model"])
    resp2 = await chat_generate_any(
        model_name=bot_ctx["ai_model"],
        messages=bundle2["messages"],
        temperature=bot_ctx["temperature"],
        system_instruction=bundle2.get("system_instruction"),
    )
    parsed2 = extract_json_from_response(resp2, model=bot_ctx["ai_model"]) or {}
    args = parsed2.get("args")
    hint2 = parsed2.get("hint", "")
    logger.info(f"📦 Args for {func_name}: {args}; hint={hint2!r}")

    if not args:
        await message.answer(
            hint2 or "❗ Недостаточно данных для выполнения запроса.",
            parse_mode=ParseMode.HTML,
            show_alert=True,
        )
        return

    # ---------- Вызов выбранной функции ---------------------------------------
    try:
        ok = await handler(message, args)
        if not ok:
            logger.warning(f"⛔ Handler returned False: {func_name}")
            await message.answer(
                hint2 or "⛔ Не удалось выполнить действие.",
                parse_mode=ParseMode.HTML,
                show_alert=True,
            )
    except Exception as e:
        logger.exception(f"⚠️ Exception in handler {func_name}: {e}")
        await message.answer(
            "⚠️ Произошла внутренняя ошибка.",
            parse_mode=ParseMode.HTML,
            show_alert=True,
        )



# ===== ВНЕШНИЕ =====

async def send_message(request: web.Request) -> web.Response:
    """Отправляет text (+ optional topic) в чат."""
    client_ip = request.headers.get("X-Real-IP", request.remote)
    allowed = bot_settings.WEBHOOK_ALLOWED_IPS
    if allowed and client_ip not in allowed:
        raise HTTPException(status_code=403, detail="Forbidden IP")

    payload = await request.json()
    chat_id = payload.get("chat_id")
    text = payload.get("text")
    parse_mode = payload.get("parse_mode")
    thread_id = payload.get("message_thread_id")

    if not chat_id or not text:
        raise HTTPException(status_code=400, detail="Invalid payload")

    kwargs = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if thread_id:
        kwargs["message_thread_id"] = thread_id

    await bot.send_message(**kwargs)
    return web.json_response({"status": "ok"})
