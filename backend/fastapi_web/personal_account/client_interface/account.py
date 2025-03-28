"""Персональный аккаунт приложения Клиентский интерфейс."""
from typing import List
from crud_core.registry import account_registry
from db.mongo.db_init import mongo_db
from personal_account.base_account import BaseAccount, InlineAccount

from .db.mongo.schemas import BonusProgramSchema, ConsentItemSchema, ContactInfoSchema, FamilyMemberSchema, HealthSurveySchema, MainInfoSchema, TransactionSchema, UserConsentsSchema

# ==========
# Основная информация
# ==========


class MainInfoAccount(BaseAccount):
    """
    Админка для вкладки 'Основная информация'
    """

    model = MainInfoSchema
    collection_name = "patients_main_info"

    verbose_name = {
        "en": "Basic information",
        "ru": "Основная информация",
        "pl": "Informacje podstawowe"
    }
    plural_name = {
        "en": "Basic information records",
        "ru": "Записи основной информации",
        "pl": "Rekordy podstawowych informacji"
    }

    icon: str = "pi pi-file"
    max_instances_per_user = 1

    list_display = []

    detail_fields = [
        "last_name",
        "first_name",
        "patronymic",
        "birth_date",
        "gender",
        "company_name",
        "patient_id",
        "created_at",
        "updated_at"
    ]

    computed_fields = ["patient_id"]
    read_only_fields = ["created_at", "updated_at", "patient_id"]

    field_titles = {
        "last_name": {"en": "Last Name", "ru": "Фамилия", "pl": "Nazwisko"},
        "first_name": {"en": "First Name", "ru": "Имя", "pl": "Imię"},
        "patronymic": {"en": "Patronymic", "ru": "Отчество", "pl": "Drugie imię"},
        "birth_date": {"en": "Birth Date", "ru": "Дата рождения", "pl": "Data urodzenia"},
        "gender": {"en": "Gender", "ru": "Пол", "pl": "Płeć"},
        "company_name": {"en": "Company Name", "ru": "Название компании", "pl": "Nazwa firmy"},
        "patient_id": {"en": "Patient ID", "ru": "ID пациента", "pl": "ID pacjenta"},
        "created_at": {"en": "Created At", "ru": "Дата создания", "pl": "Data utworzenia"},
        "updated_at": {"en": "Updated At", "ru": "Последнее обновление", "pl": "Ostatnia aktualizacja"},
    }

    help_texts = {
        "last_name": {
            "en": "User's last name",
            "ru": "Фамилия пользователя",
            "pl": "Nazwisko użytkownika"
        },
        "first_name": {
            "en": "User's first name",
            "ru": "Имя пользователя",
            "pl": "Imię użytkownika"
        },
        "patronymic": {
            "en": "User's patronymic",
            "ru": "Отчество пользователя",
            "pl": "Drugie imię użytkownika"
        },
        "birth_date": {
            "en": "User's birth date",
            "ru": "Дата рождения пользователя",
            "pl": "Data urodzenia użytkownika"
        },
        "gender": {
            "en": "Gender",
            "ru": "Пол",
            "pl": "Płeć"
        },
        "company_name": {
            "en": "Company name",
            "ru": "Название компании",
            "pl": "Nazwa firmy"
        },
        "patient_id": {
            "en": "Patient internal ID",
            "ru": "Внутренний ID пациента",
            "pl": "Wewnętrzny ID pacjenta"
        },
        "created_at": {
            "en": "Record creation date",
            "ru": "Дата создания записи",
            "pl": "Data utworzenia rekordu"
        },
        "updated_at": {
            "en": "Record last update date",
            "ru": "Дата последнего обновления записи",
            "pl": "Data ostatniej aktualizacji rekordu"
        }
    }

    field_groups = [
        {
            "title": {"en": "Personal data", "ru": "Личные данные", "pl": "Dane osobowe"},
            "fields": ["last_name", "first_name", "patronymic", "birth_date", "gender"]
        },
        {
            "title": {"en": "Company info", "ru": "Информация о компании", "pl": "Informacje o firmie"},
            "fields": ["company_name"]
        },
        {
            "title": {"en": "System info", "ru": "Системная информация", "pl": "Informacje systemowe"},
            "fields": ["patient_id", "created_at", "updated_at"]
        }
    ]

    allow_crud_actions = {
        "create": False,
        "read": True,
        "update": True,
        "delete": False
    }

    async def get_patient_id(self, obj: dict) -> str:
        """
        Получение ID пациента из внешней CRM (заглушка).
        """
        return "PAT-123456"







