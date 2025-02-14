<template>
  <div class="flex flex-col bg-[#f8f9fa] dark:bg-gray-800" style="height: var(--tg-viewport-stable-height)">
    <Toast class="max-w-[18rem] md:max-w-full" />
    <!-- {{ websocket.client_state }} -->
      <!-- <Button @click="sendMessageTest"> send</Button>
      <Button @click="getMessageTest"> get</Button>
      <Button @click="saveSeenMessagesToStorage"> savemessages</Button> -->
    <vue-advanced-chat
      :class="[{ 'iphone-margin': isIphone }]"
      height="100%"
      class="flex-1 flex shadow-none overflow-auto w-full"
      :current-user-id="currentUserId"
      :rooms="JSON.stringify(rooms)"
      :rooms-loaded="true"
      :messages="JSON.stringify(messages)"
      :messages-loaded="messagesLoaded"
      show-input-options="false"
      :selected-room-id="activeRoomId"
      :single-room="true"
      :show-audio="false"
      :show-files="false"
      :show-footer="!isChoiceStrict && !timerExpired"
      :text-messages="textMessagesJson"
      @send-message="sendMessage($event.detail[0])"
      @fetch-messages="fetchMessages($event.detail[0])"
    >
      <!-- <div slot="room-header-info">
        <div class="flex items-center justify-between">
          <h2 class="font-bold">PaNa Medica</h2>
          <Button class="w-full p-2 ml-4 flex justify-center items-center gap-2" @click="refreshChat">
            <p>{{t('newChat')}}</p>
            <i class="pi pi-replay"> </i>
          </Button>
        </div>
      </div> -->

      <div slot="room-header-info">
        <div class="flex items-center justify-between w-full">
          <h2 class="font-bold">PaNa Medica</h2>

          <div class="flex items-center gap-4">
            <!-- 🔥 Toggle for chat mode (Auto / Manual) -->
            <div class="flex items-center gap-3 px-4 py-2 bg-white dark:bg-gray-300 rounded-lg shadow ml-4">
              <span class="text-sm font-medium">{{ t("chatMode.manual") }}</span>
              
              <input
                type="checkbox"
                class="toggle-checkbox hidden"
                id="chatModeToggle"
                :checked="!isManualMode"
                @change="toggleChatMode"
              />
              
              <label for="chatModeToggle" class="toggle-label"></label>
              
              <span class="text-sm font-medium">{{ t("chatMode.auto") }}</span>
            </div>


            <!-- 🔄 Refresh chat button -->
            <Button class="w-full p-2 flex justify-center items-center gap-2" @click="refreshChat">
              <p>{{ t('newChat') }}</p>
              <i class="pi pi-replay"></i>
            </Button>
          </div>
        </div>
      </div>




    </vue-advanced-chat>
    <!-- {{ choiceOptions }}
    {{ isChoiceStrict }} -->
    <!-- Choice buttons (only if we have choice options) -->
    <div
      class="py-4 flex flex-row w-full justify-around items-center flex-wrap gap-4 max-h-[20vh] overflow-y-auto"
      v-if="choiceOptions.length && !timerExpired"
    >
      <Button
        v-for="option in choiceOptions"
        :key="option"
        :label="option"
        class="p-button-outlined min-w-[160px]"
        @click="handleChoiceClick(option)"
      />
    </div>
    <!-- Reload button (only if timer has expired) -->
    <div class="py-4 flex justify-center" v-if="timerExpired">
      <Button :label="t('chatAgain')" class="p-button-outlined p-button-danger" @click="reloadPage" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, onUnmounted } from "vue";
import { register } from "vue-advanced-chat";
register();
//  :show-footer="false" for hiding textarea

import { useToast } from "primevue/usetoast"; // Assuming you’re using primevue
import { useI18n } from "vue-i18n";
const { t } = useI18n();
// 3) Provide localized texts to vue-advanced-chat via a computed
function saveSeenMessagesToStorage(){
  const messageIds = messages.value.map((msg) => msg._id);
  localStorage.setItem("seenMessages", JSON.stringify(messageIds));
};
// New: Function to refresh chat
const refreshChat = async () => {
  try {
    const response = await useNuxtApp().$api.post("api/chats/get_chat?mode=new");
    if (response.data) {
      toast.add({
        severity: "success",
         summary: t("additionalMessages.chatRefreshed"),
        detail: t("additionalMessages.chatRefreshedSuccessfully"),
        life: 3000,
      });
      saveSeenMessagesToStorage()
      // Update messages or other state as needed
      messages.value = [];
      initializeWebSocket(response.data.chat_id); // Reinitialize the WebSocket
    }
  } catch (error) {
    console.error("Error refreshing chat:", error);
    toast.add({
      severity: "error",
      summary: t("additionalMessages.error"),
      detail: t("additionalMessages.failedToRefreshChat"),
      life: 3000,
    });
  }
};

