"""Схемы приложения Административная зона для работы с БД MongoDB."""
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr, Field

from db.mongo.base.schemas import BaseValidatedModel, Photo
from integrations.panamedica.client import get_client
from utils.help_functions import normalize_numbers

from .enums import (AccountVerificationEnum, ConditionEnum, ConsentEnum,
                    FamilyStatusEnum, GenderEnum, RelationshipEnum,
                    TransactionTypeEnum)

# ==========
# Регистрация
# ==========


class RegistrationSchema(BaseModel):
    """
    Шаг 1: Данные для регистрации (телефон обязателен).
    """
    phone: str
    email: Optional[EmailStr] = None
    full_name: str
    password: str
    password_confirm: str
    accept_terms: bool = False

    def passwords_match(self) -> bool:
        """
        Проверяет совпадение введённого пароля и подтверждения.
        """
        return self.password == self.password_confirm

    def hashed_password(self) -> str:
        """
        Возвращает хэш текущего пароля (self.password).
        """
        return bcrypt.hash(self.password)


class ConfirmationSchema(RegistrationSchema):
    """
    Шаг 2: подтверждение кода (СМС).
    Наследует поля из RegistrationSchema и добавляет код.
    """
    code: str


# ==========
# Вход и двухфакторная аутентификация
# ==========

class LoginSchema(BaseModel):
    """
    Шаг 1 входа: телефон + пароль.
    """
    phone: str
    password: str

    def check_password(self, hashed: str) -> bool:
        """
        Сравнивает self.password с уже сохранённым хэшом (hashed).
        """
        return bcrypt.verify(self.password, hashed)


class TwoFASchema(BaseModel):
    """
    Шаг 2 входа: одноразовый код, высланный на телефон.
    """
    phone: str
    code: str


# ==========
# Основная информация
# ==========

# class MainInfoSchema(BaseValidatedModel):
#     """
#     Основная информация о пациенте, хранится в MongoDB.
#     """

#     last_name: str
#     first_name: str
#     patronymic: Optional[str] = None

#     birth_date: datetime = Field(
#         ...,
#         json_schema_extra={
#             "settings": {
#                 "type": "calendar",
#                 "placeholder": {
#                     "ru": "Выберите дату рождения",
#                     "en": "Select birth date",
#                     "pl": "Wybierz datę urodzenia"
#                 }
#             }
#         }
#     )

#     gender: GenderEnum = Field(
#         ...,
#         json_schema_extra={
#             "settings": {
#                 "type": "select",
#                 "placeholder": {
#                     "ru": "Выберите пол",
#                     "en": "Select gender",
#                     "pl": "Wybierz płeć"
#                 }
#             }
#         }
#     )

#     company_name: Optional[str] = None
#     avatar: Optional[Photo] = None

#     account_status: AccountVerificationEnum = Field(
#         default=AccountVerificationEnum.UNVERIFIED,
#         json_schema_extra={"settings": {"readonly": True}}
#     )

#     metadata: Optional[Dict[str, Any]] = Field(
#         default_factory=dict,
#         json_schema_extra={"settings": {"readonly": True}}
#     )

#     created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
#     updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class MainInfoSchema(BaseValidatedModel):
    """
    Основная информация о пациенте, хранится в MongoDB.
    """

    last_name: str
    first_name: str
    patronymic: Optional[str] = None

    birth_date: Optional[datetime] = Field(
        None,
        json_schema_extra={
            "settings": {
                "type": "calendar",
                "placeholder": {
                    "ru": "Выберите дату рождения",
                    "en": "Select birth date",
                    "pl": "Wybierz datę urodzenia"
                }
            }
        }
    )

    gender: Optional[GenderEnum] = Field(
        None,
        json_schema_extra={
            "settings": {
                "type": "select",
                "placeholder": {
                    "ru": "Выберите пол",
                    "en": "Select gender",
                    "pl": "Wybierz płeć"
                }
            }
        }
    )

    company_name: Optional[str] = None
    avatar: Optional[Photo] = None

    account_status: AccountVerificationEnum = Field(
        default=AccountVerificationEnum.UNVERIFIED,
        json_schema_extra={"settings": {"readonly": True}}
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        json_schema_extra={"settings": {"readonly": True}}
    )

    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    async def get_patient_id_from_crm(
            self, contact_data: dict) -> Optional[int]:
        """
        Получает ID пациента из CRM, если он существует. Возвращает None, если не найден.
        Используется при логине или синхронизации.
        """
        # crm = get_client()
        # phone = normalize_numbers(contact_data.get("phone", ""))
        # pesel = contact_data.get("pesel")
        # gender = self.gender.value if self.gender else None
        # bdate = self.birth_date.strftime("%Y-%m-%d") if self.birth_date else None

        # try:
        #     patient_id = await crm.find_patient(
        #         phone=phone,
        #         pesel=pesel,
        #         gender=gender,
        #         birth_date=bdate
        #     )
        #     return patient_id
        # except Exception as e:
        #     print(e)
        #     return None
        return None

