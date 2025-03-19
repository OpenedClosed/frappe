"""Персональный аккаунт приложения Тест."""
from crud_core.registry import account_registry
from db.mongo.db_init import mongo_db
from personal_account.base_account import BaseAccount, InlineAccount

from .db.mongo.schemas import (MultipleInlineModel, SingleInlineModel,
                               TestSchema)


class SingleInlineModelInlineAccount(InlineAccount):
    """Инлайн-админка для одиночной связи."""

    model = SingleInlineModel
    collection_name = "test_schema"
    dot_field_path = "single_relation"

    verbose_name = {
        "en": "Single Relation",
        "ru": "Одиночная связь"
    }
    plural_name = {
        "en": "Single Relations",
        "ru": "Одиночные связи"
    }

    icon: str = "pi pi-link"

    list_display = ["data"]
    detail_fields = ["data"]

    computed_fields = []
    read_only_fields = []

    field_titles = {
        "data": {"en": "Data", "ru": "Данные"}
    }

    help_texts = {
        "data": {
            "en": "Example field for single inline relation",
            "ru": "Пример поля для одиночной инлайн-связи"
        }
    }

    field_groups = [
        {
            "title": {"en": "Main Info", "ru": "Основная информация"},
            "fields": ["data"],
            "help_text": {
                "en": "Details of the single relation",
                "ru": "Детали одиночной связи"
            }
        }
    ]


class MultipleInlineModelInlineAccount(InlineAccount):
    """Инлайн-админка для множественной связи."""

    model = MultipleInlineModel
    collection_name = "test_schema"
    dot_field_path = "multiple_relations"

    verbose_name = {
        "en": "Multiple Relation",
        "ru": "Множественная связь"
    }
    plural_name = {
        "en": "Multiple Relations",
        "ru": "Множественные связи"
    }

    icon: str = "pi pi-list"

    list_display = ["info"]
    detail_fields = ["info"]

    computed_fields = []
    read_only_fields = []

    field_titles = {
        "info": {"en": "Information", "ru": "Информация"}
    }

    help_texts = {
        "info": {
            "en": "Example field for multiple inline relation",
            "ru": "Пример поля для множественной инлайн-связи"
        }
    }

    field_groups = [
        {
            "title": {"en": "Main Info", "ru": "Основная информация"},
            "fields": ["info"],
            "help_text": {
                "en": "Details of the multiple relation",
                "ru": "Детали множественной связи"
            }
        }
    ]


