"""Схемы приложения Административная зона для работы с БД MongoDB."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from db.mongo.base.schemas import BaseValidatedModel

from .enums import (AppointmentStatusEnum, GenderEnum, LanguageEnum,
                    NotificationTypeEnum, SubscriptionStatusEnum)


class MedicalForm(BaseValidatedModel):
    """Медицинская анкета пользователя."""
    allergies: Optional[str] = None
    blood_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserProfile(BaseValidatedModel):
    """Профиль пользователя для личного кабинета."""
    email: EmailStr
    phone_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[GenderEnum] = None
    birth_date: Optional[datetime] = None
    is_2fa_enabled: bool = False
    subscription_status: Optional[SubscriptionStatusEnum] = None
    medical_forms: List[MedicalForm] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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


class Appointment(BaseValidatedModel):
    """Модель записи на приём."""
    datetime: datetime
    duration: int = Field(default=30, description="Длительность визита (мин).")
    status: Optional[AppointmentStatusEnum] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CalendarIntegration(BaseValidatedModel):
    """Интеграция с внешним календарём."""
    provider: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: datetime
    last_sync: datetime = Field(default_factory=datetime.utcnow)


class HistoryOfAppointment(BaseValidatedModel):
    """История одного приёма (визита к врачу)."""
    date: datetime = Field(default_factory=datetime.utcnow)
    doctor_name: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    cost_money: float = 0.0
    cost_bonus: float = 0.0
    pdf_reports: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BonusTransaction(BaseValidatedModel):
    """Транзакция начисления/списания бонусов."""
    date: datetime = Field(default_factory=datetime.utcnow)
    amount: float
    is_accrual: bool
    comment: Optional[str] = None


class BonusProgram(BaseValidatedModel):
    """Бонусная программа пользователя."""
    balance: float = 0.0
    referral_link: Optional[str] = None
    family_sharing: bool = False
    transactions: List[BonusTransaction] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FamilyRelation(BaseValidatedModel):
    """Одно отношение внутри семейного аккаунта."""
    relative_user_id: str
    confirmed: bool = False
    two_factor_required: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Family(BaseValidatedModel):
    """Модель семейного аккаунта."""
    family_name: Optional[str] = None
    owner_user_id: str
    members: List[FamilyRelation] = Field(default_factory=list)
    shared_bonus: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Notification(BaseValidatedModel):
    """Уведомление пользователю."""
    user_id: str
    notification_type: NotificationTypeEnum = NotificationTypeEnum.OTHER
    message: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserSettings(BaseValidatedModel):
    """Настройки пользователя."""
    user_id: str
    language: LanguageEnum = LanguageEnum.RU
    notifications_enabled: bool = True
    password_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
