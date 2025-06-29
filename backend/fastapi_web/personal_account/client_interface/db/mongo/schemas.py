"""Схемы приложения Административная зона для работы с БД MongoDB."""
from datetime import date, datetime, time
import re
from typing import Any, Dict, List, Optional

from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr, Field, ValidationInfo, model_validator

from db.mongo.base.schemas import BaseValidatedModel, Photo
from integrations.panamedica.client import get_client
from utils.help_functions import normalize_numbers

from .enums import (AccountVerificationEnum, ConditionEnum, ConsentEnum,
                    FamilyStatusEnum, GenderEnum, RelationshipEnum,
                    TransactionTypeEnum)

import re
from pydantic import field_validator

# ==========
# Регистрация
# ==========


class RegistrationSchema(BaseModel):
    """
    Шаг 1: Данные для регистрации (телефон обязателен).
    """
    phone: str
    email: Optional[EmailStr] = None
    first_name: str
    last_name: str
    birth_date: Optional[datetime] = None
    gender: Optional[str] = None
    password: str
    password_confirm: str
    referral_code: Optional[str] = None
    accept_terms: bool = False

    def passwords_match(self) -> bool:
        """
        Проверяет совпадение введённого пароля и подтверждения.
        """
        return self.password == self.password_confirm
    
    def password_strength_errors(self) -> Optional[dict[str, str]]:
        """
        Проверяет силу пароля и возвращает словарь ошибок по языкам, если пароль слабый.
        """
        password = self.password

        if len(password) < 8:
            return {
                "ru": "Пароль должен быть не менее 8 символов.",
                "en": "Password must be at least 8 characters long.",
                "pl": "Hasło musi mieć co najmniej 8 znaków."
            }
        if not re.search(r'[A-Z]', password):
            return {
                "ru": "Пароль должен содержать хотя бы одну заглавную букву.",
                "en": "Password must contain at least one uppercase letter.",
                "pl": "Hasło musi zawierać co najmniej jedną wielką literę."
            }
        if not re.search(r'[a-z]', password):
            return {
                "ru": "Пароль должен содержать хотя бы одну строчную букву.",
                "en": "Password must contain at least one lowercase letter.",
                "pl": "Hasło musi zawierać co najmniej jedną małą literę."
            }
        if not re.search(r'\d', password):
            return {
                "ru": "Пароль должен содержать хотя бы одну цифру.",
                "en": "Password must contain at least one digit.",
                "pl": "Hasło musi zawierać co najmniej jedną cyfrę."
            }
        if not re.search(r'[^\w\s]', password):
            return {
                "ru": "Пароль должен содержать хотя бы один специальный символ.",
                "en": "Password must contain at least one special character.",
                "pl": "Hasło musi zawierać co najmniej jeden znak specjalny."
            }

        return None

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


