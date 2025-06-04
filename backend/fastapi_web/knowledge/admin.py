"""Админ-панель приложения Знания."""
from admin_core.base_admin import BaseAdmin
from crud_core.registry import admin_registry
from db.mongo.db_init import mongo_db

from .db.mongo.schemas import BotSettings


class BotSettingsAdmin(BaseAdmin):
    model = BotSettings
    collection_name = "bot_settings"

    verbose_name = {
        "en": "Bot Settings",
        "pl": "Ustawienia bota",
        "uk": "Налаштування бота",
        "ru": "Настройки Бота",
        "ka": "ბოტის პარამეტრები"
    }
    plural_name = {
        "en": "Bot Settings",
        "pl": "Ustawienia bota",
        "uk": "Налаштування бота",
        "ru": "Настройки Бота",
        "ka": "ბოტის პარამეტრები"
    }
    icon = "pi pi-cog"

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
        "project_name": {
            "en": "Project Name", "pl": "Nazwa projektu",
            "uk": "Назва проєкту", "ru": "Название проекта",
            "ka": "პროექტის სახელი"
        },
        "employee_name": {
            "en": "Employee Name", "pl": "Imię pracownika",
            "uk": "Ім'я співробітника", "ru": "Имя сотрудника",
            "ka": "თანამშრომლის სახელი"
        },
        "mention_name": {
            "en": "Mention Bot Name in Conversation",
            "pl": "Wspominać nazwę bota w rozmowie",
            "uk": "Чи згадувати ім'я бота в розмові",
            "ru": "Упоминать свое имя при общении",
            "ka": "დაასახელოს თუ არა ბოტმა თავისი სახელი"
        },
        "avatar": {
            "en": "Avatar", "pl": "Avatar",
            "uk": "Аватар", "ru": "Аватар",
            "ka": "ავატარი"
        },
        "bot_color": {
            "en": "Bot Color", "pl": "Kolor bota",
            "uk": "Колір бота", "ru": "Цвет бота",
            "ka": "ბოტის ფერი"
        },
        "communication_tone": {
            "en": "Choose Communication Tone",
            "pl": "Wybierz ton komunikacji",
            "uk": "Виберіть тон спілкування",
            "ru": "Выберите тон общения",
            "ka": "აირჩიეთ კომუნიკაციის ტონი"
        },
        "personality_traits": {
            "en": "Personality Traits", "pl": "Cechy osobowości",
            "uk": "Риси характеру", "ru": "Особенности характера",
            "ka": "პერსონალური თვისებები"
        },
        "additional_instructions": {
            "en": "Additional Instructions", "pl": "Dodatkowe instrukcje",
            "uk": "Додаткові інструкції", "ru": "Дополнительные инструкции",
            "ka": "დამატებითი ინსტრუქციები"
        },
        "role": {
            "en": "Role", "pl": "Rola",
            "uk": "Роль", "ru": "Роль",
            "ka": "როლი"
        },
        "target_action": {
            "en": "Target Action", "pl": "Docelowe działanie",
            "uk": "Цільова дія", "ru": "Целевое действие",
            "ka": "სამიზნე ქმედება"
        },
        "core_principles": {
            "en": "Core Principles", "pl": "Podstawowe zasady",
            "uk": "Основні принципи", "ru": "Ключевые принципы",
            "ka": "ძირითადი პრინციპები"
        },
        "special_instructions": {
            "en": "Special Instructions", "pl": "Specjalne instrukcje",
            "uk": "Спеціальні інструкції", "ru": "Специальные инструкции",
            "ka": "სპეციალური ინსტრუქციები"
        },
        "forbidden_topics": {
            "en": "Forbidden Topics", "pl": "Tematy zakazane",
            "uk": "Заборонені теми", "ru": "Запретные темы",
            "ka": "აკრძალული თემები"
        },
        "greeting": {
            "en": "Greeting", "pl": "Powitanie",
            "uk": "Привітання", "ru": "Приветствие",
            "ka": "მისალმება"
        },
        "error_message": {
            "en": "Error Message", "pl": "Komunikat błędu",
            "uk": "Повідомлення про помилку", "ru": "Ошибка",
            "ka": "შეცდომის შეტყობინება"
        },
        "farewell_message": {
            "en": "Farewell Message", "pl": "Pożegnanie",
            "uk": "Прощальне повідомлення", "ru": "Прощание",
            "ka": "სამამშვიდობო შეტყობინება"
        },
        "fallback_ai_error_message": {
            "en": "AI Error Fallback", "pl": "Komunikat o błędzie AI",
            "uk": "Повідомлення при помилці ІІ",
            "ru": "Сообщение при ошибке ИИ", "ka": "AI-ის შეცდომის შეტყობინება"
        },
        "ai_model": {
            "en": "AI Model", "pl": "Model AI",
            "uk": "Модель ІІ", "ru": "Выбор модели",
            "ka": "AI მოდელი"
        },
        "created_at": {
            "en": "Created At", "pl": "Data utworzenia",
            "uk": "Дата створення", "ru": "Дата создания",
            "ka": "შექმნის თარიღი"
        }
    }

    help_texts = {
        "project_name": {
            "en": "Short name of the project using the bot.",
            "pl": "Krótka nazwa projektu, w którym używany jest bot.",
            "uk": "Коротка назва проєкту, в якому використовується бот.",
            "ru": "Короткое название проекта, в котором используется бот.",
            "ka": "მოკლე სახელი პროექტისა, სადაც გამოიყენება ბოტი."
        },
        "employee_name": {
            "en": "The name of the employee that the bot represents.",
            "pl": "Imię pracownika, którego bot reprezentuje.",
            "uk": "Ім'я співробітника, якого представляє бот.",
            "ru": "Имя сотрудника, которого представляет бот.",
            "ka": "თანამშრომლის სახელი, რომელსაც ბოტი წარმოადგენს."
        },
        "mention_name": {
            "en": "Should the bot mention its name?",
            "pl": "Czy bot powinien wspominać swoje imię?",
            "uk": "Чи має бот згадувати своє ім'я?",
            "ru": "Должен ли бот упоминать свое имя?",
            "ka": "უნდა ახსენოს ბოტმა თავისი სახელი?"
        },
        "avatar": {
            "en": "Upload an image for the bot's avatar.",
            "pl": "Prześlij obrazek avatara bota.",
            "uk": "Завантажте зображення аватара бота.",
            "ru": "Загрузите изображение для аватара бота.",
            "ka": "ატვირთეთ ბოტის ავატარის სურათი."
        },
        "bot_color": {
            "en": "If you don’t have time to customize the bot, we can do it for you.",
            "pl": "Jeśli nie masz czasu na personalizację bota, możemy zrobić to za Ciebie.",
            "uk": "Якщо у вас немає часу налаштовувати бота, ми можемо зробити це за вас.",
            "ru": "Если у вас нет времени на кастомизацию бота, мы можем сделать это для вас.",
            "ka": "თუ ბოტის პერსონალიზაციის დრო არ გაქვთ, ამას ჩვენ გავაკეთებთ."
        },
        "communication_tone": {
            "en": "Choose the bot's communication style.",
            "pl": "Wybierz styl komunikacji bota.",
            "uk": "Виберіть стиль спілкування бота.",
            "ru": "Выберите стиль общения бота.",
            "ka": "აირჩიეთ ბოტის კომუნიკაციის სტილი."
        },
        "personality_traits": {
            "en": "Define key personality traits for the bot.",
            "pl": "Zdefiniuj kluczowe cechy osobowości bota.",
            "uk": "Визначте ключові риси характеру бота.",
            "ru": "Определите ключевые черты характера бота.",
            "ka": "ადგინეთ ბოტის ძირითადი თვისებები."
        },
        "additional_instructions": {
            "en": "Provide any additional guidelines for bot behavior.",
            "pl": "Podaj dodatkowe wytyczne dotyczące zachowania bota.",
            "uk": "Надайте додаткові вказівки щодо поведінки бота.",
            "ru": "Укажите любые дополнительные инструкции для поведения бота.",
            "ka": "დაამატეთ დამატებითი მითითებები ბოტის ქცევისთვის."
        },
        "role": {
            "en": "Specify the bot's role in the project.",
            "pl": "Określ rolę bota w projekcie.",
            "uk": "Вкажіть роль бота в проєкті.",
            "ru": "Укажите роль бота в проекте.",
            "ka": "მიუთითეთ ბოტის როლი პროექტში."
        },
        "target_action": {
            "en": "List of actions the bot is designed to perform.",
            "pl": "Lista działań, które bot ma wykonywać.",
            "uk": "Перелік дій, які має виконувати бот.",
            "ru": "Список действий, которые должен выполнять бот.",
            "ka": "ქმედებების სია, რომელიც ბოტმა უნდა შეასრულოს."
        },
        "core_principles": {
            "en": "Fundamental principles guiding the bot's responses.",
            "pl": "Fundamentalne zasady kierujące odpowiedziami bota.",
            "uk": "Основні принципи, що визначають відповіді бота.",
            "ru": "Основные принципы, определяющие ответы бота.",
            "ka": "ფუნდამენტური პრინციპები, რომლებიც ხელმძღვანელობს ბოტს."
        },
        "special_instructions": {
            "en": "Additional functionality settings.",
            "pl": "Dodatkowe ustawienia funkcjonalności.",
            "uk": "Додаткові налаштування функціональності.",
            "ru": "Дополнительные настройки функциональности.",
            "ka": "დამატებითი ფუნქციონალური პარამეტრები."
        },
        "forbidden_topics": {
            "en": "Topics the bot should avoid.",
            "pl": "Tematy, których bot powinien unikać.",
            "uk": "Тематики, яких бот повинен уникати.",
            "ru": "Темы, которых бот должен избегать.",
            "ka": "თემები, რომლებსაც ბოტი უნდა მოერიდოს."
        },
        "greeting": {
            "en": "Default greeting messages in different languages.",
            "pl": "Domyślne wiadomości powitalne w różnych językach.",
            "uk": "Типові привітальні повідомлення різними мовами.",
            "ru": "Стандартные приветственные сообщения на разных языках.",
            "ka": "სტანდარტული მისალმებები სხვადასხვა ენაზე."
        },
        "error_message": {
            "en": "Message displayed when the bot cannot answer a question.",
            "pl": "Wiadomość wyświetlana, gdy bot nie może odpowiedzieć.",
            "uk": "Повідомлення, яке відображається, коли бот не може відповісти.",
            "ru": "Сообщение, отображаемое, когда бот не может ответить на вопрос.",
            "ka": "შეტყობინება, როცა ბოტს პასუხის გაცემვა არ შეუძლია."
        },
        "farewell_message": {
            "en": "Bot's goodbye message.",
            "pl": "Pożegnalna wiadomość bota.",
            "uk": "Прощальне повідомлення бота.",
            "ru": "Прощальное сообщение бота.",
            "ka": "ბოტის სამამშვიდობო შეტყობინება."
        },
        "fallback_ai_error_message": {
            "en": "Message shown if AI fails to generate a response.",
            "pl": "Wiadomość, gdy AI nie wygeneruje odpowiedzi.",
            "uk": "Повідомлення при помилці генерації відповіді ІІ.",
            "ru": "Сообщение при ошибке генерации ответа ИИ.",
            "ka": "შეტყობინება, თუ AI ვერ ქმნის პასუხს."
        },
        "ai_model": {
            "en": "AI model the bot is using.",
            "pl": "Model AI używany przez bota.",
            "uk": "Модель ІІ, яку використовує бот.",
            "ru": "Модель ИИ, которую использует бот.",
            "ka": "AI მოდელი, რომელსაც ბოტი იყენებს."
        },
        "created_at": {
            "en": "Timestamp when the bot settings were created.",
            "pl": "Znacznik czasu utworzenia ustawień bota.",
            "uk": "Дата та час створення налаштувань бота.",
            "ru": "Дата и время создания настроек бота.",
            "ka": "ბოტის პარამეტრების შექმნის დრო."
        }
    }

    field_groups = [
        {
            "title": {
                "en": "Basic Settings", "pl": "Ustawienia podstawowe",
                "uk": "Базові налаштування", "ru": "Основные настройки",
                "ka": "ძირითადი პარამეტრები"
            },
            "fields": ["project_name", "employee_name", "mention_name", "avatar", "bot_color"],
            "help_text": {
                "en": "Define basic bot information",
                "pl": "Zdefiniuj podstawowe informacje o bocie",
                "uk": "Визначте базову інформацію про бота",
                "ru": "Определите основные настройки бота",
                "ka": "მიუთითეთ ბოტის ძირითადი ინფორმაცია"
            }
        },
        {
            "title": {
                "en": "Character and Behavior", "pl": "Charakter i zachowanie",
                "uk": "Характер і поведінка", "ru": "Характер и поведение",
                "ka": "პერსონა და ქცევა"
            },
            "fields": ["communication_tone", "personality_traits", "additional_instructions", "role", "target_action"],
            "help_text": {
                "en": "Set how the bot interacts with users",
                "pl": "Ustaw, jak bot wchodzi w interakcję z użytkownikami",
                "uk": "Налаштуйте, як бот взаємодіє з користувачами",
                "ru": "Настройте поведение бота в общении",
                "ka": "დააყენეთ, თუ როგორ ურთიერთობს ბოტი მომხმარებლებთან"
            }
        },
        {
            "title": {
                "en": "Topics and Restrictions", "pl": "Tematy i ograniczenia",
                "uk": "Тематики та обмеження", "ru": "Темы и ограничения",
                "ka": "თემები და შეზღუდვები"
            },
            "fields": ["core_principles", "special_instructions", "forbidden_topics"],
            "help_text": {
                "en": "Define allowed and restricted topics",
                "pl": "Zdefiniuj dozwolone i ograniczone tematy",
                "uk": "Визначте дозволені та заборонені теми",
                "ru": "Настройте темы, которые бот может обсуждать",
                "ka": "დაადგინეთ დაშვებული და შეზღუდული თემები"
            }
        },
        {
            "title": {
                "en": "Interaction Guidelines", "pl": "Wytyczne interakcji",
                "uk": "Правила взаємодії", "ru": "Правила взаимодействия",
                "ka": "ინტერაქციის წესები"
            },
            "fields": ["greeting", "error_message", "farewell_message", "fallback_ai_error_message"],
            "help_text": {
                "en": "Set the bot's predefined messages",
                "pl": "Ustaw predefiniowane wiadomości bota",
                "uk": "Встановіть заздалегідь задані повідомлення бота",
                "ru": "Определите автоматические сообщения бота",
                "ka": "მიუთითეთ ბოტის ავტომატური შეტყობინებები"
            }
        },
        {
            "title": {
                "en": "Artificial Intelligence", "pl": "Sztuczna inteligencja",
                "uk": "Штучний інтелект", "ru": "Искусственный интеллект",
                "ka": "ხელოვნური ინტელექტი"
            },
            "fields": ["ai_model"],
            "help_text": {
                "en": "Choose the AI model for your bot",
                "pl": "Wybierz model AI dla swojego bota",
                "uk": "Оберіть модель ІІ для вашого бота",
                "ru": "Выберите модель ИИ для вашего бота",
                "ka": "აირჩიეთ ბოტისთვის AI მოდელი"
            }
        }
    ]


admin_registry.register("bot_settings", BotSettingsAdmin(mongo_db))