# ==========
# Контактная информация
# ==========


class ContactInfoSchema(BaseValidatedModel):
    """
    Схема для вкладки 'Контактная информация'.
    """

    email: EmailStr = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "email",
                "placeholder": {
                    "ru": "Введите e-mail",
                    "en": "Enter email",
                    "pl": "Wprowadź e-mail"
                }
            }
        }
    )

    phone: str = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "phone",
                "mask": "+9 (999) 999-99-99"
            }
        }
    )

    address: str = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "textarea",
                "rows": 2,
                "placeholder": {
                    "ru": "Введите адрес",
                    "en": "Enter address",
                    "pl": "Wprowadź adres"
                }
            }
        }
    )

    pesel: str = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "pesel",
                "placeholder": {
                    "ru": "Введите идентификатор",
                    "en": "Enter identifier",
                    "pl": "Wprowadź identyfikator"
                }
            }
        }
    )

    emergency_contact: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "phone",
                "mask": "+9 (999) 999-99-99",
                "allowExtraText": True,
                "placeholder": {
                    "ru": "Введите номер экстренного контакта",
                    "en": "Enter emergency contact number",
                    "pl": "Wprowadź numer kontaktowy awaryjny"
                }
            }
        }
    )

    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


# ==========
# Анкета здоровья
# ==========

class HealthSurveySchema(BaseValidatedModel):
    """
    Схема для вкладки 'Анкета здоровья'.
    """

    allergies: Optional[List[Any]] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "tag_cloud",
                "placeholder": {
                    "en": "List allergens separated by commas",
                    "ru": "Перечислите аллергены через запятую",
                    "pl": "Wymień alergeny, oddzielając je przecinkami"
                }
            }
        }
    )

    chronic_conditions: List[ConditionEnum] = Field(
        ...,
        json_schema_extra={
            "settings": {
                # "type": "color_multiselect",
                "color_map": {
                    "yes": "#4CAF50",
                    "no": "#F44336"
                },
                "searchable": True
            }
        }
    )

    smoking_status: Optional[dict] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "select",
                "placeholder": {
                    "en": "Select smoking status",
                    "ru": "Выберите статус курения",
                    "pl": "Wybierz status palenia"
                },
                "choices": [
                    {
                        "value": {
                            "en": "Never smoked",
                            "ru": "Никогда не курил",
                            "pl": "Nigdy nie palił"
                        },
                        "label": {
                            "en": "Never smoked",
                            "ru": "Никогда не курил",
                            "pl": "Nigdy nie palił"
                        }
                    },
                    {
                        "value": {
                            "en": "Former smoker",
                            "ru": "Бывший курильщик",
                            "pl": "Były palacz"
                        },
                        "label": {
                            "en": "Former smoker",
                            "ru": "Бывший курильщик",
                            "pl": "Były palacz"
                        }
                    },
                    {
                        "value": {
                            "en": "Current smoker",
                            "ru": "Курит в настоящее время",
                            "pl": "Pali obecnie"
                        },
                        "label": {
                            "en": "Current smoker",
                            "ru": "Курит в настоящее время",
                            "pl": "Pali obecnie"
                        }
                    }
                ]
            }
        }
    )

    current_medications: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "textarea",
                "rows": 2,
                "placeholder": {
                    "en": "List medications taken regularly",
                    "ru": "Перечислите препараты, принимаемые регулярно",
                    "pl": "Wymień regularnie przyjmowane leki"
                }
            }
        }
    )

    last_updated: Optional[datetime] = Field(default_factory=datetime.utcnow)


# ==========
# Семья
# ==========

