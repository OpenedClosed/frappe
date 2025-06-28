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
        "uk": "чоловіча",
        "de": "männlich",
        "settings": {}
    })
    FEMALE = json.dumps({
        "ru": "женский",
        "en": "female",
        "pl": "kobieta",
        "uk": "жіноча",
        "de": "weiblich",
        "settings": {}
    })


class AccountVerificationEnum(BaseJsonEnumMixin, str, Enum):
    UNVERIFIED = json.dumps({
        "ru": "не верифицирован",
        "en": "unverified",
        "pl": "niezweryfikowany",
        "uk": "невіріфіковано",
        "de": "nicht verifiziert",
        "settings": {}
    })
    VERIFIED = json.dumps({
        "ru": "верифицирован",
        "en": "verified",
        "pl": "zweryfikowany",
        "uk": "верифіковано",
        "de": "verifiziert",
        "settings": {}
    })


# ==========
# Анкета здоровья
# ==========


class ConditionEnum(str, Enum):
    """
    Хронические заболевания без цветов (цвета задаются отдельно в color_map).
    """
    DIABETES = json.dumps({
        "en": "Diabetes",
        "ru": "Диабет",
        "pl": "Cukrzyca",
        "uk": "Цукровий діабет",
        "de": "Diabetes"
    })
    ASTHMA = json.dumps({
        "en": "Asthma",
        "ru": "Астма",
        "pl": "Astma",
        "uk": "Астма",
        "de": "Asthma"
    })
    HYPERTENSION = json.dumps({
        "en": "Hypertension",
        "ru": "Гипертония",
        "pl": "Nadciśnienie",
        "uk": "Гіпертонія",
        "de": "Hypertonie"
    })
    CANCER = json.dumps({
        "en": "Cancer",
        "ru": "Рак",
        "pl": "Rak",
        "uk": "Рак",
        "de": "Krebs"
    })
    ARTHRITIS = json.dumps({
        "en": "Arthritis",
        "ru": "Артрит",
        "pl": "Artretyzm",
        "uk": "Артрит",
        "de": "Arthritis"
    })
    COPD = json.dumps({
        "en": "Chronic Obstructive Pulmonary Disease",
        "ru": "ХОБЛ",
        "pl": "POChP",
        "uk": "ХОЗЛ",
        "de": "COPD"
    })
    DEPRESSION = json.dumps({
        "en": "Depression",
        "ru": "Депрессия",
        "pl": "Depresja",
        "uk": "Депресія",
        "de": "Depression"
    })
    ANXIETY = json.dumps({
        "en": "Anxiety",
        "ru": "Тревожность",
        "pl": "Lęk",
        "uk": "Тривожність",
        "de": "Angst"
    })
    CHRONIC_KIDNEY_DISEASE = json.dumps({
        "en": "Chronic Kidney Disease",
        "ru": "Хроническая болезнь почек",
        "pl": "Przewlekła choroba nerek",
        "uk": "Хронічна хвороба нирок",
        "de": "Chronische Nierenerkrankung"
    })
    LIVER_DISEASE = json.dumps({
        "en": "Liver Disease",
        "ru": "Болезнь печени",
        "pl": "Choroba wątroby",
        "uk": "Хвороба печінки",
        "de": "Lebererkrankung"
    })
    MIGRAINE = json.dumps({
        "en": "Migraine",
        "ru": "Мигрень",
        "pl": "Migrena",
        "uk": "Мігрень",
        "de": "Migräne"
    })
    OSTEOPOROSIS = json.dumps({
        "en": "Osteoporosis",
        "ru": "Остеопороз",
        "pl": "Osteoporoza",
        "uk": "Остеопороз",
        "de": "Osteoporose"
    })
    THYROID_DISORDER = json.dumps({
        "en": "Thyroid Disorder",
        "ru": "Заболевание щитовидной железы",
        "pl": "Zaburzenie tarczycy",
        "uk": "Порушення щитоподібної залози",
        "de": "Schilddrüsenerkrankung"
    })
    EPILEPSY = json.dumps({
        "en": "Epilepsy",
        "ru": "Эпилепсия",
        "pl": "Padaczka",
        "uk": "Епілепсія",
        "de": "Epilepsie"
    })


class HealthFormStatus(str, Enum):
    """
    Статусы анкеты (одобрена, ожидает, отклонена).
    Цвета — в HEX-кодах.
    """
    APPROVED = json.dumps({
        "en": "Approved",
        "ru": "Одобрена",
        "pl": "Zatwierdzona",
        "uk": "Схвалено",
        "de": "Genehmigt",
        "settings": {"color": "#4CAF50"}
    })
    PENDING = json.dumps({
        "en": "Pending",
        "ru": "Ожидает",
        "pl": "Oczekuje",
        "uk": "Очікує",
        "de": "Ausstehend",
        "settings": {"color": "#FFA000"}
    })
    REJECTED = json.dumps({
        "en": "Rejected",
        "ru": "Отклонена",
        "pl": "Odrzucona",
        "uk": "Відхилено",
        "de": "Abgelehnt",
        "settings": {"color": "#F44336"}
    })


