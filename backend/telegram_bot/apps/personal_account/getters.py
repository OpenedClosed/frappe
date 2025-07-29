from telegram_bot.utils.help_functions import tr
from aiogram_dialog import DialogManager

async def get_pa_texts(dialog_manager: DialogManager, **_):
    lang = dialog_manager.event.from_user.language_code or "en"
    return {
        "title":   tr("cabinet_info_text", lang),
        "go_main": tr("buttons", lang, "go_main_page"),
        "go_app":  tr("buttons", lang, "go_appointments"),
        "go_sup":  tr("buttons", lang, "go_support"),
    }
