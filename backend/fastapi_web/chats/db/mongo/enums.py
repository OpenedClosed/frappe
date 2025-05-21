"""Енам приложения Чаты для работы с БД MongoDB."""
import json
from enum import Enum

from db.mongo.base.enums import BaseJsonEnumMixin


class SenderRole(BaseJsonEnumMixin, str, Enum):
    """Роль отправителя в чате."""
    CLIENT = json.dumps({"en": "Client", "ru": "Клиент"})
    AI = json.dumps({"en": "AI Assistant", "ru": "ИИ-помощник"})
    CONSULTANT = json.dumps({"en": "Consultant", "ru": "Консультант"})


class ChatStatus(BaseJsonEnumMixin, str, Enum):
    """Статусы чатов с возможностью визуального выделения."""

    IN_PROGRESS = json.dumps({
        "en": "In Progress", "ru": "В процессе",
        "settings": {"color": "#FFA500", "icon": "pi pi-spin pi-spinner"}
    })

    SUCCESSFULLY_CLOSED = json.dumps({
        "en": "Successfully Closed", "ru": "Закрыт успешно",
        "settings": {"color": "#28a745", "icon": "pi pi-check"}
    })

    CLOSED_WITHOUT_RESPONSE = json.dumps({
        "en": "Closed Without Response", "ru": "Закрыт без ответа",
        "settings": {"color": "#dc3545", "icon": "pi pi-times"}
    })

    FORCED_CLOSED = json.dumps({
        "en": "Forced Closed", "ru": "Принудительно закрыт",
        "settings": {"color": "#6c757d", "icon": "pi pi-lock"}
    })


class ChatSource(BaseJsonEnumMixin, str, Enum):
    """Источник чата (откуда начался диалог)."""

    INTERNAL = json.dumps({"en": "Internal", "ru": "Внутренний"})
    INSTAGRAM = json.dumps({"en": "Instagram", "ru": "Инстаграм"})
    FACEBOOK = json.dumps({"en": "Facebook", "ru": "Фейсбук"})
    WHATSAPP = json.dumps({"en": "WhatsApp", "ru": "Вотсап"})

