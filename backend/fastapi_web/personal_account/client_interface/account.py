"""Персональный аккаунт приложения Клиентский интерфейс."""
import asyncio
from datetime import date, datetime
import json
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException

from integrations.panamedica.mixins import CRMIntegrationMixin
from integrations.panamedica.utils.help_functions import format_crm_phone
from utils.help_functions import normalize_numbers
from crud_core.registry import account_registry
from db.mongo.db_init import mongo_db
# from crud_core.permissions import AdminPanelPermission
from integrations.panamedica.client import CRMError, get_client
from personal_account.base_account import BaseAccount, InlineAccount

from .db.mongo.enums import (AccountVerificationEnum, FamilyStatusEnum,
                             HealthFormStatus, TransactionTypeEnum)
from .db.mongo.schemas import (AppointmentSchema, BonusProgramSchema,
                               BonusTransactionSchema, ConsentItem, ConsentSchema,
                               ContactInfoSchema, FamilyMemberSchema,
                               HealthSurveySchema, MainInfoSchema)

# ==========
# Основная информация
# ==========

class MainInfoAccount(BaseAccount, CRMIntegrationMixin):
    """
    Админка для вкладки 'Основная информация'.
    """
    model = MainInfoSchema
    collection_name = "patients_main_info"

    verbose_name = {
        "en": "Basic information",
        "ru": "Основная информация",
        "pl": "Informacje podstawowe",
        "uk": "Основна інформація",
        "de": "Grundlegende Informationen"
    }
    plural_name = verbose_name

    icon = "pi pi-file"
    max_instances_per_user = 1

    # ---------------------- отображение ----------------------
    list_display: list[str] = []          # в списке карточек ничего

    detail_fields = [
        "last_name", "first_name",
        # "patronymic",
        "birth_date", "gender",
        "company_name", "avatar",
        "crm_link_status",
        "account_status", "patient_id",
    ]

    computed_fields = [
        "patient_id", "account_status",
        "first_name", "last_name", "birth_date", "gender", "company_name",
        "crm_link_status",
    ]

    read_only_fields = [
        "patient_id", "account_status",
        "last_name", "first_name",
        # "patronymic",
        "birth_date", "gender", "company_name",
        "crm_link_status",
    ]

    # ---------------------- надписи ----------------------
    field_titles = {
        "last_name":      {"en": "Last Name",      "ru": "Фамилия",                    "pl": "Nazwisko",           "uk": "Прізвище",                    "de": "Nachname"},
        "first_name":     {"en": "First Name",     "ru": "Имя",                        "pl": "Imię",               "uk": "Ім'я",                        "de": "Vorname"},
        "patronymic":     {"en": "Patronymic",     "ru": "Отчество",                   "pl": "Drugie imię",        "uk": "По батькові",                 "de": "Patronym"},
        "birth_date":     {"en": "Birth Date",     "ru": "Дата рождения",              "pl": "Data urodzenia",     "uk": "Дата народження",             "de": "Geburtsdatum"},
        "gender":         {"en": "Gender",         "ru": "Пол",                        "pl": "Płeć",               "uk": "Стать",                       "de": "Geschlecht"},
        "company_name":   {"en": "Company Name",   "ru": "Компания",                   "pl": "Firma",              "uk": "Компанія",                    "de": "Firma"},
        "avatar":         {"en": "Avatar",         "ru": "Аватар",                    "pl": "Awatar",             "uk": "Аватар",                      "de": "Avatar"},
        "account_status": {"en": "Account Status", "ru": "Статус аккаунта",            "pl": "Status konta",       "uk": "Статус облікового запису",    "de": "Kontostatus"},
        "crm_link_status":{"en": "CRM link",       "ru": "Связь с CRM",               "pl": "Połączenie z CRM",   "uk": "Зв'язок з CRM",               "de": "CRM-Verbindung"},
        "patient_id":     {"en": "Patient ID",     "ru": "ID пациента",                "pl": "ID pacjenta",        "uk": "ID пацієнта",                 "de": "Patienten-ID"},
        "created_at":     {"en": "Created At",     "ru": "Создано",                    "pl": "Utworzono",          "uk": "Створено",                    "de": "Erstellt am"},
        "updated_at":     {"en": "Updated At",     "ru": "Обновлено",                  "pl": "Zaktualizowano",     "uk": "Оновлено",                    "de": "Aktualisiert am"},
    }

    help_texts = {
        "last_name": {
            "en": "User's last name",
            "ru": "Фамилия пользователя",
            "pl": "Nazwisko użytkownika",
            "uk": "Прізвище користувача",
            "de": "Nachname des Benutzers"
        },
        "first_name": {
            "en": "User's first name",
            "ru": "Имя пользователя",
            "pl": "Imię użytkownika",
            "uk": "Ім'я користувача",
            "de": "Vorname des Benutzers"
        },
        "patronymic": {
            "en": "User's patronymic",
            "ru": "Отчество пользователя",
            "pl": "Drugie imię użytkownika",
            "uk": "По батькові користувача",
            "de": "Patronym des Benutzers"
        },
        "birth_date": {
            "en": "User's birth date",
            "ru": "Дата рождения пользователя",
            "pl": "Data urodzenia użytkownika",
            "uk": "Дата народження користувача",
            "de": "Geburtsdatum des Benutzers"
        },
        "gender": {
            "en": "Gender",
            "ru": "Пол",
            "pl": "Płeć",
            "uk": "Стать",
            "de": "Geschlecht"
        },
        "company_name": {
            "en": "Company name",
            "ru": "Название компании",
            "pl": "Nazwa firmy",
            "uk": "Назва компанії",
            "de": "Firmenname"
        },
        "avatar": {
            "en": "User photo or avatar",
            "ru": "Фотография пользователя или аватар",
            "pl": "Zdjęcie użytkownika lub awatar",
            "uk": "Фотографія користувача або аватар",
            "de": "Foto oder Avatar des Benutzers"
        },
        "account_status": {
            "en": "Verification status of the account",
            "ru": "Статус верификации аккаунта",
            "pl": "Status weryfikacji konta",
            "uk": "Статус верифікації облікового запису",
            "de": "Verifizierungsstatus des Kontos"
        },
        "patient_id": {
            "en": "Patient internal ID",
            "ru": "Внутренний ID пациента",
            "pl": "Wewnętrzny ID pacjenta",
            "uk": "Внутрішній ID пацієнта",
            "de": "Interne Patienten-ID"
        },
        "created_at": {
            "en": "Record creation date",
            "ru": "Дата создания записи",
            "pl": "Data utworzenia rekordu",
            "uk": "Дата створення запису",
            "de": "Erstellungsdatum des Eintrags"
        },
        "updated_at": {
            "en": "Record last update date",
            "ru": "Дата последнего обновления записи",
            "pl": "Data ostatniej aktualizacji rekordu",
            "uk": "Дата останнього оновлення запису",
            "de": "Datum der letzten Aktualisierung"
        }
    }

    field_groups = [
        {
            "column": 0,
            "title": {
                "en": "Personal data",
                "ru": "Личные данные",
                "pl": "Dane osobowe",
                "uk": "Особисті дані",
                "de": "Persönliche Daten"
            },
            "fields": ["last_name", "first_name",
                    #    "patronymic",
                       "birth_date", "gender", "avatar"],
        },
        {
            "column": 1,
            "title": {
                "en": "Company info",
                "ru": "Информация о компании",
                "pl": "Informacje o firmie",
                "uk": "Інформація про компанію",
                "de": "Firmeninformationen"
            },
            "fields": ["company_name"],
        },
        {
            "column": 1,
            "title": {
                "en": "System info",
                "ru": "Системная информация",
                "pl": "Informacje systemowe",
                "uk": "Системна інформація",
                "de": "Systeminformationen"
            },
            "fields": ["patient_id", "account_status", "crm_link_status"],
        },
    ]

    field_styles = {
        # unchanged
    }

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }

    async def maybe_update_status_from_crm(self, doc: dict) -> dict:
        """
        Берём «живой» статус из CRM (profile) через кеш-метод миксина.
        Если отличается от локального — фиксируем в Mongo.
        """
        patient_id: Optional[str] = doc.get("patient_id")
        if not patient_id:
            return doc

        new_status = await self.get_account_status_from_crm(patient_id)
        if new_status.value != doc.get("account_status"):
            await self.db.update_one(
                {"_id": doc["_id"]},
                {"$set": {"account_status": new_status.value}},
            )
            doc["account_status"] = new_status.value
        return doc

    async def get_queryset(
        self,
        filters: dict | None = None,
        sort_by: str | None = None,
        order: int = 1,
        page: int | None = None,
        page_size: int | None = None,
        current_user: Any | None = None,
        format: bool = True,
    ) -> list[dict]:
        """
        Перед выводом каждой записи уточняем `account_status` через CRM (если нужно).
        """
        docs = await super().get_queryset(
            filters, sort_by, order, page, page_size, current_user, format=False
        )

        updated = []
        for raw in docs:
            raw = await self.maybe_update_status_from_crm(raw)
            updated.append(
                await self.format_document(raw, current_user) if format else raw
            )
        return updated

    async def create(self, data: dict, current_user=None):
        """
        Создание записи. CRM-синхронизация отключена — предполагается,
        что запись уже создавалась через /register_confirm.
        """
        return await super().create(data, current_user)

    async def get_patient_id(self, obj: dict, current_user=None) -> str:
        """
        Просто возвращает внешний ID пациента (UUID), если есть.
        """
        return obj.get("patient_id", "Error")

    async def crm_or_local(self, obj: dict, crm_field: str, local_field: str):
        patient_id = obj.get("patient_id")
        patient = await self.get_patient_cached(patient_id) if patient_id else None
        return patient.get(crm_field) if patient and patient.get(crm_field) else obj.get(local_field)

    async def get_first_name(self, obj: dict, current_user=None) -> str | None:
        return await self.crm_or_local(obj, "firstname", "first_name")

    async def get_last_name(self, obj: dict, current_user=None) -> str | None:
        return await self.crm_or_local(obj, "lastname", "last_name")

    async def get_birth_date(self, obj: dict, current_user=None) -> datetime | None:
        iso = await self.crm_or_local(obj, "birthdate", "birth_date")
        return datetime.fromisoformat(iso) if isinstance(iso, str) else iso

    async def get_company_name(self, obj: dict, current_user=None) -> dict:
        """
        Пока компания не используется — всегда показываем заглушку с переводом.
        """
        return {
            "ru": "Скоро будет",
            "en": "Coming soon",
            "pl": "Wkrótce dostępne",
            "uk": "Скоро буде",
            "de": "Kommt bald"
        }


    async def get_account_status(self, obj: dict, current_user=None) -> str:
        """
        Статус верификации аккаунта.
        """
        patient_id = obj.get("patient_id")
        patient = await self.get_patient_cached(patient_id) if patient_id else None
        local_status = obj.get("account_status", AccountVerificationEnum.UNVERIFIED)

        if not patient:
            return local_status

        profile = patient.get("profile")
        return (
            AccountVerificationEnum.VERIFIED
            if profile == "normal"
            else AccountVerificationEnum.UNVERIFIED
        )

    async def get_gender(self, obj: dict, current_user=None) -> dict:
        """
        Возвращает пол в виде словаря с переводами.
        """
        GENDER_TRANSLATIONS = {
            "male": {
                "ru": "Мужской",
                "en": "Male",
                "pl": "Mężczyzna",
                "uk": "Чоловіча",
                "de": "Männlich"
            },
            "female": {
                "ru": "Женский",
                "en": "Female",
                "pl": "Kobieta",
                "uk": "Жіноча",
                "de": "Weiblich"
            }
        }

        gender_key = await self.crm_or_local(obj, "gender", "gender")
        if isinstance(gender_key, str):
            return GENDER_TRANSLATIONS.get(gender_key.lower(), {
                "ru": gender_key,
                "en": gender_key,
                "pl": gender_key,
                "uk": gender_key,
                "de": gender_key,
            })
        return {"ru": "—", "en": "—", "pl": "—", "uk": "—", "de": "—"}

    async def get_crm_link_status(self, obj, current_user=None) -> dict:
        """
        Возвращает мультиязычную строку-статус CRM-связи.
        """
        if not obj.get("patient_id"):
            return {
                "ru": "нет связи с CRM",
                "en": "no CRM link",
                "pl": "brak połączenia z CRM",
                "uk": "немає зв'язку з CRM",
                "de": "keine CRM-Verbindung"
            }

        patient_id = obj["patient_id"]
        try:
            _, e = await self.get_consents_cached(patient_id)
            if e:
                raise e
            return {
                "ru": "подтверждён",
                "en": "verified",
                "pl": "zweryfikowany",
                "uk": "підтверджено",
                "de": "verifiziert"
            }
        except CRMError as e:
            if e.status_code == 403:
                return {
                    "ru": "связь есть, профиль не подтверждён",
                    "en": "linked, profile unverified",
                    "pl": "połączono, profil niezweryfikowany",
                    "uk": "є зв'язок, профіль не підтверджено",
                    "de": "verbunden, Profil nicht verifiziert"
                }
            return {
                "ru": "нет связи с CRM",
                "en": "no CRM link",
                "pl": "brak połączenia z CRM",
                "uk": "немає зв'язку з CRM",
                "de": "keine CRM-Verbindung"
            }


