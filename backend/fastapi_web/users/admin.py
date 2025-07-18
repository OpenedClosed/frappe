"""Админ-панель приложения Пользователи."""
from typing import List, Optional

from admin_core.base_admin import BaseAdmin
from bson import ObjectId
from crud_core.permissions import SuperAdminOnlyPermission
from crud_core.registry import admin_registry
from db.mongo.db_init import mongo_db
from fastapi import HTTPException

from .db.mongo.schemas import User


class UserAdmin(BaseAdmin):
    """Админка для управления пользователями (добавлено поле is_active)."""

    model = User
    collection_name = "users"
    permission_class = SuperAdminOnlyPermission()

    verbose_name = {
        "en": "User",  "ru": "Пользователь",  "pl": "Użytkownik",
        "uk": "Користувач",  "ka": "მომხმარებელი",
    }
    plural_name = {
        "en": "Users",  "ru": "Пользователи",  "pl": "Użytkownicy",
        "uk": "Користувачі",  "ka": "მომხმარებლები",
    }
    icon = "pi pi-user"
    description = {
        "en": "Manage users in the system",
        "ru": "Управление пользователями в системе",
        "pl": "Zarządzanie użytkownikami w systemie",
        "uk": "Керування користувачами в системі",
        "ka": "მომხმარებლების მართვა სისტემაში",
    }

    list_display   = ["username", "full_name", "role", "is_active", "created_at"]   # ← +is_active
    detail_fields  = ["username", "password", "full_name", "avatar",
                      "role", "is_active", "created_at"]                           # ← +is_active
    read_only_fields = ["created_at"]

    field_titles = {
        "username":    {"en": "Username",   "ru": "Имя пользователя",  "pl": "Nazwa użytkownika", "uk": "Ім’я користувача", "ka": "მომხმარებლის სახელი"},
        "password":    {"en": "Password (hashed)", "ru": "Хешированный пароль", "pl": "Hasło (zhashowane)", "uk": "Пароль (хешований)", "ka": "პაროლი (დაშიფრული)"},
        "role":        {"en": "Role",       "ru": "Роль",  "pl": "Rola",  "uk": "Роль",  "ka": "როლი"},
        "full_name":   {"en": "Full name",  "ru": "Полное имя",  "pl": "Pełne imię", "uk": "Повне ім’я", "ka": "სრული სახელი"},
        "avatar":      {"en": "Avatar",     "ru": "Аватар",  "pl": "Awatar", "uk": "Аватар", "ka": "ავატარი"},
        "created_at":  {"en": "Created at", "ru": "Дата создания", "pl": "Data utworzenia", "uk": "Дата створення", "ka": "შექმნის თარიღი"},
        "is_active":   {"en": "Is active",  "ru": "Активен",          "pl": "Aktywny",          "uk": "Активний",      "ka": "აქტიური"},  # ← НОВОЕ
    }

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        current_user: Optional[dict] = None,
        format: bool = True,
    ) -> List[dict]:
        """
        • При первом же чтении админ-списка проверяем всех юзеров.  
        • Тем, у кого поле `is_active` отсутствует, выставляем True.
        """
        # 1. Добавим поле во всей коллекции одним запросом — это быстро.
        await self.db.update_many(
            {"is_active": {"$exists": False}},
            {"$set": {"is_active": True}}
        )

        # 2. Получаем обычный queryset
        docs = await super().get_queryset(
            filters, sort_by, order, page, page_size, current_user, format=False
        )

        # 3. При необходимости форматируем
        return [await self.format_document(d, current_user) if format else d for d in docs]


    async def hash_password_if_needed(self, data: dict) -> None:
        """
        Хэширует пароль через метод схемы, если он передан и ещё не хэширован.
        """
        if "password" in data and data["password"]:
            if data["password"].startswith("$2b$"):
                return
            user_schema = self.model(**data)
            user_schema.set_password()
            data["password"] = user_schema.password

    async def create(self, data: dict,
                     current_user: Optional[dict] = None) -> dict:
        """
        Создание пользователя с хэшированием пароля и проверкой уникальности.
        """
        self.check_permission("create", user=current_user)

        validated_data = await self.validate_data(data)
        await self.hash_password_if_needed(validated_data)

        if await self.db.find_one({"username": validated_data["username"]}):
            raise HTTPException(
                status_code=400,
                detail=f"User with username '{validated_data['username']}' already exists."
            )

        result = await self.db.insert_one(validated_data)
        return await self.get_or_raise(result.inserted_id, "Failed to retrieve created object.", current_user=current_user)

    async def update(self, object_id: str, data: dict,
                     current_user: Optional[dict] = None) -> dict:
        """
        Обновление пользователя с хэшированием пароля и проверкой уникальности.
        """
        self.check_permission("update", user=current_user)

        validated_data = await self.validate_data(data, partial=True)
        existing_user = await self.get(object_id, current_user=current_user)
        if not existing_user:
            raise HTTPException(404, "User not found.")

        full_data = {**existing_user, **validated_data}
        await self.hash_password_if_needed(full_data)

        if "password" in full_data:
            validated_data["password"] = full_data["password"]

        if "username" in validated_data:
            if await self.db.find_one({
                "username": validated_data["username"],
                "_id": {"$ne": ObjectId(object_id)}
            }):
                raise HTTPException(
                    status_code=400,
                    detail=f"User with username '{validated_data['username']}' already exists."
                )

        result = await self.db.update_one({"_id": ObjectId(object_id)}, {"$set": validated_data})
        if result.matched_count == 0:
            raise HTTPException(404, "Object not found for update.")

        return await self.get_or_raise(object_id, "Failed to retrieve updated object.", current_user=current_user)

    async def get_or_raise(self, object_id: str, error_message: str,
                           current_user: Optional[dict] = None) -> dict:
        """
        Получает объект по ID или выбрасывает ошибку.
        """
        obj = await self.get(str(object_id), current_user=current_user)
        if not obj:
            raise HTTPException(status_code=500, detail=error_message)
        return obj


admin_registry.register("users", UserAdmin(mongo_db))