const toast = useToast();
const isManualMode = ref(false);

// function sendMessageTest(message) {
//   console.log("Отправка сообщения локально TEST" );
//   websocket.value.send(
//       JSON.stringify({
//         type: "new_message",
//         // type: "test",
//         message: 'Сергей',
//       })
//     );
// }
// function getMessageTest(message) {
//   console.log("Получение сообщений локально TEST" );
//   websocket.value?.send(JSON.stringify({ type: "get_messages" }));
// }

// Existing reactive references
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

const messages = ref([]);
const messagesLoaded = ref(false);
const websocket = ref(null);
const currenChatId = ref("");

// NEW: Add these two:
const choiceOptions = ref([]); // Will hold the array of choices from the server
const isChoiceStrict = ref(false); // If true, disable text input

// NEW: Add a flag to track if the timer has expired
const timerExpired = ref(false);
// 1) Simple RegEx to check if content has a URL:
function detectUrl(text) {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  return urlRegex.test(text);
}

async function fetchLinkPreview(url) {
  try {
    console.log("Fetching preview for:", url);
    const res = await fetch("/api/linkpreview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!res.ok) throw new Error("Failed to fetch preview data");
    const json = await res.json(); // { success, data: {...} }
    console.log("Preview data:", json);
    return json;
  } catch (error) {
    console.error("Preview fetch error:", error);
    return null;
  }
}

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
// 2) Now convert that object to a JSON string
const textMessagesJson = computed(() => JSON.stringify(textMessagesObject.value));


// // 1) Check if message contains a URL
// if (detectUrl(contentString)) {
//   try {
//     // 2) Fetch preview data
//     const previewData = await fetchLinkPreview(contentString);
//     // If we got an image from the preview, store it
//     if (previewData?.data?.image) {
//       previewImage = previewData.data.image;
//     }
//   } catch (err) {
//     console.error("Preview fetch error:", err);
//   }
// }

async function urlToFile(url, filename, mimeType) {
  const response = await fetch(url);
  const blob = await response.blob();
  return new File([blob], filename, { type: mimeType });
}






async function transformChatMessages(apiMessages) {
  const storedSeenMessages = new Set(JSON.parse(localStorage.getItem("seenMessages") || "[]"));
  const results = [];

  for (let [index, msg] of apiMessages.entries()) {
    // Make sure the message content is a string
    const contentString = typeof msg.message === "string" ? msg.message : "";
    let files = null;

    // If the text includes a URL, try to get a preview image
    if (detectUrl(contentString)) {
      console.log("Detected URL:", contentString);
      const previewData = await fetchLinkPreview(contentString);

      // Check if the preview data contains an image
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
    const isSeen = storedSeenMessages.has(msg._id ?? index);
    // console.log("isSeen", isSeen);
    // console.log(msg._id ?? index);
    const dateObj = msg.timestamp ? new Date(msg.timestamp) : new Date();
    const isSent = ["ai", "consultant"].includes(msg.sender_role);

    results.push({
      _id: msg._id ?? index,
      content: contentString,
      senderId: msg.sender_role === "client" ? "1234" : "4321",
      username: msg.sender_role === "ai" ? "AI Bot" : msg.sender_role === "consultant" ? "Consultant" : "Client",
      date: dateObj.toDateString(),
      timestamp: dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      sent: isSent,
      // Attach the image if available
      disableActions: true,
      disableReactions: true,
      seen: isSeen,
      files,
    });
  }
  console.log("results", results);
  return results;
}

// Example fetch messages
const fetchMessages = ({ options = {} }) => {
  setTimeout(() => {
    if (options.reset) {
      // messages.value = addMessages(true);
    } else {
      messages.value = [...addMessages(), ...messages.value];
      messagesLoaded.value = true;
    }
  });
};

// const addMessages = (reset = false) => {
//   const newMessages = [];
//   for (let i = 0; i < 30; i++) {
//     newMessages.push({
//       _id: reset ? i : messages.value.length + i,
//       content: `${reset ? "" : "paginated"} message ${i + 1}`,
//       senderId: "4321",
//       username: "John Doe",
//       date: "13 November",
//       timestamp: "10:20",
//     });
//   }
//   return newMessages;
// };

const countdown = ref(0); // Holds the current countdown (in seconds)
let countdownInterval = null; // Will hold the setInterval reference

// Helper to format time (MM:SS)
function formatTime(seconds) {
  const mm = Math.floor(seconds / 60);
  const ss = seconds % 60;
  return `${mm}:${ss < 10 ? "0" : ""}${ss}`;
}

// Start or restart the timer
function startCountdown(seconds) {
  // Clear any previous interval
  if (countdownInterval) {
    clearInterval(countdownInterval);
  }

  countdown.value = seconds;
  timerExpired.value = false; // Reset the timerExpired flag when starting

  countdownInterval = setInterval(() => {
    if (countdown.value > 0) {
      countdown.value--;
    } else {
      // Timer reached zero => send status_check or handle as needed
      if (websocket.value) {
        websocket.value.send(JSON.stringify({ type: "status_check" }));
      }
      clearInterval(countdownInterval);
      countdownInterval = null;
      timerExpired.value = true; // Set the flag when timer expires
    }
  }, 1000);
}

const toggleChatMode = () => {
  isManualMode.value = !isManualMode.value;
  const command = isManualMode.value ? "/manual" : "/auto";

  console.log("Переключение режима чата. Отправка команды:", command);

  // Отправляем команду как сообщение
  sendMessage({ content: command });
};


// Chat input or button press => send
const sendMessage = (message) => {
  console.log("Отправка сообщения локально:", message);
  if (websocket.value) {
    websocket.value.send(
      JSON.stringify({
        type: "new_message",
        message: message.content,
      })
    );
  } else {
    initializeWebSocket(currenChatId.value,message.content);
  }
};

// NEW: method when the user clicks a choice button
const handleChoiceClick = (option) => {
  // Send the chosen option as a message
  sendMessage({ content: option });
};

// NEW: Method to reload the page
const reloadPage = () => {
  window.location.reload();
};

// WebSocket
const initializeWebSocket = (chatId, message) => {
  const wsUrl = `${window.location.hostname === "localhost" ? "ws" : "wss"}://${
    window.location.hostname === "localhost" ? "localhost:8000" : window.location.hostname
  }/ws/${chatId}/`;
  websocket.value = new WebSocket(wsUrl);

  websocket.value.onopen = () => {
    console.log("WebSocket connection established.");
    websocket.value?.send(JSON.stringify({ type: "status_check" }));
    websocket.value?.send(JSON.stringify({ type: "get_messages" }));
  };

  websocket.value.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    console.log("Received data:", data);

    // Show toasts if attention/error
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
      case "status_check": {
        console.log("Status Check Response:", data);
        if (data.remaining_time) {
          startCountdown(data.remaining_time);
        }
        isManualMode.value = data.manual_mode; 
        break;
      }
      case "get_messages": {
        console.log("Messages Retrieved:", data.messages);
        // 1) Transform the message array
        const transformed = await transformChatMessages(data.messages);

        // 2) Set reactive messages
        messages.value = transformed;
        messagesLoaded.value = true;

        if (data.remaining_time) {
          startCountdown(data.remaining_time);
        }
        // 3) Check the LAST message in the original data array
        const lastMsg = data.messages?.[data.messages.length - 1];
        if (lastMsg?.choice_options && Array.isArray(lastMsg.choice_options) && lastMsg.choice_options.length > 0) {
          choiceOptions.value = lastMsg.choice_options;
          isChoiceStrict.value = !!lastMsg.choice_strict;
          console.log("Choice Options (from last message):", choiceOptions.value);
        } else {
          // If no choices, reset
          choiceOptions.value = [];
          isChoiceStrict.value = false;
        }
        break;
      }

      case "new_message": {
        console.log("New Message:", data);
        // Transform new single message
        const [transformed] = await transformChatMessages([data]);
        messages.value.push(transformed);
        // 1) **Send status_check** on each new message
        websocket.value?.send(JSON.stringify({ type: "status_check" }));

        // Check if server provided choice options
        if (data.choice_options?.length > 0) {
          choiceOptions.value = data.choice_options;
          isChoiceStrict.value = !!data.choice_strict;
          console.log("Choice Options:", choiceOptions.value);
        } else {
          // If there's no choice options, reset them
          choiceOptions.value = [];
          isChoiceStrict.value = false;
        }
        break;
      }
      default:
        console.warn("Unknown message type:", data);
    }

    if( message){
      sendMessage(message);
    }
  };

  websocket.value.onclose = () => {
    console.log("WebSocket connection closed.");
  };

  websocket.value.onerror = (error) => {
    console.error("WebSocket error:", error);
  };
};
const isIphone = ref(false);
// Обработчик для изменения видимости страницы
const handleVisibilityChange = () => {
  // console.log("Visibility state changed:", document.visibilityState);
  // if (document.visibilityState === "hidden") {
  //   console.log("Окно потеряло фокус, сохраняем прочитанные сообщения...");
  //   saveSeenMessagesToStorage();
  // }
  // messagesLoaded.value = false;
  // if (document.visibilityState === "visible") {
  //   console.log("Page is visible. Checking WebSocket connection...");

  //   if (websocket.value) {
  //     console.log("WebSocket is not open. Reconnecting...");
  //     initializeWebSocket(currenChatId.value);
  //   } else {
  //     websocket.value.close();
  //     initializeWebSocket(currenChatId.value);
  //   }
  // } else {
  //   console.log("Page is hidden. Pausing updates.");
  // }
  // messagesLoaded.value = true;
};
const handleFocus = () => {
  console.log("Окно в фокусе");
  handleVisibilityChange();
};
const handleFocusOut = () => {
  console.log("Окно потеряло фокус");
  saveSeenMessagesToStorage();
};