# ==========
# Семья
# ==========


class RelationshipEnum(BaseJsonEnumMixin, str, Enum):
    SPOUSE = json.dumps({
        "en": "Spouse",
        "ru": "Супруг(а)",
        "pl": "Współmałżonek",
        "uk": "Подружжя",
        "de": "Ehepartner",
        "settings": {"color": "#8E24AA"}
    })
    CHILD = json.dumps({
        "en": "Child",
        "ru": "Ребёнок",
        "pl": "Dziecko",
        "uk": "Дитина",
        "de": "Kind",
        "settings": {"color": "#1E88E5"}
    })
    OTHER = json.dumps({
        "en": "Other",
        "ru": "Другое",
        "pl": "Inne",
        "uk": "Інше",
        "de": "Andere",
        "settings": {"color": "#757575"}
    })


class FamilyStatusEnum(BaseJsonEnumMixin, str, Enum):
    PENDING = json.dumps({
        "en": "Pending",
        "ru": "В ожидании",
        "pl": "Oczekuje",
        "uk": "Очікується",
        "de": "Ausstehend"
    })
    CONFIRMED = json.dumps({
        "en": "Confirmed",
        "ru": "Подтверждено",
        "pl": "Potwierdzony",
        "uk": "Підтверджено",
        "de": "Bestätigt"
    })
    DECLINED = json.dumps({
        "en": "Declined",
        "ru": "Отклонено",
        "pl": "Odrzucony",
        "uk": "Відхилено",
        "de": "Abgelehnt"
    })


# ==========
# Бонусная программа
# ==========


class TransactionTypeEnum(BaseJsonEnumMixin, str, Enum):
    ACCRUED = json.dumps({
        "en": "Accrued",
        "ru": "Начислено",
        "pl": "Dodane",
        "uk": "Нараховано",
        "de": "Gutgeschrieben",
        "settings": {"color": "#43A047"}
    })
    REDEEMED = json.dumps({
        "en": "Redeemed",
        "ru": "Списано",
        "pl": "Wykorzystane",
        "uk": "Списано",
        "de": "Eingelöst",
        "settings": {"color": "#E53935"}
    })


# ==========
# Согласия
# ==========

class ConsentEnum(BaseJsonEnumMixin, str, Enum):
    GDPR = json.dumps({
        "en": "GDPR Consent",
        "ru": "Согласие на обработку персональных данных (GDPR)",
        "pl": "Zgoda na przetwarzanie danych (GDPR)",
        "uk": "Згода на обробку персональних даних (GDPR)",
        "de": "Einwilligung in die Verarbeitung personenbezogener Daten (DSGVO)"
    })
    PRIVACY = json.dumps({
        "en": "Privacy Policy",
        "ru": "Согласие с политикой конфиденциальности",
        "pl": "Zgoda na politykę prywatności",
        "uk": "Згода з політикою конфіденційності",
        "de": "Einwilligung in die Datenschutzrichtlinie"
    })
    TERMS = json.dumps({
        "en": "Terms of Use",
        "ru": "Согласие с условиями использования",
        "pl": "Zgoda na warunki korzystania",
        "uk": "Згода з умовами використання",
        "de": "Einwilligung in die Nutzungsbedingungen"
    })
    COOKIES = json.dumps({
        "en": "Cookies",
        "ru": "Согласие на использование cookies",
        "pl": "Zgoda na pliki cookie",
        "uk": "Згода на використання cookies",
        "de": "Einwilligung in Cookies"
    })
    EMAIL = json.dumps({
        "en": "Email Marketing",
        "ru": "Согласие на email-маркетинг",
        "pl": "Zgoda na email marketing",
        "uk": "Згода на email-маркетинг",
        "de": "Einwilligung in E-Mail-Marketing"
    })
    SMS = json.dumps({
        "en": "SMS Marketing",
        "ru": "Согласие на SMS-маркетинг",
        "pl": "Zgoda na marketing SMS",
        "uk": "Згода на SMS-маркетинг",
        "de": "Einwilligung in SMS-Marketing"
    })
    PERSONALIZATION = json.dumps({
        "en": "Personalization",
        "ru": "Согласие на персонализацию",
        "pl": "Zgoda na personalizację",
        "uk": "Згода на персоналізацію",
        "de": "Einwilligung in Personalisierung"
    })


# ==========
# Встречи
# ==========