class ContactInfoAccount(BaseAccount):
    """
    Админка для вкладки 'Контактная информация'
    """

    model = ContactInfoSchema
    collection_name = "patients_contact_info"

    verbose_name = {
        "en": "Contact information",
        "ru": "Контактная информация",
    }
    plural_name = {
        "en": "Contact information records",
        "ru": "Записи контактной информации",
    }

    icon: str = "pi pi-envelope"  # Пример: иконка конверта

    list_display = [
        "email",
        "phone",
        "pesel",
        "doc_id"
    ]

    detail_fields = [
        "email",
        "phone",
        "address",
        "pesel",
        "doc_id",
        "emergency_contact",
        "updated_at"
    ]

    computed_fields: List[str] = []
    read_only_fields: List[str] = ["updated_at"]  # Или например: ["updated_at"]

    field_titles = {
        "email": {"en": "Email", "ru": "Email"},
        "phone": {"en": "Phone", "ru": "Телефон"},
        "address": {"en": "Address", "ru": "Адрес"},
        "pesel": {"en": "PESEL", "ru": "PESEL"},
        "doc_id": {"en": "Document ID", "ru": "ID документа"},
        "emergency_contact": {"en": "Emergency contact", "ru": "Экстренный контакт"},
        "updated_at": {"en": "Last update", "ru": "Последнее обновление"}
    }

    help_texts = {
        "email": {
            "en": "Enter a valid email address",
            "ru": "Введите действующий адрес электронной почты"
        },
        "phone": {
            "en": "Primary phone number",
            "ru": "Основной номер телефона"
        },
        "address": {
            "en": "Postal or residential address",
            "ru": "Почтовый или фактический адрес проживания"
        },
        "pesel": {
            "en": "National identifier (PESEL, SNILS, etc.)",
            "ru": "Национальный идентификатор (СНИЛС, ИИН, и т.д.)"
        },
        "doc_id": {
            "en": "Passport or other document ID",
            "ru": "Паспорт или другой номер документа"
        },
        "emergency_contact": {
            "en": "Phone of a person to contact in emergency",
            "ru": "Телефон близкого человека для экстренной связи"
        },
        "updated_at": {
            "en": "Date and time this info was last updated",
            "ru": "Дата и время последнего обновления контактных данных"
        }
    }

    # Группируем поля по смыслу
    field_groups = [
        {
            "title": {"en": "Contact details", "ru": "Контактные данные"},
            "fields": ["email", "phone", "emergency_contact"],
            "help_text": {
                "en": "User's main and emergency contact info",
                "ru": "Основные и экстренные контактные данные пользователя"
            }
        },
        {
            "title": {"en": "Address & ID", "ru": "Адрес и документы"},
            "fields": ["address", "pesel", "doc_id"]
        },
        {
            "title": {"en": "System info", "ru": "Системная информация"},
            "fields": ["updated_at"]
        }
    ]

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }


