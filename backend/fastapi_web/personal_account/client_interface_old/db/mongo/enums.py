"""Енам приложения Клиентский интерфейс для работы с БД MongoDB."""
import json
from enum import Enum


class GenderEnum(str, Enum):
    """Пол с переводами."""
    MALE = json.dumps({"en": "Male", "ru": "Мужской"})
    FEMALE = json.dumps({"en": "Female", "ru": "Женский"})
    OTHER = json.dumps({"en": "Other", "ru": "Другой"})


class AppointmentStatusEnum(str, Enum):
    """Возможные статусы визита."""
    SCHEDULED = json.dumps({"en": "Scheduled", "ru": "Запланирован"})
    COMPLETED = json.dumps({"en": "Completed", "ru": "Завершен"})
    CANCELED = json.dumps({"en": "Canceled", "ru": "Отменен"})
    RESCHEDULED = json.dumps({"en": "Rescheduled", "ru": "Перенесен"})


class SubscriptionStatusEnum(str, Enum):
    """Статусы подписки."""
    FREE = json.dumps({"en": "Free", "ru": "Бесплатная"})
    PREMIUM = json.dumps({"en": "Premium", "ru": "Премиум"})
    EXPIRED = json.dumps({"en": "Expired", "ru": "Истекшая"})


class NotificationTypeEnum(str, Enum):
    REMINDER = '{"en":"Reminder","ru":"Напоминание"}'
    BONUS = '{"en":"Bonus update","ru":"Бонусы"}'
    MEDICAL = '{"en":"Medical notice","ru":"Медицинское уведомление"}'
    OTHER = '{"en":"Other","ru":"Прочее"}'


class LanguageEnum(str, Enum):
    RU = "RU"
    EN = "EN"
    PL = "PL"
