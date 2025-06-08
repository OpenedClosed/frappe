"""Персональный аккаунт приложения Клиентский интерфейс."""
from datetime import date, datetime
from typing import Any, List, Optional

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
    Админка для вкладки 'Основная информация'
    """

    model = MainInfoSchema
    collection_name = "patients_main_info"

    verbose_name = {
        "en": "Basic information",
        "ru": "Основная информация",
        "pl": "Informacje podstawowe"
    }
    # plural_name = {
    #     "en": "Basic information records",
    #     "ru": "Записи основной информации",
    #     "pl": "Rekordy podstawowych informacji"
    # }
    plural_name = {
        "en": "Basic information",
        "ru": "Основная информация",
        "pl": "Informacje podstawowe"   
    }

    icon: str = "pi pi-file"
    max_instances_per_user = 1

    list_display = []

    detail_fields = [
        "last_name",
        "first_name",
        "patronymic",
        "birth_date",
        "gender",
        "company_name",
        "avatar",
        "account_status",
        "patient_id",
        "created_at",
        "updated_at",
        
    ]

    computed_fields = [
        "patient_id",
        "account_status",
        "first_name",
        "last_name",
        "birth_date",
        "gender",
        "company_name"
    ]

    read_only_fields = [
        "created_at",
        "updated_at",
        "patient_id",
        "account_status",
        "last_name",
        "first_name",
        "patronymic",
        "birth_date",
        "gender",
        "company_name",
    ]

    field_titles = {
        "last_name": {"en": "Last Name", "ru": "Фамилия", "pl": "Nazwisko"},
        "first_name": {"en": "First Name", "ru": "Имя", "pl": "Imię"},
        "patronymic": {"en": "Patronymic", "ru": "Отчество", "pl": "Drugie imię"},
        "birth_date": {"en": "Birth Date", "ru": "Дата рождения", "pl": "Data urodzenia"},
        "gender": {"en": "Gender", "ru": "Пол", "pl": "Płeć"},
        "company_name": {"en": "Company Name", "ru": "Название компании", "pl": "Nazwa firmy"},
        "avatar": {
            "en": "Avatar",
            "ru": "Аватар",
            "pl": "Awatar"
        },
        "account_status": {
            "en": "Account Status", "ru": "Статус аккаунта", "pl": "Status konta"
        },

        "patient_id": {"en": "Patient ID", "ru": "ID пациента", "pl": "ID pacjenta"},
        "created_at": {"en": "Created At", "ru": "Дата создания", "pl": "Data utworzenia"},
        "updated_at": {"en": "Updated At", "ru": "Последнее обновление", "pl": "Ostatnia aktualizacja"},
    }

    help_texts = {
        "last_name": {
            "en": "User's last name",
            "ru": "Фамилия пользователя",
            "pl": "Nazwisko użytkownika"
        },
        "first_name": {
            "en": "User's first name",
            "ru": "Имя пользователя",
            "pl": "Imię użytkownika"
        },
        "patronymic": {
            "en": "User's patronymic",
            "ru": "Отчество пользователя",
            "pl": "Drugie imię użytkownika"
        },
        "birth_date": {
            "en": "User's birth date",
            "ru": "Дата рождения пользователя",
            "pl": "Data urodzenia użytkownika"
        },
        "gender": {
            "en": "Gender",
            "ru": "Пол",
            "pl": "Płeć"
        },
        "company_name": {
            "en": "Company name",
            "ru": "Название компании",
            "pl": "Nazwa firmy"
        },
        "avatar": {
            "en": "User photo or avatar",
            "ru": "Фотография пользователя или аватар",
            "pl": "Zdjęcie użytkownika lub awatar"
        },
        "account_status": {
            "en": "Verification status of the account",
            "ru": "Статус верификации аккаунта",
            "pl": "Status weryfikacji konta"
        },
        # "metadata": {
        #     "en": "Extra parameters such as referral code",
        #     "ru": "Дополнительные параметры, например реферальный код",
        #     "pl": "Dodatkowe parametry, np. kod polecający"
        # },
        "patient_id": {
            "en": "Patient internal ID",
            "ru": "Внутренний ID пациента",
            "pl": "Wewnętrzny ID pacjenta"
        },
        "created_at": {
            "en": "Record creation date",
            "ru": "Дата создания записи",
            "pl": "Data utworzenia rekordu"
        },
        "updated_at": {
            "en": "Record last update date",
            "ru": "Дата последнего обновления записи",
            "pl": "Data ostatniej aktualizacji rekordu"
        }
    }

    field_groups = [
        {
            "column": 0,
            "title": {"en": "Personal data", "ru": "Личные данные", "pl": "Dane osobowe"},
            "fields": ["last_name", "first_name", "patronymic", "birth_date", "gender", "avatar"],
        },
        {
            "column": 1,
            "title": {"en": "Company info", "ru": "Информация о компании", "pl": "Informacje o firmie"},
            "fields": ["company_name"],
        },
        {
            "column": 1,
            "title": {"en": "System info", "ru": "Системная информация", "pl": "Informacje systemowe"},
            "fields": ["patient_id", "account_status", "created_at", "updated_at"],
        },
    ]

    field_styles = {
        "last_name": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "16px",
                "font_weight": "bold",
                "text_color": "#1F1F29"
            }
        },
        "first_name": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "16px",
                "font_weight": "bold",
                "text_color": "#1F1F29"
            }
        },
        "patronymic": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "16px",
                "font_weight": "bold",
                "text_color": "#1F1F29"
            }
        },
        "birth_date": {
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
        "gender": {
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
        "company_name": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "normal",
                "text_color": "#1F1F29",
                "align": "right"
            }
        },
        "patient_id": {
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
        "created_at": {
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
        },
        "updated_at": {
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
            if format:
                updated.append(await self.format_document(raw, current_user))
            else:
                updated.append(raw)
        return updated

    async def create(self, data: dict, current_user=None):
        """
        Создание записи. CRM-синхронизация отключена — предполагается, что
        запись уже создавалась через /register_confirm.
        """
        return await super().create(data, current_user)


    async def get_patient_id(self, obj: dict) -> str:
        """
        Просто возвращает внешний ID пациента (UUID), если есть.
        """
        return obj.get("patient_id", "Error")

    async def crm_or_local(self, obj: dict, crm_field: str, local_field: str):
        patient_id = obj.get("patient_id")
        patient    = await self.get_patient_cached(patient_id) if patient_id else None
        return patient.get(crm_field) if patient and patient.get(crm_field) else obj.get(local_field)

    async def get_first_name(self, obj: dict)  -> str | None:
        return await self.crm_or_local(obj, "firstname", "first_name")

    async def get_last_name(self, obj: dict)   -> str | None:
        return await self.crm_or_local(obj, "lastname",  "last_name")

    async def get_birth_date(self, obj: dict)  -> datetime | None:
        iso = await self.crm_or_local(obj, "birthdate", "birth_date")
        return datetime.fromisoformat(iso) if isinstance(iso, str) else iso

    async def get_gender(self, obj: dict)      -> str | None:
        return await self.crm_or_local(obj, "gender", "gender")
    
    async def get_account_status(self, obj: dict) -> str:
        """
        Статус верификации аккаунта.
        Берётся из CRM (`profile`) и преобразуется в Enum → JSON-строка.
        При ошибке или отсутствии данных — fallback на локальное значение.
        """
        patient_id = obj.get("patient_id")
        patient = await self.get_patient_cached(patient_id) if patient_id else None

        # Значение по умолчанию — локальное (уже JSON-строка)
        local_status = obj.get("account_status", AccountVerificationEnum.UNVERIFIED)

        if not patient:
            return local_status

        profile = patient.get("profile")
        if profile == "normal":
            return AccountVerificationEnum.VERIFIED
        else:
            return AccountVerificationEnum.UNVERIFIED


# ==========
# Контактная информация
# ==========


class ContactInfoAccount(BaseAccount, CRMIntegrationMixin):
    """
    Админка для вкладки «Контактная информация».
    """

    model = ContactInfoSchema
    collection_name = "patients_contact_info"

    verbose_name = {
        "en": "Contact information",
        "ru": "Контактная информация",
        "pl": "Informacje kontaktowe"
    }
    plural_name = verbose_name

    icon = "pi pi-envelope"
    max_instances_per_user = 1

    list_display: list[str] = []

    detail_fields = [
        "email", "phone", "address", "pesel",
        "emergency_contact", "updated_at"
    ]

    computed_fields = ["address"]
    read_only_fields = ["updated_at", "address", "pesel"]

    field_titles = {
        "email": {"en": "Email", "ru": "Email", "pl": "E-mail"},
        "phone": {"en": "Phone", "ru": "Телефон", "pl": "Telefon"},
        "address": {"en": "Address", "ru": "Адрес", "pl": "Adres"},
        "pesel": {"en": "PESEL", "ru": "PESEL", "pl": "PESEL"},
        "emergency_contact": {"en": "Emergency contact", "ru": "Экстренный контакт", "pl": "Kontakt awaryjny"},
        "updated_at": {"en": "Last update", "ru": "Последнее обновление", "pl": "Ostatnia aktualizacja"},
    }

    help_texts = {
        "email": {"en": "Valid e-mail", "ru": "Действующий e-mail", "pl": "Poprawny e-mail"},
        "phone": {"en": "Primary phone", "ru": "Основной телефон", "pl": "Główny telefon"},
        "address": {"en": "Postal address", "ru": "Адрес проживания", "pl": "Adres zamieszkania"},
        "pesel": {"en": "National ID", "ru": "Нац. идентификатор", "pl": "Numer PESEL"},
        "emergency_contact": {"en": "Emergency phone", "ru": "Телефон для экстренной связи", "pl": "Telefon awaryjny"},
        "updated_at": {"en": "Timestamp", "ru": "Отметка времени", "pl": "Znacznik czasu"},
    }

    field_groups = [
        {
            "column": 0,
            "title": {"en": "Contacts", "ru": "Контакты", "pl": "Kontakty"},
            "fields": ["email", "phone", "emergency_contact"],
        },
        {
            "column": 1,
            "title": {"en": "Address & IDs", "ru": "Адрес и идентификаторы", "pl": "Adres i ID"},
            "fields": ["address", "pesel", "updated_at"],
        },
    ]

    field_styles = {
        "email": {
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
        "phone": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "bold",
                "text_color": "#1F1F29"
            }
        },
        "address": {
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
        "pesel": {
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
        "emergency_contact": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "bold",
                "text_color": "#1F1F29"
            }
        },
        "updated_at": {
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
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }

    async def create(self, data: dict, current_user=None):
        """
        Создание контактной информации.
        Обновляет CRM, если есть `patient_id` в основной информации.
        """
        created = await super().create(data, current_user)

        user_id = current_user.data.get("user_id")
        if user_id:
            main = await mongo_db["patients_main_info"].find_one({"user_id": str(user_id)})
            patient_id = main.get("patient_id") if main else None

            if patient_id:
                patch = {
                    "phone": format_crm_phone(normalize_numbers(created["phone"])) if created.get("phone") else None,
                    "email": created.get("email")
                }
                await self.patch_contacts_in_crm(patient_id, patch)

        return created


    async def update(self, object_id: str, data: dict, current_user=None):
        """
        Обновление контактной информации.
        Обновляет CRM, если есть `patient_id` в основной информации.
        """
        updated = await super().update(object_id, data, current_user)

        user_id = current_user.data.get("user_id")
        if user_id:
            main = await mongo_db["patients_main_info"].find_one({"user_id": str(user_id)})
            patient_id = main.get("patient_id") if main else None

            if patient_id:
                patch = {
                    "phone": format_crm_phone(normalize_numbers(updated["phone"])) if updated.get("phone") else None,
                    "email": updated.get("email")
                }
                await self.patch_contacts_in_crm(patient_id, patch)

        return updated

    async def crm_or_local(self, obj: dict, crm_field: str, local_field: str):
        main = await mongo_db["patients_main_info"].find_one({"user_id": obj["user_id"]})
        patient_id = main.get("patient_id") if main else None
        patient    = await self.get_patient_cached(patient_id) if patient_id else None
        return patient.get(crm_field) if patient and patient.get(crm_field) else obj.get(local_field)


    async def get_address(self, obj: dict) -> str | None:
        """
        Склеиваем residenceAddress из CRM → одна строка.
        Fallback — локальный `address`.
        """
        print('here1')
        main = await mongo_db["patients_main_info"].find_one({"user_id": obj["user_id"]})
        patient_id = main.get("patient_id") if main else None
        patient    = await self.get_patient_cached(patient_id) if patient_id else None

        if patient and (addr := patient.get("residenceAddress")):
            parts = [addr.get(k) for k in ("street", "building", "apartment",
                                           "city", "zip", "country") if addr.get(k)]
            return ", ".join(parts)
        
        print('here2')

        return obj.get("address")

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
    # plural_name = {
    #     "en": "Health Surveys",
    #     "ru": "Анкеты здоровья",
    #     "pl": "Ankiety zdrowotne"
    # }
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

    async def get_form_status(self, obj: dict) -> str:
        """
        Вычисляет статус анкеты (заглушка).
        В будущем — логика на основе заполненности/врачебной оценки.
        """
        return HealthFormStatus.APPROVED.value


# ==========
# Семья
# ==========


class FamilyAccount(BaseAccount):
    """
    Админка для вкладки 'Семья'.
    """

    model = FamilyMemberSchema
    collection_name = "patients_family"

    verbose_name = {"en": "Family", "ru": "Семья", "pl": "Rodzina"}
    # plural_name = {"en": "Families", "ru": "Семьи", "pl": "Rodziny"}
    plural_name = {"en": "Family", "ru": "Семья", "pl": "Rodzina"}
    icon: str = "pi pi-users"

    list_display = [
        "member_name",
        "member_id",
        "status",
        "relationship",
        "bonus_balance"
    ]

    detail_fields = ["phone", "relationship"]

    computed_fields = [
        "member_name",
        "member_id",
        "bonus_balance"
    ]

    read_only_fields = [
        "member_name",
        "member_id",
        "bonus_balance"
    ]

    field_titles = {
        "phone": {"en": "Phone", "ru": "Телефон", "pl": "Telefon"},
        "relationship": {"en": "Relationship", "ru": "Родство", "pl": "Relacja"},
        "status": {"en": "Status", "ru": "Статус", "pl": "Status"},
        "get_member_name": {"en": "Full Name", "ru": "Полное имя", "pl": "Imię i nazwisko"},
        "get_member_id": {"en": "Patient ID", "ru": "ID пациента", "pl": "ID pacjenta"},
        "get_bonus_balance": {"en": "Bonuses", "ru": "Бонусы", "pl": "Bonusy"},
    }

    help_texts = {
        "phone": {
            "en": "Phone number to invite a family member",
            "ru": "Номер телефона для добавления члена семьи",
            "pl": "Numer telefonu do dodania członka rodziny"
        },
        "status": {
            "en": "Request status",
            "ru": "Статус заявки",
            "pl": "Status zgłoszenia"
        },
        "relationship": {
            "en": "Who is this person to you?",
            "ru": "Кто этот человек для вас?",
            "pl": "Kim jest ta osoba dla Ciebie?"
        }
    }

    field_groups = [
        {
            "title": {"en": "Family info", "ru": "Информация о семье", "pl": "Informacje o rodzinie"},
            "fields": ["phone", "relationship"]
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
        # bonus_balance — стилизуется отдельно
    }

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }

    async def get_member_name(self, member: dict) -> Optional[str]:
        """Вернёт имя, если статус confirmed, иначе None."""
        if member.get("status") == FamilyStatusEnum.CONFIRMED:
            return "Анна Петрова"
        return None

    async def get_member_id(self, member: dict) -> Optional[str]:
        """Вернёт ID пациента, если статус confirmed, иначе None."""
        if member.get("status") == FamilyStatusEnum.CONFIRMED:
            return "PAT-123456"
        return None

    async def get_bonus_balance(self, member: dict) -> int:
        """Возвращает заглушку для бонусов — 250 если confirmed, иначе 0."""
        if member.get("status") == FamilyStatusEnum.CONFIRMED:
            return 250
        return None


# ==========
# Бонусная программа
# ==========


class BonusTransactionInlineAccount(InlineAccount):
    """
    Инлайн-модель для транзакций бонусной программы.
    Отображается внутри поля `transaction_history`.
    """

    model = BonusTransactionSchema
    collection_name = "patients_bonuses"
    dot_field_path = "transaction_history"

    verbose_name = {
        "en": "Bonus Transaction",
        "ru": "Бонусная транзакция",
        "pl": "Transakcja bonusowa"}
    plural_name = {
        "en": "Transactions",
        "ru": "Транзакции",
        "pl": "Transakcje"}

    list_display = [
        "title",
        "amount",
        "transaction_type",
        "date_time"
    ]
    detail_fields = [
        "title",
        "amount",
        "transaction_type",
        "date_time"
    ]

    field_titles = {
        "title": {"en": "Title", "ru": "Название", "pl": "Tytuł"},
        "date_time": {"en": "Date", "ru": "Дата", "pl": "Data"},
        "transaction_type": {"en": "Type", "ru": "Тип", "pl": "Typ"},
        "amount": {"en": "Amount", "ru": "Сумма", "pl": "Kwota"},
    }

    field_styles = {
        "transaction_type": {
            "label_styles": {
                "display": "none"
            },
            "value_styles": {
                "font_size": "12px",
                "font_weight": "medium",
                "text_color": "#FFFFFF"
            }
        },
        "title": {
            "label_styles": {
                "display": "none"
            },
            "value_styles": {
                "font_size": "15px",
                "font_weight": "bold",
                "text_color": "#1F1F29"
            }
        },
        "date_time": {
            "label_styles": {
                "display": "none"
            },
            "value_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#8B8B99"
            }
        },
        "amount": {
            "label_styles": {
                "display": "none"
            },
            "value_styles": {
                "font_size": "16px",
                "font_weight": "bold",
                "text_color": "#1F1F29",
                "align": "right"
            }
        }
    }

    allow_crud_actions = {
        "create": False,
        "read": True,
        "update": False,
        "delete": False
    }


class BonusProgramAccount(BaseAccount):
    """
    Админка для вкладки 'Бонусная программа'.
    """

    model = BonusProgramSchema
    collection_name = "patients_bonuses"

    verbose_name = {
        "en": "Bonus Program",
        "ru": "Бонусная программа",
        "pl": "Program premiowy"}
    plural_name = {
        "en": "Bonus Programs",
        "ru": "Бонусные программы",
        "pl": "Programy premiowe"}

    icon = "pi pi-star"
    max_instances_per_user = 1

    list_display = []
    detail_fields = [
        "balance",
        "referral_code",
        "last_updated",
        # "transaction_history"
    ]

    computed_fields = ["balance", "referral_code"]
    read_only_fields = ["balance", "referral_code", "last_updated"]

    field_titles = {
        "balance": {"en": "Balance", "ru": "Текущий баланс", "pl": "Saldo"},
        "referral_code": {"en": "Referral Code", "ru": "Реферальный код", "pl": "Kod polecający"},
        "last_updated": {"en": "Last Updated", "ru": "Последнее обновление", "pl": "Ostatnia aktualizacja"},
        "transaction_history": {"en": "Transaction History", "ru": "История транзакций", "pl": "Historia transakcji"}
    }

    help_texts = {
        "referral_code": {
            "en": "Use this code to invite friends",
            "ru": "Используйте этот код для приглашения друзей",
            "pl": "Użyj tego kodu, aby zaprosić znajomych"
        },
        "transaction_history": {
            "en": "List of bonus point transactions",
            "ru": "Список операций с бонусами",
            "pl": "Lista operacji punktów bonusowych"
        }
    }

    field_groups = [
        {
            "title": {"en": "Bonus Info", "ru": "Информация о бонусах", "pl": "Informacje o bonusach"},
            "description": {
                "en": "Main information about user's bonus account",
                "ru": "Основная информация о бонусном счёте пользователя",
                "pl": "Główne informacje o koncie bonusowym użytkownika"
            },
            "fields": ["balance", "referral_code", "last_updated"]
        },
        {
            "title": {"en": "Transaction History", "ru": "История транзакций", "pl": "Historia transakcji"},
            "description": {
                "en": "Recent bonus point transactions",
                "ru": "Последние операции с бонусами",
                "pl": "Ostatnie operacje bonusowe"
            },
            "fields": ["transaction_history"]
        }
    ]

    field_styles = {
        "balance": {
            "label_styles": {
                "font_size": "14px",
                "font_weight": "bold",
                "text_color": "#1F1F29"
            },
            "value_styles": {
                "font_size": "28px",
                "font_weight": "bold",
                "text_color": "#0057FF"
            }
        },
        "referral_code": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"
            },
            "value_styles": {
                "font_size": "14px",
                "font_weight": "medium",
                "text_color": "#1F1F29",
                "background_color": "#F5F6F8",
                "padding": "6px 12px",
                "border_radius": "6px",
                "font_family": "monospace"
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

    inlines = {
        "transaction_history": BonusTransactionInlineAccount
    }

    allow_crud_actions = {
        "create": False,
        "read": True,
        "update": False,
        "delete": False
    }

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        current_user=None
    ) -> List[dict]:
        """
        Переопределяем, чтобы если в коллекции нет записи для текущего юзера,
        то мы её создаём и сразу возвращаем вместе с любыми другими возможными
        данными (если логика дополняется).
        """

        self.check_crud_enabled("read")
        final_filters = filters.copy() if filters else {}

        user_id = str(current_user.data["user_id"])
        final_filters["user_id"] = user_id

        cursor = self.db.find(final_filters).sort(
            sort_by or self.detect_id_field(), order)
        docs = await cursor.to_list(None)

        if not docs:
            new_doc = {
                "user_id": user_id,
                "balance": 0,
                "referral_code": "",
                "last_updated": datetime.utcnow(),
                "transaction_history": [
                    {
                        "title": "Welcome bonus",
                        "description": "Test transaction",
                        "date_time": datetime.utcnow(),
                        "transaction_type": TransactionTypeEnum.ACCRUED.value,
                        "amount": 100,
                        "referral_code": "TESTCODE"
                    }
                ]
            }
            insert_res = await self.db.insert_one(new_doc)
            if not insert_res.inserted_id:
                raise HTTPException(500, "Failed to create bonus program.")
            cursor = self.db.find(final_filters).sort(
                sort_by or self.detect_id_field(), order)
            docs = await cursor.to_list(None)

        formatted = []
        for raw_doc in docs:
            self.check_object_permission("read", current_user, raw_doc)
            formatted.append(await self.format_document(raw_doc, current_user))

        return formatted

    async def get_balance(self, obj: dict) -> int:
        """
        Пример: считаем сумму транзакций типа ACCRUED (прибавляем)
        и типа SPENT (вычитаем).
        """
        transactions = obj.get("transaction_history", [])
        balance = 0
        for tx in transactions:
            if tx.get("transaction_type") == TransactionTypeEnum.ACCRUED.value:
                balance += tx.get("amount", 0)
            elif tx.get("transaction_type") == TransactionTypeEnum.REDEEMED.value:
                balance -= tx.get("amount", 0)
        return balance

    async def get_referral_code(self, obj: dict) -> str:
        code = obj.get("referral_code")
        if not code:
            return "IVAN2023"
        return code


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
        "pl": "Moje zgody"
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
            "pl": "Zgody użytkownika"
        },
        "last_updated": {
            "en": "Last Updated",
            "ru": "Дата последнего обновления",
            "pl": "Ostatnia aktualizacja"
        }
    }

    help_texts = field_titles

    field_groups = [
        {
            "title": {
                "en": "User Consent Information",
                "ru": "Информация о согласиях пользователя",
                "pl": "Informacje o zgodach użytkownika"
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
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }

    async def sync_consents(self, doc: dict) -> dict:
        """
        Сравнивает локальные и CRM-согласия, при расхождении синхронизирует Mongo с CRM.
        Если локальное поле отсутствует — создаёт его.
        """
        patient_id = doc.get("patient_id")
        if not patient_id:
            return doc

        crm_raw = await self.get_consents_cached(patient_id)
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

    async def get_or_create_if_missing(self, patient_id: str) -> dict:
        """
        Получает запись из Mongo, если есть. Иначе — создаёт по CRM-согласиям.
        """
        doc = await self.db.find_one({"patient_id": patient_id})
        if doc:
            return await self.sync_consents(doc)

        crm_raw = await self.get_consents_cached(patient_id)
        consents = [ConsentItem(id=c["id"], accepted=c.get("accepted", False)) for c in crm_raw]

        now = datetime.utcnow()
        data = {
            "patient_id": patient_id,
            "consents": [c.model_dump() for c in consents],
            "last_updated": now,
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

        raw = await self.get_or_create_if_missing(patient_id)
        return [await self.format_document(raw, current_user) if format else raw]

    async def update(self, obj_id: str, data: dict, current_user=None):
        """
        Обновляет согласия в CRM и в локальной базе.
        """
        doc = await self.get(obj_id, current_user)
        patient_id = doc.get("patient_id")
        if not patient_id:
            raise HTTPException(400, "Patient ID missing")

        new_items = {item["id"]: item["accepted"] for item in data.get("consents", [])}
        old_items = {item.id: item.accepted for item in doc.get("consents", [])}

        crm = get_client()
        for cid, acc in new_items.items():
            if cid not in old_items or old_items[cid] != acc:
                await crm.update_consent(patient_id, cid, acc)

        data["last_updated"] = datetime.utcnow()
        return await super().update(obj_id, data, current_user)

    async def get_patient_id_for_user(self, user) -> str | None:
        client = await self.get_master_client_by_user(user)
        return client.get("patient_id") if client else None


# ==========
# Встречи
# ==========


class AppointmentAccount(BaseAccount):
    """
    Только для чтения: встречи пользователя, полученные из CRM.
    """

    model = AppointmentSchema  # фиктивная схема, не используется
    collection_name = "crm_appointments"
    verbose_name = {
        "en": "Appointments",
        "ru": "Визиты",
        "pl": "Wizyty"
    }
    plural_name = {
        "en": "Appointments",
        "ru": "Визиты",
        "pl": "Wizyty"
    }

    icon = "pi pi-calendar"
    max_instances_per_user = None
    allow_crud_actions = {
        "create": False,
        "read": True,
        "update": False,
        "delete": False
    }

    list_display = [
        "visit_date", "start", "end", "doctor"
    ]
    detail_fields = [
        "visit_date", "start", "end", "doctor"
    ]

    field_titles = {
        "visit_date": {"en": "Date", "ru": "Дата", "pl": "Data"},
        "start": {"en": "Start Time", "ru": "Начало", "pl": "Godzina rozpoczęcia"},
        "end": {"en": "End Time", "ru": "Конец", "pl": "Godzina zakończenia"},
        "doctor": {"en": "Doctor", "ru": "Врач", "pl": "Lekarz"},
    }

    read_only_fields = ["visit_date", "start", "end", "doctor"]

    # async def get_queryset(
    #     self, filters=None, sort_by=None, order=1, page=None, page_size=None, current_user=None, format=True
    # ) -> list[dict]:
    #     """
    #     Получает встречи из CRM для текущего пользователя начиная с даты регистрации.
    #     Если patient_id отсутствует, создаёт пациента в CRM.
    #     """
    #     if not current_user or not current_user.data["user_id"]:
    #         raise HTTPException(403, "Unauthorized")

    #     user_id = str(current_user.data["user_id"])
    #     info = await mongo_db["patients_main_info"].find_one({"user_id": user_id})
    #     contact = await mongo_db["patients_contact_info"].find_one({"user_id": user_id})
    #     if not info or not contact:
    #         return []

    #     # Если patient_id нет, пытаемся создать
    #     if "patient_id" not in info:
    #         try:
    #             pid = await get_client().find_or_create_patient(local_data=info, contact_data=contact)
    #             await mongo_db["patients_main_info"].update_one(
    #                 {"_id": info["_id"]},
    #                 {"$set": {"patient_id": pid}}
    #             )
    #             info["patient_id"] = pid
    #         except CRMError as e:
    #             raise HTTPException(502, f"CRM error: {e.detail}")

    #     patient_id = info["patient_id"]
    #     created = info.get("created_at", date.today())

    # appointments = await get_client().future_appointments(patient_id,
    # from_date=created.date())

    #     def to_result(raw: dict) -> dict:
    #         return {
    #             "visit_date": raw.get("date"),
    #             "start": raw.get("start"),
    #             "end": raw.get("end"),
    #             "doctor": raw.get("doctor", {}).get("name"),
    #             "id": str(raw.get("id")),
    #         }

    #     results = [to_result(a) for a in appointments]

    #     if sort_by:
    #         results.sort(key=lambda x: x.get(sort_by), reverse=(order == -1))

    #     return results


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