class HealthSurveyAccount(BaseAccount):
    """
    Админка для вкладки 'Анкета здоровья'.
    """

    model = HealthSurveySchema
    collection_name = "patients_health_survey"

    verbose_name = {
        "en": "Health Survey",
        "ru": "Анкета здоровья"
    }
    plural_name = {
        "en": "Health Surveys",
        "ru": "Анкеты здоровья"
    }

    icon: str = "pi pi-heart"

    list_display = [
        "allergies",
        "chronic_conditions",
        "smoking_status",
        "form_status",
        "last_updated"
    ]

    detail_fields = [
        "allergies",
        "chronic_conditions",
        "smoking_status",
        "current_medications",
        "form_status",
        "last_updated"
    ]

    computed_fields: List[str] = []
    read_only_fields: List[str] = ["updated_at"]  # Или например: ["updated_at"]

    field_titles = {
        "allergies": {"en": "Allergies", "ru": "Аллергии"},
        "chronic_conditions": {"en": "Chronic Conditions", "ru": "Хронические заболевания"},
        "smoking_status": {"en": "Smoking Status", "ru": "Статус курения"},
        "current_medications": {"en": "Current Medications", "ru": "Текущие медикаменты"},
        "last_updated": {"en": "Last Updated", "ru": "Последнее обновление"},
        "form_status": {"en": "Form Status", "ru": "Статус анкеты"}
    }

    # Все подсказки / help-тексты храним здесь
    help_texts = {
        "allergies": {
            "en": "Known allergies (medications, foods, etc.)",
            "ru": "Известные аллергии (лекарства, продукты и т.д.)"
        },
        "chronic_conditions": {
            "en": "Select relevant chronic diseases",
            "ru": "Укажите соответствующие хронические заболевания"
        },
        "smoking_status": {
            "en": "Smoking habit status",
            "ru": "Статус курения"
        },
        "current_medications": {
            "en": "Medications user takes on a regular basis",
            "ru": "Препараты, которые пользователь принимает регулярно"
        },
        "last_updated": {
            "en": "Date/time of the last update of this survey",
            "ru": "Дата/время последнего обновления анкеты"
        },
        "form_status": {
            "en": "Overall status of the health survey",
            "ru": "Текущий статус анкеты здоровья"
        }
    }

    field_groups = [
        {
            "title": {"en": "Medical info", "ru": "Медицинские данные"},
            "fields": ["allergies", "chronic_conditions", "smoking_status", "current_medications"]
        },
        {
            "title": {"en": "Survey status", "ru": "Статус анкеты"},
            "fields": ["form_status", "last_updated"]
        }
    ]

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }


class FamilyAccount(BaseAccount):
    """
    Админка для вкладки 'Семья'.
    Управляет списком (FamilySchema.members).
    """

    model = FamilyMemberSchema
    collection_name = "patient_families"

    verbose_name = {
        "en": "Family",
        "ru": "Семья"
    }
    plural_name = {
        "en": "Families",
        "ru": "Семьи"
    }

    icon: str = "pi pi-users"

    # Краткий список (Table View). Показывает,
    # сколько членов семьи или их имена. Это метод-вычисление.
    list_display = ["members_list"]

    # В детальном просмотре укажем поле members,
    # чтобы можно было добавлять/редактировать список членов.
    detail_fields = ["members"]

    # Методы, которые выводят вычисляемую инфу
    computed_fields = ["members_list", "update_member_bonuses"]

    # Поля, недоступные для ручного редактирования
    # (например, 'bonus_balance' внутри каждого члена)
    # Указываем их как `members.*.bonus_balance` или аналогично, зависит от реализации
    read_only_fields = ["members.bonus_balance"]

    field_titles = {
        "members": {"en": "Family Members", "ru": "Члены семьи"}
    }

    help_texts = {
        "members": {
            "en": "List of family members",
            "ru": "Список членов семьи"
        }
    }

    field_groups = [
        {
            "title": {"en": "Family info", "ru": "Информация о семье"},
            "fields": ["members"]
        }
    ]

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }

    # 1) Краткий обзор членов семьи (для list_display)
    async def members_list(self, obj: dict) -> str:
        """
        Вывести имена + ID всех членов семьи одной строкой
        (или html-списком). Это отображается в 'list_display'.
        """
        members = obj.get("members", [])
        if not members:
            return "No family members"
        # Пример форматирования:
        lines = []
        for member in members:
            full_name = member.get("full_name", "")
            patient_id = member.get("patient_id", "")
            relation = member.get("relationship", "")
            # relation может быть JSON-строка от Enum RelationshipEnum
            lines.append(f"{full_name} ({patient_id}, {relation})")
        return " | ".join(lines)

    # 2) Пример заглушки, чтобы "подтянуть" бонусы из внешней CRM
    #    при открытии детальной формы. Система может вызывать это
    #    перед отображением detail (зависит от реализации админки).
    async def update_member_bonuses(self, obj: dict) -> dict:
        """
        Пробегаемся по всем членам семьи и ставим 'bonus_balance' = фейковое значение
        (к примеру, 250 или 100) взятое "из CRM".
        """
        members = obj.get("members", [])
        # Просто пример: для первого сделаем 250, для второго — 100, остальным — 0
        # В реальности вы бы делали запрос в CRM и match'или patient_id
        for i, member in enumerate(members):
            if i == 0:
                member["bonus_balance"] = 250
            elif i == 1:
                member["bonus_balance"] = 100
            else:
                member["bonus_balance"] = 0

        # Возвращаем изменённый объект
        return obj




