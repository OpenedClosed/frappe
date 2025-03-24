"""Схемы приложения Административная зона для работы с БД MongoDB."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from .enums import ConditionEnum, ConsentEnum, GenderEnum, HealthFormStatus, RelationshipEnum, TransactionTypeEnum
from db.mongo.base.schemas import BaseValidatedModel

# from .enums import ()


from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel 


# ==========
# Регистрация
# ==========

class RegisterSchema(BaseModel):
    """Шаг 1 регистрации: email/phone + основные поля."""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[datetime] = None
    city: Optional[str] = None
    gender: Optional[str] = None


class ConfirmSchema(RegisterSchema):
    """Шаг 2 регистрации: наследуемся от RegisterSchema, добавляем 'code'."""
    code: str


# ==========
# Основная информация
# ==========


class MainInfoSchema(BaseValidatedModel):
    """
    Схема для вкладки 'Основная информация'
    """

    # Личные данные
    last_name: str
    first_name: str
    patronymic: Optional[str]
    birth_date: date = {
        "settings": {
            "type": "calendar",
            "placeholder": {
                "ru": "Выберите дату рождения",
                "en": "Select birth date",
                "pl": "Wybierz datę urodzenia"
            }
        }
    }
    gender: GenderEnum = {
        "settings": {
            "type": "select",
            "placeholder": {
                "ru": "Выберите пол",
                "en": "Select gender",
                "pl": "Wybierz płeć"
            }
        }
    }

    # Информация о компании
    company_name: Optional[str]

    # Системная информация
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime]







class ContactInfoSchema(BaseModel):
    """
    Схема для вкладки 'Контактная информация'
    (по примеру скриншота, включая поля:
    - Email
    - Телефон
    - Адрес
    - PESEL (идентификатор, может быть в разных странах по-разному)
    - ID документа (паспорт, водительские права и т.д.)
    - Экстренный контакт
    )

    Для примера добавим 'settings' в поля,
    чтобы фронтенд знал, какие виджеты использовать.
    """

    email: EmailStr = {
        "default": "ivan@example.com",
        "settings": {
            "type": "email",       # Позволяет отрисовать email-поле (валидация + формат)
            "placeholder": "Введите e-mail"
        }
    }
    phone: str = {
        "default": "+7 (999) 123-45-67",
        "settings": {
            "type": "phone",       # Можно подкючить маску телефона на фронтенде
            "mask": "+9 (999) 999-99-99"
        }
    }
    address: str = {
        "default": "г. Москва, ул. Примерная, д. 123, кв. 45",
        "settings": {
            "type": "textarea",    # или "type": "address" (кастомное поле) - если хочется расширить
            "rows": 2             # кол-во строк в многострочном поле
        }
    }
    pesel: str = {
        "default": "85051512345",
        "settings": {
            "type": "pesel",       # новый, кастомный тип для идентификатора
            # Фронтенд может решить, как валидировать PESEL (Польша), ИИН (Казахстан), СНИЛС (Россия) и т.д.
        }
    }
    doc_id: str = {
        "default": "4510 123456",
        "settings": {
            "type": "text",        # Обычное текстовое поле (можно придумать что-то вроде "document_id")
            "label": "Номер документа"
        }
    }
    emergency_contact: Optional[str] = {
        "default": "+7 (999) 765-43-21 (Анна, жена)",
        "settings": {
            "type": "phone",
            "mask": "+9 (999) 999-99-99",
            "allowExtraText": True  # Допустим, разрешаем приписывать комментарий в конце
        }
    }
    updated_at: datetime = {
        "default": datetime.now(),
        "settings": {
            "type": "datetime"
        }
    }


class HealthSurveySchema(BaseModel):
    """
    Схема для вкладки 'Анкета здоровья'.
    Здесь демонстрируются:
    - Поле с Enum (ConditionEnum) для хронических заболеваний,
    - Поле с ручным списком choices (smoking_status).
    """

    allergies: str = {
        "default": {
            "en": "Penicillin, birch pollen",
            "ru": "Пенициллин, пыльца березы"
        },
        "settings": {
            "type": "textarea",
            "rows": 2,
            "placeholder": {
                "en": "List allergens separated by commas",
                "ru": "Перечислите аллергены через запятую"
            }
        }
    }

    # Множественное поле с Enum
    chronic_conditions: List[ConditionEnum] = {
        "default": [
            ConditionEnum.DIABETES,
            ConditionEnum.ASTHMA
        ],
        "settings": {
            "type": "multiselect"
            # choices не указываем явно, так как берем значения из Enum ConditionEnum
        }
    }

    # Поле со списком выбора (без Enum), где для каждого пункта укажем свои RU/EN и цвет
    smoking_status: str = {
        "default": {
            "en": "Former smoker",
            "ru": "Бывший курильщик"
        },
        "settings": {
            "type": "select",
            "placeholder": {
                "en": "Select smoking status",
                "ru": "Выберите статус курения"
            },
            "choices": [
                {
                    "value": {
                        "en": "Never smoked",
                        "ru": "Никогда не курил",
                        "settings": {
                            "color": "#757575"
                        }
                    }
                },
                {
                    "value": {
                        "en": "Former smoker",
                        "ru": "Бывший курильщик",
                        "settings": {
                            "color": "#FFA726"
                        }
                    }
                },
                {
                    "value": {
                        "en": "Current smoker",
                        "ru": "Курит в настоящее время",
                        "settings": {
                            "color": "#D32F2F"
                        }
                    }
                }
            ]
        }
    }

    current_medications: str = {
        "default": {
            "en": "Enalapril 10mg daily",
            "ru": "Эналаприл 10мг ежедневно"
        },
        "settings": {
            "type": "textarea",
            "rows": 2,
            "placeholder": {
                "en": "List medications taken regularly",
                "ru": "Перечислите препараты, принимаемые регулярно"
            }
        }
    }

    # Поле даты/времени
    last_updated: datetime = {
        "default": datetime(2023, 5, 15, 13, 30),
        "settings": {
            "type": "datetime",
            "placeholder": {
                "en": "Pick date/time",
                "ru": "Выберите дату и время"
            }
        }
    }

    form_status: HealthFormStatus = {
        "default": HealthFormStatus.APPROVED,
        "settings": {
            "type": "radio_select",
            "placeholder": {
                "en": "Choose survey status",
                "ru": "Выберите статус анкеты"
            }
            # Перечисление вариантов берем из Enum HealthFormStatus
        }
    }


class FamilyMemberSchema(BaseModel):
    """
    Данные одного члена семьи.
    """

    full_name: str = {
        "default": {
            "en": "Anna Petrova",
            "ru": "Анна Петрова"
        },
        "settings": {
            "type": "text",
            "placeholder": {
                "en": "Enter full name",
                "ru": "Введите полное имя"
            }
        }
    }

    patient_id: str = {
        "default": {
            "en": "PAT-789012",
            "ru": "PAT-789012"
        },
        "settings": {
            "type": "text",
            "placeholder": {
                "en": "Patient ID",
                "ru": "ID пациента"
            }
        }
    }

    birth_date: Optional[date] = {
        "default": None,
        "settings": {
            "type": "calendar",
            "placeholder": {
                "en": "Select birth date",
                "ru": "Выберите дату рождения"
            }
        }
    }

    relationship: RelationshipEnum = {
        "default": RelationshipEnum.SPOUSE,
        "settings": {
            "type": "select",
            "placeholder": {
                "en": "Select relationship",
                "ru": "Выберите тип родства"
            }
            # choices будут парситься из RelationshipEnum
        }
    }


class TransactionSchema(BaseModel):
    """
    Описание одной транзакции в бонусной программе.
    """

    transaction_type: TransactionTypeEnum = {
        "default": TransactionTypeEnum.ACCRUED,
        "settings": {
            "type": "select",
            "placeholder": {
                "en": "Select transaction type",
                "ru": "Выберите тип операции"
            }
            # choices из Enum TransactionTypeEnum
        }
    }

    title: str = {
        "default": {
            "en": "Referral",
            "ru": "Реферал"
        },
        "settings": {
            "type": "text",
            "placeholder": {
                "en": "Enter reason/title",
                "ru": "Укажите причину/название"
            }
        }
    }

    date_time: datetime = {
        "default": datetime(2023, 6, 1, 13, 0),
        "settings": {
            "type": "datetime",
            "placeholder": {
                "en": "Pick transaction date/time",
                "ru": "Выберите дату и время транзакции"
            }
        }
    }

    amount: int = {
        "default": 100,
        "settings": {
            "type": "number",
            "placeholder": {
                "en": "Transaction amount",
                "ru": "Сумма транзакции"
            }
        }
    }

    comment: Optional[str] = {
        "default": {
            "en": "",
            "ru": ""
        },
        "settings": {
            "type": "textarea",
            "rows": 2,
            "placeholder": {
                "en": "Additional comment",
                "ru": "Дополнительный комментарий"
            }
        }
    }



class BonusProgramSchema(BaseModel):
    """
    Вкладка 'Бонусная программа'.
    Содержит:
    - Текущий баланс (balance) — вычисляемое поле
    - Реферальный код (referral_code)
    - Дата последнего обновления (last_updated)
    - История транзакций (transaction_history) — список TransactionSchema
    """

    balance: int = {
        "default": 450,  # Заглушка (будет вычисляться или подтягиваться из логики)
        "settings": {
            "type": "number"
            # read_only_fields для него укажем в админке
        }
    }

    referral_code: str = {
        "default": "IVAN2023",
        "settings": {
            "type": "text",
            "placeholder": {
                "en": "Referral code",
                "ru": "Реферальный код"
            }
        }
    }

    last_updated: datetime = {
        "default": datetime(2023, 6, 10, 17, 20),
        "settings": {
            "type": "datetime",
            "placeholder": {
                "en": "Date of last bonus update",
                "ru": "Дата последнего обновления"
            }
        }
    }

    transaction_history: List[TransactionSchema] = []


class ConsentItemSchema(BaseModel):
    """
    Одно согласие пользователя.
    """
    consent_type: ConsentEnum = {
        "default": ConsentEnum.GDPR,
        "settings": {
            "type": "select",
            "placeholder": {
                "en": "Select the type of consent",
                "ru": "Выберите тип согласия"
            }
            # Сами варианты берем из ConsentEnum
        }
    }

    accepted: bool = {
        "default": True,
        "settings": {
            "type": "boolean_toggle",
            # Или type: "switch", "checkbox", "radio" — в зависимости от вашего фронта
        }
    }


class UserConsentsSchema(BaseModel):
    """
    Вкладка 'Согласия'. 
    Хранит список согласий и дату последнего обновления.
    """
    last_updated: datetime = {
        "default": datetime(2023, 1, 15, 11, 30),
        "settings": {
            "type": "datetime",
            "placeholder": {
                "en": "Last update date/time",
                "ru": "Дата и время последнего обновления согласий"
            }
        }
    }

    consents: List[ConsentItemSchema] = []