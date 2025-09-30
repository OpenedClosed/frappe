from telegram_bot.utils.help_functions import tr
from aiogram_dialog import DialogManager

async def get_main_menu_text(dialog_manager: DialogManager, **_):
    lang = dialog_manager.event.from_user.language_code or "en"
    return {
        "msg_main_menu": tr("start_info_text", lang),  # key не нужен
        "btn_personal": tr("buttons", lang, "personal_account"),  # key нужен
    }