class TransactionInlineAccount(InlineAccount):
    """
    Множественная (inline) админка для списка транзакций в бонусной программе.
    """

    model = TransactionSchema
    collection_name = "bonus_transactions"  # Условно

    verbose_name = {
        "en": "Transaction",
        "ru": "Транзакция"
    }
    plural_name = {
        "en": "Transactions",
        "ru": "Транзакции"
    }

    icon: str = "pi pi-list"

    list_display = ["transaction_type", "title", "date_time", "amount"]
    detail_fields = ["transaction_type", "title", "date_time", "amount", "comment"]

    computed_fields = []
    read_only_fields = []

    field_titles = {
        "transaction_type": {"en": "Type", "ru": "Тип операции"},
        "title": {"en": "Title", "ru": "Название/причина"},
        "date_time": {"en": "Date/Time", "ru": "Дата/время"},
        "amount": {"en": "Amount", "ru": "Сумма"},
        "comment": {"en": "Comment", "ru": "Комментарий"}
    }

    help_texts = {
        "transaction_type": {
            "en": "Accrued or spent?",
            "ru": "Начислено или потрачено?"
        },
        "title": {
            "en": "Short name of the operation (e.g. 'Referral')",
            "ru": "Короткое название операции (например, 'Реферал')"
        },
        "date_time": {
            "en": "When did this operation happen?",
            "ru": "Когда произошла операция?"
        },
        "amount": {
            "en": "Positive for accrual, negative for spending (or use type?).",
            "ru": "Положительная при начислении, отрицательная при списании (или используйте тип)."
        },
        "comment": {
            "en": "Any additional details about the transaction",
            "ru": "Любые дополнительные детали операции"
        }
    }

    field_groups = [
        {
            "title": {"en": "Transaction data", "ru": "Данные транзакции"},
            "fields": ["transaction_type", "title", "date_time", "amount", "comment"]
        }
    ]

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }

    # Если нужно dot_field_path (если transaction_history вложен в BonusProgramSchema)
    dot_field_path = "transaction_history"


class BonusProgramAccount(BaseAccount):
    """
    Админка для вкладки 'Бонусная программа'.
    """

    model = BonusProgramSchema
    collection_name = "patient_bonus_program"

    verbose_name = {
        "en": "Bonus Program",
        "ru": "Бонусная программа"
    }
    plural_name = {
        "en": "Bonus Programs",
        "ru": "Бонусные программы"
    }

    icon: str = "pi pi-star"

    # В общем списке (list_display) можно показать баланс и дату обновления
    list_display = ["balance", "referral_code", "last_updated"]

    # В детальном просмотре хотим два блока:
    #  - Бонусный счёт (balance, referral_code, last_updated)
    #  - transaction_history (inline)
    detail_fields = ["balance", "referral_code", "last_updated", "transaction_history"]

    # balance - пусть будет "вычисляемым" для наглядности, либо просто read-only
    computed_fields = ["compute_balance"]
    read_only_fields = ["balance"]  # Не даём редактировать руками

    field_titles = {
        "balance": {"en": "Current Balance", "ru": "Текущий баланс"},
        "referral_code": {"en": "Referral Code", "ru": "Реферальный код"},
        "last_updated": {"en": "Last Updated", "ru": "Последнее обновление"},
        "transaction_history": {"en": "Transaction History", "ru": "История транзакций"},
    }

    help_texts = {
        "balance": {
            "en": "Calculated from transaction history or external system",
            "ru": "Вычисляется на основе истории транзакций или подтягивается из внешней системы"
        },
        "referral_code": {
            "en": "Code used for referrals",
            "ru": "Код, используемый для реферальных приглашений"
        },
        "last_updated": {
            "en": "When the bonus data was last updated",
            "ru": "Когда последний раз обновлялись бонусные данные"
        },
        "transaction_history": {
            "en": "All bonus accruals and expenditures",
            "ru": "Все начисления и траты бонусов"
        }
    }

    field_groups = [
        {
            "title": {"en": "Bonus Account", "ru": "Бонусный счёт"},
            "fields": ["balance", "referral_code", "last_updated"]
        },
        {
            "title": {"en": "Transactions", "ru": "История транзакций"},
            "fields": ["transaction_history"]
        }
    ]

    # Подключаем inline
    inlines = {
        "transaction_history": TransactionInlineAccount
    }

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }

    async def compute_balance(self, obj: dict) -> dict:
        """
        Пример вычисления баланса из списка транзакций.
        Или заглушка, возвращающая 450.
        """
        transactions = obj.get("transaction_history", [])
        # Допустим, если transaction_type = SPENT -> вычитаем, иначе добавляем
        balance_calc = 0
        for tx in transactions:
            amount = tx.get("amount", 0)
            # type Enum = json-строка => нужно распарсить или ориентироваться по ключу
            tx_type_json = tx.get("transaction_type", "")
            # Упростим: Если начинается на SPENT, вычитаем. Иначе прибавляем.
            if "SPENT" in tx_type_json:
                balance_calc -= amount
            else:
                balance_calc += amount

        # Запишем в поле 'balance'
        obj["balance"] = balance_calc
        return obj