class TestProfileAccount(BaseAccount):
    """
    Тестовый профиль пользователя в личном кабинете.
    Используется для демонстрации всех типов полей.
    """

    model = TestSchema
    collection_name = "test_profiles"

    verbose_name = {
        "en": "Test Profile",
        "ru": "Тестовый профиль"
    }
    plural_name = {
        "en": "Test Profiles",
        "ru": "Тестовые профили"
    }

    icon: str = "pi pi-user"

    list_display = [
        "str_field",
        "email",
        "phone_number",
        "dropdown_selection",
        "rating_field",
        "created_at"
    ]

    # Поля, доступные в детальном просмотре (detail view)
    detail_fields = [
        "str_field",
        "text_field",
        "wysiwyg_field",
        "email",
        "phone_number",
        "password_field",
        "image_upload",
        "multi_images",
        "file_upload",
        "multi_files",
        "dropdown_selection",
        "multi_dropdown_selection",
        "tag_cloud",
        "autocomplete_field",
        "date_field",
        "datetime_field",
        "map_field",
        "rating_field",
        "range_slider",
        "boolean_toggle",
        "checkbox_group",
        "drag_and_drop_list",
        "color_picker",
        "table_data",
        "code_editor",
        "dict_editor",

        "crm_user_id_display",
        "crm_subscription_status_display",
        "full_name_display",
        "last_login_display",
        "bonus_balance_display",
        "family_members_count_display",
        "notifications_enabled_display",
        "created_at",
        "updated_at",
    ]

    computed_fields = [
        "crm_user_id_display",
        "crm_subscription_status_display",
        "full_name_display",
        "last_login_display",
        "bonus_balance_display",
        "family_members_count_display",
        "notifications_enabled_display"
    ]

    read_only_fields = [
        "created_at",
        "updated_at",
    ]

    field_titles = {
        "str_field": {"en": "String Field", "ru": "Строковое поле"},
        "text_field": {"en": "Text Field", "ru": "Текстовое поле"},
        "wysiwyg_field": {"en": "Rich Text", "ru": "Форматированный текст"},
        "email": {"en": "Email", "ru": "Эл. почта"},
        "phone_number": {"en": "Phone Number", "ru": "Номер телефона"},
        "password_field": {"en": "Password", "ru": "Пароль"},
        "image_upload": {"en": "Single Image", "ru": "Одиночное изображение"},
        "multi_images": {"en": "Multiple Images", "ru": "Несколько изображений"},
        "file_upload": {"en": "Single File", "ru": "Одиночный файл"},
        "multi_files": {"en": "Multiple Files", "ru": "Несколько файлов"},
        "dropdown_selection": {"en": "Dropdown", "ru": "Выпадающий список"},
        "multi_dropdown_selection": {"en": "Multi-Select", "ru": "Множественный выбор"},
        "tag_cloud": {"en": "Tag Cloud", "ru": "Облако тегов"},
        "autocomplete_field": {"en": "Autocomplete", "ru": "Автодополнение"},
        "date_field": {"en": "Date", "ru": "Дата"},
        "datetime_field": {"en": "Date & Time", "ru": "Дата и время"},
        "map_field": {"en": "Location", "ru": "Местоположение"},
        "rating_field": {"en": "Rating", "ru": "Оценка"},
        "range_slider": {"en": "Range Slider", "ru": "Диапазон значений"},
        "boolean_toggle": {"en": "Boolean Toggle", "ru": "Переключатель"},
        "checkbox_group": {"en": "Checkbox Group", "ru": "Группа чекбоксов"},
        "drag_and_drop_list": {"en": "Drag & Drop", "ru": "Перетаскивание"},
        "color_picker": {"en": "Color Picker", "ru": "Выбор цвета"},
        "table_data": {"en": "Table Data", "ru": "Таблица"},
        "code_editor": {"en": "Code Editor", "ru": "Редактор кода"},
        "dict_editor": {"en": "Dict Editor", "ru": "Редактор словаря"},
        "crm_user_id": {"en": "CRM User ID", "ru": "CRM ID пользователя"},
        "crm_subscription_status": {"en": "CRM Subscription", "ru": "Подписка (CRM)"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Дата обновления"}
    }

    # Группировка полей (вкладки)
    field_groups = [
        {
            "title": {"en": "Basic Info", "ru": "Основная информация"},
            "fields": ["str_field", "email", "phone_number", "password_field"],
            "help_text": {
                "en": "Basic user information",
                "ru": "Основные данные пользователя"
            }
        },
        {
            "title": {"en": "Media & Files", "ru": "Медиа и файлы"},
            "fields": ["image_upload", "multi_images", "file_upload", "multi_files"]
        },
        {
            "title": {"en": "Selections", "ru": "Выборы"},
            "fields": ["dropdown_selection", "multi_dropdown_selection", "tag_cloud", "autocomplete_field"]
        },
        {
            "title": {"en": "Date & Time", "ru": "Дата и время"},
            "fields": ["date_field", "datetime_field"]
        },
        {
            "title": {"en": "Additional Features", "ru": "Дополнительные возможности"},
            "fields": ["rating_field", "range_slider", "boolean_toggle", "checkbox_group", "drag_and_drop_list", "color_picker"]
        },
        {
            "title": {"en": "Table & Code", "ru": "Таблицы и код"},
            "fields": ["table_data", "code_editor", "dict_editor"]
        },
        {
            "title": {"en": "CRM Data", "ru": "Данные CRM"},
            "fields": ["crm_user_id_display", "crm_subscription_status_display", "full_name_display", "last_login_display", "bonus_balance_display", "family_members_count_display", "notifications_enabled_display"],
            "help_text": {
                "en": "These fields are pulled from an external CRM system",
                "ru": "Эти поля подтягиваются из внешней CRM"
            }
        },
        {
            "title": {"en": "Inline Relations", "ru": "Инлайн-связи"},
            "fields": ["single_relation", "multiple_relations"],
            "help_text": {
                "en": "Demonstrates how to manage single and multiple inline relations in the admin panel.",
                "ru": "Демонстрация управления одиночными и множественными инлайн-связями в админке."
            }
        },
        {
            "title": {"en": "System", "ru": "Система"},
            "fields": ["created_at", "updated_at"]
        }
    ]

    help_texts = {
        "str_field": {
            "en": "A simple string field.",
            "ru": "Простое строковое поле."
        },
        "text_field": {
            "en": "A multi-line text field.",
            "ru": "Многострочное текстовое поле."
        },
        "wysiwyg_field": {
            "en": "Rich text editor with formatting.",
            "ru": "Редактор форматированного текста."
        },
        "email": {
            "en": "Field for entering an email address.",
            "ru": "Поле для ввода адреса электронной почты."
        },
        "phone_number": {
            "en": "Field for entering a phone number.",
            "ru": "Поле для ввода номера телефона."
        },
        "password_field": {
            "en": "A password input field.",
            "ru": "Поле для ввода пароля."
        },
        "image_upload": {
            "en": "Upload a single image.",
            "ru": "Загрузка одного изображения."
        },
        "multi_images": {
            "en": "Upload multiple images.",
            "ru": "Загрузка нескольких изображений."
        },
        "file_upload": {
            "en": "Upload a single file.",
            "ru": "Загрузка одного файла."
        },
        "multi_files": {
            "en": "Upload multiple files.",
            "ru": "Загрузка нескольких файлов."
        },
        "dropdown_selection": {
            "en": "Dropdown selection field.",
            "ru": "Поле выбора из списка."
        },
        "multi_dropdown_selection": {
            "en": "Multi-select dropdown.",
            "ru": "Множественный выбор из списка."
        },
        "tag_cloud": {
            "en": "Tag input with multiple selections.",
            "ru": "Ввод тегов с возможностью выбора нескольких вариантов."
        },
        "autocomplete_field": {
            "en": "Autocomplete input field.",
            "ru": "Поле с автодополнением."
        },
        "date_field": {
            "en": "Date picker field.",
            "ru": "Поле выбора даты."
        },
        "datetime_field": {
            "en": "Date and time picker field.",
            "ru": "Поле выбора даты и времени."
        },
        "map_field": {
            "en": "Select a location on the map.",
            "ru": "Выбор местоположения на карте."
        },
        "rating_field": {
            "en": "Rating field using stars or emojis.",
            "ru": "Поле для оценки с использованием звездочек или эмодзи."
        },
        "range_slider": {
            "en": "A range selection slider.",
            "ru": "Ползунок выбора диапазона значений."
        },
        "boolean_toggle": {
            "en": "A simple toggle switch.",
            "ru": "Простой переключатель."
        },
        "checkbox_group": {
            "en": "Group of checkboxes for multiple selections.",
            "ru": "Группа чекбоксов для множественного выбора."
        },
        "drag_and_drop_list": {
            "en": "Drag and drop reordering list.",
            "ru": "Список с возможностью перетаскивания элементов."
        },
        "color_picker": {
            "en": "Color selection field.",
            "ru": "Поле выбора цвета."
        },
        "table_data": {
            "en": "A table with editable rows.",
            "ru": "Таблица с редактируемыми строками."
        },
        "code_editor": {
            "en": "Code editor for structured input.",
            "ru": "Редактор кода для структурированного ввода."
        },
        "dict_editor": {
            "en": "Dict editor for structured input.",
            "ru": "Редактор словаря для структурированного ввода."
        },
        "crm_user_id": {
            "en": "User ID retrieved from CRM.",
            "ru": "ID пользователя, полученный из CRM."
        },
        "crm_subscription_status": {
            "en": "User subscription status from CRM.",
            "ru": "Статус подписки пользователя из CRM."
        },
        "single_relation": {
            "en": "A single inline relation demonstrating how to connect a related object.",
            "ru": "Одиночная инлайн-связь, демонстрирующая связь с другим объектом."
        },
        "multiple_relations": {
            "en": "A list of related objects demonstrating multiple inline relations.",
            "ru": "Список связанных объектов, демонстрирующий множественные инлайн-связи."
        },
        "created_at": {
            "en": "Timestamp when the record was created.",
            "ru": "Отметка времени создания записи."
        },
        "updated_at": {
            "en": "Timestamp when the record was last updated.",
            "ru": "Отметка времени последнего обновления записи."
        },
        "full_name_display": {
            "en": "Computed full name of the user.",
            "ru": "Вычисляемое полное имя пользователя."
        },
        "last_login_display": {
            "en": "Computed last login time.",
            "ru": "Вычисляемое время последнего входа."
        },
        "bonus_balance_display": {
            "en": "Computed bonus balance of the user.",
            "ru": "Вычисляемый баланс бонусов пользователя."
        },
        "family_members_count_display": {
            "en": "Computed count of family members linked to the user.",
            "ru": "Вычисляемое количество привязанных членов семьи."
        },
        "notifications_enabled_display": {
            "en": "Computed notification subscription status.",
            "ru": "Вычисляемый статус подписки на уведомления."
        },
    }

    inlines = {
        "single_relation": SingleInlineModelInlineAccount,
        "multiple_relations": MultipleInlineModelInlineAccount
    }

    # CRUD-доступ (создание, чтение, обновление разрешены, удаление – нет)
    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }

    # Методы для вычисляемых полей
    async def crm_user_id_display(self, obj: dict) -> str:
        """Получает ID пользователя из CRM."""
        return obj.get("crm_data", {}).get("user_id", "N/A")

    async def crm_subscription_status_display(self, obj: dict) -> str:
        """Получает статус подписки из CRM."""
        subscription = obj.get("crm_data", {}).get("subscription_status")
        if isinstance(subscription, dict):
            return subscription.get("ru", "Неизвестно")
        return "Неизвестно"

    async def full_name_display(self, obj: dict) -> str:
        """Формирует полное имя пользователя."""
        first_name = obj.get("first_name", "")
        last_name = obj.get("last_name", "")
        return f"{first_name} {last_name}".strip() or "Без имени"

    async def last_login_display(self, obj: dict) -> str:
        """Форматирует дату последнего входа."""
        last_login = obj.get("last_login")
        if not last_login:
            return "Никогда"
        return last_login.strftime("%d.%m.%Y %H:%M")

    async def bonus_balance_display(self, obj: dict) -> str:
        """Возвращает баланс бонусов пользователя."""
        return f"{obj.get('bonus_balance', 0)} бонусов"

    async def family_members_count_display(self, obj: dict) -> str:
        """Возвращает количество привязанных членов семьи."""
        family_members = obj.get("family_members", [])
        return f"{len(family_members)} родственников"

    async def notifications_enabled_display(self, obj: dict) -> str:
        """Возвращает статус подписки на уведомления."""
        return "Включены" if obj.get(
            "notifications_enabled", False) else "Выключены"


account_registry.register("test", TestProfileAccount(mongo_db))
