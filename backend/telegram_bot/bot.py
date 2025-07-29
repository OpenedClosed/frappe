"""Файл запуска бота."""
import asyncio
import logging
import sys
from pathlib import Path

from telegram_bot.infra.states import MainMenu

sys.path.append(str(Path(__file__).resolve().parent.parent))

from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiogram.types import MenuButtonWebApp, WebAppInfo, Message
from aiogram.filters import Command, CommandObject
from aiogram.enums import ParseMode

from telegram_bot.utils.translations import BOT_TRANSLATIONS
from telegram_bot.utils.decorators import check_private_chat
from telegram_bot.apps.chats.routers import send_message
from telegram_bot.apps.chats.handlers import relay_router
from telegram_bot.infra.create_bot import bot, dp
from fastapi_web.infra import settings as backend_settings
from telegram_bot.apps.main_menu.dialogs import main_menu_dialog
from telegram_bot.apps.personal_account.dialogs import personal_account_dialog
from telegram_bot.utils.help_functions import generate_secure_webapp_url, set_menu_webapp_for_user
import logging
from aiogram_dialog import DialogManager, StartMode, setup_dialogs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Роутеры и диалоги
dp.include_router(relay_router)

dp.include_router(main_menu_dialog)
dp.include_router(personal_account_dialog)

setup_dialogs(dp)

@dp.startup()
async def on_startup(*args, **kwargs):
    pass


@dp.shutdown()
async def on_shutdown(*args, **kwargs):
    pass


@dp.message(Command("start"))
@check_private_chat
async def start(message: Message, command: CommandObject, dialog_manager: DialogManager):
    """
    Обработчик команды '/start'.
    """
    user_lang = message.from_user.language_code
    # start_text = BOT_TRANSLATIONS["start_info_text"].get(
    #     user_lang, BOT_TRANSLATIONS["start_info_text"]["en"]
    # )
    url = await generate_secure_webapp_url(message.from_user, message.bot)
    # await message.answer(start_text, parse_mode=ParseMode.HTML)
    await set_menu_webapp_for_user(message.from_user, message.bot)
    await dialog_manager.start(MainMenu.START, mode=StartMode.RESET_STACK)



@dp.message(Command("help"))
@check_private_chat
async def help(message: Message, command: CommandObject):
    """
    Обработчик команды '/help'.
    """
    user_lang = message.from_user.language_code
    help_text = BOT_TRANSLATIONS["help_info_text"].get(
        user_lang, BOT_TRANSLATIONS["help_info_text"]["en"]
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)


async def main():
    """
    Основная функция запуска Telegram-бота с веб-сервером для Webhook.
    """
    aiohttp_app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    ).register(aiohttp_app, path="/webhook")

    aiohttp_app.router.add_post("/webhook/send_message", send_message)

    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=9999)
    await site.start()

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Работа бота остановлена с клавиатуры.")
    except Exception as e:
        logging.error(f"Ошибка при запуске: {e}")