class ConsentInlineAccount(InlineAccount):
    """
    Inline-админка для редактирования списка согласий (consents).
    """

    model = ConsentItemSchema
    collection_name = "user_consents_items"  # пример

    verbose_name = {
        "en": "Consent",
        "ru": "Согласие"
    }
    plural_name = {
        "en": "Consents",
        "ru": "Согласия"
    }

    icon: str = "pi pi-check-circle"

    list_display = ["consent_type", "accepted"]
    detail_fields = ["consent_type", "accepted"]

    computed_fields = []
    read_only_fields = []

    field_titles = {
        "consent_type": {"en": "Consent Type", "ru": "Тип согласия"},
        "accepted": {"en": "Accepted", "ru": "Принято"},
    }

    help_texts = {
        "consent_type": {
            "en": "Select which consent is this",
            "ru": "Выберите, какое именно это согласие"
        },
        "accepted": {
            "en": "Whether the user has accepted or declined the consent",
            "ru": "Принял ли пользователь это согласие или нет"
        }
    }

    field_groups = [
        {
            "title": {"en": "Consent Data", "ru": "Данные согласия"},
            "fields": ["consent_type", "accepted"]
        }
    ]

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True
    }

    # Если нужно, указываем dot_field_path = "consents"
    dot_field_path = "consents"



class UserConsentsAccount(BaseAccount):
    """
    Админка для вкладки 'Согласия'.
    """

    model = UserConsentsSchema
    collection_name = "user_consents"  # условное название

    verbose_name = {
        "en": "User Consents",
        "ru": "Согласия пользователя"
    }
    plural_name = {
        "en": "User Consents",
        "ru": "Согласия пользователя"
    }

    icon: str = "pi pi-lock"

    list_display = ["consents_list", "last_updated"]
    detail_fields = ["last_updated", "consents"]

    computed_fields = ["consents_list"]
    read_only_fields = []

    field_titles = {
        "last_updated": {"en": "Last Updated", "ru": "Дата последнего обновления"},
        "consents": {"en": "Consents", "ru": "Согласия"},
    }

    help_texts = {
        "last_updated": {
            "en": "When user consents were last updated",
            "ru": "Когда в последний раз обновлялись согласия пользователя"
        },
        "consents": {
            "en": "List of accepted or declined consents",
            "ru": "Список принятых или отклонённых согласий"
        }
    }

    field_groups = [
        {
            "title": {"en": "User Consents", "ru": "Согласия пользователя"},
            "fields": ["last_updated", "consents"]
        }
    ]

    # Подключаем inline-редактор для массива 'consents'
    inlines = {
        "consents": ConsentInlineAccount
    }

    allow_crud_actions = {
        "create": True,
        "read": True,
        "update": True,
        "delete": False
    }

    async def consents_list(self, obj: dict) -> str:
        """
        Для list_display — показать краткую инфу обо всех согласиях (принятые/непринятые).
        """
        items = obj.get("consents", [])
        if not items:
            return "No consents"
        result = []
        for c in items:
            # consent_type может быть JSON-строка (Enum)
            # accepted — bool
            ctype = c.get("consent_type", "")
            accepted = c.get("accepted", False)
            status_label = "✅" if accepted else "❌"
            result.append(f"{status_label} {ctype}")
        return " | ".join(result)


account_registry.register("user_consents", UserConsentsAccount(mongo_db))
account_registry.register("bonus_program", BonusProgramAccount(mongo_db))
account_registry.register("family", FamilyAccount(mongo_db))
account_registry.register("health_survey", HealthSurveyAccount(mongo_db))
account_registry.register("user_settings", MainInfoAccount(mongo_db))
account_registry.register("contact_info", ContactInfoAccount(mongo_db))