# ==========
# Контактная информация
# ==========

class ContactInfoAccount(BaseAccount, CRMIntegrationMixin):
    """
    Админка для вкладки «Контактная информация».
    """

    # ------------------------------------------------------------------
    # Базовые параметры
    # ------------------------------------------------------------------
    model = ContactInfoSchema
    collection_name = "patients_contact_info"

    verbose_name = {
        "en": "Contact information",
        "ru": "Контактная информация",
        "pl": "Informacje kontaktowe",
        "uk": "Контактна інформація",
        "de": "Kontaktinformationen",
    }
    plural_name = verbose_name

    icon = "pi pi-envelope"
    max_instances_per_user = 1
    list_display: list[str] = []

    # ------------------------------------------------------------------
    # Отображаемые, вычисляемые и только-для-чтения поля
    # ------------------------------------------------------------------
    detail_fields = [
        "email", "phone",
        "emergency_contact_name", "emergency_contact_phone", "emergency_contact_consent",
        "country", "region", "city", "street",
        "building_number", "apartment", "zip",
        "address",
        "pesel",
        "passport",
        "updated_at",
    ]

    computed_fields = ["address", "passport",
                       "country", "region", "city", "street",
                       "building_number", "apartment", "zip"]
    read_only_fields = ["phone", "address", "pesel", "updated_at"]

    # ------------------------------------------------------------------
    # Локализация заголовков
    # ------------------------------------------------------------------
    field_titles = {
        "email":   {"en": "E-mail", "ru": "E-mail", "pl": "E-mail", "uk": "E-mail", "de": "E-Mail"},
        "phone":   {"en": "Phone", "ru": "Телефон", "pl": "Telefon", "uk": "Телефон", "de": "Telefon"},
        "pesel":   {"en": "PESEL", "ru": "PESEL", "pl": "PESEL", "uk": "PESEL", "de": "PESEL"},
        "passport": {
            "ru": "Паспорт",
            "en": "Passport",
            "pl": "Paszport",
            "uk": "Паспорт",
            "de": "Reisepass"
        },
        "updated_at": {
            "en": "Last update",
            "ru": "Последнее обновление",
            "pl": "Ostatnia aktualizacja",
            "uk": "Останнє оновлення",
            "de": "Letzte Aktualisierung"
        },
        "emergency_contact_name": {
            "en": "Emergency contact name",
            "ru": "Имя экстренного контакта",
            "pl": "Imię kontaktu awaryjnego",
            "uk": "Ім’я екстреного контакту",
            "de": "Name der Notfallkontaktperson"
        },
        "emergency_contact_phone": {
            "en": "Emergency contact phone",
            "ru": "Телефон экстренного контакта",
            "pl": "Telefon kontaktu awaryjnego",
            "uk": "Телефон екстреного контакту",
            "de": "Telefon der Notfallkontaktperson"
        },
        "emergency_contact_consent": {
            "en": "Consent to share health info",
            "ru": "Согласие на передачу данных о здоровье",
            "pl": "Zgoda na udostępnienie danych zdrowotnych",
            "uk": "Згода на передачу даних про здоров’я",
            "de": "Einwilligung zur Weitergabe von Gesundheitsdaten"
        },
        "country": {
            "en": "Country",
            "ru": "Страна",
            "pl": "Kraj",
            "uk": "Країна",
            "de": "Land"
        },
        "region": {
            "en": "Voivodeship / Region",
            "ru": "Воеводство / Регион",
            "pl": "Województwo / Region",
            "uk": "Область / Регіон",
            "de": "Region / Bundesland"
        },
        "city": {
            "en": "City",
            "ru": "Город",
            "pl": "Miasto",
            "uk": "Місто",
            "de": "Stadt"
        },
        "street": {
            "en": "Street",
            "ru": "Улица",
            "pl": "Ulica",
            "uk": "Вулиця",
            "de": "Straße"
        },
        "building_number": {
            "en": "Building number",
            "ru": "Номер дома",
            "pl": "Numer budynku",
            "uk": "Номер будинку",
            "de": "Hausnummer"
        },
        "apartment": {
            "en": "Apartment",
            "ru": "Кв./пом.",
            "pl": "Mieszkanie",
            "uk": "Квартира",
            "de": "Wohnung"
        },
        "zip": {
            "en": "Postal code",
            "ru": "Почтовый индекс",
            "pl": "Kod pocztowy",
            "uk": "Поштовий індекс",
            "de": "Postleitzahl"
        },
        "address": {
            "en": "Address (full)",
            "ru": "Адрес (строкой)",
            "pl": "Adres (pełny)",
            "uk": "Адреса (повна)",
            "de": "Adresse (vollständig)"
        },
    }

    # ------------------------------------------------------------------
    # Группы полей (две колонки)
    # ------------------------------------------------------------------
    field_groups = [
        {
            "column": 0,
            "title": {"en": "Contacts", "ru": "Контакты", "pl": "Kontakty", "uk": "Контакти", "de": "Kontakte"},
            "fields": [
                "email", "phone",
                "emergency_contact_name", "emergency_contact_phone", "emergency_contact_consent"
            ],
        },
        {
            "column": 1,
            "title": {
                "en": "About Me",
                "ru": "Обо мне",
                "pl": "O mnie",
                "uk": "Про мене",
                "de": "Über mich"
            },
            "fields": [
                "country", "region", "city", "street",
                "building_number", "apartment", "zip",
                "address",
                "pesel", "passport", "updated_at",
            ],
        }
    ]

    allow_crud_actions = {"create": True, "read": True, "update": True, "delete": False}

    # ------------------------------------------------------------------
    # Создание / обновление — синхронизация с CRM
    # ------------------------------------------------------------------
    async def create(self, data: dict, current_user=None):
        """
        Создание контактной информации. В CRM отправляем только email и адрес.
        """
        created = await super().create(data, current_user)
        await self._patch_crm_contacts(created, current_user)
        return created

    async def update(self, object_id: str, data: dict, current_user=None):
        """
        Обновление контактной информации. Телефон менять нельзя.
        """
        updated = await super().update(object_id, data, current_user)
        print("===== UPDATED =====")
        print(updated)
        asyncio.create_task(self._patch_crm_contacts(updated, current_user))
        return updated

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------
    async def _patch_crm_contacts(self, local_doc: dict, current_user=None) -> None:
        """
        Формирует PATCH-тело и отправляет его в CRM (email + residenceAddress).
        """
        user_id = current_user.data.get("user_id") if current_user else None
        if not user_id:
            return

        main = await mongo_db["patients_main_info"].find_one({"user_id": str(user_id)})
        patient_id = main.get("patient_id") if main else None
        if not patient_id:
            return

        patch: dict[str, Any] = {}
        if local_doc.get("email"):
            patch["email"] = local_doc["email"]

        addr_fields = (
            "street", "building_number", "apartment",
            "city", "zip", "country"
        )
        if any(local_doc.get(f) for f in addr_fields):
            patch["residenceAddress"] = {
                "street":   local_doc.get("street"),
                "building": local_doc.get("building_number"),
                "apartment": local_doc.get("apartment"),
                "city":     local_doc.get("city"),
                "zip":      local_doc.get("zip"),
                "country":  local_doc.get("country"),
            }

        if patch:
            await self.patch_contacts_in_crm(patient_id, patch)

    # ------------------------------------------------------------------
    # CRM-vs-локальные данные
    # ------------------------------------------------------------------
    async def crm_or_local(self, obj: dict, crm_field: str, local_field: str):
        """
        Берёт поле либо из CRM, либо из локального документа.
        """
        main = await mongo_db["patients_main_info"].find_one({"user_id": obj["user_id"]})
        patient_id = main.get("patient_id") if main else None
        patient = await self.get_patient_cached(patient_id) if patient_id else None
        return patient.get(crm_field) if patient and patient.get(crm_field) else obj.get(local_field)

    async def get_address(self, obj: dict, current_user=None) -> str | None:
        """
        Возвращает строку адреса: CRM > локальные поля.
        """
        main = await mongo_db["patients_main_info"].find_one({"user_id": obj["user_id"]})
        patient_id = main.get("patient_id") if main else None
        patient = await self.get_patient_cached(patient_id) if patient_id else None

        if patient and (addr := patient.get("residenceAddress")):
            parts = [
                addr.get(k) for k in (
                    "street", "building", "apartment",
                    "city", "zip", "country"
                ) if addr.get(k)
            ]
            return ", ".join(parts)

        parts_local = [
            obj.get(k) for k in (
                "street", "building_number", "apartment",
                "city", "zip", "country"
            ) if obj.get(k)
        ]
        return ", ".join(parts_local) or None

    async def get_passport(self, obj, current_user=None) -> Optional[str]:
        """
        Возвращает паспорт из CRM, если он есть.
        """
        user_id = current_user.data.get("user_id") if current_user else None
        if not user_id:
            return None

        main_info = await mongo_db["patients_main_info"].find_one({"user_id": user_id})
        patient_id = main_info.get("patient_id") if main_info else None
        if not patient_id:
            return None

        try:
            crm_data = await self.get_patient_cached(patient_id)
            return crm_data.get("passport")
        except Exception:
            return None

    async def get_field_overrides(self, obj=None, current_user=None) -> dict:
        """
        Делает email и адрес read_only, если профиль не подтверждён в CRM.
        """
        readonly_fields = False
        patient_id = None

        if current_user:
            user_id = current_user.data.get("user_id")
            if user_id:
                main_info = await mongo_db["patients_main_info"].find_one({"user_id": user_id})
                patient_id = main_info.get("patient_id") if main_info else None

        if patient_id:
            try:
                _, e = await self.get_consents_cached(patient_id)
                if e:
                    raise e
            except CRMError as e:
                if e.status_code == 403:
                    readonly_fields = True

        fields_to_lock = [
            "email", "zip", "city", "country",
            "region", "street", "building_number", "apartment"
        ]

        return {
            field: {
                "settings": {"read_only": readonly_fields},
                "read_only": readonly_fields
            } for field in fields_to_lock
        }

    async def _get_residence_address_field(self, obj: dict, field: str, fallback: str) -> str | None:
        """
        Универсальный метод для получения поля из residenceAddress или fallback из obj.
        """
        main = await mongo_db["patients_main_info"].find_one({"user_id": obj["user_id"]})
        patient_id = main.get("patient_id") if main else None
        patient = await self.get_patient_cached(patient_id)

        if patient:
            address = patient.get("residenceAddress") or {}
            if address:
                return address.get(field)
        return obj.get(fallback)

    async def get_country(self, obj, current_user=None) -> str | None:
        return await self._get_residence_address_field(obj, "country", "country")

    async def get_city(self, obj, current_user=None) -> str | None:
        return await self._get_residence_address_field(obj, "city", "city")

    async def get_region(self, obj, current_user=None) -> str | None:
        return await self._get_residence_address_field(obj, "region", "region")

    async def get_street(self, obj, current_user=None) -> str | None:
        return await self._get_residence_address_field(obj, "street", "street")

    async def get_building_number(self, obj, current_user=None) -> str | None:
        return await self._get_residence_address_field(obj, "building", "building_number")

    async def get_apartment(self, obj, current_user=None) -> str | None:
        return await self._get_residence_address_field(obj, "apartment", "apartment")

    async def get_zip(self, obj, current_user=None) -> str | None:
        return await self._get_residence_address_field(obj, "zip", "zip")


