"""Схемы приложения Пользователи для работы с БД MongoDB."""
from datetime import datetime
from typing import Optional

from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator

from infra import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Settings(BaseModel):
    """Настройки JWT."""
    authjwt_secret_key: str = settings.SECRET_KEY
    authjwt_access_token_expires: int = 43200
    authjwt_refresh_token_expires: int = 604800


class User(BaseModel):
    """
    Базовая схема пользователя.
    """
    username: str = Field(..., min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=5)
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("username")
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        """Проверка структуры пароля."""
        if v is not None and len(v) < 5:
            raise ValueError("Password must be at least 5 characters long")
        return v

    def set_password(self):
        """
        Хеширует пароль.
        """
        if not self.password:
            return None
        self.password = pwd_context.hash(self.password)

    def check_password(self, raw_password: str) -> bool:
        """
        Проверка Пароля.
        """
        if not self.password:
            return False
        return pwd_context.verify(raw_password, self.password)


class LoginSchema(BaseModel):
    """Схема входа."""
    username: str
    password: str
