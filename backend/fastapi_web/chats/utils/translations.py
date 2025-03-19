"""Перевод фраз бота в приложении Чаты."""

TRANSLATIONS = {
    "brief": {
        "please_choose": {
            "en": "Please choose:",
            "ru": "Пожалуйста, выберите:",
            "ar": "يرجى الاختيار:",
            "pl": "Proszę wybrać:",
            "uk": "Будь ласка, виберіть:",
            "zh": "请选择：",
            "es": "Por favor elige:"
        },
        "brief_completed": {
            "en": "Brief completed! You can now ask your question.",
            "ru": "Бриф завершён! Теперь вы можете задать свой вопрос.",
            "ar": "تم إكمال الموجز! يمكنك الآن طرح سؤالك.",
            "pl": "Brief zakończony! Teraz możesz zadać swoje pytanie.",
            "uk": "Бриф завершено! Тепер ви можете задати своє питання.",
            "zh": "简介完成！现在您可以提问了。",
            "es": "¡Brief completado! Ahora puedes hacer tu pregunta."
        },
    },
    "choices": {
        "consultant": {
            "en": "Consultant",
            "ru": "Консультант",
            "ar": "مستشار",
            "pl": "Konsultant",
            "uk": "Консультант",
            "zh": "顾问",
            "es": "Consultor"
        },
        "get_auto_mode": {
            "en": "🔄 Switch to Auto Mode",
            "ru": "🔄 Вернуться в авто-режим",
            "ar": "🔄 العودة إلى الوضع التلقائي",
            "pl": "🔄 Przełącz na tryb automatyczny",
            "uk": "🔄 Перейти в авто-режим",
            "zh": "🔄 切换到自动模式",
            "es": "🔄 Cambiar al modo automático"
        }
    },
    "info": {
        "manual_mode_enabled": {
            "en": "Chat has been switched to manual mode. A consultant will assist you soon!",
            "ru": "Чат переведён в ручной режим. Скоро вам поможет консультант!",
            "ar": "تم تحويل الدردشة إلى الوضع اليدوي. سيساعدك المستشار قريبًا!",
            "pl": "Czat został przełączony w tryb ręczny. Konsultant wkrótce pomoże!",
            "uk": "Чат переведено в ручний режим. Незабаром вам допоможе консультант!",
            "zh": "聊天已切换到手动模式。顾问很快会帮助您！",
            "es": "El chat se ha cambiado al modo manual. ¡Un consultor te asistirá pronto!"
        },
        "auto_mode_enabled": {
            "en": "You are back in automatic mode. Feel free to ask any questions!",
            "ru": "Вы снова в автоматическом режиме. Не стесняйтесь задавать вопросы!",
            "ar": "أنت الآن في الوضع التلقائي. لا تتردد في طرح أي أسئلة!",
            "pl": "Jesteś z powrotem w trybie automatycznym. Śmiało zadawaj pytania!",
            "uk": "Ви знову в автоматичному режимі. Не соромтеся ставити запитання!",
            "zh": "您已返回自动模式。请随时提问！",
            "es": "Has vuelto al modo automático. ¡Siéntete libre de hacer preguntas!"
        }
    },
    "errors": {
        "chat_not_exist": {
            "en": "Chat does not exist.",
            "ru": "Чат не существует.",
            "ar": "المحادثة غير موجودة.",
            "pl": "Czat nie istnieje.",
            "uk": "Чат не існує.",
            "zh": "聊天不存在。",
            "es": "El chat no existe."
        },
        "invalid_chat_data": {
            "en": "Invalid chat data.",
            "ru": "Неверные данные чата.",
            "ar": "بيانات المحادثة غير صالحة.",
            "pl": "Nieprawidłowe dane czatu.",
            "uk": "Невірні дані чату.",
            "zh": "无效的聊天数据。",
            "es": "Datos de chat inválidos."
        },
        "chat_status_invalid": {
            "en": "Chat is in status {status}.",
            "ru": "Чат в статусе {status}.",
            "ar": "المحادثة في حالة {status}.",
            "pl": "Czat jest w statusie {status}.",
            "uk": "Чат у статусі {status}.",
            "zh": "聊天处于 {status} 状态。",
            "es": "El chat está en estado {status}."
        },
        "invalid_choice": {
            "en": "Invalid choice. Must pick from: {choices}.",
            "ru": "Неверный выбор. Нужно выбрать из: {choices}.",
            "ar": "اختيار غير صالح. يجب الاختيار من: {choices}.",
            "pl": "Nieprawidłowy wybór. Musisz wybrać z: {choices}.",
            "uk": "Невірний вибір. Потрібно вибрати з: {choices}.",
            "zh": "无效的选择。必须从以下选项中选择：{choices}。",
            "es": "Opción inválida. Debes elegir entre: {choices}."
        },
        "invalid_answer": {
            "en": "Invalid answer. Must pick from: {choices}.",
            "ru": "Неверный ответ. Нужно выбрать из: {choices}.",
            "ar": "إجابة غير صالحة. يجب الاختيار من: {choices}.",
            "pl": "Nieprawidłowa odpowiedź. Musisz wybrać z: {choices}.",
            "uk": "Невірна відповідь. Потрібно вибрати з: {choices}.",
            "zh": "无效的答案。必须从以下选项中选择：{choices}。",
            "es": "Respuesta inválida. Debes elegir entre: {choices}."
        }
    },
    "attention": {
        "too_fast": {
            "en": "You are sending messages too quickly. Please wait a bit.",
            "ru": "Вы отправляете сообщения слишком быстро. Пожалуйста, подождите немного.",
            "ar": "أنت ترسل الرسائل بسرعة كبيرة. يرجى الانتظار قليلاً.",
            "pl": "Wysyłasz wiadomości zbyt szybko. Poczekaj chwilę.",
            "uk": "Ви надсилаєте повідомлення надто швидко. Будь ласка, зачекайте трохи.",
            "zh": "您发送消息的速度太快了。请稍等片刻。",
            "es": "Estás enviando mensajes demasiado rápido. Por favor, espera un poco."
        },
        "unknown_command": {
            "en": "Unknown command. Please check your input.",
            "ru": "Неизвестная команда. Проверьте правильность ввода.",
            "ar": "أمر غير معروف. يرجى التحقق من الإدخال.",
            "pl": "Nieznana komenda. Sprawdź swoje dane wejściowe.",
            "uk": "Невідома команда. Перевірте правильність введення.",
            "zh": "未知命令。请检查您的输入。",
            "es": "Comando desconocido. Por favor, revisa tu entrada."
        }
    }
}
