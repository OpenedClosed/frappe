"""Базовые сущности админ-панели."""
import logging
from typing import List, Optional

from crud_core.models import BaseCrud, BaseCrudCore, InlineCrud

logger = logging.getLogger(__name__)


class BasePublicCore(BaseCrudCore):
    """Базовый класс для публичных CRUD-операций без user_id."""

    user_collection_name = None

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
    ) -> List[dict]:
        """Возвращает список документов без фильтрации по пользователю."""
        return await super().get_queryset(filters, sort_by, order, current_user_id=None)

    async def create(self, data: dict) -> dict:
        """Создаёт объект без привязки к пользователю."""
        return await super().create(data, current_user_id=None)

    async def update(self, object_id: str, data: dict) -> dict:
        """Обновляет объект без проверки user_id."""
        return await super().update(object_id, data, current_user_id=None)

    async def delete(self, object_id: str) -> dict:
        """Удаляет объект без проверки user_id."""
        return await super().delete(object_id, current_user_id=None)


class BaseAdminCore(BasePublicCore):
    """Базовый класс для админок."""

    user_collection_name = "users"


class InlineAdmin(InlineCrud):
    """Базовый класс для инлайнов."""
    pass


class BaseAdmin(BaseCrud):
    """Основной класс для админок."""
    pass