# ==========
# Анкета здоровья
# ==========

class HealthSurveyAccount(BaseAccount):
    """
    Админка для вкладки 'Анкета здоровья'
    """

    model = HealthSurveySchema
    collection_name = "patients_health_survey"

    verbose_name = {
        "en": "Health Survey",
        "ru": "Анкета здоровья",
        "pl": "Ankieta zdrowotna"
    }
    plural_name = {
        "en": "Health Survey",
        "ru": "Анкета здоровья",
        "pl": "Ankieta zdrowotna"
    }

    icon: str = "pi pi-heart"
    max_instances_per_user = 1

    list_display = []

    detail_fields = [
        "allergies",
        "chronic_conditions",
        "smoking_status",
        "current_medications",
        "form_status",
        "last_updated"
    ]

    computed_fields = ["form_status"]
    read_only_fields = ["form_status", "last_updated"]

    field_titles = {
        "allergies": {
            "en": "Allergies",
            "ru": "Аллергии",
            "pl": "Alergie"
        },
        "chronic_conditions": {
            "en": "Chronic Conditions",
            "ru": "Хронические заболевания",
            "pl": "Choroby przewlekłe"
        },
        "smoking_status": {
            "en": "Smoking Status",
            "ru": "Статус курения",
            "pl": "Status palenia"
        },
        "current_medications": {
            "en": "Current Medications",
            "ru": "Текущие медикаменты",
            "pl": "Przyjmowane leki"
        },
        "form_status": {
            "en": "Form Status",
            "ru": "Статус анкеты",
            "pl": "Status formularza"
        },
        "last_updated": {
            "en": "Last Updated",
            "ru": "Последнее обновление",
            "pl": "Ostatnia aktualizacja"
        }
    }

    help_texts = {
        "allergies": {
            "en": "List of known allergies, including food, drugs, etc.",
            "ru": "Список известных аллергий: пища, лекарства и т.д.",
            "pl": "Lista znanych alergii, np. pokarmowych, leków itd."
        },
        "chronic_conditions": {
            "en": "Select one or more chronic health conditions.",
            "ru": "Выберите одно или несколько хронических заболеваний.",
            "pl": "Wybierz jedną lub więcej chorób przewlekłych."
        },
        "smoking_status": {
            "en": "Current or past smoking habits.",
            "ru": "Текущие или прошлые привычки курения.",
            "pl": "Obecne lub przeszłe nawyki palenia."
        },
        "current_medications": {
            "en": "Drugs taken regularly, including dosage and schedule.",
            "ru": "Регулярно принимаемые лекарства, дозировка и режим.",
            "pl": "Leki przyjmowane regularnie, dawki i harmonogram."
        },
        "form_status": {
            "en": "Automatically calculated status of this survey.",
            "ru": "Автоматически вычисляемый статус анкеты.",
            "pl": "Automatycznie obliczany status formularza."
        },
        "last_updated": {
            "en": "Timestamp when the form was last edited.",
            "ru": "Дата и время последнего редактирования анкеты.",
            "pl": "Data i godzina ostatniej edycji formularza."
        }
    }

    field_groups = [
        {
            "title": {
                "en": "Medical Information",
                "ru": "Медицинская информация",
                "pl": "Informacje medyczne"
            },
            "fields": [
                "allergies",
                "chronic_conditions",
                "smoking_status",
                "current_medications"
            ]
        },
        {
            "title": {
                "en": "Survey Status",
                "ru": "Статус анкеты",
                "pl": "Status ankiety"
            },
            "fields": ["form_status", "last_updated"]
        }
    ]

    field_styles = {
        "allergies": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "normal",
                "text_color": "#1F1F29"
            }
        },
        "chronic_conditions": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "bold",
                "text_color": "#4C4C64"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "normal",
                "text_color": "#1F1F29"
            }
        },
        "smoking_status": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "normal",
                "text_color": "#1F1F29"
            }
        },
        "current_medications": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "normal",
                "text_color": "#1F1F29"
            }
        },
        "last_updated": {
            "label_styles": {
                "font_size": "12px",
                "font_weight": "normal",
                "text_color": "#8B8B99"
            },
            "value_styles": {
                "font_size": "14px",
                "font_weight": "normal",
                "text_color": "#4F4F59"
            }
        }
        # form_status — НЕ задаём стили
    }

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }

    async def get_form_status(self, obj: dict, current_user=None) -> str:
        """
        Вычисляет статус анкеты (заглушка).
        В будущем — логика на основе заполненности/врачебной оценки.
        """
        return HealthFormStatus.APPROVED.value


