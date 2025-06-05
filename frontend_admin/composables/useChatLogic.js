// ~/composables/useChatLogic.js
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
// import { useI18n } from "vue-i18n";
// import { useToast } from "primevue/usetoast";
// УБРАЛ import { throttle } from "lodash";
const { isAutoMode, currentChatId, chatMessages, messagesLoaded } = useChatState();

import { debounce } from "lodash";
import { useI18n } from "#imports";

export function useChatLogic(options = {}) {
  const { isTelegram = false, locale = "en", chatRoles } = options; // Переключение под Telegram при необходимости
  console.log("currentChatId.value", currentChatId.value);

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
      typingUsers: [],
    },
  ];

  // Список сообщений и статус загрузки

  // Настройки выбора опций
  const choiceOptions = ref([]);
  const isChoiceStrict = ref(false);

  // Таймеры и флаги
  const timerExpired = ref(false);
  const countdown = ref(0);
  let countdownInterval = null;

  // WebSocket-соединение и chatId
  const websocket = ref(null);

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

  function getExtFromUrl(url) {
    const match = url.match(/\.(\w+?)(?:[?#]|$)/i);
    if (!match) return "image";
    const ext = match[1].toLowerCase();
    if (ext === "jpg") return "jpeg";
    if (ext === "svg") return "svg+xml";
    return ext;
  }

  /**
   * Преобразовать сообщения API в формат для компонента чата (vue-advanced-chat).
   */
  async function transformChatMessages(apiMessages, isInitial = false) {
    if (isInitial) {
      chatMessages.value = [];
    }
    // const currentLocale = locale.value; // e.g., "ru-RU" or "en-US"
    const currentLocale = locale;
    const results = [];
    if (!apiMessages) return results;
    for (let [index, msg] of apiMessages?.entries()) {
      const contentString = typeof msg.message === "string" ? msg.message : "";
      console.log("msg", msg);

      // Attached files (if link preview exists)
      let files = [];
      if (detectUrl(contentString)) {
        const previewData = await fetchLinkPreview(contentString);
        if (previewData?.data?.image) {
          files
            .filter((u) => typeof u === "string" && u.trim().length)
            .push({
              type: "png",
              name: "Preview",
              url: previewData.data.image,
              preview: previewData.data.image,
            });
        }
      }
      // 2. Обрабатываем attachments, пришедшие сразу в msg.files
      if (Array.isArray(msg.files) && msg.files?.length) {
        msg.files.forEach((url, i) => {
          const ext = getExtFromUrl(url); // jpg / png / pdf …
          files.push({
            type: ext.startsWith("image/") ? ext : "image/" + ext,
            name: `Attachment-${i + 1}.${ext.replace(/^image\//, "")}`,
            url,
            preview: url, // изображение сразу отображается
          });
        });
      }

      // Если ничего не нашли, ставим null
      if (files?.length === 0) files = null;

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
      console.log("chatRoles", chatRoles);
      console.log("roleEn", roleEn);
      if (roleEn === "Client") {
        senderId = "1234";
        username = chatRoles.client;
      } else if (roleEn === "AI Assistant") {
        senderId = "4321";
        username = chatRoles.aiAssistant;
      } else if (roleEn === "Consultant") {
        senderId = "4321";
        username = chatRoles.consultant;
      } else {
        senderId = "4321";
        username = chatRoles.unknown;
      }

      // Determine if the message should appear on the right (sent) or left
      const isSent = ["ai", "AI Assistant", "consultant", "Consultant"].includes(roleEn);
      // console.log("senderId", senderId);

      let sources = null;
      if (msg?.snippets_by_source) {
        sources = msg.snippets_by_source;
        console.log("sources", sources);
      }

      const displayContent = `**${username}:** \n ${contentString}`;

      results.push({
        _id: msg._id ?? index,
        backend_id: msg.id,
        content: displayContent,
        senderId,
        username,
        date: formattedDate,
        timestamp: formattedTime,
        sent: isSent, // true for messages from Consultant/AI, false for Client
        disableActions: false,
        disableReactions: true,
        files,
        sources: msg?.snippets_by_source,
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
    chatMessages.value = [...chatMessages.value, newMessage];
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
  function initializeWebSocket() {
    if (!token.value && currentChatId.value) {
      console.error("Токен доступа отсутствует. WebSocket не инициализирован.");
      return;
    }

    // Определяем схему (ws для localhost, wss для prod)
    const wsUrl = `${window.location.hostname === "localhost" ? "ws" : "wss"}://${
      window.location.hostname === "localhost" ? "localhost:8000" : window.location.hostname
    }/ws/${currentChatId.value}/?token=${token.value}&as_admin=true`;

    console.log("Инициализация WebSocket по адресу:", wsUrl);
    websocket.value = new WebSocket(wsUrl);

    websocket.value.onopen = () => {
      console.log("WebSocket открыт.");
      // Запрашиваем начальное состояние (однократно)
      if (websocket.value && websocket.value.readyState === WebSocket.OPEN) {
        console.log("---------------------------------------------------------------------------");
        console.log("Отправляем запрос на получение сообщений и проверку статуса.", currentChatId.value);
        console.log("currentChatId.value", currentChatId.value);
        console.log("currentChatId.value", currentChatId.value);
        console.log("---------------------------------------------------------------------------");
        websocket.value?.send(JSON.stringify({ type: "status_check" }));
        websocket.value?.send(JSON.stringify({ type: "get_messages", with_enter: true }));
      }
    };

    websocket.value.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      if (data.chat_id && data.chat_id !== currentChatId.value) return;
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
            console.log("data.messages:", data.messages);
            const transformed = await transformChatMessages(data.messages, true);
            chatMessages.value = transformed;
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
            console.log("Получено новое сообщение:", data);
            const [transformed] = await transformChatMessages([data]);
            // $event("new_message_arrived", transformed);
            chatMessages.value = [...chatMessages.value, transformed];
            messagesLoaded.value = true;
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
  async function refreshChat() {}

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
      websocket.value.onopen = null;
      websocket.value.onmessage = null;
      websocket.value.onerror = null;
      websocket.value.onclose = null;
      websocket.value.close(1000, "Switching room");
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
    messagesLoaded,
    choiceOptions,
    isChoiceStrict,
    timerExpired,

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
