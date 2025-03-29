"""Схемы приложения Пользователи для работы с БД MongoDB."""
from datetime import datetime
from token import OP
from typing import Optional

from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, field_validator

from db.mongo.base.schemas import BaseValidatedModel
from db.mongo.db_init import mongo_db
from infra import settings

from .enums import RoleEnum

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Settings(BaseModel):
    """Настройки JWT."""
    authjwt_secret_key: str = settings.SECRET_KEY
    authjwt_access_token_expires: int = 43200
    authjwt_refresh_token_expires: int = 604800


class User(BaseValidatedModel):
    username: Optional[str] = Field(None)
    password: str = Field("", min_length=5)
    role: RoleEnum = RoleEnum.CLIENT
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("username")
    def validate_username(cls, v):
        if v and len(v) < 3:
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
            return
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


class UserWithData(User):
    data: Optional[dict] = {}

    async def get_email(self) -> Optional[str]:
        contact = None
        if self.data and self.data.get("user_id"):
            user_id = self.data.get("user_id")
            contact = await mongo_db["patients_contact_info"].find_one({"user_id": user_id})
        return contact.get("email") if contact else None

    async def get_phone(self) -> Optional[str]:
        main = None
        if self.data and self.data.get("user_id"):
            user_id = self.data.get("user_id")
            main = await mongo_db["patients_main_info"].find_one({"user_id": user_id})
        return main.get("phone") if main else None
