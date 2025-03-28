"""Персональный аккаунт приложения Клиентский интерфейс."""
from crud_core.registry import account_registry
from db.mongo.db_init import mongo_db
from personal_account.base_account import BaseAccount, InlineAccount

from .db.mongo.schemas import (Appointment, BonusProgram, BonusTransaction,
                               CalendarIntegration, Family, FamilyRelation,
                               HistoryOfAppointment, MedicalForm, Notification,
                               UserProfile, UserSettings)


class MedicalFormInline(InlineAccount):
    """Инлайн для медицинской анкеты пользователя."""

    model = MedicalForm
    collection_name = "user_profiles"
    dot_field_path = "medical_forms"

    verbose_name = {
        "en": "Medical Form",
        "ru": "Медицинская анкета"
    }
    plural_name = {
        "en": "Medical Forms",
        "ru": "Медицинские анкеты"
    }

    icon: str = "pi pi-heart"

    list_display = [
        "allergies",
        "blood_type",
        "created_at"
    ]

    detail_fields = [
        "allergies",
        "blood_type",
        "created_at",
        "updated_at"
    ]

    computed_fields = []
    read_only_fields = ["created_at", "updated_at"]

    field_titles = {
        "allergies": {"en": "Allergies", "ru": "Аллергии"},
        "blood_type": {"en": "Blood Type", "ru": "Группа крови"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Дата обновления"},
    }

    field_groups = [
        {
            "title": {"en": "Medical Information", "ru": "Медицинская информация"},
            "fields": ["allergies", "blood_type"],
            "help_text": {
                "en": "Basic medical data for emergency situations",
                "ru": "Основные медицинские данные на случай ЧП"
            }
        },
        {
            "title": {"en": "Timestamps", "ru": "Временные метки"},
            "fields": ["created_at", "updated_at"],
            "help_text": {
                "en": "Time of form creation and last update",
                "ru": "Время создания анкеты и последнего обновления"
            }
        }
    ]


class UserProfileAccount(BaseAccount):
    """
    "Админ" (на самом деле "личный кабинет") для профиля пользователя.
    Аналогично, у нас есть все те же поля, что и в админке:
    - model
    - collection_name
    - verbose_name, plural_name
    - list_display, detail_fields, computed_fields, read_only_fields
    - field_groups (вкладки)
    - inlines (дочерние модели)
    - и т.д.
    """

    model = UserProfile
    collection_name = "user_profiles"
    max_instances_per_user = 1

    verbose_name = {
        "en": "User Profile",
        "ru": "Профиль пользователя"
    }
    plural_name = {
        "en": "User Profiles",
        "ru": "Профили пользователей"
    }

    icon: str = "pi pi-user"

    list_display = [
        "email",
        "phone_number",
        "subscription_status",
        "is_2fa_enabled",
        "created_at",
    ]

    detail_fields = [
        "email",
        "phone_number",
        "subscription_status",
        "is_2fa_enabled",
        "created_at",
        "updated_at",
    ]

    computed_fields = []
    read_only_fields = ["created_at", "updated_at"]

    field_titles = {
        "email": {"en": "E-mail", "ru": "Эл. почта"},
        "phone_number": {"en": "Phone Number", "ru": "Номер телефона"},
        "is_2fa_enabled": {"en": "Two-Factor Auth", "ru": "Двухфакторная аутентификация"},
        "subscription_status": {"en": "Subscription", "ru": "Статус подписки"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Дата обновления"},
    }

    help_texts = {
        "is_2fa_enabled": {
            "en": "Enable or disable two-factor authentication",
            "ru": "Включить или отключить двухфакторную аутентификацию"
        },
        "medical_forms": {
            "en": "User’s medical data (allergies, blood type, etc.)",
            "ru": "Медицинские данные пользователя (аллергии, группа крови и т.д.)"
        }
    }

    field_groups = [
        {
            "title": {"en": "Basic Info", "ru": "Основная информация"},
            "fields": ["email", "phone_number", "subscription_status"],
            "help_text": {
                "en": "User’s primary contact and subscription data",
                "ru": "Основные контактные данные пользователя и статус подписки"
            }
        },
        {
            "title": {"en": "Security", "ru": "Безопасность"},
            "fields": ["is_2fa_enabled"],
            "help_text": {
                "en": "Security-related settings (2FA)",
                "ru": "Настройки безопасности (2FA)"
            }
        },
    ]

    inlines = {
        "medical_forms": MedicalFormInline
    }

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }


class AppointmentAccount(BaseAccount):
    """
    Админка для управления записями на приём.
    """

    model = Appointment
    collection_name = "appointments"

    verbose_name = {
        "en": "Appointment",
        "ru": "Запись на приём"
    }
    plural_name = {
        "en": "Appointments",
        "ru": "Записи на приём"
    }

    icon: str = "pi pi-calendar"

    list_display = [
        "datetime",
        "duration",
        "status",
        "created_at",
    ]

    detail_fields = [
        "datetime",
        "duration",
        "status",
        "notes",
        "created_at",
        "updated_at",
    ]

    computed_fields = []

    read_only_fields = ["created_at", "updated_at"]

    field_titles = {
        "datetime": {"en": "Appointment Time", "ru": "Дата и время визита"},
        "duration": {"en": "Duration (minutes)", "ru": "Длительность (минуты)"},
        "status": {"en": "Status", "ru": "Статус"},
        "notes": {"en": "Notes", "ru": "Заметки"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Дата обновления"},
    }

    help_texts = {
        "status": {
            "en": "Current status of the appointment",
            "ru": "Текущий статус визита"
        },
        "notes": {
            "en": "Additional details about the appointment",
            "ru": "Дополнительные детали визита"
        }
    }

    field_groups = [
        {
            "title": {"en": "Appointment Details", "ru": "Детали визита"},
            "fields": ["datetime", "duration", "status", "notes"],
            "help_text": {
                "en": "Basic information about the scheduled appointment",
                "ru": "Основная информация о запланированном визите"
            }
        },
        {
            "title": {"en": "Timestamps", "ru": "Временные метки"},
            "fields": ["created_at", "updated_at"],
            "help_text": {
                "en": "Track when the appointment was created and last updated",
                "ru": "Отслеживание времени создания и последнего обновления визита"
            }
        }
    ]


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


class HistoryOfAppointmentAccount(BaseAccount):
    """
    Отображение истории визитов пользователя (личный кабинет).
    """
    model = HistoryOfAppointment
    collection_name = "appointments_history"

    verbose_name = {"en": "Appointment History", "ru": "История приёмов"}
    plural_name = {"en": "Appointments History", "ru": "Истории приёмов"}

    icon = "pi pi-history"

    list_display = [
        "date",
        "doctor_name",
        "diagnosis",
        "cost_money",
        "cost_bonus",
        "created_at",
    ]

    detail_fields = [
        "date",
        "doctor_name",
        "diagnosis",
        "treatment_plan",
        "cost_money",
        "cost_bonus",
        "pdf_reports",
        "created_at",
        "updated_at",
    ]

    computed_fields = []
    read_only_fields = ["created_at", "updated_at"]

    field_titles = {
        "date": {"en": "Visit Date", "ru": "Дата визита"},
        "doctor_name": {"en": "Doctor", "ru": "Врач"},
        "diagnosis": {"en": "Diagnosis", "ru": "Диагноз"},
        "treatment_plan": {"en": "Treatment Plan", "ru": "Назначенное лечение"},
        "cost_money": {"en": "Paid (Money)", "ru": "Оплачено деньгами"},
        "cost_bonus": {"en": "Paid (Bonus)", "ru": "Оплачено бонусами"},
        "pdf_reports": {"en": "PDF Reports", "ru": "Отчёты (PDF)"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Дата обновления"}
    }

    help_texts = {
        "diagnosis": {
            "en": "Brief description of the diagnosis",
            "ru": "Краткое описание диагноза"
        },
        "treatment_plan": {
            "en": "Assigned treatments or instructions from CRM",
            "ru": "Назначенное лечение или инструкции (из CRM)"
        },
        "pdf_reports": {
            "en": "Links or files for conclusions and treatment plans",
            "ru": "Ссылки или файлы на заключения и планы лечения"
        }
    }

    field_groups = [
        {
            "title": {"en": "Visit Details", "ru": "Детали визита"},
            "fields": ["date", "doctor_name", "diagnosis", "treatment_plan", "pdf_reports"],
            "help_text": {
                "en": "Main info about the visit",
                "ru": "Основная информация о приёме"
            }
        },
        {
            "title": {"en": "Costs", "ru": "Оплата"},
            "fields": ["cost_money", "cost_bonus"],
            "help_text": {
                "en": "Payment breakdown (money/bonus)",
                "ru": "Разбивка оплаты (деньги/бонусы)"
            }
        },
        {
            "title": {"en": "Timestamps", "ru": "Временные метки"},
            "fields": ["created_at", "updated_at"],
            "help_text": {
                "en": "When record was created and updated",
                "ru": "Время создания и обновления записи"
            }
        }
    ]


class BonusTransactionInline(InlineAccount):
    """
    Инлайн для транзакций бонусов (accrual/deduction).
    """
    model = BonusTransaction
    collection_name = "bonus_programs"  # Коллекция, где лежит сама BonusProgram
    dot_field_path = "transactions"     # Поле внутри BonusProgram

    verbose_name = {"en": "Bonus Transaction", "ru": "Бонусная транзакция"}
    plural_name = {"en": "Bonus Transactions", "ru": "Бонусные транзакции"}

    icon = "pi pi-dollar"

    list_display = ["date", "amount", "is_accrual"]
    detail_fields = ["date", "amount", "is_accrual", "comment"]

    read_only_fields = []
    computed_fields = []
    field_titles = {
        "date": {"en": "Date", "ru": "Дата"},
        "amount": {"en": "Amount", "ru": "Сумма"},
        "is_accrual": {"en": "Accrual?", "ru": "Начисление?"},
        "comment": {"en": "Comment", "ru": "Комментарий"}
    }

    field_groups = [
        {
            "title": {"en": "Transaction Info", "ru": "Детали транзакции"},
            "fields": ["date", "amount", "is_accrual", "comment"],
            "help_text": {
                "en": "Accrual or deduction of bonus points",
                "ru": "Начисление или списание бонусных баллов"
            }
        }
    ]


class BonusProgramAccount(BaseAccount):
    """
    Управление бонусной программой пользователя.
    """
    model = BonusProgram
    collection_name = "bonus_programs"

    verbose_name = {"en": "Bonus Program", "ru": "Бонусная программа"}
    plural_name = {"en": "Bonus Programs", "ru": "Бонусные программы"}

    icon = "pi pi-credit-card"

    list_display = [
        "balance",
        "referral_link",
        "family_sharing",
        "created_at"
    ]
    detail_fields = [
        "balance",
        "referral_link",
        "family_sharing",
        "transactions",
        "created_at",
        "updated_at"
    ]

    read_only_fields = ["created_at", "updated_at"]
    computed_fields = []

    field_titles = {
        "balance": {"en": "Balance", "ru": "Баланс"},
        "referral_link": {"en": "Referral Link", "ru": "Реферальная ссылка"},
        "family_sharing": {"en": "Family Sharing", "ru": "Передача семье"},
        "transactions": {"en": "Transactions", "ru": "Транзакции"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Дата обновления"}
    }

    help_texts = {
        "balance": {
            "en": "Current bonus balance",
            "ru": "Текущий бонусный баланс"
        },
        "referral_link": {
            "en": "Use this link to invite friends/family",
            "ru": "Используйте ссылку, чтобы приглашать друзей/семью"
        },
        "family_sharing": {
            "en": "Allow transferring bonus points to family members",
            "ru": "Разрешать передавать бонусы членам семьи"
        },
    }

    field_groups = [
        {
            "title": {"en": "Basic Info", "ru": "Основная информация"},
            "fields": ["balance", "referral_link", "family_sharing"],
            "help_text": {
                "en": "Overview of bonus program",
                "ru": "Обзор бонусной программы"
            }
        },
        {
            "title": {"en": "Timestamps", "ru": "Временные метки"},
            "fields": ["created_at", "updated_at"],
            "help_text": {
                "en": "Creation and update times",
                "ru": "Время создания и обновления"
            }
        },
    ]

    # Инлайны
    inlines = {
        "transactions": BonusTransactionInline
    }

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }


class FamilyRelationInline(InlineAccount):
    """
    Инлайн для FamilyRelation (список родственников).
    """
    model = FamilyRelation
    collection_name = "families"     # Коллекция Family
    dot_field_path = "members"       # Поле, где лежат связи

    verbose_name = {"en": "Family Relation", "ru": "Связь в семье"}
    plural_name = {"en": "Family Relations", "ru": "Связи в семье"}

    icon = "pi pi-user-plus"

    list_display = [
        "relative_user_id",
        "confirmed",
        "two_factor_required",
        "created_at"]
    detail_fields = [
        "relative_user_id",
        "confirmed",
        "two_factor_required",
        "created_at",
        "updated_at"]

    field_titles = {
        "relative_user_id": {"en": "Relative User ID", "ru": "ID родственника"},
        "confirmed": {"en": "Confirmed?", "ru": "Подтверждено?"},
        "two_factor_required": {"en": "2FA required?", "ru": "Нужна 2FA?"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Дата обновления"},
    }

    field_groups = [
        {
            "title": {"en": "Relation Info", "ru": "Информация о связи"},
            "fields": ["relative_user_id", "confirmed", "two_factor_required"],
            "help_text": {
                "en": "User ID of relative, 2FA config, and status",
                "ru": "ID родственника, настройка двухфакторки и статус подтверждения"
            }
        },
        {
            "title": {"en": "Timestamps", "ru": "Временные метки"},
            "fields": ["created_at", "updated_at"]
        }
    ]


class FamilyAccount(BaseAccount):
    """
    Раздел «Семья» в личном кабинете.
    """
    model = Family
    collection_name = "families"

    verbose_name = {"en": "Family", "ru": "Семья"}
    plural_name = {"en": "Families", "ru": "Семьи"}

    icon = "pi pi-users"

    list_display = [
        "family_name",
        "owner_user_id",
        "shared_bonus",
        "created_at"
    ]
    detail_fields = [
        "family_name",
        "owner_user_id",
        "shared_bonus",
        "members",
        "created_at",
        "updated_at"
    ]

    read_only_fields = ["created_at", "updated_at"]
    computed_fields = []

    field_titles = {
        "family_name": {"en": "Family Name", "ru": "Название семьи"},
        "owner_user_id": {"en": "Family Owner ID", "ru": "Владелец семьи"},
        "shared_bonus": {"en": "Shared Bonus", "ru": "Общий бонус"},
        "members": {"en": "Family Members", "ru": "Члены семьи"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Дата обновления"},
    }

    field_groups = [
        {
            "title": {"en": "Basic Info", "ru": "Основная информация"},
            "fields": ["family_name", "owner_user_id", "shared_bonus"],
            "help_text": {
                "en": "Manage family name, owner, and shared bonus.",
                "ru": "Управление названием семьи, владельцем и общим бонусом."
            }
        },
        {
            "title": {"en": "Timestamps", "ru": "Временные метки"},
            "fields": ["created_at", "updated_at"]
        }
    ]

    inlines = {
        "members": FamilyRelationInline
    }

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }


class NotificationAccount(BaseAccount):
    """
    Раздел «Уведомления» в личном кабинете.
    """
    model = Notification
    collection_name = "notifications"

    verbose_name = {"en": "Notification", "ru": "Уведомление"}
    plural_name = {"en": "Notifications", "ru": "Уведомления"}

    icon = "pi pi-bell"

    list_display = [
        "user_id",
        "notification_type",
        "message",
        "is_read",
        "created_at",
    ]
    detail_fields = [
        "user_id",
        "notification_type",
        "message",
        "is_read",
        "created_at",
        "updated_at",
    ]

    read_only_fields = ["created_at", "updated_at"]
    computed_fields = []

    field_titles = {
        "user_id": {"en": "User ID", "ru": "ID пользователя"},
        "notification_type": {"en": "Type", "ru": "Тип"},
        "message": {"en": "Message", "ru": "Сообщение"},
        "is_read": {"en": "Read?", "ru": "Прочитано?"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Дата обновления"},
    }

    field_groups = [
        {
            "title": {"en": "Notification Info", "ru": "Информация об уведомлении"},
            "fields": ["user_id", "notification_type", "message", "is_read"],
            "help_text": {
                "en": "Details about the notification",
                "ru": "Детали уведомления"
            }
        },
        {
            "title": {"en": "Timestamps", "ru": "Временные метки"},
            "fields": ["created_at", "updated_at"]
        }
    ]

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }


class UserSettingsAccount(BaseAccount):
    """
    Раздел «Настройки» в личном кабинете.
    """
    model = UserSettings
    collection_name = "user_settings"

    verbose_name = {"en": "User Settings", "ru": "Настройки пользователя"}
    plural_name = {"en": "User Settings", "ru": "Настройки пользователей"}

    icon = "pi pi-cog"

    list_display = [
        "user_id",
        "language",
        "notifications_enabled",
        "created_at"
    ]
    detail_fields = [
        "user_id",
        "language",
        "notifications_enabled",
        "password_hash",
        "created_at",
        "updated_at"
    ]

    read_only_fields = ["created_at", "updated_at"]
    computed_fields = []

    field_titles = {
        "user_id": {"en": "User ID", "ru": "ID пользователя"},
        "language": {"en": "Interface Language", "ru": "Язык интерфейса"},
        "notifications_enabled": {"en": "Notifications Enabled?", "ru": "Включить уведомления?"},
        "password_hash": {"en": "Password Hash", "ru": "Хеш пароля"},
        "created_at": {"en": "Created At", "ru": "Дата создания"},
        "updated_at": {"en": "Updated At", "ru": "Дата обновления"},
    }

    help_texts = {
        "language": {
            "en": "Choose your interface language (RU, EN, PL, etc.)",
            "ru": "Выберите язык интерфейса (RU, EN, PL и т.д.)"
        },
        "notifications_enabled": {
            "en": "Subscribe/unsubscribe from notifications",
            "ru": "Подписаться/отписаться от уведомлений"
        }
    }

    field_groups = [
        {
            "title": {"en": "Main Settings", "ru": "Основные настройки"},
            "fields": ["user_id", "language", "notifications_enabled"],
            "help_text": {
                "en": "Basic user preferences",
                "ru": "Основные пользовательские настройки"
            }
        },
        {
            "title": {"en": "Security", "ru": "Безопасность"},
            "fields": ["password_hash"],
            "help_text": {
                "en": "Change password or store hash",
                "ru": "Смена пароля или хранение хеша"
            }
        },
        {
            "title": {"en": "Timestamps", "ru": "Временные метки"},
            "fields": ["created_at", "updated_at"]
        }
    ]

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }


# account_registry.register("user_settings", UserSettingsAccount(mongo_db))
# account_registry.register("notifications", NotificationAccount(mongo_db))
# account_registry.register("families", FamilyAccount(mongo_db))
# account_registry.register("bonus_programs", BonusProgramAccount(mongo_db))
# account_registry.register(
#     "appointments_history",
#     HistoryOfAppointmentAccount(mongo_db))
# account_registry.register(
#     "calendar_integrations",
#     CalendarIntegrationAccount(mongo_db))
# account_registry.register("appointments", AppointmentAccount(mongo_db))
# account_registry.register("user_profiles", UserProfileAccount(mongo_db))