class MainInfoSchema(BaseValidatedModel):
    """
    Основная информация о пациенте, хранится в MongoDB.
    """
    patient_id: Optional[str] = Field(
        default=None,
    )

    last_name: Optional[str] = None
    first_name: Optional[str] = None
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

    gender: Optional[str] = Field(
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
    crm_link_status: Optional[str] = Field(
        default="",
        json_schema_extra={"settings": {"readonly": True}}
    )
    referral_id: Optional[str] = Field(
        default=None,
        json_schema_extra={"settings": {"readonly": True}}
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        json_schema_extra={"settings": {"readonly": True}}
    )

    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


# ==========
# Контактная информация
# ==========


# class ContactInfoSchema(BaseValidatedModel):
#     """
#     Схема для вкладки 'Контактная информация'.
#     """

#     email: EmailStr = Field(
#         ...,
#         json_schema_extra={
#             "settings": {
#                 "type": "email",
#                 "placeholder": {
#                     "ru": "Введите e-mail",
#                     "en": "Enter email",
#                     "pl": "Wprowadź e-mail"
#                 }
#             }
#         }
#     )

#     phone: str = Field(
#         ...,
#         json_schema_extra={
#             "settings": {
#                 "type": "phone",
#                 "mask": "+99 (999) 999-999"
#             }
#         }
#     )

#     address: Optional[str] = Field(
#         default=None,
#         json_schema_extra={
#             "settings": {
#                 "type": "textarea",
#                 "rows": 2,
#                 "placeholder": {
#                     "ru": "Введите адрес",
#                     "en": "Enter address",
#                     "pl": "Wprowadź adres"
#                 }
#             }
#         }
#     )

#     pesel: Optional[str] = Field(
#         default=None,
#         json_schema_extra={
#             "settings": {
#                 "type": "pesel",
#                 "placeholder": {
#                     "ru": "Введите идентификатор",
#                     "en": "Enter identifier",
#                     "pl": "Wprowadź identyfikator"
#                 }
#             }
#         }
#     )

#     emergency_contact: Optional[str] = Field(
#         default=None,
#         json_schema_extra={
#             "settings": {
#                 "type": "phone",
#                 "mask": "+99 (999) 999-999",
#                 "allowExtraText": True,
#                 "placeholder": {
#                     "ru": "Введите номер экстренного контакта",
#                     "en": "Enter emergency contact number",
#                     "pl": "Wprowadź numer kontaktowy awaryjny"
#                 }
#             }
#         }
#     )

#     updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

#     @model_validator(mode="before")
#     def update_timestamp(cls, data):
#         data["updated_at"] = datetime.utcnow()
#         return data

class ContactInfoSchema(BaseModel):
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
                "mask": "+99 (999) 999-999"
            }
        }
    )

    # ----------------------- Экстренный контакт -----------------------
    emergency_contact_name: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "text",
                "placeholder": {
                    "ru": "Имя экстренного контакта",
                    "en": "Emergency contact name",
                    "pl": "Imię kontaktu awaryjnego"
                }
            }
        }
    )

    emergency_contact_phone: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "phone",
                "mask": "+99 (999) 999-999",
                "placeholder": {
                    "ru": "Телефон экстренного контакта",
                    "en": "Emergency phone number",
                    "pl": "Telefon kontaktu awaryjnego"
                }
            }
        }
    )

    emergency_contact_consent: Optional[bool] = Field(
        default=False,
        json_schema_extra={
            "settings": {
                "label": {
                    "ru": "Я выражаю согласие на предоставление информации о моем здоровье контакту для экстренной связи.",
                    "en": "I consent to sharing my health information with the emergency contact.",
                    "pl": "Wyrażam zgodę na udostępnienie informacji o moim stanie zdrowia kontaktowi w nagłych wypadkach.",
                    "uk": "Я висловлюю згоду на надання інформації про моє здоров'я контакту для екстреного зв'язку.",
                    "de": "Ich stimme der Weitergabe meiner Gesundheitsinformationen an den Notfallkontakt zu."
                }
            }
        }
    )

    # ----------------------- Адрес -----------------------
    country: Optional[str] = Field(
        default=None,
        # json_schema_extra={
        #     "settings": {
        #         "type": "select",
        #         "placeholder": {
        #             "ru": "Страна",
        #             "en": "Country",
        #             "pl": "Kraj"
        #         }
        #     }
        # }
    )

    region: Optional[str] = Field(
        default=None,
        # json_schema_extra={
        #     "settings": {
        #         "type": "select",
        #         "options": [  # можно заменить на динамическое подгрузку
        #             {"label": "Mazowieckie", "value": "Mazowieckie"},
        #             {"label": "Małopolskie", "value": "Małopolskie"},
        #             {"label": "Wielkopolskie", "value": "Wielkopolskie"},
        #             # ...
        #         ],
        #         "placeholder": {
        #             "ru": "Выберите регион",
        #             "en": "Select region",
        #             "pl": "Wybierz województwo"
        #         }
        #     }
        # }
    )

    city: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "placeholder": {
                    "ru": "Город",
                    "en": "City",
                    "pl": "Miasto"
                }
            }
        }
    )

    street: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "placeholder": {
                    "ru": "Улица",
                    "en": "Street",
                    "pl": "Ulica"
                }
            }
        }
    )

    building_number: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "placeholder": {
                    "ru": "Номер дома",
                    "en": "Building number",
                    "pl": "Numer budynku"
                }
            }
        }
    )

    apartment: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "placeholder": {
                    "ru": "Номер квартиры (опционально)",
                    "en": "Apartment number (optional)",
                    "pl": "Numer mieszkania (opcjonalnie)"
                }
            }
        }
    )

    zip: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "type": "text",
                "mask": "XX-XXX",
                "placeholder": {
                    "ru": "Почтовый индекс",
                    "en": "Postal code",
                    "pl": "Kod pocztowy"
                }
            }
        }
    )

    # для обратной совместимости (readonly)
    address: Optional[str] = Field(
        default=None,
        json_schema_extra={
            "settings": {
                "readonly": True
            }
        }
    )

    # ----------------------- Идентификаторы -----------------------
    pesel: Optional[str] = Field(
        default=None,
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

    passport: Optional[str] = Field(
        default=None,
        json_schema_extra={
        }
    )

    # ----------------------- Метаданные -----------------------
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    @model_validator(mode="before")
    def update_timestamp(cls, data):
        data["updated_at"] = datetime.utcnow()
        return data
    
    @field_validator("zip", mode="before")
    def validate_zip_format(cls, v, info: ValidationInfo):
        print('вызвана проврека')
        if v is None or v == "":
            return None

        if not re.match(r"^\d{2}-\d{3}$", v):
            raise ValueError({
                "ru": "Неверный формат почтового индекса. Используйте формат XX-XXX.",
                "en": "Invalid postal code format. Expected format: XX-XXX.",
                "pl": "Nieprawidłowy format kodu pocztowego. Oczekiwany format: XX-XXX.",
                "uk": "Невірний формат поштового індексу. Очікується формат: XX-XXX.",
                "de": "Ungültiges Postleitzahl-Format. Erwartetes Format: XX-XXX."
            })

        return v

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

    chronic_conditions: Optional[List[ConditionEnum]] = Field(
        None,
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
    Схема одной записи во вкладке «Семья».
    """

    phone: str = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "phone",
                "mask": "+99 (999) 999-999",
                "placeholder": {
                    "ru": "Введите номер телефона",
                    "en": "Enter phone number",
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
                    "ru": "Выберите тип родства",
                    "en": "Select relationship",
                    "pl": "Wybierz relację"
                }
            }
        }
    )

    # ▼––– статус оформлен как Enum, но UI получит список «choices»
    status: FamilyStatusEnum = Field(
        # default=FamilyStatusEnum.PENDING,
        # json_schema_extra={
        #     "settings": {
        #         "type": "select",
                # "choices": [
                #     {"value": FamilyStatusEnum.PENDING,   "label": {"ru": "Ожидает",  "en": "Pending",  "pl": "Oczekuje"}},
                #     {"value": FamilyStatusEnum.CONFIRMED, "label": {"ru": "Принято",  "en": "Confirmed","pl": "Przyjęto"}},
                #     {"value": FamilyStatusEnum.DECLINED,  "label": {"ru": "Отклонено","en": "Declined", "pl": "Odrzucono"}},
                # ],
                # "placeholder": {
                #     "ru": "Выберите статус",
                #     "en": "Select status",
                #     "pl": "Wybierz status"
                # }
            # }
        # }

        ...,
        json_schema_extra={
            "settings": {
                "type": "select",
                "placeholder": {
                    "ru": "Выберите тип родства",
                    "en": "Select relationship",
                    "pl": "Wybierz relację"
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
                    "ru": "Выберите дату рождения",
                    "en": "Select birth date",
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
                    "ru": "Полное имя",
                    "en": "Full name",
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
                    "ru": "ID пациента",
                    "en": "Patient ID",
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
                    "ru": "Бонусы",
                    "en": "Bonuses",
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


class ConsentItem(BaseModel):
    """Согласие в CRM."""
    id: int
    accepted: bool

class ConsentSchema(BaseValidatedModel):
    """Согласия пользователя, кеш 60 с."""
    consents: List[ConsentItem] = Field(
        default_factory=list,
        json_schema_extra={
            "settings": {
                "type": "color_multiselect",
                "color_map": {"true": "#4CAF50", "false": "#F44336"},
                "searchable": True,
            }
        },
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)

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
                },
            }
        },
    )

    start: time = Field(
        ...,
        json_schema_extra={"settings": {"type": "time", "readonly": True}},
    )

    end: time = Field(
        ...,
        json_schema_extra={"settings": {"type": "time", "readonly": True}},
    )

    doctor: str = Field(
        ...,
        json_schema_extra={
            "settings": {
                "type": "text",
                "readonly": True,
                "placeholder": {
                    "ru": "Имя врача",
                    "en": "Doctor name",
                    "pl": "Imię lekarza",
                },
            }
        },
    )

    status: str | None = Field(
        None,
        json_schema_extra={
            "settings": {
                "type": "select",
                "readonly": True,
                "placeholder": {
                    "ru": "Статус визита",
                    "en": "Appointment status",
                    "pl": "Status wizyty",
                },
            }
        },
    )
