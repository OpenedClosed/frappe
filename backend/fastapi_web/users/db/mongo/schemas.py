"""Схемы приложения Пользователи для работы с БД MongoDB."""
from datetime import datetime
from typing import Optional

from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator

from db.mongo.base.schemas import BaseValidatedModel, Photo
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
    """Пользователь."""
    username: Optional[str] = Field(None)
    password: str = Field("", min_length=5)
    role: RoleEnum = RoleEnum.CLIENT
    is_active: bool = Field(default=True) 
    created_at: datetime = Field(default_factory=datetime.utcnow)
    full_name: Optional[str] = Field(None)
    avatar: Optional[Photo] = None

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
    """Данные пользователя."""
    data: Optional[dict] = {}

    async def get_email(self) -> Optional[str]:
        """Получить email из контактной информации."""
        contact = None
        if self.data and self.data.get("user_id"):
            user_id = self.data.get("user_id")
            contact = await mongo_db["patients_contact_info"].find_one({"user_id": user_id})
        return contact.get("email") if contact else None

    async def get_phone(self) -> Optional[str]:
        """Получить номер телефона из основной информации."""
        main = None
        if self.data and self.data.get("user_id"):
            user_id = self.data.get("user_id")
            main = await mongo_db["patients_main_info"].find_one({"user_id": user_id})
        return main.get("phone") if main else None

    async def get_full_user_data(self) -> dict:
        """
        Возвращает объединённую информацию о пользователе: базовую, контактную и основную.
        """
        base_data = self.dict(exclude={"password"})
        user_id = self.data.get("user_id") if self.data else None

        contact_info = await mongo_db["patients_contact_info"].find_one({"user_id": user_id}) or {}
        main_info = await mongo_db["patients_main_info"].find_one({"user_id": user_id}) or {}

        full_data = {
            **base_data,
            "main_info": main_info,
            "contact_info": contact_info,
        }

        return full_data
