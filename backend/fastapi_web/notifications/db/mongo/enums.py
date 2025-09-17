# db/mongo/apps/notifications/enums.py
import json
from enum import Enum
from db.mongo.base.enums import BaseJsonEnumMixin


class Priority(BaseJsonEnumMixin, str, Enum):
    LOW = json.dumps(
        {"en": "Low", "pl": "Niski", "uk": "Низький", "ru": "Низкий", "ka": "დაბალი"}
    )
    NORMAL = json.dumps(
        {"en": "Normal", "pl": "Normalny", "uk": "Звичайний", "ru": "Обычный", "ka": "ჩვეულებრივი"}
    )
    HIGH = json.dumps(
        {"en": "High", "pl": "Wysoki", "uk": "Високий", "ru": "Высокий", "ka": "მაღალი"}
    )
    CRITICAL = json.dumps(
        {"en": "Critical", "pl": "Krytyczny", "uk": "Критичний", "ru": "Критичный", "ka": "კრიტიკული"}
    )


class NotificationChannel(BaseJsonEnumMixin, str, Enum):
    """Куда доставляем/отображаем уведомление."""
    WEB = json.dumps(
        {"en": "Web (in-app)", "pl": "Web (w systemie)", "uk": "Web (у системі)", "ru": "Web (в системе)", "ka": "Web (სისტემაში)"}
    )
    TELEGRAM = json.dumps(
        {"en": "Telegram", "pl": "Telegram", "uk": "Telegram", "ru": "Telegram", "ka": "ტელეგრამი"}
    )
    WEB_PUSH = json.dumps(
        {"en": "Web Push", "pl": "Web Push", "uk": "Web Push", "ru": "Web Push", "ka": "Web Push"}
    )
    WINDOWS_NOTIFICATION = json.dumps(
        {
            "en": "Windows Notify",
            "pl": "Powiadomienie Windows",
            "uk": "Сповіщення Windows",
            "ru": "Windows уведомление",
            "ka": "Windows შეტყობინება",
        }
    )
    EMAIL = json.dumps(
        {"en": "Email", "pl": "Email", "uk": "Email", "ru": "Email", "ka": "ელფოსტა"}
    )
