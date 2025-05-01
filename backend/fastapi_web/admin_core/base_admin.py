"""Базовые сущности админ-панели."""
import logging

from crud_core.models import BaseCrud, BaseCrudCore, InlineCrud
from crud_core.permissions import AdminPanelPermission

logger = logging.getLogger(__name__)


class BaseAdminCore(BaseCrudCore):
    """
    Базовый класс для админских операций.
    Требует проверки прав доступа через AdminPanelPermission.
    """
    user_collection_name = "users"
    permission_class = AdminPanelPermission()


class InlineAdmin(InlineCrud):
    """
    Базовый класс для инлайнов в админке.
    Использует AdminPanelPermission.
    """
    permission_class = AdminPanelPermission()
    # pass


class BaseAdmin(BaseCrud):
    """
    Основной CRUD-класс для админки.
    Использует AdminPanelPermission.
    """
    permission_class = AdminPanelPermission()
