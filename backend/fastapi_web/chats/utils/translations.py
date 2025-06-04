"""Перевод фраз бота в приложении Чаты."""

TRANSLATIONS = {
    "brief": {
        "please_choose": {
            "en": "Please choose:",
            "pl": "Proszę wybrać:",
            "uk": "Будь ласка, виберіть:",
            "ru": "Пожалуйста, выберите:",
            "ka": "გთხოვთ, აირჩიეთ:"
        },
        "brief_completed": {
            "en": "Brief completed! You can now ask your question.",
            "pl": "Brief zakończony! Teraz możesz zadać swoje pytanie.",
            "uk": "Бриф завершено! Тепер ви можете задати своє питання.",
            "ru": "Бриф завершён! Теперь вы можете задать свой вопрос.",
            "ka": "ბრიფი დასრულებულია! შეგიძლიათ დასვათ კითხვა."
        },
    },
    "choices": {
        "consultant": {
            "en": "Consultant",
            "pl": "Konsultant",
            "uk": "Консультант",
            "ru": "Консультант",
            "ka": "კონსულტანტი"
        },
        "get_auto_mode": {
            "en": "🔄 Switch to Auto Mode",
            "pl": "🔄 Przełącz na tryb automatyczny",
            "uk": "🔄 Перейти в авто-режим",
            "ru": "🔄 Вернуться в авто-режим",
            "ka": "🔄 გადართვა ავტომატურ რეჟიმზე"
        }
    },
    "info": {
        "manual_mode_enabled": {
            "en": "Chat has been switched to manual mode. A consultant will assist you soon!",
            "pl": "Czat został przełączony w tryb ręczny. Konsultant wkrótce pomoże!",
            "uk": "Чат переведено в ручний режим. Незабаром вам допоможе консультант!",
            "ru": "Чат переведён в ручной режим. Скоро вам поможет консультант!",
            "ka": "ჩატი გადაიყვანეს ხელით რეჟიმში. კონსულტანტი მალე დაგეხმარებათ!"
        },
        "auto_mode_enabled": {
            "en": "You are back in automatic mode. Feel free to ask any questions!",
            "pl": "Jesteś z powrotem w trybie automatycznym. Śmiało zadawaj pytania!",
            "uk": "Ви знову в автоматичному режимі. Не соромтеся ставити запитання!",
            "ru": "Вы снова в автоматическом режиме. Не стесняйтесь задавать вопросы!",
            "ka": "თქვენ დაბრუნდით ავტომატურ რეჟიმში. თავისუფლად დასვით კითხვები!"
        }
    },
    "errors": {
        "chat_not_exist": {
            "en": "Chat does not exist.",
            "pl": "Czat nie istnieje.",
            "uk": "Чат не існує.",
            "ru": "Чат не существует.",
            "ka": "ჩატი არ არსებობს."
        },
        "invalid_chat_data": {
            "en": "Invalid chat data.",
            "pl": "Nieprawidłowe dane czatu.",
            "uk": "Невірні дані чату.",
            "ru": "Неверные данные чата.",
            "ka": "არასწორი ჩატის მონაცემები."
        },
        "chat_status_invalid": {
            "en": "Chat is in status {status}.",
            "pl": "Czat jest w statusie {status}.",
            "uk": "Чат у статусі {status}.",
            "ru": "Чат в статусе {status}.",
            "ka": "ჩატი იმყოფება სტატუსში: {status}."
        },
        "invalid_choice": {
            "en": "Invalid choice. Must pick from: {choices}.",
            "pl": "Nieprawidłowy wybór. Musisz wybrać z: {choices}.",
            "uk": "Невірний вибір. Потрібно вибрати з: {choices}.",
            "ru": "Неверный выбор. Нужно выбрать из: {choices}.",
            "ka": "არასწორი არჩევანი. აირჩიეთ შემდეგიდან: {choices}."
        },
        "invalid_answer": {
            "en": "Invalid answer. Must pick from: {choices}.",
            "pl": "Nieprawidłowa odpowiedź. Musisz wybrać z: {choices}.",
            "uk": "Невірна відповідь. Потрібно вибрати з: {choices}.",
            "ru": "Неверный ответ. Нужно выбрать из: {choices}.",
            "ka": "არასწორი პასუხი. აირჩიეთ შემდეგიდან: {choices}."
        },
        "message_too_long": {
            "en": "Message is too long. Please shorten it.",
            "pl": "Wiadomość jest zbyt długa. Skróć ją.",
            "uk": "Повідомлення надто довге. Скоротіть його.",
            "ru": "Сообщение слишком длинное. Пожалуйста, сократите его.",
            "ka": "შეტყობინება ძალიან გრძელია. შეამოკლეთ ის."
        }
    },
    "attention": {
        "too_fast": {
            "en": "You are sending messages too quickly. Please wait a bit.",
            "pl": "Wysyłasz wiadomości zbyt szybko. Poczekaj chwilę.",
            "uk": "Ви надсилаєте повідомлення надто швидко. Будь ласка, зачекайте трохи.",
            "ru": "Вы отправляете сообщения слишком быстро. Пожалуйста, подождите немного.",
            "ka": "შეტყობინებებს ძალიან სწრაფად აგზავნით. გთხოვთ, მოითმინეთ ცოტათი."
        },
        "unknown_command": {
            "en": "Unknown command. Please check your input.",
            "pl": "Nieznana komenda. Sprawdź swoje dane wejściowe.",
            "uk": "Невідома команда. Перевірте правильність введення.",
            "ru": "Неизвестная команда. Проверьте правильность ввода.",
            "ka": "უცნობი ბრძანება. გთხოვთ გადაამოწმოთ შეყვანილი ტექსტი."
        }
    }
}
