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
    """Статусы чатов (взаимоисключающие)."""

    # --- Старт чата ---
    NEW_SESSION = json.dumps({
        "en": "New Session", "ru": "Новая сессия",
        "settings": {"color": "#17a2b8", "icon": "pi pi-comment"}
    })

    # --- Брифинг ---
    BRIEF_IN_PROGRESS = json.dumps({
        "en": "Brief In Progress", "ru": "Заполняется бриф",
        "settings": {"color": "#6c757d", "icon": "pi pi-list"}
    })
    BRIEF_COMPLETED = json.dumps({
        "en": "Brief Completed", "ru": "Бриф заполнен",
        "settings": {"color": "#20c997", "icon": "pi pi-check-circle"}
    })

    # --- Автоматический режим ---
    AUTO_WAITING_AI = json.dumps({
        "en": "Waiting for AI", "ru": "Ожидает ИИ",
        "settings": {"color": "#6f42c1", "icon": "pi pi-spin pi-cog"}
    })
    AUTO_WAITING_CLIENT = json.dumps({
        "en": "Waiting for Client", "ru": "Ожидает клиента",
        "settings": {"color": "#0d6efd", "icon": "pi pi-reply"}
    })

    # --- Ручной режим ---
    MANUAL_WAITING_CONSULTANT = json.dumps({
        "en": "Waiting for Consultant", "ru": "Ожидает консультанта",
        "settings": {"color": "#dc3545", "icon": "pi pi-user-clock"}
    })
    MANUAL_READ_BY_CONSULTANT = json.dumps({
        "en": "Read by Consultant", "ru": "Прочитано консультантом",
        "settings": {"color": "#ffc107", "icon": "pi pi-eye"}
    })
    MANUAL_WAITING_CLIENT = json.dumps({
        "en": "Waiting for Client", "ru": "Ожидает клиента",
        "settings": {"color": "#198754", "icon": "pi pi-user-check"}
    })

    # --- Завершённые ---
    CLOSED_NO_MESSAGES = json.dumps({
        "en": "Closed – No Messages", "ru": "Закрыт без сообщений",
        "settings": {"color": "#adb5bd", "icon": "pi pi-times"}
    })
    CLOSED_BY_TIMEOUT = json.dumps({
        "en": "Closed by Timeout", "ru": "Закрыт по таймауту",
        "settings": {"color": "#6c757d", "icon": "pi pi-clock"}
    })
    CLOSED_BY_OPERATOR = json.dumps({
        "en": "Closed by Operator", "ru": "Закрыт оператором",
        "settings": {"color": "#28a745", "icon": "pi pi-lock"}
    })



class ChatSource(BaseJsonEnumMixin, str, Enum):
    """Источник чата (откуда начался диалог)."""

    INTERNAL = json.dumps({"en": "Internal", "ru": "Внутренний"})
    INSTAGRAM = json.dumps({"en": "Instagram", "ru": "Инстаграм"})
    FACEBOOK = json.dumps({"en": "Facebook", "ru": "Фейсбук"})
    WHATSAPP = json.dumps({"en": "WhatsApp", "ru": "Вотсап"})
    TELEGRAM = json.dumps({"en": "Telegram", "ru": "Телеграм"})
    TELEGRAM_MINI_APP = json.dumps(
        {"en": "Telegram Mini-App", "ru": "Телеграм-мини-апп"})
