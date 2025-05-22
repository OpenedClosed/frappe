<!-- ~/components/ChatPanel.vue -->
<template>
  <div class="flex flex-col h-[80vh] max-h-[80vh]">
    <Toast class="max-w-[18rem] md:max-w-full" />
    <div class="flex flex-row justify-between items-center">
      <div class="flex items-center gap-3 m-2">
        <!-- “All” label -->
        <span class="text-sm font-medium text-gray-700 dark:text-gray-300"> {{ t("EmbeddedChat.allLabel") }} </span>

        <!-- InputSwitch (PrimeVue) -->
        <InputSwitch
          v-model="unreadOnly"
          :onLabel="t('EmbeddedChat.unreadLabel')"
          :offLabel="t('EmbeddedChat.allLabel')"
          onIcon="pi pi-envelope-open"
          offIcon="pi pi-inbox"
          class="h-6 w-11 shrink-0 cursor-pointer outline-none transition-colors duration-200"
        />

        <!-- “Unread” label -->
        <span class="text-sm font-medium text-gray-700 dark:text-gray-300"> {{ t("EmbeddedChat.unreadLabel") }} </span>
      </div>
      <SplitButton
        :label="t('EmbeddedChat.exportButton')"
        icon="pi pi-file-excel"
        :model="exportItems"
        severity="success"
        class="m-2"
        @click="onExportToExcel"
      />
    </div>

    <vue-advanced-chat
      :height="'72vh'"
      :current-user-id="currentUserId"
      :rooms="JSON.stringify(displayedRooms)"
      :messages="JSON.stringify(chatMessages)"
      :messages-loaded="messagesLoaded"
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
      :rooms-loaded="isRoomsLoading"
      @fetch-more-rooms="loadMoreChats"
      :message-actions="JSON.stringify(messageActions)"
      @message-action-handler="onMessageAction"
      :text-messages="textMessagesJson"
    >
      <div slot="room-header-avatar">
        <Avatar icon="pi pi-user" size="large" class="mr-2" style="background: #ece9fc; color: #2a1261" />
      </div>
      <div slot="room-header-info" class="flex-1">
        <!-- 🔥 Added flex-1 here -->
        <div class="flex flex-row items-center justify-between gap-2 w-full flex-1 min-w-0">
          <div class="flex flex-col">
            <h2 class="font-bold truncate max-w-[15rem] md:max-w-full">{{ t("EmbeddedChat.userIdLabel") }}: {{ activeUserId }}</h2>
            <p class="text-sm">{{ formatTimeDifferenceEU(activeStartDate) }}</p>
          </div>
          <div class="flex flex-row justify-center items-center gap-1">
            {{ t("EmbeddedChat.sourceLabel") }}:
            <p class="text-sm">{{ currentRoomSource }}</p>
          </div>
        </div>
      </div>
      <div slot="rooms-list-search">
        <div v-if="isRoomsLoading" class="flex items-center justify-center py-5">
          <LoaderSmall />
        </div>
        <div v-else class="h-[65px]"></div>
      </div>
    </vue-advanced-chat>
    <!-- ⬇️ add this right after the closing </vue-advanced-chat> tag -->
    <Paginator :rows="20" :totalRecords="totalRecords" class="mt-2 self-center" @page="onPageChange" />
    <!-- place this just before </template> so it sits outside vue‑advanced-chat -->
    <Dialog v-model:visible="showMsgDialog" modal :header="t('EmbeddedChat.messageDialogHeader')" :style="{ width: '600px' }">
      <p class="mb-3">
        <strong>{{ t("EmbeddedChat.messageDialogId") }}:</strong> {{ selectedMsg?.message?.backend_id || "" }}<br />
        <strong>{{ t("EmbeddedChat.messageDialogText") }}:</strong> {{ selectedMsg?.message?.content || "" }}
      </p>

      <ReadonlyKB v-if="selectedMsg?.message?.sources" :sources="selectedMsg?.message.sources" />
      <div v-else>
        <p class="font-semibold text-start text-gray-500">{{ t("EmbeddedChat.noSources") }}</p>
      </div>

      <template #footer>
        <Button :label="t('EmbeddedChat.closeButton')" icon="pi pi-times" @click="showMsgDialog = false" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
