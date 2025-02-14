"""Файл запуска бота."""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.decorators import check_private_chat
from chats.routers import send_message
from bot_conf.create_bot import bot, dp
from fastapi_web.infra import settings
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiogram.types import MenuButtonWebApp, Message, WebAppInfo
from aiogram.filters import Command, CommandObject
from aiogram.enums import ParseMode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@dp.startup()
async def on_startup(*args, **kwargs):
    pass


@dp.shutdown()
async def on_shutdown(*args, **kwargs):
    pass


@dp.message(Command("start"))
@check_private_chat
async def start(message: Message, command: CommandObject):
    """Обработчик команды '/start'."""
    info_text = """
👋 Welcome to the <b>Nika Hotel AI Assistant</b>! 🏡✨

▶️ Press the 💬 button to start chatting with your hotel assistant.
<b>With this bot, you can:</b>
    - Check availability and book a stay 🏷
    - Get details about hotel amenities and services 🛎
    - Ask about transfers, meals, and local attractions 🚗🍽🏞
    - Receive personalized recommendations 📌

ℹ️ Use /help command to see additional features.
"""
    await message.answer(info_text, parse_mode=ParseMode.HTML)



@dp.message(Command("help"))
@check_private_chat
async def help(message: Message, command: CommandObject):
    """Обработчик команды '/help'."""
    help_text = """
ℹ️ <b>How to Use Nika Hotel AI Assistant</b> 🏡

This bot is your **personal assistant** for everything related to <b>Nika Hotel & Club</b>.  
Here’s what you can do:
1. 📋 <b>Interactive Menu:</b> Tap the 💬 button at the bottom of this chat  
   to open the assistant’s interface.
2. 💬 <b>Chat with the AI Assistant:</b> Ask any questions about our hotel,  
   including bookings, amenities, pricing, transfers, and activities.
3. 📆 <b>Plan Your Stay:</b> Get personalized recommendations for your visit.
4. 🌍 <b>Explore Attractions:</b> Learn about things to do near the hotel.

Need human assistance? Our team is ready to help! 🛎
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)



async def main():
    """
    Основная функция запуска Telegram-бота с веб-сервером для Webhook.
    """
    aiohttp_app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot).register(
        aiohttp_app,
        path="/webhook")
    aiohttp_app.router.add_post("/webhook/send_message", send_message)


    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=9999)
    await site.start()

    web_app_url = f"{settings.FRONTEND_URL}/telegram-chat"
    web_app_url = "https://hotel-aihub.su/telegram-chat"

    web_app_info = WebAppInfo(url=web_app_url)
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="💬", web_app=web_app_info))
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Работа бота остановлена с клавиатуры.")
    except Exception as e:
        logging.error(f"Ошибка при запуске: {e}")