# ==========
# Семья
# ==========

class FamilyAccount(BaseAccount, CRMIntegrationMixin):
    """
    Вкладка «Семья».
    Создание – приглашение по номеру; подтверждение – со стороны приглашённого.
    """

    model = FamilyMemberSchema
    collection_name = "patients_family"

    verbose_name = {
        "ru": "Семья",
        "en": "Family",
        "pl": "Rodzina",
        "uk": "Сімʼя",
        "de": "Familie"
    }
    plural_name = verbose_name

    icon = "pi pi-users"
    max_instances_per_user = None

    list_display = [
        "member_name", "member_id", "status",
        "relationship", "bonus_balance", "request_type"
    ]
    detail_fields = ["phone", "relationship", "status"]
    computed_fields = [
        "member_name", "member_id", "bonus_balance", "request_type", "phone"
    ]
    read_only_fields = ["member_name", "member_id", "bonus_balance"]

    field_titles = {
        "phone": {
            "en": "Phone",
            "ru": "Телефон",
            "pl": "Telefon",
            "uk": "Телефон",
            "de": "Telefon"
        },
        "relationship": {
            "en": "Relationship",
            "ru": "Родство",
            "pl": "Relacja",
            "uk": "Ступінь родинних звʼязків",
            "de": "Verwandtschaft"
        },
        "status": {
            "en": "Status",
            "ru": "Статус",
            "pl": "Status",
            "uk": "Статус",
            "de": "Status"
        },
        "get_member_name": {
            "en": "Full Name",
            "ru": "Полное имя",
            "pl": "Imię i nazwisko",
            "uk": "Повне імʼя",
            "de": "Vollständiger Name"
        },
        "get_member_id": {
            "en": "Patient ID",
            "ru": "ID пациента",
            "pl": "ID pacjenta",
            "uk": "ID пацієнта",
            "de": "Patienten-ID"
        },
        "get_bonus_balance": {
            "en": "Bonuses",
            "ru": "Бонусы",
            "pl": "Bonusy",
            "uk": "Бонуси",
            "de": "Bonuspunkte"
        },
        "request_type": {
            "en": "Request type",
            "ru": "Тип заявки",
            "pl": "Typ zgłoszenia",
            "uk": "Тип запиту",
            "de": "Anfragetyp"
        },
    }

    help_texts = {
        "phone": {
            "en": "Phone number to invite a family member",
            "ru": "Номер телефона для добавления члена семьи",
            "pl": "Numer telefonu do dodania członka rodziny",
            "uk": "Номер телефону для запрошення члена сімʼї",
            "de": "Telefonnummer zum Einladen eines Familienmitglieds"
        },
        "status": {
            "en": "Request status",
            "ru": "Статус заявки",
            "pl": "Status zgłoszenia",
            "uk": "Статус запиту",
            "de": "Anfragestatus"
        },
        "relationship": {
            "en": "Who is this person to you?",
            "ru": "Кто этот человек для вас?",
            "pl": "Kim jest ta osoba dla Ciebie?",
            "uk": "Хто ця людина для вас?",
            "de": "Wer ist diese Person für Sie?"
        }
    }

    field_groups = [
        {
            "title": {
                "en": "Family info",
                "ru": "Информация о семье",
                "pl": "Informacje o rodzinie",
                "uk": "Інформація про сімʼю",
                "de": "Familieninformationen"
            },
            "fields": ["phone", "relationship", "status"]
        }
    ]

    field_styles = {
        "phone": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "normal",
                "text_color": "#1F1F29"
            }
        },
        "relationship": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "normal",
                "text_color": "#1F1F29"
            }
        },
        "status": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "14px",
                "font_weight": "medium",
                "text_color": "#4F4F59"
            }
        },
        "member_name": {
            "label_styles": {
                "font_size": "14px",
                "font_weight": "normal",
                "text_color": "#8B8B99"
            },
            "value_styles": {
                "font_size": "16px",
                "font_weight": "bold",
                "text_color": "#1F1F29"
            }
        },
        "member_id": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#8B8B99"
            },
            "value_styles": {
                "font_size": "14px",
                "font_weight": "normal",
                "text_color": "#4F4F59"
            }
        }
    }

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        current_user: Optional[dict] = None,
    ) -> List[dict]:
        """
        Возвращает исходящие и входящие семейные заявки пользователя.
        """
        user_id = str(current_user.data.get("user_id"))
        client = await self.get_master_client_by_user(current_user)
        patient_id = str(client["patient_id"]) if client and client.get("patient_id") else None

        docs: list[dict] = []

        outgoing = await super().get_queryset(
            filters={"user_id": user_id},
            sort_by=sort_by,
            order=order,
            page=None,
            page_size=None,
            current_user=current_user,
            format=False,
        )
        docs.extend(outgoing)

        if patient_id:
            cursor = self.db.find({"member_id": patient_id})
            incoming = [doc async for doc in cursor]

            existing_ids = {doc["_id"] for doc in docs}
            new_incoming = [doc for doc in incoming if doc["_id"] not in existing_ids]
            docs.extend(new_incoming)

        if sort_by:
            reverse = order == -1
            docs.sort(key=lambda x: x.get(sort_by), reverse=reverse)

        if page is not None and page_size is not None:
            start = (page - 1) * page_size
            end = start + page_size
            docs = docs[start:end]

        formatted = [await self.format_document(d, current_user) for d in docs]
        return formatted

    async def get_field_overrides(self, obj=None, current_user=None) -> dict:
        """
        Делает поле status редактируемым только для входящих pending-заявок.
        """
        readonly = True

        if obj and current_user:
            client = await self.get_master_client_by_user(current_user)
            if client and obj.get("member_id") == client.get("patient_id"):
                readonly = False

        return {
            "status": {
                "settings": {"read_only": readonly},
                "read_only": readonly,
            },
            "phone": {
                "settings": {"read_only": False},
                "read_only": False,
            }
        }

    async def get_member_name(self, obj: dict, current_user: Optional[dict] = None) -> Optional[str]:
        """
        Показываем имя, если текущий пользователь — приглашённый или заявка подтверждена.
        """
        patient_id = obj.get("member_id")
        if not patient_id:
            return None

        is_invited = False
        if current_user:
            client = await self.get_master_client_by_user(current_user)
            is_invited = client and client.get("patient_id") == patient_id

        if obj.get("status") == FamilyStatusEnum.CONFIRMED or is_invited:
            main_user_id = obj.get("user_id")
            main_doc = await mongo_db.patients_main_info.find_one({"user_id": main_user_id})
            if main_doc:
                main_patient_id = main_doc["patient_id"]
                patient = await self.get_patient_cached(main_patient_id)
                if patient:
                    return f'{patient.get("firstname", "")} {patient.get("lastname", "")}'.strip()

        return None

    async def get_phone(self, obj: dict, current_user: Optional[dict] = None) -> Optional[str]:
        """
        Показываем телефон другой стороны — всегда.
        """
        if not obj or not current_user:
            return None

        client = await self.get_master_client_by_user(current_user)
        if not client:
            return None

        current_user_id = current_user.data.get("user_id")
        current_patient_id = client.get("patient_id")

        if obj.get("user_id") == current_user_id:
            print(obj)
            member_id = obj.get("member_id")
            if not member_id:
                return obj.get("phone")
            main_doc = await mongo_db.patients_main_info.find_one({"patient_id": member_id})
            if not main_doc:
                print('2')
                return None
            contact_doc = await mongo_db.patients_contact_info.find_one({"user_id": main_doc["user_id"]})
            print('3')
            return contact_doc.get("phone") if contact_doc else None

        if obj.get("member_id") == current_patient_id:
            contact_doc = await mongo_db.patients_contact_info.find_one({"user_id": obj.get("user_id")})
            print('4')
            return contact_doc.get("phone") if contact_doc else None
        print('5')
        return None

    async def get_member_id(self, obj: dict, current_user: Optional[dict] = None) -> Optional[str]:
        """
        Показываем ID, если текущий пользователь — приглашённый или заявка подтверждена.
        """
        patient_id = obj.get("member_id")
        if not patient_id or not current_user:
            return None

        client = await self.get_master_client_by_user(current_user)
        is_invited = client and client.get("patient_id") == patient_id

        if obj.get("status") == FamilyStatusEnum.CONFIRMED or is_invited:
            main_user_id = obj.get("user_id")
            main_doc = await mongo_db.patients_main_info.find_one({"user_id": main_user_id})
            if main_doc:
                return main_doc.get("patient_id")

        return None

    async def get_bonus_balance(self, obj: dict, current_user: Optional[dict] = None) -> Optional[int]:
        """
        Показываем бонусы, если текущий пользователь — приглашённый или заявка подтверждена.
        """
        patient_id = obj.get("member_id")
        if not patient_id or not current_user:
            return None

        client = await self.get_master_client_by_user(current_user)
        is_invited = client and client.get("patient_id") == patient_id

        if obj.get("status") == FamilyStatusEnum.CONFIRMED or is_invited:
            main_user_id = obj.get("user_id")
            main_doc = await mongo_db.patients_main_info.find_one({"user_id": main_user_id})
            if main_doc:
                main_patient_id = main_doc["patient_id"]
                patient = await self.get_patient_cached(main_patient_id)
                return patient.get("bonuses") if patient else None

        return None

    async def get_request_type(self, obj: dict, current_user: Optional[dict] = None) -> Optional[dict]:
        """
        Возвращает тип заявки с локализацией.
        """
        if not current_user:
            return None

        client = await self.get_master_client_by_user(current_user)
        if not client:
            return None

        if obj.get("user_id") == current_user.data.get("user_id"):
            return {
                "en": "Outgoing request",
                "ru": "Исходящая заявка",
                "pl": "Zgłoszenie wychodzące",
                "uk": "Вихідний запит",
                "de": "Ausgehende Anfrage"
            }

        if obj.get("member_id") == client.get("patient_id"):
            return {
                "en": "Incoming request",
                "ru": "Входящая заявка",
                "pl": "Zgłoszenie przychodzące",
                "uk": "Вхідний запит",
                "de": "Eingehende Anfrage"
            }

        return None

    async def create(self, data: dict, current_user=None):
        """
        Создаёт приглашение: нормализует телефон,
        сохраняет user_id отправителя и статус pending,
        добавляет member_id, имя и бонусы, если возможен поиск в CRM.
        """
        if current_user and getattr(current_user, "data", None):
            data["user_id"] = str(current_user.data["user_id"])
        data["status"] = FamilyStatusEnum.PENDING
        phone_key = normalize_numbers(data["phone"])
        data["phone"] = phone_key

        try:
            format_crm_phone(phone_key)
        except ValueError:
            raise HTTPException(
                400,
                detail={
                    "ru": "Неверный номер телефона",
                    "en": "Invalid phone number",
                    "pl": "Nieprawidłowy numer telefonu",
                    "uk": "Невірний номер телефону",
                    "de": "Ungültige Telefonnummer"
                }
            )

        contact_info = await self.get_contact_info_by_phone(phone_key)
        if contact_info:
            user_id = contact_info.get("user_id")
            client = await mongo_db.patients_main_info.find_one({"user_id": user_id})

            if client and client.get("patient_id"):
                patient = await self.get_patient_cached(client["patient_id"])
                if patient:
                    data["member_id"] = patient["externalId"]
                    data["member_name"] = (
                        f'{patient.get("firstname", "")} {patient.get("lastname", "")}'.strip()
                    )
                    data["bonus_balance"] = patient.get("bonuses")

        return await super().create(data, current_user)

    async def update(self, object_id: str, data: dict, current_user=None):
        """
        Разрешает приглашённому принять или отклонить заявку.
        """
        current = await self.get(object_id, current_user)
        client = await self.get_master_client_by_user(current_user)

        new_status = data.get("status")
        if new_status not in [FamilyStatusEnum.CONFIRMED, FamilyStatusEnum.DECLINED]:
            raise HTTPException(400, "Invalid status value.")

        patch = {"status": new_status}

        if new_status == FamilyStatusEnum.CONFIRMED:
            patient = await self.get_patient_cached(client["patient_id"])
            if patient:
                patch["member_id"] = patient["externalId"]
                patch["member_name"] = (
                    f'{patient.get("firstname", "")} {patient.get("lastname", "")}'.strip()
                )
                patch["bonus_balance"] = patient.get("bonuses")

        return await super().update(object_id, patch, current_user)

    async def get_contact_info_by_phone(self, crm_phone: str) -> Optional[dict]:
        """
        Находит документ ContactInfo по телефону.
        """
        return await mongo_db.patients_contact_info.find_one({"phone": crm_phone})