/* ── imports ──────────────────────────────────────────────── */
import { ref, computed, watch, watchEffect, shallowRef, onBeforeUnmount } from "vue";
import { register } from "vue-advanced-chat";
import Toast from "primevue/toast";
import { useChatLogic } from "~/composables/useChatLogic";
import LoaderOverlay from "../LoaderOverlay.vue";
import LoaderSmall from "../LoaderSmall.vue";
import ReadonlyKB from "~/components/Dashboard/Components/ReadonlyKB.vue";
import * as XLSX from "xlsx";
import { saveAs } from "file-saver";
import { useI18n } from "#imports";
const { t, locale } = useI18n();
const { isAutoMode, currentChatId, chatMessages, messagesLoaded } = useChatState();
const route = useRoute();
const currentGroup = computed(() => route.params.group); // :group
const currentEntity = computed(() => route.params.entity); // :entity
const { currentPageName, currentPageInstances } = usePageState();
register();
const colorMode = useColorMode();
const { $listen } = useNuxtApp();
const roomsLoaded = computed(() => rooms.value.length > 0);
const unreadOnly = ref(false); // false → “All”, true → “Unread”

/* ── REFS ───────────────────────────────────────────── */
const showMsgDialog = ref(false);
const selectedMsg = ref(null);

/* ── CUSTOM DROPDOWN ITEMS (only one in this example) ─ */
const messageActions = [{ name: "seeSources", title: t("EmbeddedChat.seeSources") }];

/* ── EVENT HANDLER ──────────────────────────────────── */
function onMessageAction(messageAction) {
  if (!messageAction || !messageAction.detail || !messageAction.detail[0]) return;

  const info = messageAction.detail[0]; // Extract message from action

  console.log("onMessageAction", info); // For debugging: log action and message
  if (info.action.name === "seeSources") {
    selectedMsg.value = info; // full message object
    showMsgDialog.value = true;
  }
}

/* ── props / emits ─────────────────────────────────────────── */
const props = defineProps({
  user_id: { type: String, default: "" },
  totalRecords: { type: Number, default: 0 },
  chatsData: { type: Array, default: () => [] },
  isRoomsLoading: { type: Boolean, default: false },
});

watch(props, () => {
  console.log("props", props); // For debugging: log props changes (e.g. close chat on user_id change)
});

const toast = useToast();

/* ── dropdown items for SplitButton ───────────────── */
const exportItems = [
  {
    label: t("EmbeddedChat.exportCSV"), // add this key to i18n files
    icon: "pi pi-file",
    command: onExportToCSV,
  },
];

/* ── CSV export handler ──────────────────────────── */
async function onExportToCSV() {
  try {
    const { utils } = await import("xlsx");

    /* gather rows exactly like onExportToExcel() */
    const response = await useNuxtApp().$api.get(`api/${currentPageName.value}/${currentEntity.value}/?order=-1`);

    const rows = response.data.flatMap((chat) =>
      chat.messages.map((m) => ({
        ChatID: chat.chat_id,
        Time: m.timestamp,
        Sender: m.sender_role?.en || "",
        Text: m.message,
        ReadBy: (m.read_by_display || []).join(", "),
      }))
    );

    const ws = utils.json_to_sheet(rows);
    const csv = utils.sheet_to_csv(ws); // convert sheet → CSV string

    /* trigger download */
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    saveAs(blob, `chats_${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}.csv`);

    toast.add({ severity: "success", summary: t("EmbeddedChat.csvSuccess"), life: 3000 });
  } catch (err) {
    console.error("CSV export failed:", err);
    toast.add({
      severity: "error",
      summary: t("EmbeddedChat.csvFailed"),
      detail: err.message || err,
      life: 5000,
    });
  }
}

