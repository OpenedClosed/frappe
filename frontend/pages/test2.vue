<template>
    <div class="flex flex-col h-screen">
      <Toast />
      <vue-advanced-chat
        height="calc(100vh - 160px)"
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
      >
        <!-- Override each message rendering by using v-for and the slot name "message_ID" -->
        <!-- Named slots for each message -->
         
        <div
          v-for="message in messages"
          :key="message._id"
          :slot="'message_' + message._id"
          class="flex flex-col"
        >
          <!-- Our custom Tailwind bubble component -->
          <TailwindBubble
            :message="message"
            :currentUserId="currentUserId"
          />
  
          <!-- If the server sent choice options, display them below the bubble -->
          <div
            v-if="message.choiceOptions && message.choiceOptions.length"
            class="flex flex-wrap mt-1 space-x-2"
          >
            <button
              v-for="option in message.choiceOptions"
              :key="option"
              @click="sendMessage({ content: option })"
              class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              {{ option }}
            </button>
          </div>
        </div>
  
        <div slot="room-header-info">
          <div>
            <h2 class="font-bold">DenisDrive</h2>
            <p>Time left: {{ formatTime(countdown) }}</p>
          </div>
        </div>
      </vue-advanced-chat>
      <!-- {{ choiceOptions }}
      {{ isChoiceStrict }} -->
      <!-- Choice buttons (only if we have choice options) -->
      <div v-if="choiceOptions.length" class="choice-buttons-container">
        <Button
          v-for="option in choiceOptions"
          :key="option"
          :label="option"
          class="p-button-outlined p-mr-2"
          @click="handleChoiceClick(option)"
        />
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted, onBeforeUnmount } from "vue";
  import { register } from "vue-advanced-chat";
  register();
  //  :show-footer="false" for hiding textarea
  
  import { useToast } from "primevue/usetoast"; // Assuming you’re using primevue
  
  const toast = useToast();
  
  // Existing reactive references
  const currentUserId = ref("1234");
  const activeRoomId = ref("1");
  const rooms = ref([
    {
      roomId: "1",
      avatar: "/favicon.ico",
      users: [
        { _id: "1234", username: "John Doe" },
        { _id: "4321", username: "John Snow" },
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
  
  // NEW: Add these two:
  const choiceOptions = ref([]); // Will hold the array of choices from the server
  const isChoiceStrict = ref(false); // If true, disable text input
  
  function transformChatMessages(apiMessages) {
    return apiMessages.map((msg, index) => {
      const dateObj = msg.timestamp ? new Date(msg.timestamp) : new Date();
  
      return {
        _id: msg._id ?? index, // safe optional chaining
        content: typeof msg.message === "string" ? msg.message : "",
        senderId: msg.sender_role === "ai" ? "4321" : "1234",
        username: msg.sender_role === "ai" ? "AI Bot" : "You",
        date: dateObj.toDateString(),
        timestamp: dateObj.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        // **Include choice options** if they exist on the server’s message
        choiceOptions: Array.isArray(msg.choice_options) ? msg.choice_options : [],
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
  
    // Clear choice options and re-enable chat input
    choiceOptions.value = [];
    isChoiceStrict.value = false;
  };
  
  // WebSocket
  const initializeWebSocket = (chatId) => {
    const wsUrl = `ws://localhost:8000/ws/${chatId}/`;
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
      console.log("WebSocket connection closed.");
    };
  
    websocket.value.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  };
  
  onMounted(async () => {
    const chatData = await useAsyncData("chatData", getChatData);
    if (chatData.data && chatData.data.value) {
      const { chat_id } = chatData.data.value;
      initializeWebSocket(chat_id);
    }
  });
  
  onBeforeUnmount(() => {
    if (websocket.value) {
      websocket.value.close();
    }
    if (countdownInterval) {
      clearInterval(countdownInterval);
    }
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
  }
  /* Hide the rooms container if you only want a single chat */
  .vac-rooms-container {
    display: none !important;
  }
  </style>
  