"""Админ-панель приложения Пользователи."""
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException

from admin_core.admin_registry import admin_registry
from admin_core.base_admin import BaseAdmin
from db.mongo.db_init import mongo_db

from .db.mongo.schemas import User


class UserAdmin(BaseAdmin):
    """Админка для управления пользователями."""

    collection_name = "users"
    model = User
    verbose_name = {
        "en": "User",
        "pl": "Użytkownik",
        "uk": "Користувач",
        "zh": "用户",
        "es": "Usuario",
        "ru": "Пользователь"
    }
    plural_name = {
        "en": "Users",
        "pl": "Użytkownicy",
        "uk": "Користувачі",
        "zh": "用户",
        "es": "Usuarios",
        "ru": "Пользователи"
    }
    icon = "pi pi-user"
    description = {
        "en": "Manage users in the system",
        "pl": "Zarządzaj użytkownikami w systemie",
        "uk": "Керування користувачами у системі",
        "zh": "管理系统中的用户",
        "es": "Gestionar usuarios en el sistema",
        "ru": "Управление пользователями в системе"
    }

    detail_fields = ["username", "is_superuser"]
    list_display = ["username", "is_superuser"]
    read_only_fields = []

    field_titles = {
        "username": {
            "en": "Username", "pl": "Nazwa użytkownika", "uk": "Ім'я користувача", "zh": "用户名", "es": "Nombre de usuario", "ru": "Имя пользователя"
        },
        "password": {
            "en": "Hashed password", "pl": "Zahaszowane hasło", "uk": "Хешований пароль", "zh": "哈希密码", "es": "Contraseña cifrada", "ru": "Хешированный пароль"
        },
        "is_superuser": {
            "en": "Superuser", "pl": "Superużytkownik", "uk": "Суперкористувач", "zh": "超级用户", "es": "Superusuario", "ru": "Суперпользователь"
        }
    }

    async def _hash_password_if_needed(
        self, data: dict, existing_hashed_password: Optional[str] = None
    ) -> None:
        """Хэширует пароль, если передан и не является уже хэшем."""
        if "password" in data and data["password"]:
            if existing_hashed_password and data["password"] == existing_hashed_password:
                return  # Пропускаем, если пароль уже хэширован
            user_schema = self.model(**data)
            data["hashed_password"] = user_schema.set_password()
            del data["password"]

    async def create(self, data: dict) -> dict:
        """Создание пользователя с хэшированием пароля и проверкой уникальности."""
        validated_data = await self.validate_data(data)
        await self._hash_password_if_needed(validated_data)

        if await self.db.find_one({"username": validated_data["username"]}):
            raise HTTPException(
                status_code=400,
                detail=f"User with username '{validated_data['username']}' already exists."
            )

        result = await self.db.insert_one(validated_data)
        return await self._get_or_raise(result.inserted_id, "Не удалось получить созданный объект.")

    async def update(self, object_id: str, data: dict) -> dict:
        """Обновление пользователя с хэшированием пароля и проверкой уникальности."""
        validated_data = await self.validate_data(data, partial=True)

        existing_user = await self.get(object_id)
        if not existing_user:
            raise HTTPException(
                status_code=404,
                detail="Пользователь не найден.")

        await self._hash_password_if_needed(validated_data, existing_user.get("hashed_password"))

        if "username" in validated_data:
            if await self.db.find_one({"username": validated_data["username"], "_id": {"$ne": ObjectId(object_id)}}):
                raise HTTPException(
                    status_code=400,
                    detail=f"User with username '{validated_data['username']}' already exists."
                )

        result = await self.db.update_one({"_id": ObjectId(object_id)}, {"$set": validated_data})
        if result.matched_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Объект не найден для обновления."
            )

        return await self._get_or_raise(object_id, "Не удалось получить обновленный объект.")

    async def _get_or_raise(self, object_id: str, error_message: str) -> dict:
        """Получает объект по ID или выбрасывает ошибку."""
        obj = await self.get(str(object_id))
        if not obj:
            raise HTTPException(status_code=500, detail=error_message)
        return obj


admin_registry.register("users", UserAdmin(mongo_db))