# ==========
# Бонусная программа
# ==========


class BonusTransactionInlineAccount(InlineAccount, CRMIntegrationMixin):
    """
    Инлайн-модель для транзакций бонусной программы.
    """

    model = BonusTransactionSchema
    collection_name = "patients_bonuses"
    dot_field_path = "transaction_history"

    verbose_name = {
        "en": "Bonus Transaction",
        "ru": "Бонусная транзакция",
        "pl": "Transakcja bonusowa",
        "uk": "Бонусна транзакція",
        "de": "Bonustransaktion",
    }
    plural_name = {
        "en": "Transactions",
        "ru": "Транзакции",
        "pl": "Transakcje",
        "uk": "Транзакції",
        "de": "Transaktionen",
    }

    list_display = ["title", "amount", "transaction_type", "date_time"]
    detail_fields = ["title", "amount", "transaction_type", "date_time"]

    field_titles = {
        "title":         {"en": "Title",  "ru": "Название",  "pl": "Tytuł",  "uk": "Назва",  "de": "Titel"},
        "date_time":     {"en": "Date",   "ru": "Дата",      "pl": "Data",   "uk": "Дата",   "de": "Datum"},
        "transaction_type": {"en": "Type",   "ru": "Тип",       "pl": "Typ",    "uk": "Тип",    "de": "Typ"},
        "amount":        {"en": "Amount", "ru": "Сумма",     "pl": "Kwota",  "uk": "Сума",   "de": "Betrag"},
    }

    field_styles = {  # без изменений
        "transaction_type": {
            "label_styles": {"display": "none"},
            "value_styles": {"font_size": "12px", "font_weight": "medium", "text_color": "#FFFFFF"},
        },
        "title": {
            "label_styles": {"display": "none"},
            "value_styles": {"font_size": "15px", "font_weight": "bold", "text_color": "#1F1F29"},
        },
        "date_time": {
            "label_styles": {"display": "none"},
            "value_styles": {"font_size": "13px", "font_weight": "normal", "text_color": "#8B8B99"},
        },
        "amount": {
            "label_styles": {"display": "none"},
            "value_styles": {
                "font_size": "16px",
                "font_weight": "bold",
                "text_color": "#1F1F29",
                "align": "right",
            },
        },
    }

    async def get_queryset(
        self,
        filters: dict | None = None,
        sort_by: str | None = None,
        order: int = 1,
        page: int | None = None,
        page_size: int | None = None,
        current_user=None,
        format: bool = True,
    ) -> list[dict]:
        """
        Тянет историю транзакций из CRM и отдаёт как инлайн-список.
        """
        parent = getattr(self, "parent_document", {}) or {}
        patient_id = parent.get("patient_id")

        if not patient_id:
            client = await self.get_master_client_by_user(current_user)
            patient_id = client.get("patient_id") if client else None
        if not patient_id:
            return []

        crm_rows, _ = await self.get_bonuses_history_cached(patient_id)

        def map_row(r: dict) -> dict:
            tx_type = (
                TransactionTypeEnum.ACCRUED
                if r.get("type") == "award"
                else TransactionTypeEnum.REDEEMED
            )
            return BonusTransactionSchema(
                title=r.get("title")
                or ("Bonus accrued" if tx_type is TransactionTypeEnum.ACCRUED else "Bonus spent"),
                description="",
                amount=r.get("amount", 0),
                transaction_type=tx_type,
                date_time=datetime.strptime(r["date"], "%Y-%m-%d"),
                referral_code=r.get("referralCode", ""),
            ).model_dump()

        items = [map_row(r) for r in crm_rows]
        items.sort(key=lambda x: x["date_time"], reverse=True)

        return (
            [await self.format_document(i, current_user) for i in items] if format else items
        )

    allow_crud_actions = {"create": False, "read": True, "update": False, "delete": False}


