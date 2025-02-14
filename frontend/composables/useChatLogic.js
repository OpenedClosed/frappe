// ~/composables/useChatLogic.js
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import { useToast } from "primevue/usetoast";

export function useChatLogic(options = {}) {
  const { isTelegram = false } = options; // если нужно переключение под Telegram
  const { t } = useI18n();
  const toast = useToast();

  // Состояние экрана, устройства и т.п.
  const isMobile = ref(false);
  const isIphone = ref(false);

  // Текущий пользователь и комнаты
  const currentUserId = ref("1234");
  const activeRoomId = ref("1");
  const rooms = ref([
    {
      roomId: "1",
      avatar: "/favicon.ico",
      users: [
        { _id: "1234", username: "User" },
        { _id: "4321", username: "AI" },
      ],
      roomActions: [
        { name: "inviteUser", title: "Invite User" },
        { name: "removeUser", title: "Remove User" },
        { name: "deleteRoom", title: "Delete Room" },
      ],
    },
  ]);

  // Список сообщений и статус загрузки
  const messages = ref([]);
  const messagesLoaded = ref(false);

  // Настройки выбора опций
  const choiceOptions = ref([]);
  const isChoiceStrict = ref(false);

  // Таймеры и флаги
  const timerExpired = ref(false);
  const countdown = ref(0);
  let countdownInterval = null;

  // Храним WebSocket-соединение
  const websocket = ref(null);
  const currenChatId = ref("");

  // Текстовые сообщения для vue-advanced-chat (i18n)
  const textMessagesObject = computed(() => ({
    SEARCH: t("textMessages.SEARCH"),
    TYPE_MESSAGE: t("textMessages.TYPE_MESSAGE"),
    ROOM_EMPTY: t("textMessages.ROOM_EMPTY"),
    ROOMS_EMPTY: t("textMessages.ROOMS_EMPTY"),
    MESSAGES_EMPTY: t("textMessages.MESSAGES_EMPTY"),
    MESSAGE_DELETED: t("textMessages.MESSAGE_DELETED"),
    NEW_MESSAGES: t("textMessages.NEW_MESSAGES"),
    IS_ONLINE: t("textMessages.IS_ONLINE"),
    IS_TYPING: t("textMessages.IS_TYPING"),
    LAST_SEEN: t("textMessages.LAST_SEEN"),
    CONVERSATION_STARTED: t("textMessages.CONVERSATION_STARTED"),
    CANCEL_SELECT_MESSAGE: t("textMessages.CANCEL_SELECT_MESSAGE"),
  }));
  const textMessagesJson = computed(() => JSON.stringify(textMessagesObject.value));

  /**
   * Проверка, содержит ли текст какую-либо ссылку (URL).
   */
  function detectUrl(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return urlRegex.test(text);
  }

  /**
   * Получение данных о ссылке (preview).
   */
  async function fetchLinkPreview(url) {
    try {
      const res = await fetch("/api/linkpreview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) throw new Error("Failed to fetch preview data");
      const json = await res.json();
      return json;
    } catch (error) {
      console.error("Preview fetch error:", error);
      return null;
    }
  }

  /**
   * Трансформация массива сообщений, полученных от API.
   */
  async function transformChatMessages(apiMessages) {
    const results = [];
    for (let [index, msg] of apiMessages.entries()) {
      const contentString = typeof msg.message === "string" ? msg.message : "";
      let files = null;

      // Проверяем, есть ли в сообщении URL и получаем превью
      if (detectUrl(contentString)) {
        const previewData = await fetchLinkPreview(contentString);
        if (previewData?.data?.image) {
          files = [
            {
              type: "png",
              name: "Preview",
              url: previewData.data.image,
              preview: previewData.data.image,
            },
          ];
        }
      }

      const dateObj = msg.timestamp ? new Date(msg.timestamp) : new Date();
      const isSent = ["ai", "consultant"].includes(msg.sender_role);

      results.push({
        _id: msg._id ?? index,
        content: contentString,
        senderId: msg.sender_role === "client" ? "1234" : "4321",
        username:
          msg.sender_role === "ai"
            ? "AI Bot"
            : msg.sender_role === "consultant"
            ? "Consultant"
            : "Client",
        date: dateObj.toDateString(),
        timestamp: dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        sent: isSent,
        disableActions: true,
        disableReactions: true,
        files,
      });
    }
    return results;
  }

  /**
   * Функция-пустышка для fetchMessages, если нужна пагинация или другая логика.
   */
  function messagesFetcher({ options = {} }) {
    if (options.reset) {
      // Пример: обновить массив сообщений заново
    } else {
      // Пример: добавить новые сообщения в начало/конец
      messagesLoaded.value = true;
    }
  }

  /**
   * Запуск или перезапуск обратного отсчёта.
   */
  function startCountdown(seconds) {
    if (countdownInterval) {
      clearInterval(countdownInterval);
    }
    countdown.value = seconds;
    timerExpired.value = false;

    countdownInterval = setInterval(() => {
      if (countdown.value > 0) {
        countdown.value--;
      } else {
        if (websocket.value) {
          websocket.value.send(JSON.stringify({ type: "status_check" }));
        }
        clearInterval(countdownInterval);
        countdownInterval = null;
        timerExpired.value = true;
      }
    }, 1000);
  }

  /**
   * Отправка сообщения в WebSocket.
   */
  function sendMessage(message) {
    if (!message || !message.content) return;
    websocket.value?.send(
      JSON.stringify({
        type: "new_message",
        message: message.content,
      })
    );
  }

  const toggleChatMode = (isManualMode) => {
    isManualMode = !isManualMode;
    const command = isManualMode ? "/manual" : "/auto";
  
    console.log("Переключение режима чата. Отправка команды:", command);
  
    // Отправляем команду как сообщение
    sendMessage({ content: command });
  };

  /**
   * Обработка клика по одной из вариативных кнопок (choiceOptions).
   */
  function handleChoiceClick(option) {
    sendMessage({ content: option });
  }

  /**
   * Перезагрузка страницы (кнопка "Начать заново", если таймер истёк).
   */
  function reloadPage() {
    window.location.reload();
  }

  /**
   * Инициализация WebSocket.
   */
  function initializeWebSocket(chatId) {
    const scheme = window.location.hostname === "localhost" ? "ws" : "wss";
    const host = window.location.hostname === "localhost" ? "localhost:8000" : window.location.hostname;
    const wsUrl = `${scheme}://${host}/ws/${chatId}/`;
    websocket.value = new WebSocket(wsUrl);

    websocket.value.onopen = () => {
      websocket.value?.send(JSON.stringify({ type: "status_check" }));
      websocket.value?.send(JSON.stringify({ type: "get_messages" }));
    };

    websocket.value.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      // Показываем toast при определённых типах сообщений
      if (data.type === "attention") {
        toast.add({
          severity: "warn",
          summary: t("additionalMessages.attention"),
          detail: data.message,
          life: 6000,
        });
      } else if (data.type === "error") {
        toast.add({
          severity: "error",
          summary: t("additionalMessages.error"),
          detail: data.message,
          life: 6000,
        });
      }

      switch (data.type) {
        case "status_check":
          if (data.remaining_time) {
            startCountdown(data.remaining_time);
          }
          break;

        case "get_messages": {
          const transformed = await transformChatMessages(data.messages);
          messages.value = transformed;
          messagesLoaded.value = true;
          if (data.remaining_time) {
            startCountdown(data.remaining_time);
          }
          const lastMsg = data.messages?.[data.messages.length - 1];
          if (lastMsg?.choice_options?.length) {
            choiceOptions.value = lastMsg.choice_options;
            isChoiceStrict.value = !!lastMsg.choice_strict;
          } else {
            choiceOptions.value = [];
            isChoiceStrict.value = false;
          }
          break;
        }

        case "new_message": {
          const [transformed] = await transformChatMessages([data]);
          messages.value.push(transformed);
          websocket.value?.send(JSON.stringify({ type: "status_check" }));
          if (data.choice_options?.length) {
            choiceOptions.value = data.choice_options;
            isChoiceStrict.value = !!data.choice_strict;
          } else {
            choiceOptions.value = [];
            isChoiceStrict.value = false;
          }
          break;
        }

        default:
          console.warn("Unknown message type:", data);
      }
    };

    websocket.value.onclose = () => {
      console.log("WebSocket connection closed.");
    };

    websocket.value.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }

  /**
   * Проверка размера экрана (для мобильных).
   */
  function checkScreenSize() {
    isMobile.value = window.innerWidth < 768;
  }

  /**
   * Обновление чата (получить новый chat_id, очистить сообщения).
   */
  async function refreshChat() {
    try {
      const response = await useNuxtApp().$api.post("api/chats/get_chat?mode=new");
      if (response.data) {
        toast.add({
          severity: "success",
          summary: t("additionalMessages.chatRefreshed"),
          detail: t("additionalMessages.chatRefreshedSuccessfully"),
          life: 3000,
        });
        messages.value = [];
        initializeWebSocket(response.data.chat_id);
      }
    } catch (error) {
      toast.add({
        severity: "error",
        summary: t("additionalMessages.error"),
        detail: t("additionalMessages.failedToRefreshChat"),
        life: 3000,
      });
    }
  }

  /**
   * Запрос chatId при первом рендере.
   */
  async function getChatData() {
    try {
      const response = await useNuxtApp().$api.post("api/chats/get_chat");
      return response.data;
    } catch (error) {
      console.error("Error fetching chat data:", error);
      return null;
    }
  }

  /**
   * Событие фокуса окна — если соединение потеряно, переподключаемся.
   */
  function handleFocus() {
    if (websocket.value?.readyState !== 1 && currenChatId.value) {
      websocket.value.close();
      initializeWebSocket(currenChatId.value);
    }
  }

  /**
   * Жизненный цикл onMounted.
   */
  onMounted(async () => {
    checkScreenSize();
    window.addEventListener("resize", checkScreenSize);

    const ua = navigator.userAgent || navigator.vendor || window.opera;
    isIphone.value = /iPhone/i.test(ua);

    // Получаем начальный chat_id
    const chatData = await useAsyncData("chatData", getChatData);
    if (chatData.data && chatData.data.value) {
      const { chat_id } = chatData.data.value;
      currenChatId.value = chat_id;
      initializeWebSocket(chat_id);
    }

    // Пример для Telegram
    if (window.Telegram && isTelegram) {
      let tg = window.Telegram.WebApp;
      tg.expand();
      tg.isVerticalSwipesEnabled = false;
      tg.enableClosingConfirmation();
    }

    window.addEventListener("focus", handleFocus);
  });

  /**
   * Жизненный цикл onBeforeUnmount.
   */
  onBeforeUnmount(() => {
    if (websocket.value) {
      websocket.value.close();
    }
    if (countdownInterval) {
      clearInterval(countdownInterval);
    }
    window.removeEventListener("focus", handleFocus);
    window.removeEventListener("resize", checkScreenSize);
  });

  // Возвращаем наружу все необходимые refs и методы для использования в компонентах
  return {
    // reactive-свойства
    t,
    isMobile,
    isIphone,
    currentUserId,
    activeRoomId,
    rooms,
    messages,
    messagesLoaded,
    choiceOptions,
    isChoiceStrict,
    timerExpired,
    textMessagesJson,

    // методы
    fetchMessages: messagesFetcher,
    sendMessage,
    toggleChatMode,
    handleChoiceClick,
    reloadPage,
    refreshChat,
  };
}
