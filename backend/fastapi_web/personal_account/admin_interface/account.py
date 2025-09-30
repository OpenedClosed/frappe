"""Персональный аккаунт приложения Административная зона."""
from crud_core.registry import account_registry
from db.mongo.db_init import mongo_db
from personal_account.base_account import BaseAccount

from .db.mongo.schemas import CalendarIntegration


class CalendarIntegrationAccount(BaseAccount):
    """
    Админка для управления интеграцией с календарем.
    """

    model = CalendarIntegration
    collection_name = "calendar_integrations"

    verbose_name = {
        "en": "Calendar Integration",
        "ru": "Интеграция с календарем"
    }
    plural_name = {
        "en": "Calendar Integrations",
        "ru": "Интеграции с календарем"
    }

    icon: str = "pi pi-calendar-plus"

    list_display = [
        "provider",
        "last_sync",
        "expires_at",
    ]

    detail_fields = [
        "provider",
        "access_token",
        "refresh_token",
        "expires_at",
        "last_sync",
    ]

    computed_fields = []

    read_only_fields = ["last_sync"]

    field_titles = {
        "provider": {"en": "Provider", "ru": "Сервис"},
        "access_token": {"en": "Access Token", "ru": "Токен доступа"},
        "refresh_token": {"en": "Refresh Token", "ru": "Токен обновления"},
        "expires_at": {"en": "Expires At", "ru": "Срок действия"},
        "last_sync": {"en": "Last Sync", "ru": "Последняя синхронизация"},
    }

    field_groups = [
        {
            "title": {"en": "Integration Details", "ru": "Детали интеграции"},
            "fields": ["provider", "access_token", "refresh_token"],
            "help_text": {
                "en": "Manage user’s external calendar connections",
                "ru": "Управление подключениями пользователя к внешним календарям"
            }
        },
        {
            "title": {"en": "Timestamps", "ru": "Временные метки"},
            "fields": ["last_sync", "expires_at"],
            "help_text": {
                "en": "Synchronization and token expiration info",
                "ru": "Информация о синхронизации и сроке действия токена"
            }
        }
    ]


# account_registry.register(
#     "calendar_integrations",
#     CalendarIntegrationAccount(mongo_db))