class BonusProgramAccount(BaseAccount, CRMIntegrationMixin):
    """
    Админка для вкладки 'Бонусная программа'.
    """

    model = BonusProgramSchema
    collection_name = "patients_bonuses"

    verbose_name = {
        "en": "Bonus Program",
        "ru": "Бонусная программа",
        "pl": "Program premiowy",
        "uk": "Бонусна програма",
        "de": "Bonusprogramm",
    }
    plural_name = {
        "en": "Bonus Programs",
        "ru": "Бонусные программы",
        "pl": "Programy premiowe",
        "uk": "Бонусні програми",
        "de": "Bonusprogramme",
    }

    icon = "pi pi-star"
    max_instances_per_user = 1

    list_display: list[str] = []
    detail_fields = ["balance", "referral_code", "last_updated"]

    computed_fields = ["balance", "referral_code"]
    read_only_fields = ["balance", "referral_code", "last_updated"]

    field_titles = {
        "balance":            {"en": "Balance",          "ru": "Текущий баланс",          "pl": "Saldo",             "uk": "Баланс",                 "de": "Saldo"},
        "referral_code":      {"en": "Referral Code",    "ru": "Реферальный код",         "pl": "Kod polecający",    "uk": "Реферальний код",        "de": "Empfehlungscode"},
        "last_updated":       {"en": "Last Updated",     "ru": "Последнее обновление",    "pl": "Ostatnia aktualizacja", "uk": "Останнє оновлення", "de": "Letzte Aktualisierung"},
        "transaction_history":{"en": "Transaction History","ru": "История транзакций",   "pl": "Historia transakcji","uk": "Історія транзакцій",     "de": "Transaktionsverlauf"},
    }

    help_texts = {
        "referral_code": {
            "en": "Use this code to invite friends",
            "ru": "Используйте этот код для приглашения друзей",
            "pl": "Użyj tego kodu, aby zaprosić znajomych",
            "uk": "Використовуйте цей код для запрошення друзів",
            "de": "Verwenden Sie diesen Code, um Freunde einzuladen",
        },
        "transaction_history": {
            "en": "List of bonus point transactions",
            "ru": "Список операций с бонусами",
            "pl": "Lista operacji punktów bonusowych",
            "uk": "Список операцій з бонусами",
            "de": "Liste der Bonuspunktransaktionen",
        },
    }

    field_groups = [
        {
            "title": {"en": "Bonus Info", "ru": "Информация о бонусах", "pl": "Informacje o bonusach", "uk": "Інформація про бонуси", "de": "Bonusinformationen"},
            "description": {
                "en": "Main information about user's bonus account",
                "ru": "Основная информация о бонусном счёте пользователя",
                "pl": "Główne informacje o koncie bonusowym użytkownika",
                "uk": "Основна інформація про бонусний рахунок користувача",
                "de": "Hauptinformationen zum Bonuskonto des Benutzers",
            },
            "fields": ["balance", "referral_code", "last_updated"],
        },
        {
            "title": {"en": "Transaction History", "ru": "История транзакций", "pl": "Historia transakcji", "uk": "Історія транзакцій", "de": "Transaktionsverlauf"},
            "description": {
                "en": "Recent bonus point transactions",
                "ru": "Последние операции с бонусами",
                "pl": "Ostatnie operacje bonusowe",
                "uk": "Останні операції з бонусами",
                "de": "Neueste Bonusvorgänge",
            },
            "fields": ["transaction_history"],
        },
    ]

    field_styles = {  # без изменений
        "balance": {
            "label_styles": {"font_size": "14px", "font_weight": "bold", "text_color": "#1F1F29"},
            "value_styles": {"font_size": "28px", "font_weight": "bold", "text_color": "#0057FF"},
        },
        "referral_code": {
            "label_styles": {"font_size": "13px", "font_weight": "normal", "text_color": "#6B6B7B"},
            "value_styles": {
                "font_size": "14px",
                "font_weight": "medium",
                "text_color": "#1F1F29",
                "background_color": "#F5F6F8",
                "padding": "6px 12px",
                "border_radius": "6px",
                "font_family": "monospace",
            },
        },
        "last_updated": {
            "label_styles": {"font_size": "12px", "font_weight": "normal", "text_color": "#8B8B99"},
            "value_styles": {"font_size": "14px", "font_weight": "normal", "text_color": "#4F4F59"},
        },
    }

    inlines = {"transaction_history": BonusTransactionInlineAccount}

    allow_crud_actions = {"create": False, "read": True, "update": False, "delete": False}

    async def ensure_local_document(self, current_user) -> dict | None:
        """Возвращает готовый локальный doc, обновлённый из CRM."""
        client = await self.get_master_client_by_user(current_user)
        patient_id = client.get("patient_id") if client else None
        if not patient_id:
            return None

        user_id = str(current_user.data["user_id"])
        doc = await self.db.find_one({"user_id": user_id})
        if not doc:
            now = datetime.utcnow()
            res = await self.db.insert_one(
                {
                    "user_id": user_id,
                    "patient_id": patient_id,
                    "referral_code": f"CODE_{patient_id}",
                    "last_updated": now,
                    "transaction_history": [],
                }
            )
            doc = await self.db.find_one({"_id": res.inserted_id})

        doc = await self.refresh_transactions_from_crm(doc, patient_id)
        return doc

    async def refresh_transactions_from_crm(self, doc: dict, patient_id: str) -> dict:
        crm_rows, _ = await self.get_bonuses_history_cached(patient_id)

        def map_row(r: dict) -> dict:
            tx_type = (
                TransactionTypeEnum.ACCRUED
                if r.get("type") == "award"
                else TransactionTypeEnum.REDEEMED
            )
            return BonusTransactionSchema(
                title=r.get("title")
                or ("Bonus accrued" if tx_type is TransactionTypeEnum.ACCRUED else "Bonus spent"),
                description="",
                amount=r.get("amount", 0),
                transaction_type=tx_type,
                date_time=datetime.strptime(r["date"], "%Y-%m-%d"),
                referral_code=r.get("referralCode", ""),
            ).model_dump()

        new_history = [map_row(r) for r in crm_rows]
        if new_history != doc.get("transaction_history", []):
            await self.db.update_one(
                {"_id": doc["_id"]},
                {"$set": {"transaction_history": new_history, "last_updated": datetime.utcnow()}},
            )
            doc["transaction_history"] = new_history
        return doc

    async def get_queryset(
        self,
        filters: dict | None = None,
        sort_by: str | None = None,
        order: int = 1,
        page: int | None = None,
        page_size: int | None = None,
        current_user=None,
        format: bool = True,
    ) -> list[dict]:
        doc = await self.ensure_local_document(current_user)
        if not doc:
            return []
        return [await self.format_document(doc, current_user) if format else doc]

    async def get_balance(self, obj: dict, current_user=None) -> int:
        """Возвращает текущий баланс бонусов."""
        patient_id = obj.get("patient_id")
        if patient_id:
            crm_data = await self.get_patient_cached(patient_id)
            if crm_data and isinstance(crm_data.get("bonuses"), int):
                return crm_data["bonuses"]
        return 0

    async def get_referral_code(self, obj: dict, current_user=None) -> str:
        return obj.get("referral_code") or "Error"


