"""Перевод фраз бота в чате."""

TRANSLATIONS = {
    "brief": {
        "please_choose": {
            "en": "Please choose:",
            "ru": "Пожалуйста, выберите:",
            "pl": "Proszę wybrać:",
            "uk": "Будь ласка, виберіть:",
            "ge": "გთხოვთ, აირჩიეთ:"
        },
        "brief_completed": {
            "en": "Brief completed! You can now ask your question.",
            "ru": "Бриф завершён! Теперь вы можете задать свой вопрос.",
            "pl": "Brief zakończony! Możesz teraz zadać pytanie.",
            "uk": "Бриф завершено! Тепер ви можете задати своє питання.",
            "ge": "ბრიფი დასრულდა! ახლა შეგიძლიათ დასვათ თქვენი შეკითხვა."
        },
    },
    "choices": {
        "consultant": {
            "en": "Consultant",
            "ru": "Консультант",
            "pl": "Konsultant",
            "uk": "Консультант",
            "ge": "კონსულტანტი"
        },
        "get_auto_mode": {
            "en": "🔄 Switch to Auto Mode",
            "ru": "🔄 Вернуться в авто-режим",
            "pl": "🔄 Przełącz na tryb automatyczny",
            "uk": "🔄 Повернутися в авто-режим",
            "ge": "🔄 გადართვა ავტომატურ რეჟიმზე"
        }
    },
    "info": {
        "manual_mode_enabled": {
            "en": "Chat has been switched to manual mode. A consultant will assist you soon!",
            "ru": "Чат переведён в ручной режим. Скоро вам поможет консультант!",
            "pl": "Czat został przełączony na tryb ręczny. Konsultant wkrótce Ci pomoże!",
            "uk": "Чат переведено в ручний режим. Незабаром вам допоможе консультант!",
            "ge": "ჩეთი გადართულია ხელით რეჟიმზე. კონსულტანტი მალე დაგეხმარებათ!"
        },
        "auto_mode_enabled": {
            "en": "You are back in automatic mode. Feel free to ask any questions!",
            "ru": "Вы снова в автоматическом режиме. Не стесняйтесь задавать вопросы!",
            "pl": "Jesteś z powrotem w trybie automatycznym. Śmiało pytaj!",
            "uk": "Ви знову в автоматичному режимі. Не соромтеся задавати питання!",
            "ge": "თქვენ კვლავ ავტომატურ რეჟიმში ხართ. ნუ მოგერიდებათ დასვათ შეკითხვები!"
        }
    },
    "errors": {
        "complex_question": {
            "en": (
                "Hello! 😊 Thank you for your question!\n\n"
                "At the moment, I don’t have the exact information, but our manager will join the chat shortly to assist you. 🚀\n\n"
                "If your request is urgent, you can also contact us via:\n"
                "📞 WhatsApp: +995 555 497 992\n\n"
                "We appreciate your patience and will get back to you as soon as possible! 🙌"
            ),
            "ru": (
                "Здравствуйте! 😊 Спасибо за ваш вопрос!\n\n"
                "В данный момент у меня нет точной информации, но менеджер скоро подключится к чату и поможет вам. 🚀\n\n"
                "Если ваш запрос срочный, вы можете связаться с нами через:\n"
                "📞 WhatsApp: +995 555 497 992\n\n"
                "Благодарим вас за терпение, скоро ответим! 🙌"
            ),
            "pl": (
                "Cześć! 😊 Dziękujemy za pytanie!\n\n"
                "Obecnie nie mam dokładnych informacji, ale nasz menedżer wkrótce dołączy do czatu, aby Ci pomóc. 🚀\n\n"
                "Jeśli Twoje zapytanie jest pilne, możesz skontaktować się z nami poprzez:\n"
                "📞 WhatsApp: +995 555 497 992\n\n"
                "Dziękujemy za cierpliwość, wkrótce odpowiemy! 🙌"
            ),
            "uk": (
                "Вітаю! 😊 Дякуємо за ваше питання!\n\n"
                "Наразі у мене немає точної інформації, але наш менеджер незабаром приєднається до чату, щоб допомогти вам. 🚀\n\n"
                "Якщо ваш запит терміновий, ви також можете зв'язатися з нами через:\n"
                "📞 WhatsApp: +995 555 497 992\n\n"
                "Дякуємо за терпіння, незабаром відповімо! 🙌"
            ),
            "ge": (
                "გამარჯობა! 😊 გმადლობთ თქვენს შეკითხვაზე!\n\n"
                "ამჟამად არ მაქვს ზუსტი ინფორმაცია, მაგრამ ჩვენი მენეჯერი მალე შემოგიერთდება ჩეთში, რათა დაგეხმაროთ. 🚀\n\n"
                "თუ თქვენი მოთხოვნა სასწრაფოა, შეგიძლიათ დაგვიკავშირდეთ:\n"
                "📞 WhatsApp: +995 555 497 992\n\n"
                "გმადლობთ მოთმინებისთვის, მალე დაგიბრუნებთ პასუხს! 🙌"
            )
        }
    },
    "attention": {
        "too_fast": {
            "en": "You are sending messages too quickly. Please wait a bit.",
            "ru": "Вы отправляете сообщения слишком быстро. Пожалуйста, подождите немного.",
            "pl": "Wysyłasz wiadomości zbyt szybko. Proszę chwilę poczekać.",
            "uk": "Ви надсилаєте повідомлення занадто швидко. Будь ласка, зачекайте трохи.",
            "ge": "თქვენ ძალიან სწრაფად აგზავნით შეტყობინებებს. გთხოვთ, დაელოდეთ ცოტა."
        },
        "unknown_command": {
            "en": "Unknown command. Please check your input.",
            "ru": "Неизвестная команда. Проверьте правильность ввода.",
            "pl": "Nieznana komenda. Proszę sprawdzić poprawność wpisu.",
            "uk": "Невідома команда. Перевірте правильність введення.",
            "ge": "უცნობი ბრძანება. გთხოვთ, შეამოწმოთ შეყვანილი ინფორმაცია."
        }
    }
}