onMounted(async () => {
  const ua = navigator.userAgent || navigator.vendor || window.opera;
  isIphone.value = /iPhone/i.test(ua);
  const chatData = await useAsyncData("chatData", getChatData);
  if (chatData.data && chatData.data.value) {
    const { chat_id } = chatData.data.value;
    initializeWebSocket(chat_id);
    currenChatId.value = chat_id;
  }
  let tg = window.Telegram.WebApp;
  tg.expand();
  tg.isVerticalSwipesEnabled = false;
  tg.enableClosingConfirmation();
  // Добавляем слушатель события visibilitychange
  // document.addEventListener("visibilitychange", handleVisibilityChange);
  window.addEventListener("focus", handleFocus);
  window.addEventListener("focusout", handleFocusOut);
});

onBeforeUnmount(() => {
  saveSeenMessagesToStorage();
  if (websocket.value) {
    websocket.value.close();
  }
  if (countdownInterval) {
    clearInterval(countdownInterval);
  }
  
  window.removeEventListener("focus", handleFocus);
  window.removeEventListener("focusout", handleFocusOut);
  // document.removeEventListener("visibilitychange",handleVisibilityChange);
});

// Example: fetch chat data from your API
async function getChatData() {
  try {
    const response = await useNuxtApp().$api.post("api/chats/get_chat");
    return response.data;
  } catch (error) {
    console.error("Error fetching chat data:", error);
    return null;
  }
}
</script>

