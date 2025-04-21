<!-- ~/components/ChatPanel.vue -->
<template>
  <div class="flex flex-col h-[80vh] max-h-[80vh] ">
    <Toast class="max-w-[18rem] md:max-w-full" />

    <div class="flex items-center gap-3 m-2">
      <!-- “All” label -->
      <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
        All
      </span>

      <!-- InputSwitch (PrimeVue) -->
      <InputSwitch v-model="unreadOnly" onLabel="Unread" offLabel="All" onIcon="pi pi-envelope-open"
        offIcon="pi pi-inbox" class="h-6 w-11 shrink-0 cursor-pointer outline-none
             transition-colors duration-200" />

      <!-- “Unread” label -->
      <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
        Unread
      </span>
    </div>


    <vue-advanced-chat
      :height="'80vh'"
      :current-user-id="currentUserId"
      :rooms="JSON.stringify(displayedRooms)"
      :messages="JSON.stringify(panelMessages)"
      :messages-loaded="true"
      :selected-room-id="activeRoomId"
      :single-room="false"
      :show-input-options="false"
      :show-audio="false"
      :show-files="false"
      :show-add-room="false"
      :theme="colorMode.preference"
      auto-scroll='{
        "send": { "new": true, "newAfterScrollUp": true },
        "receive": { "new": true, "newAfterScrollUp": true }
      }'
      @send-message="(msg) => sendMessage(msg.detail[0])"
      @fetch-messages="getChatId"
      @room-selected="({ detail }) => (activeRoomId = detail[0])"
      :rooms-loaded="roomsLoaded"
      @fetch-more-rooms="loadMoreChats"
    >
      <div slot="room-header-avatar">
        <Avatar icon="pi pi-user" size="large" class="mr-2" style="background: #ece9fc; color: #2a1261" />
      </div>
      <div slot="room-header-info">
        <div class="flex flex-col">
          <h2 class="font-bold truncate max-w-[15rem] md:max-w-full">User id: {{ activeUserId }}</h2>
          <p class="text-sm">{{ formatTimeDifferenceEU(activeStartDate) }}</p>
        </div>
      </div>
    </vue-advanced-chat>
  </div>
</template>

<script setup>
/* ── imports ──────────────────────────────────────────────── */
import { ref, computed, watch, watchEffect, shallowRef, onBeforeUnmount } from "vue";
import { register } from "vue-advanced-chat";
import Toast from "primevue/toast";
import { useChatLogic } from "~/composables/useChatLogic";
const { isAutoMode, currentChatId } = useChatState();

register();
const colorMode = useColorMode();
const { $listen } = useNuxtApp();
const roomsLoaded = computed(() => rooms.value.length > 0);
const unreadOnly = ref(false); // false → “All”, true → “Unread”

/* ── props / emits ─────────────────────────────────────────── */
const props = defineProps({
  user_id: { type: String, default: "" },
  chatsData: { type: Array, default: () => [] },
});
defineEmits(["close-chat"]);

watch(props, () => {
  console.log("props", props); // For debugging: log props changes (e.g. close chat on user_id change)
});

function getChatId(data) {
  console.log("getChatId", data?.detail?.[0]?.room?.roomId); // For debugging: log chat ID retrieval
  if (data?.detail?.[0]?.room?.roomId) {
    activeRoomId.value = data.detail[0].room.roomId;
  }
}
/* ── expose refs coming from useChatLogic ──────────────────── */
const isMobile = computed(() => chatLogic.value?.isMobile);
// const currentUserId = computed(() => chatLogic.value?.currentUserId);
const isChoiceStrict = computed(() => chatLogic.value?.isChoiceStrict);
const timerExpired = computed(() => chatLogic.value?.timerExpired);
const textMessagesJson = computed(() => chatLogic.value?.textMessagesJson);
const sendMessage = computed(() => chatLogic.value?.sendMessage);
const fetchMessages = computed(() => chatLogic.value?.fetchMessages);
const initializeWebSocket = computed(() => chatLogic.value?.initializeWebSocket);
const currentUserId = ref("4321"); // ← это захардкожено
/* ── state ─────────────────────────────────────────────────── */
const rooms = ref([]);
const messagesMap = ref({}); // { [roomId]: ChatMessage[] }
const activeRoomId = ref(null);
const activeUsername = ref(null);
const activeUserId = ref(null);
const activeStartDate = ref(null);
const panelMessages = computed(() => messagesMap.value[activeRoomId.value] || []);


function clearRoomName(room) {
  const clean = room.roomName.replace(/^🔴\s*/, '')            // strip a previous badge
  return clean 
}

/* ── Chat logic instance (re‑created on room switch) ───────── */
const chatLogic = shallowRef(null);
function initChatLogic(chat_id) {
  if (!chat_id) return;
  chatLogic.value?.destroy?.(); // optional cleanup
  chatLogic.value = null;
  chatLogic.value = useChatLogic({});
}

/* ── NEW: helper to decide if a room is unread for you ───── */
function isRoomUnread(room) {
  // Very simple rule: last message isn’t from the consultant
  return room.lastMessage && room.lastMessage.senderId !== currentUserId.value;
}
const displayedRooms = ref([]);

watch([unreadOnly, rooms], (newVal) => {
  console.log("unreadOnly changed to:", newVal); // Log the change for debugging
  let filteredRooms = rooms.value;
  if (unreadOnly.value) {
    // Filter for unread rooms
    filteredRooms = filteredRooms.filter((room) => !room.seen);
  }
  displayedRooms.value = filteredRooms;
});

