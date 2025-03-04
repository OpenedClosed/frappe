"""Файл запуска бота."""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import MenuButtonWebApp, Message, WebAppInfo
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
from bot_conf.create_bot import bot, dp
from chats.routers import send_message
from fastapi_web.infra import settings
from utils.decorators import check_private_chat
from utils.translations import BOT_TRANSLATIONS

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
    """
    Обработчик команды '/start' для PaNa Medica AI Assistant.
    """
    user_lang = message.from_user.language_code
    start_text = BOT_TRANSLATIONS["start_info_text"].get(
        user_lang, BOT_TRANSLATIONS["start_info_text"]["en"])
    await message.answer(start_text, parse_mode=ParseMode.HTML)


@dp.message(Command("help"))
@check_private_chat
async def help(message: Message, command: CommandObject):
    """
    Обработчик команды '/help' для PaNa Medica AI Assistant.
    """
    user_lang = message.from_user.language_code
    help_text = BOT_TRANSLATIONS["help_info_text"].get(
        user_lang, BOT_TRANSLATIONS["help_info_text"]["en"])
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
    web_app_url = "https://panamed-aihubworks.com/chats/telegram-chat"

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