<style>
body {
  font-family: "Quicksand", sans-serif;
  overflow: hidden;
  background-color: #f8f9fa;
}

/* Hide the rooms container if you only want a single chat */
.vac-rooms-container {
  display: none !important;
}

/* Ensure the chat container fills its parent and handles overflow */
.vue-advanced-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.vue-advanced-chat .vac-message-list {
  flex: 1;
  overflow-y: auto;
}

/* Conditional margin for iPhone users */
.iphone-margin {
  margin-bottom: 20px; /* Adjust the value as needed */

  /* Optional: Use safe area insets for better compatibility */
  padding-bottom: env(safe-area-inset-bottom);
}

.vue-advanced-chat {
  box-shadow: none !important;
}

/* Alternatively, use a Tailwind CSS utility */
.shadow-none {
  box-shadow: none !important;
}

/* If the shadow is on a child element, target it specifically */
.vue-advanced-chat .specific-child-class {
  box-shadow: none !important;
}
.vac-message {
  background-color: #e0f7fa; /* Change this to your desired color */
  color: #006064; /* Change this to your desired text color */
}

.vac-message.vac-message-sent {
  background-color: #b2ebf2; /* Change this to your desired color for sent messages */
  color: #004d40; /* Change this to your desired text color for sent messages */
}





.toggle-checkbox {
  display: none;
}

/* 🔥 Улучшенный тоггл-переключатель */
.toggle-label {
  display: inline-block;
  width: 60px; /* Увеличенная ширина */
  height: 28px; /* Выше для лучшего вида */
  background-color: #e6e6e6; /* Светлый фон для контраста */
  border-radius: 50px;
  position: relative;
  cursor: pointer;
  transition: background 0.3s, box-shadow 0.3s;
  border: 1px solid #bbb;
}

.toggle-label::before {
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;
  width: 22px; /* Чуть больше кружок */
  height: 22px;
  background-color: white;
  border-radius: 50%;
  transition: transform 0.3s, box-shadow 0.3s;
}

/* Когда включён авто-режим */
.toggle-checkbox:checked + .toggle-label {
  background-color: #4caf50; /* Зелёный при авто-режиме */
  border-color: #3e8e41;
}

/* Двигаем кружок в авто-режиме */
.toggle-checkbox:checked + .toggle-label::before {
  transform: translateX(30px);
}

/* Эффект тени при наведении */
.toggle-label:hover {
  box-shadow: 0px 0px 8px rgba(0, 0, 0, 0.15);
}


</style>
<style scoped></style>
