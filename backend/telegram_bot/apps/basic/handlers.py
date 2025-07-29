"""Базовые функции-обработчики."""
import importlib
import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from telegram_bot.infra.create_bot import bot

logger = logging.getLogger(__name__)


async def delete_keboard_messages(dialog_manager: DialogManager, chat_id: int):
    """Удаление сообщений с inline-клавиатурами (по сохранённым id)."""
    keyboard_message_ids = []

    if dialog_manager.start_data:
        keyboard_message_ids += dialog_manager.start_data.get("keyboard_message_ids", [])

    if dialog_manager.dialog_data:
        keyboard_message_ids += dialog_manager.dialog_data.get("keyboard_message_ids", [])

    for msg_id in keyboard_message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            logger.warning("⚠️ Невозможно удалить сообщение с id=%s", msg_id)


async def process_stub(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Заглушка — функция пока не реализована."""
    # await callback.message.answer(InfoMessage.UNDER_DEVELOPMENT)
    pass


async def go_back(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Откат на предыдущий шаг."""
    # await delete_old_info(callback)
    # await delete_keboard_messages(dialog_manager, callback.message.chat.id)
    await dialog_manager.back()


async def go_next(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Переход к следующему шагу."""
    # await delete_old_info(callback)
    # await delete_keboard_messages(dialog_manager, callback.message.chat.id)
    await dialog_manager.next()


def str_to_class(classname: str):
    """Получить класс состояния из telegram_bot.infra.states по имени."""
    module = importlib.import_module("telegram_bot.infra.states")
    return getattr(module, classname)


async def sub_dialog_starter(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    """Старт вложенного диалога по имени класса."""
    data = dialog_manager.dialog_data
    sub_dialog = str_to_class(callback.data)
    # await delete_old_info(callback)
    # await delete_keboard_messages(dialog_manager, callback.message.chat.id)
    await dialog_manager.start(sub_dialog.START, data=data)


async def sub_dialog_step_starter(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    """Старт вложенного диалога с конкретного шага."""
    data = dialog_manager.dialog_data
    dialog_key = callback.data
    dialog_name, step = dialog_key.split("__")
    sub_dialog = str_to_class(dialog_name)
    # await delete_old_info(callback)
    # await delete_keboard_messages(dialog_manager, callback.message.chat.id)
    await dialog_manager.start(getattr(sub_dialog, step), data=data)


async def close_subdialog(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Завершение поддиалога."""
    # await delete_old_info(callback)
    # await delete_keboard_messages(dialog_manager, callback.message.chat.id)
    await dialog_manager.done()