async function onExportToExcel() {
  try {
    // динамический импорт, чтобы не трогать SSR
    const { utils, writeFileXLSX } = await import("xlsx");

    // ── 1. Создаём книгу ───────────────────────────────
    const wb = utils.book_new();
    const usedNames = new Set();

    const response = await useNuxtApp().$api.get(`api/${currentPageName.value}/${currentEntity.value}/?order=-1`);
    console.log("response", response); // For debugging: log API response

    // ── 2. Добавляем листы без дубликатов ──────────────
    response.data.forEach((chat, idx) => {
      const rows = chat.messages.map((m) => ({
        ChatID: chat.chat_id,
        Time: m.timestamp,
        Sender: m.sender_role?.en || "",
        Text: m.message,
        ReadBy: (m.read_by_display || []).join(", "),
      }));

      /* базовое имя листа */
      let name = chat.chat_id;
      name = name.slice(0, 31); // Excel ≤ 31 символ
      usedNames.add(name);

      const ws = utils.json_to_sheet(rows);

      // Auto-adjust column widths based on content
      const columnWidths = Object.keys(rows[0] || {}).map((key) => {
        const maxLen = Math.max(key.length, ...rows.map((row) => (row[key] ? row[key].toString().length : 0)));
        return { wch: maxLen + 2 }; // +2 for padding
      });

      ws["!cols"] = columnWidths;
      console.log("ws", ws); // For debugging: log worksheet data
      utils.book_append_sheet(wb, ws, name);
    });

    // ── 3. Сохраняем файл ──────────────────────────────
    writeFileXLSX(wb, `chats_${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}.xlsx`);

    toast.add({ severity: "success", summary: t("EmbeddedChat.excelSuccess"), life: 3000 });
  } catch (err) {
    console.error("Excel export failed:", err);
    toast.add({
      severity: "error",
      summary: t("EmbeddedChat.excelFailed"),
      detail: err.message || err,
      life: 5000,
    });
  }
}

const chatRows = computed(() => props.chatsData.filter((row) => !row._isBlank && row.chat_id));

const emit = defineEmits(["close-chat", "page"]); // Emit if you still need "exportToExcel" or other events

function onPageChange(e) {
  emit("page", e.page);
}

watch(props, () => {
  console.log("props", props); // For debugging: log props changes (e.g. close chat on user_id change)
});

/* ── expose refs coming from useChatLogic ──────────────────── */
const isMobile = computed(() => chatLogic.value?.isMobile);
// const currentUserId = computed(() => chatLogic.value?.currentUserId);
const isChoiceStrict = computed(() => chatLogic.value?.isChoiceStrict);
const timerExpired = computed(() => chatLogic.value?.timerExpired);
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

const chatRoles = computed(() => ({
  client: t("UseChatLogic.client"),
  aiAssistant: t("UseChatLogic.aiAssistant"),
  consultant: t("UseChatLogic.consultant"),
  unknown: t("UseChatLogic.unknown"),
}));

const textMessagesJson = computed(() => JSON.stringify(textMessagesObject.value));

function getChatId(data) {
  console.log("getChatId", data?.detail?.[0]?.room?.roomId); // For debugging: log chat ID retrieval
  if (data?.detail?.[0]?.room?.roomId) {
    activeRoomId.value = data.detail[0].room.roomId;

    currentChatId.value = activeRoomId.value;
    initChatLogic(activeRoomId.value);
    initializeWebSocket.value?.(activeRoomId.value);

    const idx = rooms.value.findIndex((r) => r.roomId === activeRoomId.value);
    if (idx !== -1) {
      const room = rooms.value[idx];
      rooms.value[idx] = { ...room, seen: true, roomName: clearRoomName(room) };
      activeUserId.value = room?.roomName || null;
      activeStartDate.value = room?.lastMessage?.timestamp || null;
    }
  }
}

function clearRoomName(room) {
  const clean = room.roomName.replace(/^🔴\s*/, ""); // strip a previous badge
  return clean;
}

