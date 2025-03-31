"""Персональный аккаунт приложения Клиентский интерфейс."""
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException

from crud_core.registry import account_registry
from db.mongo.db_init import mongo_db
from personal_account.base_account import BaseAccount, InlineAccount

from .db.mongo.enums import (FamilyStatusEnum, HealthFormStatus,
                             TransactionTypeEnum)
from .db.mongo.schemas import (BonusProgramSchema, BonusTransactionSchema,
                               ConsentSchema, ContactInfoSchema,
                               FamilyMemberSchema, HealthSurveySchema,
                               MainInfoSchema)

# ==========
# Основная информация
# ==========


class MainInfoAccount(BaseAccount):
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
    plural_name = {
        "en": "Basic information records",
        "ru": "Записи основной информации",
        "pl": "Rekordy podstawowych informacji"
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
        "patient_id",
        "created_at",
        "updated_at"
    ]

    computed_fields = ["patient_id"]
    read_only_fields = ["created_at", "updated_at", "patient_id"]

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
            "title": {"en": "Personal data", "ru": "Личные данные", "pl": "Dane osobowe"},
            "fields": ["last_name", "first_name", "patronymic", "birth_date", "gender", "avatar"]
        },
        {
            "title": {"en": "Company info", "ru": "Информация о компании", "pl": "Informacje o firmie"},
            "fields": ["company_name"]
        },
        {
            "title": {"en": "System info", "ru": "Системная информация", "pl": "Informacje systemowe"},
            "fields": ["patient_id", "created_at", "updated_at"]
        }
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
        "create": False,
        "read": True,
        "update": True,
        "delete": False
    }

    async def get_patient_id(self, obj: dict) -> str:
        """
        Получение ID пациента из внешней CRM (заглушка).
        """
        return "PAT-123456"


# ==========
# Контактная информация
# ==========


class ContactInfoAccount(BaseAccount):
    """
    Админка для вкладки 'Контактная информация'
    """

    model = ContactInfoSchema
    collection_name = "patients_contact_info"

    verbose_name = {
        "en": "Contact information",
        "ru": "Контактная информация",
        "pl": "Informacje kontaktowe"
    }
    plural_name = {
        "en": "Contact information records",
        "ru": "Записи контактной информации",
        "pl": "Rekordy informacji kontaktowych"
    }

    icon: str = "pi pi-envelope"
    max_instances_per_user = 1

    list_display = []

    detail_fields = [
        "email",
        "phone",
        "address",
        "pesel",
        "emergency_contact",
        "doc_id",
        "updated_at"
    ]

    computed_fields = ["doc_id"]
    read_only_fields = ["updated_at", "doc_id"]

    field_titles = {
        "email": {"en": "Email", "ru": "Email", "pl": "E-mail"},
        "phone": {"en": "Phone", "ru": "Телефон", "pl": "Telefon"},
        "address": {"en": "Address", "ru": "Адрес", "pl": "Adres"},
        "pesel": {"en": "PESEL", "ru": "PESEL", "pl": "PESEL"},
        "emergency_contact": {"en": "Emergency contact", "ru": "Экстренный контакт", "pl": "Kontakt awaryjny"},
        "doc_id": {"en": "Document ID", "ru": "ID документа", "pl": "ID dokumentu"},
        "updated_at": {"en": "Last update", "ru": "Последнее обновление", "pl": "Ostatnia aktualizacja"},
    }

    help_texts = {
        "email": {
            "en": "Enter a valid email address",
            "ru": "Введите действующий адрес электронной почты",
            "pl": "Wprowadź poprawny adres e-mail"
        },
        "phone": {
            "en": "Primary phone number",
            "ru": "Основной номер телефона",
            "pl": "Główny numer telefonu"
        },
        "address": {
            "en": "Postal or residential address",
            "ru": "Почтовый или фактический адрес проживания",
            "pl": "Adres pocztowy lub zamieszkania"
        },
        "pesel": {
            "en": "National identifier (PESEL, SNILS, etc.)",
            "ru": "Национальный идентификатор (СНИЛС, ИИН, и т.д.)",
            "pl": "Numer identyfikacyjny (PESEL, itp.)"
        },
        "emergency_contact": {
            "en": "Phone of a person to contact in emergency",
            "ru": "Телефон близкого человека для экстренной связи",
            "pl": "Telefon kontaktowy w nagłych wypadkach"
        },
        "doc_id": {
            "en": "Passport or other document ID",
            "ru": "Паспорт или другой номер документа",
            "pl": "Paszport lub inny dokument tożsamości"
        },
        "updated_at": {
            "en": "Date and time this info was last updated",
            "ru": "Дата и время последнего обновления контактных данных",
            "pl": "Data i godzina ostatniej aktualizacji danych kontaktowych"
        }
    }

    field_styles = {
        "email": {
            "label_styles": {
                "font_size": "13px",
                "font_weight": "normal",
                "text_color": "#6B6B7B"  # серовато-синий
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
        "doc_id": {
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
        "create": False,
        "read": True,
        "update": True,
        "delete": False
    }

    async def get_doc_id(self, obj: dict) -> str:
        """
        Получение ID документа из внешней системы (заглушка).
        """
        return "4510 123456"


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
        "en": "Health Surveys",
        "ru": "Анкеты здоровья",
        "pl": "Ankiety zdrowotne"
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
    plural_name = {"en": "Families", "ru": "Семьи", "pl": "Rodziny"}
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

class ConsentAccount(BaseAccount):
    """
    Админка для вкладки 'Согласия'.
    """

    model = ConsentSchema
    collection_name = "patients_consents"

    verbose_name = {
        "en": "Consents",
        "ru": "Согласия",
        "pl": "Zgody"
    }
    plural_name = {
        "en": "User Consents",
        "ru": "Согласия пользователя",
        "pl": "Zgody użytkownika"
    }

    icon: str = "pi pi-check-circle"
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

    help_texts = {
        "consents": {
            "en": "Select which consents the user has agreed to",
            "ru": "Выберите, на что пользователь дал согласие",
            "pl": "Wybierz zgody użytkownika"
        },
        "last_updated": {
            "en": "Date when consents were last updated",
            "ru": "Дата последнего обновления согласий",
            "pl": "Data ostatniej aktualizacji zgód"
        }
    }

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
