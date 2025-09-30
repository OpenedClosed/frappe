"""Основные классы резрешений для CRUD."""
from typing import List, Optional

from db.mongo.db_init import mongo_db
from fastapi import HTTPException
from pydantic import BaseModel
from users.db.mongo.enums import RoleEnum


class BasePermission:
    """Базовый класс для всех Permissions."""

    def check(self, action: str,
              user: Optional[BaseModel] = None, obj: Optional[dict] = None) -> None:
        """
        Универсальный метод проверки прав.
        Если права нет — выбрасывает HTTPException(403, "...").
        """
        raise NotImplementedError("Permission check not implemented.")

    async def get_base_filter(self, user: Optional[BaseModel]) -> dict:
        """
        Возвращает фильтр для выборки объектов из базы.
        Например, {"user_id": user.id} — если нужно ограничить доступ к своим объектам.
        По умолчанию: доступ ко всем.
        """
        return {}


class MethodPermissionMixin(BasePermission):
    """Миксин, который даёт метод-ориентированный интерфейс."""

    def can_create(self, user: Optional[BaseModel],
                   obj: Optional[dict]) -> bool:
        return True

    def can_read(self, user: Optional[BaseModel], obj: Optional[dict]) -> bool:
        return True

    def can_update(self, user: Optional[BaseModel],
                   obj: Optional[dict]) -> bool:
        return True

    def can_delete(self, user: Optional[BaseModel],
                   obj: Optional[dict]) -> bool:
        return True

    def check(self, action: str,
              user: Optional[BaseModel] = None, obj: Optional[dict] = None) -> None:
        if action == "create" and not self.can_create(user, obj):
            raise HTTPException(403, "No permission to create.")
        elif action == "read" and not self.can_read(user, obj):
            raise HTTPException(403, "No permission to read.")
        elif action == "update" and not self.can_update(user, obj):
            raise HTTPException(403, "No permission to update.")
        elif action == "delete" and not self.can_delete(user, obj):
            raise HTTPException(403, "No permission to delete.")


class AllowAll(MethodPermissionMixin):
    """Разрешает доступ любому пользователю (даже анонимному)."""
    pass


class IsAuthenticated(MethodPermissionMixin):
    """Разрешает доступ только если пользователь залогинен."""

    def can_create(self, user, obj):
        return bool(user)

    def can_read(self, user, obj):
        return bool(user)

    def can_update(self, user, obj):
        return bool(user)

    def can_delete(self, user, obj):
        return bool(user)


class IsOwner(MethodPermissionMixin):
    """Разрешает доступ только владельцу объекта."""

    def can_read(self, user, obj):
        return bool(user) and obj.get(
            "user_id") == str(getattr(user, "id", None))

    def can_update(self, user, obj):
        return bool(user) and obj.get(
            "user_id") == str(getattr(user, "id", None))

    def can_delete(self, user, obj):
        return bool(user) and obj.get(
            "user_id") == str(getattr(user, "id", None))

    async def get_base_filter(self, user: Optional[BaseModel]) -> dict:
        if not user:
            raise HTTPException(403, "Authentication required.")
        user_doc = await mongo_db["users"].find_one({"username": user.username})
        return {"user_id": str(getattr(user_doc, "id", None))}


class RoleBasedPermission(MethodPermissionMixin):
    """
    Permission-класс, основанный на ролях.
    Переопределите списки roles_create / read / update / delete.
    """

    roles_create: List[RoleEnum] = [RoleEnum.SUPERADMIN, RoleEnum.ADMIN, RoleEnum.DEMO_ADMIN]
    roles_read: List[RoleEnum] = [RoleEnum.SUPERADMIN, RoleEnum.ADMIN, RoleEnum.DEMO_ADMIN]
    roles_update: List[RoleEnum] = [RoleEnum.SUPERADMIN, RoleEnum.ADMIN, RoleEnum.DEMO_ADMIN]
    roles_delete: List[RoleEnum] = [RoleEnum.SUPERADMIN, RoleEnum.ADMIN, RoleEnum.DEMO_ADMIN]

    def can_create(self, user, obj):
        return user and user.role in self.roles_create

    def can_read(self, user, obj):
        return user and user.role in self.roles_read

    def can_update(self, user, obj):
        return user and user.role in self.roles_update

    def can_delete(self, user, obj):
        return user and user.role in self.roles_delete


