"""Енам приложения Клиентский интерфейс для работы с БД MongoDB."""
import json
from enum import Enum

from db.mongo.base.enums import BaseJsonEnumMixin

# ==========
# Основная информация
# ==========


class GenderEnum(BaseJsonEnumMixin, str, Enum):
    MALE = json.dumps({
        "ru": "мужской",
        "en": "male",
        "pl": "mężczyzna",
        "settings": {}
    })
    FEMALE = json.dumps({
        "ru": "женский",
        "en": "female",
        "pl": "kobieta",
        "settings": {}
    })


class AccountVerificationEnum(BaseJsonEnumMixin, str, Enum):
    UNVERIFIED = json.dumps({
        "ru": "не верифицирован",
        "en": "unverified",
        "pl": "niezweryfikowany",
        "settings": {}
    })
    VERIFIED = json.dumps({
        "ru": "верифицирован",
        "en": "verified",
        "pl": "zweryfikowany",
        "settings": {}
    })


# ==========
# Анкета здоровья
# ==========


class ConditionEnum(str, Enum):
    """
    Хронические заболевания без цветов (цвета задаются отдельно в color_map).
    """
    DIABETES = json.dumps({"en": "Diabetes", "ru": "Диабет"})
    ASTHMA = json.dumps({"en": "Asthma", "ru": "Астма"})
    HYPERTENSION = json.dumps({"en": "Hypertension", "ru": "Гипертония"})
    CANCER = json.dumps({"en": "Cancer", "ru": "Рак"})
    ARTHRITIS = json.dumps({"en": "Arthritis", "ru": "Артрит"})
    COPD = json.dumps(
        {"en": "Chronic Obstructive Pulmonary Disease", "ru": "ХОБЛ"})
    DEPRESSION = json.dumps({"en": "Depression", "ru": "Депрессия"})
    ANXIETY = json.dumps({"en": "Anxiety", "ru": "Тревожность"})
    CHRONIC_KIDNEY_DISEASE = json.dumps(
        {"en": "Chronic Kidney Disease", "ru": "Хроническая болезнь почек"})
    LIVER_DISEASE = json.dumps({"en": "Liver Disease", "ru": "Болезнь печени"})
    MIGRAINE = json.dumps({"en": "Migraine", "ru": "Мигрень"})
    OSTEOPOROSIS = json.dumps({"en": "Osteoporosis", "ru": "Остеопороз"})
    THYROID_DISORDER = json.dumps(
        {"en": "Thyroid Disorder", "ru": "Заболевание щитовидной железы"})
    EPILEPSY = json.dumps({"en": "Epilepsy", "ru": "Эпилепсия"})


class HealthFormStatus(str, Enum):
    """
    Статусы анкеты (одобрена, ожидает, отклонена).
    Цвета — в HEX-кодах.
    """
    APPROVED = json.dumps({
        "en": "Approved",
        "ru": "Одобрена",
        "pl": "Zatwierdzona",
        "settings": {
            "color": "#4CAF50"
        }
    })
    PENDING = json.dumps({
        "en": "Pending",
        "ru": "Ожидает",
        "pl": "Oczekuje",
        "settings": {
            "color": "#FFA000"
        }
    })
    REJECTED = json.dumps({
        "en": "Rejected",
        "ru": "Отклонена",
        "pl": "Odrzucona",
        "settings": {
            "color": "#F44336"
        }
    })


# ==========
# Семья
# ==========


class RelationshipEnum(BaseJsonEnumMixin, str, Enum):
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


class FamilyStatusEnum(BaseJsonEnumMixin, str, Enum):
    PENDING = json.dumps({
        "en": "Pending",
        "ru": "В ожидании",
        "pl": "Oczekuje"
    })
    CONFIRMED = json.dumps({
        "en": "Confirmed",
        "ru": "Подтверждено",
        "pl": "Potwierdzony"
    })


# ==========
# Бонусная программа
# ==========


class TransactionTypeEnum(BaseJsonEnumMixin, str, Enum):
    ACCRUED = json.dumps({
        "en": "Accrued",
        "ru": "Начислено",
        "pl": "Dodane",
        "settings": {
            "color": "#43A047"
        }
    })
    REDEEMED = json.dumps({
        "en": "Redeemed",
        "ru": "Списано",
        "pl": "Wykorzystane",
        "settings": {
            "color": "#E53935"
        }
    })


# ==========
# Согласия
# ==========

class ConsentEnum(BaseJsonEnumMixin, str, Enum):
    GDPR = json.dumps({
        "en": "GDPR Consent",
        "ru": "Согласие на обработку персональных данных (GDPR)",
        "pl": "Zgoda na przetwarzanie danych (GDPR)"
    })
    PRIVACY = json.dumps({
        "en": "Privacy Policy",
        "ru": "Согласие с политикой конфиденциальности",
        "pl": "Zgoda na politykę prywatności"
    })
    TERMS = json.dumps({
        "en": "Terms of Use",
        "ru": "Согласие с условиями использования",
        "pl": "Zgoda na warunki korzystania"
    })
    COOKIES = json.dumps({
        "en": "Cookies",
        "ru": "Согласие на использование cookies",
        "pl": "Zgoda na pliki cookie"
    })
    EMAIL = json.dumps({
        "en": "Email Marketing",
        "ru": "Согласие на email-маркетинг",
        "pl": "Zgoda na email marketing"
    })
    SMS = json.dumps({
        "en": "SMS Marketing",
        "ru": "Согласие на SMS-маркетинг",
        "pl": "Zgoda na marketing SMS"
    })
    PERSONALIZATION = json.dumps({
        "en": "Personalization",
        "ru": "Согласие на персонализацию",
        "pl": "Zgoda na personalizację"
    })

# ==========
# Встречи
# ==========
