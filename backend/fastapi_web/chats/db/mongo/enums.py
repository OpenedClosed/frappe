"""Енам приложения Чаты для работы с БД MongoDB."""
from enum import Enum


class SenderRole(str, Enum):
    CLIENT = "client"
    AI = "ai"
    CONSULTANT = "consultant"


class ChatStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SUCCESSFULLY_CLOSED = "successfully_closed"
    CLOSED_WITHOUT_RESPONSE = "closed_without_response"
    FORCED_CLOSED = "forced_closed"


class ChatSource(str, Enum):
    """Источник чата."""
    INTERNAL = "internal"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    WHATSAPP = "whatsapp"