function markRoomAsSeen(roomId) {
  console.log("markRoomAsSeen", roomId); // For debugging: log room ID to be marked as seen
  const i = rooms.value.findIndex((r) => r.roomId === roomId);
  if (i !== -1) {
    // Spread forces Vue to emit a reactive change
    rooms.value[i] = { ...rooms.value[i], seen: true, roomName: clearRoomName(rooms.value[i]) };
  }
  console.log("rooms.value[i].seen", rooms.value[i].seen); // For debugging: log seen status
  console.log("Index", i); // For debugging: log seen status
  console.log(" rooms.value[i]", rooms.value[i]); // For debugging: log all rooms
}

watch(activeRoomId, (id) => {
  // console.log("activeRoomId", id); // For debugging: log active room ID changes
  currentChatId.value = id; // 👈 update the global state
  initChatLogic(id);
  initializeWebSocket.value?.(id); // initialize WebSocket connection
  // 🔥 Find the selected room
  const activeRoom = rooms.value.find((r) => r.roomId === id);
  markRoomAsSeen(id); // 👈 NEW
  console.log("rooms", rooms.value); // For debugging: log all rooms
  console.log("activeRoom", activeRoom); // For debugging: log active room data
  if (activeRoom) {
    // Assume client user is always the first one (customize as needed)
    const clientUser = activeRoom.users.find((u) => u._id === "1234");
    activeUserId.value = activeRoom?.roomName || null;
    activeStartDate.value = activeRoom?.lastMessage?.timestamp || null;
  }
});

function loadMoreChats() {
  console.log("loadMoreChats"); // For debugging: log load more chats action
  // Implement your logic to load more chats here
  // This could be an API call or any other logic to fetch more chat data
}

/* ① initialize as early as possible –
      if a single :id is passed
      or once the first chat appears in props.chatsData */
watchEffect(() => {
  const firstChatId = props.chatsData[0]?.chat_id;
  initChatLogic(props.id || firstChatId);
  initializeWebSocket.value?.(firstChatId); // initialize WebSocket connection
});
function formatDateEU(isoDateStr) {
  const date = new Date(isoDateStr);
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
function formatTimeDifferenceEU(dateStr) {
  if (!dateStr) return "No date provided";
  const now = new Date();
  const [day, month, year, hour, minute] = dateStr
    .replace(",", "")
    .split(/[\s.:]/)
    .map(Number);
  const targetDate = new Date(year, month - 1, day, hour, minute);
  const diffMs = now - targetDate;

  if (diffMs <= 0) return "In the future";

  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  return `Started ${diffDays} days, ${diffHours} hours, ${diffMinutes} minutes ago`;
}


/* ② rebuild rooms + messages when data and transformFn are ready */
const transformFn = computed(() => chatLogic.value?.transformChatMessages);
function buildRooms(chats, consultantId) {
  console.log("buildRooms", chats); // For debugging: log chat data
  const sourceAvatars = {
    Internal: "/avatars/telegram.png",
    Instagram: "/avatars/insta.png",
    Facebook: "/avatars/facebook.png",
    WhatsApp: "/avatars/whatsapp.png",
  };

  return chats.map((chat, idx) => {
    // console.log("chatelement", chat); // For debugging: log chat data
    const client = chat.client && chat.client[0] ? chat.client[0] : {};
    const sourceName = client.source && client.source.en ? client.source.en : "Client";

    const clientUser = {
      _id: "1234",
      username: sourceName,
      avatar: sourceAvatars[sourceName] || "/avatars/default.png",
    };

    const consultantUser = {
      _id: consultantId,
      username: "Consultant",
      avatar: "/avatars/consultant.png", // or whatever default you want
    };

    const last = chat.messages && chat.messages.length ? chat.messages[chat.messages.length - 1] : null;
    const lastMessage = last
      ? {
          content: last.message,
          senderId: last.sender_role && last.sender_role.en === "Client" ? clientUser._id : consultantUser._id,
          timestamp: formatDateEU(chat.created_at),
        }
      : { content: "", senderId: consultantUser._id };

    return {
      avatar: sourceAvatars[sourceName] || "/avatars/default.png",
      roomId: chat.chat_id,
      roomName: `🔴 ${client.id}` || `Chat ${idx + 1}`,
      users: [clientUser, consultantUser],
      lastMessage,
      typingUsers: [],
      seen: false,
    };
  });
}
watch(
  () => props.chatsData,
  async () => {
    if (!props.chatsData.length || !transformFn.value) return;

    // Build the messages map
    const newMap = {};
    for (const chat of props.chatsData) {
      newMap[chat.chat_id] = (await transformFn.value(chat.messages)) || [];
    }
    messagesMap.value = newMap;

    // Use the helper to build rooms
    rooms.value = buildRooms(props.chatsData, currentUserId.value);
    console.log("rooms", rooms.value);
    /* Pick first room if nothing selected yet */
    if (!rooms.value.find((r) => r.roomId === activeRoomId.value)) {
      activeRoomId.value = rooms.value[0]?.roomId ?? null;
    }
  }
);

/* ── external events ───────────────────────────────────────── */
$listen("new_message_arrived", (msg) => {
  if (!msg || !messagesMap.value[activeRoomId.value]) return;
  messagesMap.value[activeRoomId.value].push(msg);
});

/* ── tidy up on unmount ───────────────────────────────────── */
onBeforeUnmount(() => chatLogic.value?.destroy?.());
</script>

<style scoped>
.vue-advanced-chat {
  box-shadow: none !important;
}
</style>
