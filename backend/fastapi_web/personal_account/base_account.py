"""Базовые сущности приложения Персональный аккаунт."""
import logging
from typing import List, Optional

from crud_core.models import BaseCrud, BaseCrudCore, InlineCrud

logger = logging.getLogger(__name__)


class BaseAccountCore(BaseCrudCore):
    """Базовый класс для работы с личными кабинетами пользователей."""

    user_collection_name = "personal_accounts"

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        current_user_id: Optional[str] = None
    ) -> List[dict]:
        """
        Возвращает список документов с учётом фильтра.
        Если передан current_user_id, фильтрует только записи пользователя.
        """
        query = filters.copy() if filters else {}
        if current_user_id:
            query["user_id"] = current_user_id

        cursor = self.db.find(query)
        if sort_by:
            cursor = cursor.sort(sort_by, order)

        return [await self.format_document(raw_doc) async for raw_doc in cursor]


class InlineAccount(InlineCrud):
    """Базовый класс для инлайновых объектов в личном кабинете."""
    pass


class BaseAccount(BaseCrud):
    """Основной класс для управления личными кабинетами."""
    pass
