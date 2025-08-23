from aiogram.enums import ParseMode
from aiogram_dialog import Dialog, Window
from .getters import get_pa_texts
from telegram_bot.infra.states import PersonalAccount
from telegram_bot.utils.widgets import WebAppUrl
from telegram_bot.utils.messages import InfoMessage, ButtonMessage
from aiogram_dialog.widgets.text import Const, Format
from fastapi_web.infra import settings as backend_settings

MINI_APP_HOST = backend_settings.HOST if backend_settings.HOST not in ["localhost", "127.0.0.1"] else "portal.pa-na.pl"

personal_account_dialog = Dialog(
    Window(
        Format("{title}"),
        WebAppUrl(
            text=Format("{go_main}"),
            url=Const(f"https://{MINI_APP_HOST}/personal_account"),
            service=Const("telegram_mini_app"),
            id="go_main",
        ),
        WebAppUrl(
            text=Format("{go_app}"),
            url=Const(f"https://{MINI_APP_HOST}/personal_account/client_interface/crm_appointments"),
            service=Const("telegram_mini_app"),
            id="go_appointments",
        ),
        WebAppUrl(
            text=Format("{go_sup}"),
            url=Const(f"https://{MINI_APP_HOST}/personal_account/support/support"),
            service=Const("telegram_mini_app"),
            id="go_support",
        ),
        getter=get_pa_texts,
        state=PersonalAccount.START,
        parse_mode=ParseMode.HTML,
    )
)