/* ── Chat logic instance (re‑created on room switch) ───────── */
const chatLogic = shallowRef(null);
function initChatLogic(chat_id) {
  if (!chat_id) return;

  // если комната та же, ничего не делаем
  if (chatLogic.value && chatLogic.value.chatId === chat_id) return;

  // создаём новую и сразу открываем сокет внутри самого хука
  chatLogic.value = useChatLogic({ chatId: chat_id, locale: locale.value, chatRoles: chatRoles.value });
}

const displayedRooms = ref([]);

watch([unreadOnly, rooms], (newVal) => {
  // console.log("unreadOnly changed to:", newVal); // Log the change for debugging
  let filteredRooms = rooms.value;
  if (unreadOnly.value) {
    // Filter for unread rooms
    filteredRooms = filteredRooms.filter((room) => !room.seen);
  }
  displayedRooms.value = filteredRooms;
});

function formatDateEU(isoDateStr) {
  if (!isoDateStr) return "";

  // If input has no "Z" at end, add it to force UTC parsing
  const normalizedStr = isoDateStr.endsWith("Z") ? isoDateStr : isoDateStr + "Z";

  const date = new Date(normalizedStr);

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatTimeDifferenceEU(dateStr) {
  if (!dateStr) return t("EmbeddedChat.noDate");
  const now = new Date();
  const [day, month, year, hour, minute] = dateStr
    .replace(",", "")
    .split(/[\s.:]/)
    .map(Number);
  const targetDate = new Date(year, month - 1, day, hour, minute);
  const diffMs = now - targetDate;

  if (diffMs <= 0) return t("EmbeddedChat.inFuture");

  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  return t("EmbeddedChat.startedAgo", {
    diffDays,
    diffHours,
    diffMinutes,
  });
}

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
    const sourceName = client.source && client.source.en ? client.source.en : t("EmbeddedChat.client");

    const clientUser = {
      _id: "1234",
      username: sourceName,
      avatar: sourceAvatars[sourceName] || "/avatars/default.png",
    };

    const consultantUser = {
      _id: consultantId,
      username: t("EmbeddedChat.consultant"),
      avatar: "/avatars/consultant.png", // or whatever default you want
    };

    const last = chat.messages && chat.messages.length ? chat.messages[chat.messages.length - 1] : null;
    const lastMessage = last
      ? {
          content: last.message,
          senderId: last.sender_role && last.sender_role.en === t("EmbeddedChat.client") ? clientUser._id : consultantUser._id,
          timestamp: formatDateEU(chat.created_at),
        }
      : { content: "", senderId: consultantUser._id };
    console.log("lastMessage", chat.messages?.[chat.messages?.length - 1]?.read_by_display?.length > 0); // For debugging: log last message data
    const seen = chat.messages?.[chat.messages?.length - 1]?.read_by_display?.length > 0 || false;
    return {
      avatar: sourceAvatars[sourceName] || "/avatars/default.png",
      roomId: chat.chat_id,
      roomName: `${seen ? "" : "🔴"} ${client.id}` || t("EmbeddedChat.chatFallback", { index: idx + 1 }),
      users: [clientUser, consultantUser],
      lastMessage,
      typingUsers: [],
      seen: seen,
      sourceName: sourceName,
    };
  });
}

const currentRoomSource = computed(() => {
  return rooms.value.find((r) => r.roomId === activeRoomId.value)?.sourceName || "";
});

watch([chatRows], async ([rows]) => {
  if (!rows.length) return;

  rooms.value = buildRooms(rows, currentUserId.value);

  if (!rooms.value.find((r) => r.roomId === activeRoomId.value)) {
    activeRoomId.value = rooms.value[0]?.roomId ?? null;
  }
});
/* ── external events ───────────────────────────────────────── */
// $listen("new_message_arrived", (msg) => {
//   if (!msg || !messagesMap.value[activeRoomId.value]) return;
//   messagesMap.value[activeRoomId.value].push(msg);
// });

/* ── tidy up on unmount ───────────────────────────────────── */
onBeforeUnmount(() => chatLogic.value?.destroy?.());
</script>

<style scoped>
.vue-advanced-chat {
  box-shadow: none !important;
}
</style>
