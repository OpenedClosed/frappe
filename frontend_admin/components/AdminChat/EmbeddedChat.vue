<template>
  <div class="flex flex-col">
    <Toast class="max-w-[18rem] md:max-w-full" />
    <vue-advanced-chat
      :class="[{ 'iphone-margin': isIphone }]"
      height="80vh"
      class="shadow-none"
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
      @send-message="sendMessage($event.detail[0])"
      @fetch-messages="fetchMessages($event.detail[0])"
      :theme="colorMode.preference"
    >
      <div slot="room-header-avatar">
        <div>
          <Avatar icon="pi pi-user" class="mr-2" size="large" style="background-color: #ece9fc; color: #2a1261" shape="circle" />
        </div>
      </div>
      <div slot="room-header-info">
        <div>
          <h2 class="font-bold max-w-[15rem] md:max-w-full truncate">User id: {{ user_id }}</h2>
          <p>Time left: {{ formatTime(countdown) }}</p>
        </div>
      </div>
    </vue-advanced-chat>
    <!-- {{ choiceOptions }}
    {{ isChoiceStrict }} -->
    <!-- Choice buttons (only if we have choice options) -->
    <!-- <div
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
    </div> -->
    <!-- Reload button (only if timer has expired) -->
    <!-- <div class="py-4 flex justify-center" v-if="timerExpired">
      <Button label="Chat again" class="p-button-outlined p-button-danger" @click="reloadPage" />
    </div> -->
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { register } from "vue-advanced-chat";
register();
//  :show-footer="false" for hiding textarea
const colorMode = useColorMode();
import { useToast } from "primevue/usetoast"; // Assuming you’re using primevue

const toast = useToast();

// Existing reactive references
const currentUserId = ref("4321");
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

let props = defineProps({
  id: {
    type: String,
  },
  user_id: {
    type: String,
  },
});

const messages = ref([]);
const messagesLoaded = ref(false);
const websocket = ref(null);

// NEW: Add these two:
const choiceOptions = ref([]); // Will hold the array of choices from the server
const isChoiceStrict = ref(false); // If true, disable text input

// NEW: Add a flag to track if the timer has expired
const timerExpired = ref(false);

function transformChatMessages(apiMessages) {
  return apiMessages.map((msg, index) => {
    const dateObj = msg.timestamp ? new Date(msg.timestamp) : new Date();
    const isSent = msg.sender_role === "ai" || msg.sender_role === "consultant";

    return {
      _id: msg._id ?? index,
      content: typeof msg.message === "string" ? msg.message : "",
      senderId: msg.sender_role === "client" ? "1234" : "4321",
      username: msg.sender_role === "ai" ? "AI Bot" : msg.sender_role === "consultant" ? "Consultant" : "Client",
      date: dateObj.toDateString(),
      timestamp: dateObj.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      sent: isSent, // Add sent property based on the role
      seen: true, // Assume all messages are seen
    };
  });
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
function formatTime(totalSeconds) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  // Pad with leading zeros if necessary
  const hh = hours.toString().padStart(2, '0');
  const mm = minutes.toString().padStart(2, '0');
  const ss = seconds.toString().padStart(2, '0');

  return `${hh}:${mm}:${ss}`;
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

// Chat input or button press => send
const sendMessage = (message) => {
  // By default, we only send to the server via WebSocket
  websocket.value?.send(
    JSON.stringify({
      type: "new_message",
      message: message.content,
    })
  );
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
const token = useCookie("access_token");
let route = useRoute();
// WebSocket
const initializeWebSocket = (chatId) => {
  if (!token.value) {
    return;
  }

  const wsUrl = `${window.location.hostname === "localhost" ? "ws" : "wss"}://${
    window.location.hostname === "localhost" ? "localhost:8000" : window.location.hostname
  }/ws/${chatId}/?token=${token.value}`;
  console.log("WebSocket URL:", wsUrl);
  websocket.value = new WebSocket(wsUrl);

  websocket.value.onopen = () => {
    console.log("WebSocket connection established.");
    websocket.value?.send(JSON.stringify({ type: "status_check" }));
    websocket.value?.send(JSON.stringify({ type: "get_messages" }));
  };

  websocket.value.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Received data:", data);

    // Show toasts if attention/error
    if (data.type === "attention") {
      toast.add({
        severity: "warn",
        summary: "Attention",
        detail: data.message,
        life: 6000,
      });
    } else if (data.type === "error") {
      toast.add({
        severity: "error",
        summary: "Error",
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
        break;
      }
      case "get_messages": {
        console.log("Messages Retrieved:", data.messages);
        // 1) Transform the message array
        const transformed = transformChatMessages(data.messages);

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
        const [transformed] = transformChatMessages([data]);
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
  };

  websocket.value.onclose = () => {
    console.log("WebSocket connection closed by backend.");
  };

  websocket.value.onerror = (error) => {
    console.error("WebSocket error:", error);
  };
};
const isIphone = ref(false);
// Обработчик для изменения видимости страницы
const handleVisibilityChange = () => {
  console.log("Visibility state changed:", document.visibilityState);
  if (document.visibilityState === "visible") {
    console.log("Page is visible. Checking WebSocket connection...");

    if (websocket.value) {
      console.log("WebSocket is not open. Reconnecting...");
      initializeWebSocket(props.id);
    } else {
      websocket.value.close();
      initializeWebSocket(props.id);
    }
  } else {
    console.log("Page is hidden. Pausing updates.");
  }
};

const handleFocus = () => {
    console.log('Окно в фокусе');
    handleVisibilityChange();
  };

onMounted(() => {
  const ua = navigator.userAgent || navigator.vendor || window.opera;
  isIphone.value = /iPhone/i.test(ua);
  let tg = window.Telegram.WebApp;
  if (props.id) {
    initializeWebSocket(props.id);
  }
  tg.expand();
  tg.isVerticalSwipesEnabled = false;
  tg.enableClosingConfirmation();

  

  // Добавляем слушатель события visibilitychange
  window.addEventListener('focus', handleFocus);
});

onBeforeUnmount(() => {
  if (websocket.value) {
    console.log("UNMOUNTED WebSocket disconnection...");
    websocket.value.close();
  }
  if (countdownInterval) {
    clearInterval(countdownInterval);
  }
  window.removeEventListener('focus', handleFocus);
});


watch(props, () => {
  if (props.id && !websocket.value) {
    initializeWebSocket(props.id);
  }
});


</script>

<style>
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
</style>
<style scoped></style>
