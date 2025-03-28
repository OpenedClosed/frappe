"""Енам приложения Клиентский интерфейс для работы с БД MongoDB."""
import json
from enum import Enum

from db.mongo.base.enums import BaseJsonEnumMixin


# ==========
# Основная информация
# ==========


class GenderEnum(BaseJsonEnumMixin, str, Enum):
    MALE = json.dumps({
        "ru": "Мужской",
        "en": "Male",
        "pl": "Mężczyzna",
        "settings": {}
    })
    FEMALE = json.dumps({
        "ru": "Женский",
        "en": "Female",
        "pl": "Kobieta",
        "settings": {}
    })









class ConditionEnum(str, Enum):
    """
    Хронические заболевания:
    Храним перевод (ru/en) и цвет в отдельном блоке settings.
    """
    DIABETES = json.dumps({
        "en": "Diabetes",
        "ru": "Диабет",
        "settings": {
            "color": "#E53935"
        }
    })
    ASTHMA = json.dumps({
        "en": "Asthma",
        "ru": "Астма",
        "settings": {
            "color": "#E53935"
        }
    })
    HYPERTENSION = json.dumps({
        "en": "Hypertension",
        "ru": "Гипертония",
        "settings": {
            "color": "#43A047"
        }
    })
    OTHER = json.dumps({
        "en": "Other",
        "ru": "Другое",
        "settings": {
            "color": "#43A047"
        }
    })


class HealthFormStatus(str, Enum):
    """
    Статусы анкеты (одобрена, ожидает, отклонена).
    Аналогично, у каждого статуса свой цвет в settings.
    """
    APPROVED = json.dumps({
        "en": "Approved",
        "ru": "Одобрена",
        "settings": {
            "color": "green"
        }
    })
    PENDING = json.dumps({
        "en": "Pending",
        "ru": "Ожидает",
        "settings": {
            "color": "orange"
        }
    })
    REJECTED = json.dumps({
        "en": "Rejected",
        "ru": "Отклонена",
        "settings": {
            "color": "red"
        }
    })

class RelationshipEnum(str, Enum):
    SPOUSE = json.dumps({
        "en": "Spouse",
        "ru": "Супруг(а)",
        "settings": {
            "color": "#8E24AA"
        }
    })
    CHILD = json.dumps({
        "en": "Child",
        "ru": "Ребёнок",
        "settings": {
            "color": "#1E88E5"
        }
    })
    OTHER = json.dumps({
        "en": "Other",
        "ru": "Другое",
        "settings": {
            "color": "#757575"
        }
    })





class TransactionTypeEnum(str, Enum):
    # Два варианта: начислено (accrual) или потрачено (spent).
    # В JSON храним перевод и цвет в settings.
    ACCRUED = json.dumps({
        "en": "Accrued",
        "ru": "Начислено",
        "settings": {
            "color": "green"
        }
    })
    SPENT = json.dumps({
        "en": "Spent",
        "ru": "Потрачено",
        "settings": {
            "color": "red"
        }
    })




class ConsentEnum(str, Enum):
    GDPR = json.dumps({
        "en": "Consent to process personal data (GDPR)",
        "ru": "Согласие на обработку персональных данных (GDPR)",
        "settings": {
            "color": "green"  # или по умолчанию "green" (если принято)
        }
    })
    PRIVACY_POLICY = json.dumps({
        "en": "Consent to the privacy policy",
        "ru": "Согласие с политикой конфиденциальности",
        "settings": {
            "color": "green"
        }
    })
    TERMS_OF_USE = json.dumps({
        "en": "Consent to terms of use",
        "ru": "Согласие с условиями использования",
        "settings": {
            "color": "green"
        }
    })
    COOKIES = json.dumps({
        "en": "Consent to cookies usage",
        "ru": "Согласие на использование cookies",
        "settings": {
            "color": "green"
        }
    })
    EMAIL_MARKETING = json.dumps({
        "en": "Consent to email marketing",
        "ru": "Согласие на email-маркетинг",
        "settings": {
            "color": "green"
        }
    })
    SMS_MARKETING = json.dumps({
        "en": "Consent to SMS marketing",
        "ru": "Согласие на SMS-маркетинг",
        "settings": {
            "color": "green"
        }
    })
    PERSONALIZATION = json.dumps({
        "en": "Consent to personalization",
        "ru": "Согласие на персонализацию",
        "settings": {
            "color": "green"
        }
    }) 