class FamilyMemberSchema(BaseValidatedModel):
    """
    Схема для вкладки 'Семья'. Использует json_schema_extra для настроек UI.
    """

    phone: str = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "phone",
                "mask": "+9 (999) 999-99-99",
                "placeholder": {
                    "en": "Enter phone number",
                    "ru": "Введите номер телефона",
                    "pl": "Wprowadź numer telefonu"
                }
            }
        }
    )

    relationship: RelationshipEnum = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "select",
                "placeholder": {
                    "en": "Select relationship",
                    "ru": "Выберите тип родства",
                    "pl": "Wybierz relację"
                }
            }
        }
    )

    status: FamilyStatusEnum = Field(
        default=FamilyStatusEnum.PENDING,
        json_schema_extra={
            "settings": {
                "type": "select",
                "placeholder": {
                    "en": "Select status",
                    "ru": "Выберите статус",
                    "pl": "Wybierz status"
                }
            }
        }
    )

    birth_date: Optional[datetime] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "calendar",
                "placeholder": {
                    "en": "Select birth date",
                    "ru": "Выберите дату рождения",
                    "pl": "Wybierz datę urodzenia"
                }
            }
        }
    )

    member_name: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "text",
                "hide_if_none": True,
                "placeholder": {
                    "en": "Full name",
                    "ru": "Полное имя",
                    "pl": "Imię i nazwisko"
                }
            }
        }
    )

    member_id: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "text",
                "hide_if_none": True,
                "placeholder": {
                    "en": "Patient ID",
                    "ru": "ID пациента",
                    "pl": "ID pacjenta"
                }
            }
        }
    )

    bonus_balance: Optional[int] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "int",
                "hide_if_none": True,
                "placeholder": {
                    "en": "Bonuses",
                    "ru": "Бонусы",
                    "pl": "Bonusy"
                }
            }
        }
    )


# ==========
# Бонусная программа
# ==========


class BonusTransactionSchema(BaseValidatedModel):
    """
    Схема для вкладки 'Бонусная программа' (транзакции).
    """

    title: str = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "text",
                "placeholder": {
                    "en": "Enter title",
                    "ru": "Введите название",
                    "pl": "Wprowadź tytuł"
                }
            }
        }
    )

    description: Optional[str] = Field(
        default="",
        json_schema_extra={
            "settings": {
                "type": "str",
                "placeholder": {
                    "en": "Additional comment",
                    "ru": "Дополнительный комментарий",
                    "pl": "Dodatkowy komentarz"
                }
            }
        }
    )

    date_time: Optional[datetime] = Field(default_factory=datetime.utcnow)

    transaction_type: TransactionTypeEnum = Field(
        default=TransactionTypeEnum.ACCRUED,
        json_schema_extra={
            "settings": {
                "type": "select",
                "placeholder": {
                    "en": "Select transaction type",
                    "ru": "Выберите тип операции",
                    "pl": "Wybierz typ transakcji"
                }
            }
        }
    )

    amount: int = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "number",
                "placeholder": {
                    "en": "Amount",
                    "ru": "Сумма",
                    "pl": "Kwota"
                }
            }
        }
    )

    referral_code: str = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "str",
                "can_copy": True
            }
        }
    )


class BonusProgramSchema(BaseValidatedModel):
    """
    Схема для вкладки 'Бонусная программа' (основная).
    """

    balance: int = Field(
        default=0,
        json_schema_extra={
            "settings": {
                "type": "int",
                "placeholder": {
                    "en": "Current balance",
                    "ru": "Текущий баланс",
                    "pl": "Aktualne saldo"
                }
            }
        }
    )

    referral_code: Optional[str] = Field(
        default="",
        json_schema_extra={
            "settings": {
                "type": "str",
                "placeholder": {
                    "en": "Referral code",
                    "ru": "Реферальный код",
                    "pl": "Kod polecający"
                }
            }
        }
    )

    last_updated: Optional[datetime] = Field(default_factory=datetime.utcnow)

    transaction_history: List[BonusTransactionSchema]

# ==========
# Согласия
# ==========


class ConsentSchema(BaseValidatedModel):
    """
    Схема для вкладки 'Согласия пользователя'.
    """

    consents: List[ConsentEnum] = Field(
        json_schema_extra={
            "settings": {
                "color_map": {
                    "yes": "#4CAF50",
                    "no": "#F44336"
                },
                "placeholder": {
                    "en": "Select consents",
                    "ru": "Выберите согласия",
                    "pl": "Wybierz zgody"
                }
            }
        }
    )

    last_updated: Optional[datetime] = Field(default_factory=datetime.utcnow)

# ==========
# Встречи
# ==========


class AppointmentSchema(BaseModel):
    """
    Схема для вкладки 'Визиты пациента'. Только для чтения (read-only).
    """

    visit_date: date = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "calendar",
                "readonly": True,
                "placeholder": {
                    "ru": "Дата визита",
                    "en": "Visit date",
                    "pl": "Data wizyty"
                }
            }
        }
    )

    start: time = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "time",
                "readonly": True
            }
        }
    )

    end: time = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "time",
                "readonly": True
            }
        }
    )

    doctor_name: str = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "text",
                "readonly": True,
                "placeholder": {
                    "ru": "Имя врача",
                    "en": "Doctor name",
                    "pl": "Imię lekarza"
                }
            }
        }
    )

    status: Optional[str] = Field(
        None,
        json_schema_extra={
            "settings": {
                "type": "select",
                "readonly": True,
                "placeholder": {
                    "ru": "Статус визита",
                    "en": "Appointment status",
                    "pl": "Status wizyty"
                }
            }
        }
    )
