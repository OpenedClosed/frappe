// ~/composables/useChatLogic.js
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
// import { useI18n } from "vue-i18n";
// import { useToast } from "primevue/usetoast";
// УБРАЛ import { throttle } from "lodash";
const { isAutoMode, currentChatId } = useChatState();

import { debounce } from "lodash";

export function useChatLogic(options = {}) {
  const { isTelegram = false } = options; // Переключение под Telegram при необходимости
  console.log("currentChatId.value", currentChatId.value);
  // const { t, locale } = useI18n();
  // const toast = useToast();

  // Состояние экрана, устройства и т.п.
  const isMobile = ref(false);
  const isIphone = ref(false);

  const { rooms } = useHeaderState();
  // Текущий пользователь и комнаты
  const currentUserId = ref("4321");
  const activeRoomId = ref("1");
  rooms.value = [
    {
      roomId: "1",
      users: [
        { _id: "1234", username: "User" },
        { _id: "4321", username: "Consultant" },
      ],
      roomActions: [
        { name: "inviteUser", title: "Invite User" },
        { name: "removeUser", title: "Remove User" },
        { name: "deleteRoom", title: "Delete Room" },
      ],
      typingUsers: [],
    },
  ];

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

  // WebSocket-соединение и chatId
  const websocket = ref(null);
  const currenChatId = ref("");

  // Текстовые сообщения для vue-advanced-chat (i18n)
  const textMessagesObject = computed(() => ({
    SEARCH: "Search",
    TYPE_MESSAGE: "Type a message",
    ROOM_EMPTY: "This room is empty",
    ROOMS_EMPTY: "No rooms available",
    MESSAGES_EMPTY: "No messages yet",
    MESSAGE_DELETED: "Message deleted",
    NEW_MESSAGES: "New messages",
    IS_ONLINE: "is online",
    IS_TYPING: "is typing...",
    LAST_SEEN: "Last seen",
    CONVERSATION_STARTED: "Conversation started",
    CANCEL_SELECT_MESSAGE: "Cancel message selection",
  }));
  const textMessagesJson = computed(() => JSON.stringify(textMessagesObject.value));

  /**
   * Проверка, содержит ли текст ссылку (URL).
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
   * Преобразовать сообщения API в формат для компонента чата (vue-advanced-chat).
   */
  async function transformChatMessages(apiMessages) {
    // const currentLocale = locale.value; // e.g., "ru-RU" or "en-US"
    const currentLocale = "en";
    const results = [];
    if (!apiMessages) return results;
    for (let [index, msg] of apiMessages?.entries()) {
      const contentString = typeof msg.message === "string" ? msg.message : "";

      // Attached files (if link preview exists)
      let files = null;
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

      // Parse date from UTC string
      const utcString = msg.timestamp ? msg.timestamp.replace(/\.\d+$/, "") + "Z" : null;
      const dateObj = utcString ? new Date(utcString) : new Date();

      const formattedDate = dateObj.toLocaleDateString(currentLocale, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      const formattedTime = dateObj.toLocaleTimeString(currentLocale, {
        hour: "2-digit",
        minute: "2-digit",
      });

      // Parse role (sender_role can be JSON)
      let role = msg.sender_role;
      try {
        role = JSON.parse(role);
      } catch (e) {
        // If not JSON, leave it as a string
      }

      let roleEn;
      if (typeof role === "object" && role?.en) {
        roleEn = role.en;
      } else if (typeof role === "string") {
        roleEn = role;
      } else {
        roleEn = "unknown";
      }
      // console.log("roleEn", roleEn);

      // Determine senderId and username
      let senderId;
      let username;
      if (roleEn === "Client") {
        senderId = "1234";
        username = "Client";
      } else if (roleEn === "ai" || roleEn === "AI Assistant") {
        senderId = "4321";
        username = "AI Assistant";
      } else if (roleEn === "consultant" || roleEn === "Consultant") {
        senderId = "4321";
        username = "Consultant";
      } else {
        senderId = "4321";
        username = "Unknown";
      }

      // Determine if the message should appear on the right (sent) or left
      const isSent = ["ai", "AI Assistant", "consultant", "Consultant"].includes(roleEn);
      // console.log("senderId", senderId);

      results.push({
        _id: msg._id ?? index,
        content: contentString,
        senderId,
        username,
        date: formattedDate,
        timestamp: formattedTime,
        sent: isSent, // true for messages from Consultant/AI, false for Client
        disableActions: true,
        disableReactions: true,
        files,
      });
    }

    return results;
  }

  /**
   * Пустышка для загрузки сообщений (пагинация и т.д. по необходимости).
   */
  function messagesFetcher({ options = {} }) {
    if (options.reset) {
      // Здесь можно обнулить messages
    } else {
      // Или догрузить новые
      messagesLoaded.value = true;
    }
  }

  /**
   * Запуск или перезапуск обратного отсчёта.
   * (УБРАНА автоматическая отправка повторных status_check при обнулении таймера)
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
        clearInterval(countdownInterval);
        countdownInterval = null;
        timerExpired.value = true;
      }
    }, 1000);
  }

  /**
   * Отправить новое сообщение через WebSocket.
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

  /**
   * Переключение режима (авто/вручную).
   */
  function toggleChatMode(isAuto) {
    console.log("toggleChatMode:", isAuto);
    const command = isAuto ? "/auto" : "/manual";
    console.log("Отправляем команду:", command);
    sendMessage({ content: command });
  }

  /**
   * Клик по одной из опций (вариативные кнопки).
   */
  function handleChoiceClick(option) {
    sendMessage({ content: option });
  }

  /**
   * Добавление нового сообщения в локальный массив (прихват по событию).
   */
  function updateMessages(newMessage) {
    messages.value = [...messages.value, newMessage];
  }

  /**
   * Перезагрузка страницы (например, если таймер истёк, кнопка «Начать заново»).
   */
  function reloadPage() {
    window.location.reload();
  }

  const token = useCookie("access_token");
  const { $event, $listen } = useNuxtApp();
  // УБРАНА throttle и прочие повторные вызовы, оставляем простую функцию
  function initializeWebSocket(chatId) {
    if (!token.value) {
      return;
    }
    // Определяем схему (ws для localhost, wss для prod)
    const wsUrl = `${window.location.hostname === "localhost" ? "ws" : "wss"}://${
      window.location.hostname === "localhost" ? "localhost:8000" : window.location.hostname
    }/ws/${chatId}/?token=${token.value}`;

    console.log("Инициализация WebSocket по адресу:", wsUrl);
    websocket.value = new WebSocket(wsUrl);

    websocket.value.onopen = () => {
      console.log("WebSocket открыт.");
      // Запрашиваем начальное состояние (однократно)
      if (websocket.value && websocket.value.readyState === WebSocket.OPEN) {
        websocket.value?.send(JSON.stringify({ type: "status_check" }));
        websocket.value?.send(JSON.stringify({ type: "get_messages", with_enter: true })); 
      }
    };

    websocket.value.onmessage = async (event) => {
      const data = JSON.parse(event.data);
      console.log("Получено сообщение:", data);
      // Показываем toast при определённых типах
      if (data.type === "attention") {
        // toast.add({
        //   severity: "warn",
        //   // summary: t("additionalMessages.attention"),
        //   summary: "attention",
        //   detail: data.message,
        //   life: 6000,
        // });
      } else if (data.type === "error") {
        // toast.add({
        //   severity: "error",
        //   // summary: t("additionalMessages.error"),
        //   summary: "error",
        //   detail: data.message,
        //   life: 6000,
        // });
      }

      // Основная обработка типов сообщений
      switch (data.type) {
        case "status_check":
          if (data.remaining_time) {
            startCountdown(data.remaining_time);
          }
          // Синхронизируем режим
          isAutoMode.value = !data.manual_mode;
          break;

        case "get_messages":
          {
            const transformed = await transformChatMessages(data.messages);
            messages.value = transformed;
            messagesLoaded.value = true;
            if (data.remaining_time) {
              startCountdown(data.remaining_time);
            }
            // Вытащим choiceOptions из последнего сообщения, если есть
            const lastMsg = data.messages?.[data.messages.length - 1];
            if (lastMsg?.choice_options?.length) {
              choiceOptions.value = lastMsg.choice_options;
              isChoiceStrict.value = !!lastMsg.choice_strict;
            } else {
              choiceOptions.value = [];
              isChoiceStrict.value = false;
            }
          }
          break;

        case "new_message":
          {
            const [transformed] = await transformChatMessages([data]);
            $event("new_message_arrived", transformed);

            // УБРАНО повторное status_check после каждого сообщения

            // Обновляем choiceOptions, если пришли
            if (data.choice_options?.length) {
              choiceOptions.value = data.choice_options;
              isChoiceStrict.value = !!data.choice_strict;
            } else {
              choiceOptions.value = [];
              isChoiceStrict.value = false;
            }
            $event("choice_options_arrived", choiceOptions.value);
          }
          break;

        case "typing_users":
          {
            // Пример: показываем "консультант печатает"
            if (data?.users.includes("ai_bot")) {
              rooms.value[0].typingUsers = [{ id: "4321", username: "Consultant" }];
            } else {
              rooms.value[0].typingUsers = [];
            }
          }
          break;

        default:
          console.warn("Неизвестный тип сообщения:", data);
      }
    };

    // УБРАНА логика повторных переподключений
    websocket.value.onclose = () => {
      console.log("WebSocket соединение закрыто.");
      websocket.value = null;
    };

    websocket.value.onerror = (error) => {
      console.error("WebSocket ошибка:", error);
    };
  }

  /**
   * Проверка мобильного экрана.
   */
  function checkScreenSize() {
    isMobile.value = window.innerWidth < 768;
  }

  /**
   * Обновление чата (просим новый currentChatId.value, очищаем сообщения).
   */
  async function refreshChat() {
    // try {
    //   if (response.data) {
    //     // toast.add({
    //     //   severity: "success",
    //     //   summary: t("additionalMessages.chatRefreshed"),
    //     //   detail: t("additionalMessages.chatRefreshedSuccessfully"),
    //     //   life: 3000,
    //     // });
    //     messages.value = [];
    //     currenChatId.value = currentChatId.value;
    //     // initializeWebSocket(currentChatId.value);
    //   }
    // } catch (error) {
    //   // toast.add({
    //   //   severity: "error",
    //   //   summary: t("additionalMessages.error"),
    //   //   detail: t("additionalMessages.failedToRefreshChat"),
    //   //   life: 3000,
    //   // });
    // }
  }

  /**
   * Первичная загрузка chatId с бэкенда.
   */
  async function getChatData() {
    try {
      const response = await useNuxtApp().$api.post("api/chats/get_chat");
      return response.data;
    } catch (error) {
      console.error("Ошибка при получении chat_data:", error);
      return null;
    }
  }

  /**
   * Если вкладка вернулась в фокус, при необходимости можно проверить состояние.
   * (УБРАНО повторное переподключение тут же)
   */
  function handleFocus() {
    // Можно оставить пустым, чтобы не было автопереподключений или повторных запросов
  }


  // ---------------- Жизненный цикл ----------------

  onMounted(async () => {
    checkScreenSize();
    window.addEventListener("resize", checkScreenSize);

    const ua = navigator.userAgent || navigator.vendor || window.opera;
    isIphone.value = /iPhone/i.test(ua);

    // Получаем начальный currentChatId.value с бэкенда
    const chatData = await useAsyncData("chatData", getChatData);
    if (chatData.data && chatData.data.value) {
      currenChatId.value = currentChatId.value;
      initializeWebSocket(currentChatId.value);
    }

    // Настройки для Telegram (если нужно)
    if (window.Telegram && isTelegram) {
      let tg = window.Telegram.WebApp;
      tg.expand();
      tg.isVerticalSwipesEnabled = false;
      tg.enableClosingConfirmation();
    }

    // Следим за фокусом окна (без автоповторов)
    window.addEventListener("focus", handleFocus);
  });

  onBeforeUnmount(() => {
    // Закрываем сокет, очищаем обработчики
    if (websocket.value) {
      websocket.value.onclose = null;
      websocket.value.close();
      websocket.value = null;
    }

    // Останавливаем countdown
    if (countdownInterval) {
      clearInterval(countdownInterval);
    }

    window.removeEventListener("focus", handleFocus);
    window.removeEventListener("resize", checkScreenSize);
  });

  // ⟵⟵⟵  добавляем функцию‑чистильщик
  function destroy() {
    if (websocket.value) {
      websocket.value.onclose = null;
      websocket.value.close();
      websocket.value = null;
    }
    if (countdownInterval) clearInterval(countdownInterval);
    window.removeEventListener("focus", handleFocus);
    window.removeEventListener("resize", checkScreenSize);
  }

  // ---------------- Возвращаемые переменные и методы ----------------

  return {
    // Состояния

    isMobile,
    isIphone,
    currentUserId,
    activeRoomId,
    messages,
    messagesLoaded,
    choiceOptions,
    isChoiceStrict,
    timerExpired,
    textMessagesJson,

    // Методы
    fetchMessages: messagesFetcher,
    sendMessage,
    toggleChatMode,
    handleChoiceClick,
    reloadPage,
    refreshChat,
    updateMessages,
    transformChatMessages,
    destroy,
    initializeWebSocket,
  };
}
