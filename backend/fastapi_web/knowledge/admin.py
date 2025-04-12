"""Админ-панель приложения Знания."""
from admin_core.base_admin import BaseAdmin
from crud_core.registry import admin_registry
from db.mongo.db_init import mongo_db

from .db.mongo.schemas import BotSettings


class BotSettingsAdmin(BaseAdmin):
    model = BotSettings
    collection_name = "bot_settings"

    verbose_name = {"en": "Bot Settings", "ru": "Настройки Бота"}
    plural_name = {"en": "Bot Settings", "ru": "Настройки Бота"}
    icon: str = "pi pi-cog"

    list_display = [
        "project_name",
        "created_at",
    ]

    detail_fields = [
        "project_name", "employee_name", "mention_name", "avatar", "bot_color",
        "communication_tone", "personality_traits", "additional_instructions", "role", "target_action",
        "core_principles", "special_instructions", "forbidden_topics",
        "greeting", "error_message", "farewell_message", "fallback_ai_error_message",
        "ai_model", "created_at"
    ]

    computed_fields = []
    read_only_fields = ["created_at"]

    field_titles = {
        "project_name": {"en": "Project Name", "ru": "Название проекта"},
        "employee_name": {"en": "Employee Name", "ru": "Имя сотрудника"},
        "mention_name": {"en": "Mention Bot Name in Conversation", "ru": "Упоминать свое имя при общении"},
        "avatar": {"en": "Avatar", "ru": "Аватар"},
        "bot_color": {"en": "Bot Color", "ru": "Цвет бота"},
        "communication_tone": {"en": "Choose Communication Tone", "ru": "Выберите тон общения"},
        "personality_traits": {"en": "Personality Traits", "ru": "Особенности характера"},
        "additional_instructions": {"en": "Additional Instructions", "ru": "Дополнительные инструкции"},
        "role": {"en": "Role", "ru": "Роль"},
        "target_action": {"en": "Target Action", "ru": "Целевое действие"},
        "core_principles": {"en": "Core Principles", "ru": "Ключевые принципы"},
        "special_instructions": {"en": "Special Instructions", "ru": "Специальные инструкции"},
        "forbidden_topics": {"en": "Forbidden Topics", "ru": "Запретные темы"},
        "greeting": {"en": "Greeting", "ru": "Приветствие"},
        "error_message": {"en": "Error Message", "ru": "Ошибка"},
        "farewell_message": {"en": "Farewell Message", "ru": "Прощание"},
        "fallback_ai_error_message": {"en": "AI Error Fallback", "ru": "Сообщение при ошибке ИИ"},
        "ai_model": {"en": "AI Model", "ru": "Выбор модели"},
        "created_at": {"en": "Created At", "ru": "Дата создания"}
    }

    help_texts = {
        "project_name": {
            "en": "Short name of the project using the bot.",
            "ru": "Короткое название проекта, в котором используется бот."
        },
        "employee_name": {
            "en": "The name of the employee that the bot represents.",
            "ru": "Имя сотрудника, которого представляет бот."
        },
        "mention_name": {
            "en": "Should the bot mention its name?",
            "ru": "Должен ли бот упоминать свое имя?"
        },
        "avatar": {
            "en": "Upload an image for the bot's avatar.",
            "ru": "Загрузите изображение для аватара бота."
        },
        "bot_color": {
            "en": "If you don’t have time to customize the bot, we can do it for you.",
            "ru": "Если у вас нет времени на кастомизацию бота, мы можем сделать это для вас."
        },
        "communication_tone": {
            "en": "Choose the bot's communication style.",
            "ru": "Выберите стиль общения бота."
        },
        "personality_traits": {
            "en": "Define key personality traits for the bot.",
            "ru": "Определите ключевые черты характера бота."
        },
        "additional_instructions": {
            "en": "Provide any additional guidelines for bot behavior.",
            "ru": "Укажите любые дополнительные инструкции для поведения бота."
        },
        "role": {
            "en": "Specify the bot's role in the project.",
            "ru": "Укажите роль бота в проекте."
        },
        "target_action": {
            "en": "List of actions the bot is designed to perform.",
            "ru": "Список действий, которые должен выполнять бот."
        },
        "core_principles": {
            "en": "Fundamental principles guiding the bot's responses.",
            "ru": "Основные принципы, определяющие ответы бота."
        },
        "special_instructions": {
            "en": "Additional functionality settings.",
            "ru": "Дополнительные настройки функциональности."
        },
        "forbidden_topics": {
            "en": "Topics the bot should avoid.",
            "ru": "Темы, которых бот должен избегать."
        },
        "greeting": {
            "en": "Default greeting messages in different languages.",
            "ru": "Стандартные приветственные сообщения на разных языках."
        },
        "error_message": {
            "en": "Message displayed when the bot cannot answer a question.",
            "ru": "Сообщение, отображаемое, когда бот не может ответить на вопрос."
        },
        "farewell_message": {
            "en": "Bot's goodbye message.",
            "ru": "Прощальное сообщение бота."
        },
        "fallback_ai_error_message": {
            "en": "Message shown if AI fails to generate a response.",
            "ru": "Сообщение при ошибке генерации ответа ИИ."
        },
        "ai_model": {
            "en": "AI model the bot is using.",
            "ru": "Модель ИИ, которую использует бот."
        },
        "created_at": {
            "en": "Timestamp when the bot settings were created.",
            "ru": "Дата и время создания настроек бота."
        }
    }

    field_groups = [
        {
            "title": {"en": "Basic Settings", "ru": "Основные настройки"},
            "fields": ["project_name", "employee_name", "mention_name", "avatar", "bot_color"],
            "help_text": {"en": "Define basic bot information", "ru": "Определите основные настройки бота"}
        },
        {
            "title": {"en": "Character and Behavior", "ru": "Характер и поведение"},
            "fields": ["communication_tone", "personality_traits", "additional_instructions", "role", "target_action"],
            "help_text": {"en": "Set how the bot interacts with users", "ru": "Настройте поведение бота в общении"}
        },
        {
            "title": {"en": "Topics and Restrictions", "ru": "Темы и ограничения"},
            "fields": ["core_principles", "special_instructions", "forbidden_topics"],
            "help_text": {"en": "Define allowed and restricted topics", "ru": "Настройте темы, которые бот может обсуждать"}
        },
        {
            "title": {"en": "Interaction Guidelines", "ru": "Правила взаимодействия"},
            "fields": ["greeting", "error_message", "farewell_message", "fallback_ai_error_message"],
            "help_text": {"en": "Set the bot's predefined messages", "ru": "Определите автоматические сообщения бота"}
        },
        {
            "title": {"en": "Artificial Intelligence", "ru": "Искусственный интеллект"},
            "fields": ["ai_model"],
            "help_text": {"en": "Choose the AI model for your bot", "ru": "Выберите модель ИИ для вашего бота"}
        }
    ]


admin_registry.register("bot_settings", BotSettingsAdmin(mongo_db))