# ==========
# Согласия
# ==========

class ConsentAccount(BaseAccount, CRMIntegrationMixin):
    """
    Админка для вкладки 'Согласия'.
    """

    model = ConsentSchema
    collection_name = "patients_consents"

    verbose_name = {
        "en": "My Consents",
        "ru": "Мои согласия",
        "pl": "Moje zgody",
        "uk": "Мої згоди",
        "de": "Meine Einwilligungen"
    }
    plural_name = verbose_name

    icon = "pi pi-check-circle"
    max_instances_per_user = 1

    list_display = ["consents", "last_updated"]
    detail_fields = ["consents", "last_updated"]
    read_only_fields = ["last_updated"]

    field_titles = {
        "consents": {
            "en": "User Consents",
            "ru": "Согласия пользователя",
            "pl": "Zgody użytkownika",
            "uk": "Згоди користувача",
            "de": "Einwilligungen des Nutzers"
        },
        "last_updated": {
            "en": "Last Updated",
            "ru": "Дата последнего обновления",
            "pl": "Ostatnia aktualizacja",
            "uk": "Останнє оновлення",
            "de": "Letzte Aktualisierung"
        }
    }

    help_texts = field_titles

    field_groups = [
        {
            "title": {
                "en": "User Consent Information",
                "ru": "Информация о согласиях пользователя",
                "pl": "Informacje o zgodach użytkownika",
                "uk": "Інформація про згоди користувача",
                "de": "Einwilligungsinformationen des Nutzers"
            },
            "fields": ["consents", "last_updated"]
        }
    ]

    field_styles = {
        "consents": {
            "label_styles": {
                "font_size": "14px",
                "font_weight": "bold",
                "text_color": "#1F1F29"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "normal",
                "text_color": "#1F1F29"
            }
        },
        "last_updated": {
            "label_styles": {
                "font_size": "12px",
                "font_weight": "normal",
                "text_color": "#8B8B99"
            },
            "value_styles": {
                "font_size": "14px",
                "font_weight": "normal",
                "text_color": "#4F4F59"
            }
        }
    }

    allow_crud_actions = {
        "create": False,
        "read": True,
        "update": True,
        "delete": False
    }

    async def sync_consents(self, doc: dict) -> dict:
        """
        Сравнивает локальные и CRM-согласия, при расхождении синхронизирует Mongo с CRM.
        """
        patient_id = doc.get("patient_id")
        if not patient_id:
            return doc

        crm_raw, e = await self.get_consents_cached(patient_id)
        if e:
            raise HTTPException(
                400,
                detail = {
                    "ru": "Согласия становятся доступны только после подтверждения аккаунта.",
                    "en": "Consents are only available after account verification.",
                    "pl": "Zgody są dostępne dopiero po weryfikacji konta.",
                    "uk": "Згоди доступні лише після підтвердження облікового запису.",
                    "de": "Einwilligungen sind erst nach der Konto­bestätigung verfügbar."
                }
            )

        crm_set = {(c["id"], c.get("accepted", False)) for c in crm_raw}
        crm_items = [ConsentItem(id=i, accepted=a) for i, a in crm_set]

        local_set = {(c["id"], c["accepted"]) for c in doc.get("consents", [])}

        if crm_set != local_set:
            doc["consents"] = crm_items
            doc["last_updated"] = datetime.utcnow()
            await self.db.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "consents": [c.model_dump() for c in crm_items],
                        "last_updated": doc["last_updated"],
                    }
                },
            )
        return doc

    async def get_or_create_if_missing(self, patient_id: str, current_user) -> dict:
        """
        Получает запись из Mongo, если есть. Иначе — создаёт по CRM-согласиям.
        """
        doc = await self.db.find_one({"patient_id": patient_id})
        if doc:
            return await self.sync_consents(doc)

        crm_raw, e = await self.get_consents_cached(patient_id)
        if e:
            raise HTTPException(
                400,
                detail={
                    "ru": "Согласия доступны после подтверждения в системе PaNa",
                    "en": "Consents are available after confirmation in the PaNa system",
                    "pl": "Zgody są dostępne po potwierdzeniu w systemie PaNa",
                    "uk": "Згоди доступні після підтвердження в системі PaNa",
                    "de": "Einwilligungen sind nach Bestätigung im PaNa-System verfügbar"
                }
            )

        consents = [ConsentItem(id=c["id"], accepted=c.get("accepted", False)) for c in crm_raw]

        now = datetime.utcnow()
        data = {
            "patient_id": patient_id,
            "consents": [c.model_dump() for c in consents],
            "last_updated": now,
            "current_user": current_user.data.get("user_id") if current_user else None,
        }
        result = await self.db.insert_one(data)
        data["_id"] = result.inserted_id
        return data

    async def get_queryset(
        self,
        filters: dict | None = None,
        sort_by: str | None = None,
        order: int = 1,
        page: int | None = None,
        page_size: int | None = None,
        current_user=None,
        format: bool = True,
    ) -> list[dict]:
        patient_id = await self.get_patient_id_for_user(current_user)
        if not patient_id:
            return []

        raw = await self.get_or_create_if_missing(patient_id, current_user)
        return [await self.format_document(raw, current_user) if format else raw]

    async def update(self, object_id: str, data: dict, current_user=None):
        """
        Обновляет согласия в CRM и локальной базе.
        """
        doc = await self.get(object_id, current_user)
        patient_id = await self.get_patient_id_for_user(current_user)
        if not patient_id:
            raise HTTPException(400, "Patient ID missing")

        raw_consents = data.get("consents", [])

        if isinstance(raw_consents, str):
            try:
                raw_consents = json.loads(raw_consents)
            except Exception:
                raw_consents = [raw_consents]
        if not isinstance(raw_consents, list):
            raise HTTPException(400, "Invalid consents format: must be list")

        consents, _ = await self.get_consents_cached(patient_id)
        consents_by_title = {
            c["title"]: c["id"]
            for c in consents
            if isinstance(c, dict) and "title" in c and "id" in c
        }

        input_titles = set()
        for item in raw_consents:
            if isinstance(item, str):
                input_titles.add(item)
            elif isinstance(item, dict) and "title" in item:
                input_titles.add(item["title"])
            else:
                raise HTTPException(400, f"Invalid consent format: {item}")

        new_items = {cid: title in input_titles for title, cid in consents_by_title.items()}

        old_items = {
            item["id"]: item["accepted"]
            for item in doc.get("consents", [])
            if isinstance(item, dict) and "id" in item and "accepted" in item
        }

        crm = get_client()
        for cid, acc in new_items.items():
            if old_items.get(cid) != acc:
                asyncio.create_task(crm.update_consent(patient_id, cid, acc))

        data["consents"] = [{"id": cid, "accepted": acc} for cid, acc in new_items.items()]
        data["last_updated"] = datetime.utcnow()

        return await super().update(object_id, data, current_user)

    async def get_field_overrides(
        self, obj: Optional[dict] = None, current_user: Optional[Any] = None
    ) -> dict:
        patient_id = None
        if obj:
            patient_id = obj.get("patient_id")
        elif current_user:
            client = await self.get_master_client_by_user(current_user)
            patient_id = client.get("patient_id") if client else None

        if not patient_id:
            return {}

        try:
            consents, _ = await self.get_consents_cached(patient_id)
        except Exception:
            return {}

        return {
            "consents": {
                "choices": [{"value": c["title"], "label": c["title"]} for c in consents if "title" in c]
            }
        }

    async def format_document(self, doc: dict, current_user: Optional[dict] = None) -> dict:
        """
        Форматирует согласия как список строк (title) для multiselect.
        """
        formatted = await super().format_document(doc, current_user)

        patient_id = doc.get("patient_id")
        if not patient_id:
            return formatted

        try:
            crm_consents, _ = await self.get_consents_cached(patient_id)
            accepted_titles = [c["title"] for c in crm_consents if c.get("accepted") and "title" in c]
            formatted["consents"] = accepted_titles
        except Exception:
            pass

        return formatted