class OperatorPermission(RoleBasedPermission):
    """
    Просмотр чатов для main-operator + остальных,
    изменение/удаление ‒ только для (super)admin.
    """
    roles_create = [RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.DEMO_ADMIN]
    roles_read = [
        RoleEnum.MAIN_OPERATOR,
        RoleEnum.STAFF,
        RoleEnum.ADMIN,
        RoleEnum.DEMO_ADMIN,
        RoleEnum.SUPERADMIN,
    ]
    roles_update = [RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.DEMO_ADMIN]
    roles_delete = [RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.DEMO_ADMIN]


class AdminPanelPermission(RoleBasedPermission):
    """
    Permission-класс, для Админ-панели.
    """
    roles_create = [RoleEnum.ADMIN, RoleEnum.DEMO_ADMIN, RoleEnum.SUPERADMIN]
    roles_read = [RoleEnum.STAFF, RoleEnum.ADMIN, RoleEnum.DEMO_ADMIN, RoleEnum.SUPERADMIN]
    roles_update = [RoleEnum.ADMIN, RoleEnum.DEMO_ADMIN, RoleEnum.SUPERADMIN]
    roles_delete = [RoleEnum.ADMIN, RoleEnum.DEMO_ADMIN, RoleEnum.SUPERADMIN]

    async def get_base_filter(self, user: Optional[BaseModel]) -> dict:
        if not user:
            raise HTTPException(403, "Authentication required.")
        if user.role in [RoleEnum.ADMIN, RoleEnum.DEMO_ADMIN, RoleEnum.SUPERADMIN]:

            return {}
        user_doc = await mongo_db["users"].find_one({"username": user.username})
        user_id = str(user_doc.get("_id"))
        return {"user_id": user_id}


class SuperAdminOnlyPermission(MethodPermissionMixin):
    """Permission-класс, только для суперадминов."""

    def is_superadmin(self, user: Optional[BaseModel]) -> bool:
        return bool(user and user.role == RoleEnum.SUPERADMIN)

    def can_create(self, user, obj):
        return self.is_superadmin(user)

    def can_read(self, user, obj):
        return self.is_superadmin(user)

    def can_update(self, user, obj):
        return self.is_superadmin(user)

    def can_delete(self, user, obj):
        return self.is_superadmin(user)

    async def get_base_filter(self, user: Optional[BaseModel]) -> dict:
        """Суперадмин получает доступ ко всем записям."""
        if not self.is_superadmin(user):
            raise HTTPException(403, "Superadmin access required.")
        return {}


class PersonalCabinetPermission(RoleBasedPermission):
    """Permission-класс, для Личного кабинета."""
    roles_create = [
        RoleEnum.CLIENT,
        RoleEnum.STAFF,
        RoleEnum.ADMIN,
        RoleEnum.DEMO_ADMIN,
        RoleEnum.SUPERADMIN]
    roles_read = [
        RoleEnum.CLIENT,
        RoleEnum.STAFF,
        RoleEnum.ADMIN,
        RoleEnum.DEMO_ADMIN,
        RoleEnum.SUPERADMIN]
    roles_update = [
        RoleEnum.CLIENT,
        RoleEnum.STAFF,
        RoleEnum.ADMIN,
        RoleEnum.DEMO_ADMIN,
        RoleEnum.SUPERADMIN]
    roles_delete = [
        RoleEnum.CLIENT,
        RoleEnum.STAFF,
        RoleEnum.ADMIN,
        RoleEnum.DEMO_ADMIN,
        RoleEnum.SUPERADMIN]

    async def get_base_filter(self, user: Optional[BaseModel]) -> dict:
        if not user:
            raise HTTPException(403, "Authentication required.")
        user_id = user.data["user_id"]
        return {"user_id": user_id}
