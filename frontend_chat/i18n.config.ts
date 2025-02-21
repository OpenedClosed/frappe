// i18n.config.js
export default defineI18nConfig(() => {
  let userLang = "en";
  if (process.client) {
    const browserLang = navigator.language || navigator.userLanguage;
    const shortLang = browserLang.split("-")[0];
    if (["en", "ru", "uk", "pl"].includes(shortLang)) {
      userLang = shortLang;
    }
  }

  return {
    legacy: false,
    locale: userLang,
    fallbackLocale: "en",
    messages: {
      en: {
        chat: "Chat",
        newChat: "New chat",
        sendMessage: "Send a message...",
        chatAgain: "Chat again",
        language: "Language",
        roomActions: [
          {
            name: "archiveRoom",
            title: "Archive Room",
          },
        ],
        menuActions: [
          {
            name: "inviteUser",
            title: "Invite User",
          },
          {
            name: "removeUser",
            title: "Remove User",
          },
          {
            name: "deleteRoom",
            title: "Delete Room",
          },
        ],
        messageActions: [
          {
            name: "replyMessage",
            title: "Reply",
          },
          {
            name: "editMessage",
            title: "Edit Message",
            onlyMe: true,
          },
          {
            name: "deleteMessage",
            title: "Delete Message",
            onlyMe: true,
          },
          {
            name: "selectMessages",
            title: "Select",
          },
        ],
        messageSelectionActions: [
          {
            name: "deleteMessages",
            title: "Delete",
          },
          {
            name: "forwardMessages",
            title: "Forward",
          },
        ],
        templatesText: [
          {
            tag: "help",
            text: "This is the help",
          },
          {
            tag: "action",
            text: "This is the action",
          },
        ],
        textMessages: {
          ROOMS_EMPTY: "No conversations",
          ROOM_EMPTY: "No conversation selected",
          NEW_MESSAGES: "New messages",
          MESSAGE_DELETED: "This message was deleted",
          MESSAGES_EMPTY: "No messages",
          CONVERSATION_STARTED: "The conversation started on:",
          TYPE_MESSAGE: "Type your message",
          SEARCH: "Search",
          IS_ONLINE: "is online",
          LAST_SEEN: "last seen ",
          IS_TYPING: "is typing...",
          CANCEL_SELECT_MESSAGE: "Cancel Selection",
        },
        additionalMessages: {
          chatRefreshed: "Chat Refreshed",
          chatRefreshedSuccessfully: "The chat has been refreshed successfully.",
          errorRefreshingChat: "Error refreshing chat:",
          failedToRefreshChat: "Failed to refresh the chat.",
          sendingMessage: "Sending message:",
          attention: "Attention",
          error: "Error",
          choiceOptions: "Choice Options:",
          choiceOptionsFromLastMessage: "Choice Options (from last message):",
          messagesRetrieved: "Messages Retrieved:",
          newMessage: "New Message:",
          unknownMessageType: "Unknown message type:",
          webSocketConnectionEstablished: "WebSocket connection established.",
          webSocketConnectionClosed: "WebSocket connection closed.",
          webSocketError: "WebSocket error:",
          pageIsVisibleCheckingWSConnection: "Page is visible. Checking WebSocket connection...",
          pageIsHiddenPausingUpdates: "Page is hidden. Pausing updates.",
          windowInFocus: "Window in focus",
          webSocketIsNotOpenReconnecting: "WebSocket is not open. Reconnecting...",
        },
      },
      ru: {
        chat: "Чат",
        newChat: "Новый чат",
        sendMessage: "Отправить сообщение...",
        chatAgain: "Начать заново",
        language: "Язык",
        roomActions: [
          {
            name: "archiveRoom",
            title: "Архивировать комнату",
          },
        ],
        menuActions: [
          {
            name: "inviteUser",
            title: "Пригласить пользователя",
          },
          {
            name: "removeUser",
            title: "Удалить пользователя",
          },
          {
            name: "deleteRoom",
            title: "Удалить комнату",
          },
        ],
        messageActions: [
          {
            name: "replyMessage",
            title: "Ответить",
          },
          {
            name: "editMessage",
            title: "Редактировать",
            onlyMe: true,
          },
          {
            name: "deleteMessage",
            title: "Удалить",
            onlyMe: true,
          },
          {
            name: "selectMessages",
            title: "Выбрать",
          },
        ],
        messageSelectionActions: [
          {
            name: "deleteMessages",
            title: "Удалить",
          },
          {
            name: "forwardMessages",
            title: "Переслать",
          },
        ],
        templatesText: [
          {
            tag: "help",
            text: "Это справка",
          },
          {
            tag: "action",
            text: "Это действие",
          },
        ],
        textMessages: {
          ROOMS_EMPTY: "Нет диалогов",
          ROOM_EMPTY: "Выберите диалог",
          NEW_MESSAGES: "Новые сообщения",
          MESSAGE_DELETED: "Сообщение удалено",
          MESSAGES_EMPTY: "Нет сообщений",
          CONVERSATION_STARTED: "Разговор начался:",
          TYPE_MESSAGE: "Введите сообщение",
          SEARCH: "Поиск",
          IS_ONLINE: "в сети",
          LAST_SEEN: "был(а) в сети",
          IS_TYPING: "печатает...",
          CANCEL_SELECT_MESSAGE: "Отменить выбор",
        },
        additionalMessages: {
          chatRefreshed: "Чат обновлен",
          chatRefreshedSuccessfully: "Чат успешно обновлен.",
          errorRefreshingChat: "Ошибка при обновлении чата:",
          failedToRefreshChat: "Не удалось обновить чат.",
          sendingMessage: "Отправка сообщения:",
          attention: "Внимание",
          error: "Ошибка",
          choiceOptions: "Варианты выбора:",
          choiceOptionsFromLastMessage: "Варианты (из последнего сообщения):",
          messagesRetrieved: "Сообщения получены:",
          newMessage: "Новое сообщение:",
          unknownMessageType: "Неизвестный тип сообщения:",
          webSocketConnectionEstablished: "WebSocket-соединение установлено.",
          webSocketConnectionClosed: "WebSocket-соединение закрыто.",
          webSocketError: "Ошибка WebSocket:",
          pageIsVisibleCheckingWSConnection: "Страница активна. Проверяем соединение...",
          pageIsHiddenPausingUpdates: "Страница скрыта. Обновления приостановлены.",
          windowInFocus: "Окно в фокусе",
          webSocketIsNotOpenReconnecting: "WebSocket не открыт. Переподключаемся...",
        },
      },
      uk: {
        chat: "Чат",
        newChat: "Новий чат",
        sendMessage: "Надіслати повідомлення...",
        chatAgain: "Почати знову",
        language: "Мова",
        roomActions: [
          {
            name: "archiveRoom",
            title: "Архівувати кімнату",
          },
        ],
        menuActions: [
          {
            name: "inviteUser",
            title: "Запросити користувача",
          },
          {
            name: "removeUser",
            title: "Видалити користувача",
          },
          {
            name: "deleteRoom",
            title: "Видалити кімнату",
          },
        ],
        messageActions: [
          {
            name: "replyMessage",
            title: "Відповісти",
          },
          {
            name: "editMessage",
            title: "Редагувати повідомлення",
            onlyMe: true,
          },
          {
            name: "deleteMessage",
            title: "Видалити повідомлення",
            onlyMe: true,
          },
          {
            name: "selectMessages",
            title: "Вибрати",
          },
        ],
        messageSelectionActions: [
          {
            name: "deleteMessages",
            title: "Видалити",
          },
          {
            name: "forwardMessages",
            title: "Переслати",
          },
        ],
        templatesText: [
          {
            tag: "help",
            text: "Це довідка",
          },
          {
            tag: "action",
            text: "Це дія",
          },
        ],
        textMessages: {
          ROOMS_EMPTY: "Немає діалогів",
          ROOM_EMPTY: "Не вибрано діалог",
          NEW_MESSAGES: "Нові повідомлення",
          MESSAGE_DELETED: "Повідомлення видалено",
          MESSAGES_EMPTY: "Немає повідомлень",
          CONVERSATION_STARTED: "Розмова розпочалася:",
          TYPE_MESSAGE: "Введіть повідомлення",
          SEARCH: "Пошук",
          IS_ONLINE: "в мережі",
          LAST_SEEN: "був(ла) в мережі",
          IS_TYPING: "друкує...",
          CANCEL_SELECT_MESSAGE: "Скасувати вибір",
        },
        additionalMessages: {
          chatRefreshed: "Чат оновлено",
          chatRefreshedSuccessfully: "Чат успішно оновлено.",
          errorRefreshingChat: "Помилка під час оновлення чату:",
          failedToRefreshChat: "Не вдалося оновити чат.",
          sendingMessage: "Надсилання повідомлення:",
          attention: "Увага",
          error: "Помилка",
          choiceOptions: "Варіанти вибору:",
          choiceOptionsFromLastMessage: "Варіанти (з останнього повідомлення):",
          messagesRetrieved: "Повідомлення отримано:",
          newMessage: "Нове повідомлення:",
          unknownMessageType: "Невідомий тип повідомлення:",
          webSocketConnectionEstablished: "Підключено WebSocket.",
          webSocketConnectionClosed: "З’єднання WebSocket закрито.",
          webSocketError: "Помилка WebSocket:",
          pageIsVisibleCheckingWSConnection: "Сторінка активна. Перевіряємо з'єднання...",
          pageIsHiddenPausingUpdates: "Сторінка неактивна. Оновлення призупинено.",
          windowInFocus: "Вікно у фокусі",
          webSocketIsNotOpenReconnecting: "WebSocket не відкритий. Повторне підключення...",
        },
      },
      pl: {
        chat: "Czat",
        newChat: "Nowy czat",
        sendMessage: "Wyślij wiadomość...",
        chatAgain: "Rozpocznij ponownie",
        language: "Język",
        roomActions: [
          {
            name: "archiveRoom",
            title: "Archiwizuj pokój",
          },
        ],
        menuActions: [
          {
            name: "inviteUser",
            title: "Zaproś użytkownika",
          },
          {
            name: "removeUser",
            title: "Usuń użytkownika",
          },
          {
            name: "deleteRoom",
            title: "Usuń pokój",
          },
        ],
        messageActions: [
          {
            name: "replyMessage",
            title: "Odpowiedz",
          },
          {
            name: "editMessage",
            title: "Edytuj wiadomość",
            onlyMe: true,
          },
          {
            name: "deleteMessage",
            title: "Usuń wiadomość",
            onlyMe: true,
          },
          {
            name: "selectMessages",
            title: "Wybierz",
          },
        ],
        messageSelectionActions: [
          {
            name: "deleteMessages",
            title: "Usuń",
          },
          {
            name: "forwardMessages",
            title: "Prześlij",
          },
        ],
        templatesText: [
          {
            tag: "help",
            text: "To jest pomoc",
          },
          {
            tag: "action",
            text: "To jest działanie",
          },
        ],
        textMessages: {
          ROOMS_EMPTY: "Brak konwersacji",
          ROOM_EMPTY: "Brak wybranej konwersacji",
          NEW_MESSAGES: "Nowe wiadomości",
          MESSAGE_DELETED: "Wiadomość została usunięta",
          MESSAGES_EMPTY: "Brak wiadomości",
          CONVERSATION_STARTED: "Rozmowa rozpoczęła się:",
          TYPE_MESSAGE: "Wpisz swoją wiadomość",
          SEARCH: "Szukaj",
          IS_ONLINE: "jest online",
          LAST_SEEN: "ostatnio widziano ",
          IS_TYPING: "pisze...",
          CANCEL_SELECT_MESSAGE: "Anuluj wybór",
        },
        additionalMessages: {
          chatRefreshed: "Czat odświeżony",
          chatRefreshedSuccessfully: "Czat został pomyślnie odświeżony.",
          errorRefreshingChat: "Błąd podczas odświeżania czatu:",
          failedToRefreshChat: "Nie udało się odświeżyć czatu.",
          sendingMessage: "Wysyłanie wiadomości:",
          attention: "Uwaga",
          error: "Błąd",
          choiceOptions: "Opcje wyboru:",
          choiceOptionsFromLastMessage: "Opcje (z ostatniej wiadomości):",
          messagesRetrieved: "Odebrano wiadomości:",
          newMessage: "Nowa wiadomość:",
          unknownMessageType: "Nieznany typ wiadomości:",
          webSocketConnectionEstablished: "Połączono z WebSocket.",
          webSocketConnectionClosed: "Połączenie WebSocket zostało zamknięte.",
          webSocketError: "Błąd WebSocket:",
          pageIsVisibleCheckingWSConnection: "Strona jest widoczna. Sprawdzanie połączenia...",
          pageIsHiddenPausingUpdates: "Strona jest ukryta. Wstrzymano aktualizacje.",
          windowInFocus: "Okno w fokuse",
          webSocketIsNotOpenReconnecting: "WebSocket nie jest otwarty. Ponowne łączenie...",
        },
      },
    },
  };
});
