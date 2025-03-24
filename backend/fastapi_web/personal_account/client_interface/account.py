"""Персональный аккаунт приложения Клиентский интерфейс."""
from typing import List
from crud_core.registry import account_registry
from db.mongo.db_init import mongo_db
from personal_account.base_account import BaseAccount, InlineAccount

from .db.mongo.schemas import MainInfoSchema

class MainInfoAccount(BaseAccount):
    """
    Админка для вкладки 'Основная информация'.
    Отображает личные данные, данные о компании и системную информацию.
    """
    model = MainInfoSchema              # Модель, с которой работает эта админка
    collection_name = "patients_main_info"  # Название коллекции в Mongo (пример)

    # Настраиваем, как будет отображаться в админке
    verbose_name = {
        "en": "Basic information",
        "ru": "Основная информация",
    }
    plural_name = {
        "en": "Basic information records",
        "ru": "Записи основной информации",
    }

    icon: str = "pi pi-file"  # Или любая другая иконка из PrimeIcons

    # Какие поля показывать в списке (list view) — обычно не нужно все
    list_display = [
        "last_name",
        "first_name",
        "patronymic",
        "patient_id"
    ]

    # Какие поля показывать в детальном просмотре (detail view)
    detail_fields = [
        "last_name",
        "first_name",
        "patronymic",
        "birth_date",
        "gender",
        "company_name",
        "patient_id",
        "created_at",
        "updated_at",
    ]

    # Если у вас есть вычисляемые поля/методы, укажите их здесь:
    computed_fields: List[str] = []
    read_only_fields = [
        "created_at",
        "updated_at"
    ]

    field_titles = {
        "last_name": {"en": "Last Name", "ru": "Фамилия"},
        "first_name": {"en": "First Name", "ru": "Имя"},
        "patronymic": {"en": "Patronymic", "ru": "Отчество"},
        "birth_date": {"en": "Birth Date", "ru": "Дата рождения"},
        "gender": {"en": "Gender", "ru": "Пол"},
        "company_name": {"en": "Company Name", "ru": "Название компании"},
        "patient_id": {"en": "Patient ID", "ru": "ID пациента"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Последнее обновление"}
    }

    help_texts = {
        "last_name": {"en": "User's last name", "ru": "Фамилия пользователя"},
        "first_name": {"en": "User's first name", "ru": "Имя пользователя"},
        "patronymic": {"en": "User's patronymic", "ru": "Отчество пользователя"},
        "birth_date": {"en": "User's birth date", "ru": "Дата рождения пользователя"},
        "gender": {"en": "Gender (male/female)", "ru": "Пол (мужской/женский)"},
        "company_name": {"en": "Company name", "ru": "Название компании"},
        "patient_id": {"en": "Patient internal ID", "ru": "Внутренний ID пациента"},
        "created_at": {"en": "Record creation date", "ru": "Дата создания записи"},
        "updated_at": {"en": "Record last update date", "ru": "Дата последнего обновления записи"}
    }

    # Полезно сгруппировать поля, чтобы на вкладке была именно та разбивка, что вы хотите:
    field_groups = [
        {
            "title": {"en": "Personal data", "ru": "Личные данные"},
            "fields": ["last_name", "first_name", "patronymic", "birth_date", "gender"],
            "help_text": {
                "en": "Personal information about the user",
                "ru": "Личная информация о пользователе"
            }
        },
        {
            "title": {"en": "Company info", "ru": "Информация о компании"},
            "fields": ["company_name"]
        },
        {
            "title": {"en": "System info", "ru": "Системная информация"},
            "fields": ["patient_id", "created_at", "updated_at"]
        }
    ]

    # Настраиваем CRUD-доступ (пример)
    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }

account_registry.register("user_settings", MainInfoAccount(mongo_db))