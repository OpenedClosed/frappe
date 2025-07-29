"""Диалоги Главного меню."""
from aiogram.enums import ParseMode
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Const, Format

from .getters import get_main_menu_text
from telegram_bot.apps.basic.handlers import sub_dialog_starter
from telegram_bot.infra.states import MainMenu
from telegram_bot.utils.messages import ButtonMessage, InfoMessage

main_menu_dialog = Dialog(
    Window(
        Format("{msg_main_menu}"),
        Button(
            Format("{btn_personal}"),
            id="PersonalAccount",
            on_click=sub_dialog_starter,
        ),
        getter=get_main_menu_text,
        state=MainMenu.START,
        parse_mode=ParseMode.HTML,
    )
)