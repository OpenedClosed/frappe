"""Схемы приложения Административная зона для работы с БД MongoDB."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from db.mongo.base.schemas import BaseValidatedModel

# from .enums import ()


from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel 


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


class MainInfoSchema(BaseValidatedModel):
    """
    Схема для вкладки 'Основная информация'
    """
    # Личные данные
    last_name: str = "Петров"
    first_name: str = "Иван"
    patronymic: Optional[str] = "Сергеевич"
    birth_date: date = date(1985, 5, 15)
    gender: str = "Мужской"

    # Информация о компании
    company_name: Optional[str] = "ООО Рога и Копыта"

    # Системная информация
    patient_id: str = "PAT-123456"
    created_at: datetime = datetime(2023, 1, 15, 11, 30)
    updated_at: datetime = datetime(2023, 6, 10, 17, 20)
