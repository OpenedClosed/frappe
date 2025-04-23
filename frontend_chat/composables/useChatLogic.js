// ~/composables/useChatLogic.js
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import { useToast } from "primevue/usetoast";
// УБРАЛ import { throttle } from "lodash";

export function useChatLogic(options = {}) {
  const { isTelegram = false } = options; // Переключение под Telegram при необходимости
  const { t, locale } = useI18n();
  const toast = useToast();
  const { isAutoMode } = useChatState();

  // Состояние экрана, устройства и т.п.
  const isMobile = ref(false);
  const isIphone = ref(false);
// ← здесь
let skipNextStatusCheck = false;
  const { rooms } = useHeaderState();
  // Текущий пользователь и комнаты
  const currentUserId = ref("1234");
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
    const currentLocale = locale.value; // например, "ru-RU" или "en-US"
    const results = [];

    for (let [index, msg] of apiMessages.entries()) {
      const contentString = typeof msg.message === "string" ? msg.message : "";

      // Прикреплённые файлы (если есть превью по ссылке)
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

      // Парсим дату из UTC-строки
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

      // Парсим роль (sender_role может быть JSON)
      let role = msg.sender_role;
      try {
        role = JSON.parse(role);
      } catch (e) {
        // Если не JSON, оставим строку, как есть
      }

      let roleEn;
      if (typeof role === "object" && role?.en) {
        roleEn = role.en;
      } else if (typeof role === "string") {
        roleEn = role;
      } else {
        roleEn = "unknown";
      }

      // Определяем senderId и username
      let senderId;
      let username;
      if (roleEn === "Client") {
        senderId = "1234";
        username = "Client";
      } else if (roleEn === "ai" || roleEn === "AI Assistant") {
        senderId = "4321";
        username = "AI Bot";
      } else if (roleEn === "consultant" || roleEn === "Consultant") {
        senderId = "4321";
        username = "Consultant";
      } else {
        senderId = "4321";
        username = "Unknown";
      }

      // Определяем, отображать сообщение справа (sent) или слева
      const isSent = ["ai", "AI Assistant", "consultant", "Consultant"].includes(roleEn);

      results.push({
        _id: msg._id ?? index,
        content: contentString,
        senderId,
        username,
        date: formattedDate,
        timestamp: formattedTime,
        sent: isSent,
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
    console.log("Отправляем сообщение:", message);
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
    // console.log("toggleChatMode:", isAuto);
    skipNextStatusCheck = true;        
    const command = isAuto ? "/auto" : "/manual";
    // console.log("Отправляем команду:", command);
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
  const { $event, $listen } = useNuxtApp();

  const MIN_INTERVAL = 0; // ≥ 5 с между отправками
  const AFTER_MESSAGE = 0; // ≥ 2 с после события «пришло сообщение»

  // ---- NEW: управление status_check ----
  let lastStatusSent = 0; // timeStamp последней отправки
  let pendingStatusTimer = null; // id тайм‑аута, если уже запланирован

  function scheduleStatusCheck() {
    const now = Date.now();

    // если тайм‑аут уже стоит, ничего не делаем – он отправит в нужное время
    if (pendingStatusTimer) return;

    // когда мы _теоретически_ можем отправить следующий статус
    const earliest = lastStatusSent + MIN_INTERVAL;
    const plannedAt = Math.max(now + AFTER_MESSAGE, earliest);
    const delay = plannedAt - now;

    pendingStatusTimer = setTimeout(() => {
      websocket.value?.send(JSON.stringify({ type: "status_check" }));
      lastStatusSent = Date.now();
      pendingStatusTimer = null; // освободили слоты для следующего сообщения
    }, delay);
  }
  // УБРАНА throttle и прочие повторные вызовы, оставляем простую функцию
  function initializeWebSocket(chatId) {
    // Определяем схему (ws для localhost, wss для prod)
    const scheme = window.location.hostname === "localhost" ? "ws" : "wss";
    const host = window.location.hostname === "localhost" ? "localhost:8000" : window.location.hostname;
    const wsUrl = `${scheme}://${host}/ws/${chatId}/`;

    console.log("Инициализация WebSocket по адресу:", wsUrl);
    websocket.value = new WebSocket(wsUrl);

    websocket.value.onopen = () => {
      console.log("WebSocket открыт.");
      // Запрашиваем начальное состояние (однократно)
      if (websocket.value && websocket.value.readyState === WebSocket.OPEN) {
        websocket.value?.send(JSON.stringify({ type: "status_check" }));
        websocket.value?.send(JSON.stringify({ type: "get_messages" }));
      }
    };

    websocket.value.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      // Показываем toast при определённых типах
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

      // Основная обработка типов сообщений
      switch (data.type) {
        case "status_check":
          if (data.remaining_time) {
            startCountdown(data.remaining_time);
          }
          // console.log("status_check", data);
          // Синхронизируем режим
          // console.log("isAutoMode", !data.manual_mode);
          isAutoMode.value = !data.manual_mode;
          break;

        case "get_messages":
          {
            const transformed = await transformChatMessages(data.messages);
            messages.value = transformed;
            messagesLoaded.value = true;
            if (!skipNextStatusCheck) {
              scheduleStatusCheck();
            } else {
              skipNextStatusCheck = false;         // сбросили однократный запрет
            }

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
            // Синхронизируем режим
            isAutoMode.value = !data.manual_mode;
          }
          break;

        case "new_message":
          {
            const [transformed] = await transformChatMessages([data]);
            $event("new_message_arrived", transformed);
            if (!skipNextStatusCheck) {
              scheduleStatusCheck();
            } else {
              skipNextStatusCheck = false;         // сбросили однократный запрет
            }

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
            // Синхронизируем режим
            isAutoMode.value = !data.manual_mode;
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
   * Обновление чата (просим новый chat_id, очищаем сообщения).
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
        currenChatId.value = response.data.chat_id;
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
  // ───  Настройки «debounce» для переподключения  ────────────────────────────────
  const RECONNECT_DEBOUNCE = 5000; // 5 секунд
  let lastReconnectAttempt = 0; // timestamp последней попытки

  /**
   * Если WebSocket закрыт / не открыт — переподключаемся.
   * Если открыт — просто шлём status_check.
   * Повторяем не чаще, чем раз в 5 секунд.
   */
  function attemptReconnect() {
    const now = Date.now();
    if (now - lastReconnectAttempt < RECONNECT_DEBOUNCE) return; // debounce

    lastReconnectAttempt = now;

    if (!websocket.value || [WebSocket.CLOSED, WebSocket.CLOSING].includes(websocket.value.readyState)) {
      console.log("[focus] сокет закрыт → переподключаемся");
      initializeWebSocket(currenChatId.value);
    } else {
      console.log("[focus] сокет открыт → status_check");
      websocket.value?.send(JSON.stringify({ type: "status_check" }));
    }
  }

  // ───  Заменяем пустую handleFocus  ─────────────────────────────────────────────
  function handleFocus() {
    attemptReconnect();
  }

  // ---------------- Жизненный цикл ----------------

  onMounted(async () => {
    checkScreenSize();
    window.addEventListener("resize", checkScreenSize);

    const ua = navigator.userAgent || navigator.vendor || window.opera;
    isIphone.value = /iPhone/i.test(ua);

    // Получаем начальный chat_id с бэкенда
    const chatData = await useAsyncData("chatData", getChatData);
    if (chatData.data && chatData.data.value) {
      const { chat_id } = chatData.data.value;
      currenChatId.value = chat_id;
      initializeWebSocket(chat_id);
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

  // ---------------- Возвращаемые переменные и методы ----------------

  return {
    // Состояния
    t,
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
  };
}