# ==========
# Встречи
# ==========


class AppointmentAccount(BaseAccount, CRMIntegrationMixin):
    """
    Только для чтения: встречи пользователя, полученные из CRM.
    """

    model = AppointmentSchema  # фиктивная схема, не используется
    collection_name = "crm_appointments"

    verbose_name = {
        "en": "Appointments",
        "ru": "Визиты",
        "pl": "Wizyty",
        "uk": "Візити",
        "de": "Termine"
    }
    plural_name = verbose_name

    icon = "pi pi-calendar"
    max_instances_per_user = None

    allow_crud_actions = {
        "create": False,
        "read": True,
        "update": False,
        "delete": False
    }

    list_display = ["visit_date", "start", "end", "doctor"]
    detail_fields = ["visit_date", "start", "end", "doctor"]
    read_only_fields = ["visit_date", "start", "end", "doctor"]

    field_titles = {
        "visit_date": {
            "en": "Date",
            "ru": "Дата",
            "pl": "Data",
            "uk": "Дата",
            "de": "Datum"
        },
        "start": {
            "en": "Start Time",
            "ru": "Начало",
            "pl": "Godzina rozpoczęcia",
            "uk": "Час початку",
            "de": "Beginn"
        },
        "end": {
            "en": "End Time",
            "ru": "Конец",
            "pl": "Godzina zakończenia",
            "uk": "Час закінчення",
            "de": "Ende"
        },
        "doctor": {
            "en": "Doctor",
            "ru": "Врач",
            "pl": "Lekarz",
            "uk": "Лікар",
            "de": "Arzt"
        },
    }

    async def get_queryset(  # noqa: D401
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        current_user: Optional[Any] = None,
        format: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Возвращает список визитов из CRM.
        Параметры пагинации игнорируются – отдаем все, как пришло.
        """
        self.check_crud_enabled("read")

        patient_id = await self.get_patient_id_for_user(current_user)
        if not patient_id:
            return []

        crm_raw, e = await self.get_future_appointments_cached(patient_id, date.today())
        if e:
            raise HTTPException(
                400,
                detail={
                    "ru": "Расписание встреч доступно после подтверждения в системе PaNa",
                    "en": "Appointment schedule is available after confirmation in the PaNa system",
                    "pl": "Harmonogram wizyt jest dostępny po potwierdzeniu w systemie PaNa",
                    "uk": "Розклад візитів доступний після підтвердження в системі PaNa",
                    "de": "Der Terminplan ist nach Bestätigung im PaNa-System verfügbar"
                }
            )

        rows = crm_raw.get("data") if isinstance(crm_raw, dict) and "data" in crm_raw else crm_raw

        formatted: List[Dict[str, Any]] = []
        for item in rows or []:
            formatted.append(
                {
                    "id": str(item.get("id", "")),
                    "visit_date": item.get("date"),
                    "start": item.get("start"),
                    "end": item.get("end"),
                    "doctor": (item.get("doctor") or {}).get("name"),
                    "status": item.get("status"),  # на будущее
                }
            )

        formatted.sort(key=lambda x: (x["visit_date"], x["start"]))
        return formatted


account_registry.register("patients_main_info", MainInfoAccount(mongo_db))
account_registry.register(
    "patients_contact_info",
    ContactInfoAccount(mongo_db))
account_registry.register(
    "patients_health_survey",
    HealthSurveyAccount(mongo_db))
account_registry.register("patients_family", FamilyAccount(mongo_db))
account_registry.register(
    "patients_bonus_program",
    BonusProgramAccount(mongo_db))
account_registry.register("patients_consents", ConsentAccount(mongo_db))
account_registry.register("crm_appointments", AppointmentAccount(mongo_db))
