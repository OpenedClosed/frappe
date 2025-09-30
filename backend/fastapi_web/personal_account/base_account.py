"""Базовые сущности приложения Персональный аккаунт."""
import logging
from typing import List, Optional

from crud_core.models import BaseCrud, BaseCrudCore, InlineCrud
from crud_core.permissions import PersonalCabinetPermission

logger = logging.getLogger(__name__)


class BaseAccountCore(BaseCrudCore):
    """Базовый класс для работы с личными кабинетами пользователей."""

    user_collection_name = "users"
    permission_class = PersonalCabinetPermission()


class InlineAccount(InlineCrud):
    """Базовый класс для инлайновых объектов в личном кабинете."""

    user_collection_name = "users"
    permission_class = PersonalCabinetPermission()


class BaseAccount(BaseCrud):
    """Основной класс для управления личными кабинетами."""

    user_collection_name = "users"
    permission_class = PersonalCabinetPermission()
