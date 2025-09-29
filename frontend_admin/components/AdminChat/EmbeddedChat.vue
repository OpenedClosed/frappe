<!-- ~/components/ChatPanel.vue -->
<template>
  <div class="flex flex-col " :class="isMobile ? 'h-[100vh] max-h-[100vh]' : 'h-[80vh] max-h-[80vh]'">
    <Toast class="max-w-[18rem] md:max-w-full" />
    <div class="flex flex-col sm:flex-row justify-between items-center gap-1 sm:gap-0 p-2  sm:py-2">
      <div class="flex flex-col sm:flex-row items-center gap-2 sm:gap-3 w-full sm:w-auto">
        <div class="flex flex-row items-center gap-2 sm:gap-3">
          <!-- Mobile: Stack labels and switch vertically, Desktop: Horizontal -->
          <div class="flex flex-col sm:flex-row items-center gap-2 sm:gap-3 w-full sm:w-auto">
            <!-- InputSwitch (PrimeVue) -->
            <div class="flex items-center gap-2 justify-center sm:justify-start">
              <span class="text-xs sm: text-sm font-medium text-gray-700 dark:text-gray-300"> {{ t("EmbeddedChat.allLabel") }} </span>
              <InputSwitch
                v-model="unreadOnly"
                :onLabel="t('EmbeddedChat.unreadLabel')"
                :offLabel="t('EmbeddedChat.allLabel')"
                onIcon="pi pi-envelope-open"
                offIcon="pi pi-inbox"
                class="h-6 w-11 shrink-0 cursor-pointer outline-none transition-colors duration-200"
              />
              <span class="text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300"> {{ t("EmbeddedChat.unreadLabel") }} </span>
            </div>
          </div>

          <Button icon="pi pi-info-circle" text size="small" class="self-center sm:self-auto" @click="toggleLegend" />
          <ChatFilters
            v-if="filterMetadata"
            :metadata="filterMetadata"
            :metadata-loading="metadataLoading"
            :has-active-filters="true"
            :has-empty-results="hasEmptyFilterResults"
            :results-count="totalRecords"
            :show-debug="true"
            @filters-changed="onFiltersChanged"
            @clear-filters="clearFilters"
          />
          <Button
            v-if="isExportChangeButtonVisible"
            :icon="showExport ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
            class="sm:hidden"
            text
            size="small"
            @click="toggleExport"
          />
        </div>

        <OverlayPanel ref="legendPanel">
          <div class="text-sm space-y-1">
            <div>{{ t("Legend.NewSession") }}</div>
            <div>{{ t("Legend.WaitingForAI") }}</div>
            <div>{{ t("Legend.AIWaitingForClient") }}</div>
            <div>{{ t("Legend.WaitingForConsultant") }}</div>
            <div>{{ t("Legend.ReadByConsultant") }}</div>
            <div>{{ t("Legend.ConsultantWaitingForClient") }}</div>
            <div>{{ t("Legend.ClosedNoMessages") }}</div>
            <div>{{ t("Legend.ClosedByTimeout") }}</div>
            <div>{{ t("Legend.ClosedByOperator") }}</div>
            <div>{{ t("Legend.BriefInProgress") }}</div>
            <div>{{ t("Legend.BriefCompleted") }}</div>
          </div>
        </OverlayPanel>
      </div>

      <transition name="slide-down">
        <SplitButton
          v-show="isExportVisible"
          :label="t('EmbeddedChat.exportButton')"
          icon="pi pi-file-excel"
          :model="exportItems"
          severity="success"
          size="small"
          class="w-auto sm:w-auto mt-2 sm:mt-0 mobile-icon-only sm:block"
          @click="onExportToExcel"
        />
      </transition>
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
      :rooms-loaded="!isRoomsLoading"
      @fetch-more-rooms="loadMoreChats"
      :message-actions="JSON.stringify(messageActions)"
      @message-action-handler="onMessageAction"
      :text-messages="textMessagesJson"
    >
      <div slot="room-header-avatar" class="flex items-center justify-center">
        <Avatar v-if="activePdEntry?.avatar" :image="activePdEntry?.avatar" :size="isMobile ? 'normal' : 'large'" shape="circle" class="mr-2" />
        <Avatar v-else icon="pi pi-user" :size="isMobile ? 'normal' : 'large'" shape="circle" class="mr-2" />
      </div>
      <div slot="room-header-info" class="flex-1 pl-1">
        <!-- 🔥 Added flex-1 here -->
        <div class="flex flex-row items-center justify-between gap-2 w-full flex-1 min-w-0">
          <div class="flex flex-col flex-1">
            <!-- Mobile: Compact view with dialog button -->
            <div v-if="isMobile" class="flex items-center justify-between gap-2">
              <h2 class="font-bold text-sm truncate max-w-[8rem]">
                {{ activePdEntry?.username || activeUserId }}
              </h2>
              <Button icon="pi pi-info" severity="info" size="small" class="p-1 text-xs" @click="showUserInfoDialog = true" />
            </div>

            <div v-else class="flex flex-col justify-center items-start gap-2">
              <!-- Desktop: Full view -->
              <h2 class="font-bold truncate max-w-[15rem] md:max-w-full">
                {{ t("EmbeddedChat.userIdLabel") }}: {{ activePdEntry?.username || activeUserId }}
              </h2>
              <p class="text-sm">{{ formatTimeDifferenceEU(activeStartDate) }}</p>
            </div>
          </div>
          <div v-if="!isMobile" class="flex flex-row justify-center items-center gap-1">
            {{ t("EmbeddedChat.sourceLabel") }}:
            <p class="text-sm">{{ currentRoomSource }}</p>
          </div>
        </div>
      </div>
      <div slot="rooms-list-search">
        <ChatSearch
          ref="chatSearchRef"
          v-model="roomSearchQuery"
          :placeholder="t('EmbeddedChat.searchRooms', 'Search chats...')"
          :debounce-time="300"
          :loading="isRoomsLoading"
          :loading-text="t('EmbeddedChat.searchingChats', 'Searching chats...')"
          @search="onRoomSearch"
          @clear="onRoomSearchClear"
        />
      </div>
    </vue-advanced-chat>
    <!-- ⬇️ add this right after the closing </vue-advanced-chat> tag -->
    <Paginator :rows="props.pageSize" :totalRecords="totalRecords" class="mt-2 self-center" @page="onPageChange" :template="{
        '640px': 'FirstPageLink PrevPageLink CurrentPageReport NextPageLink LastPageLink JumpToPageDropdown',
        default: 'FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink JumpToPageDropdown'
    }" />
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

    <!-- User Info Dialog for Mobile -->
    <Dialog
      v-model:visible="showUserInfoDialog"
      modal
      :closable="false"
      :header="t('EmbeddedChat.userInfoDialogHeader')"
      :style="{ width: '90vw' }"
    >
      <div class="space-y-3">
        <div v-if="activePdEntry?.avatar" class="flex justify-center">
          <Avatar :image="activePdEntry.avatar" size="xlarge" shape="circle" />
        </div>
        <div>
          <strong>{{ t("EmbeddedChat.userIdLabel") }}:</strong>
          <p class="mt-1">{{ activePdEntry?.username || activeUserId }}</p>
        </div>
        <div>
          <strong>{{ t("EmbeddedChat.sourceLabel") }}:</strong>
          <p class="mt-1">{{ currentRoomSource }}</p>
        </div>
        <div>
          <strong>{{ t("EmbeddedChat.startedLabel") }}:</strong>
          <p class="mt-1">{{ formatTimeDifferenceEU(activeStartDate) }}</p>
        </div>
        <div v-if="activePdEntry?.externalId">
          <strong>{{ t("EmbeddedChat.externalIdLabel") }}:</strong>
          <p class="mt-1">{{ activePdEntry.externalId }}</p>
        </div>
        <div v-if="activePdEntry?.phone">
          <strong>{{ t("EmbeddedChat.phoneLabel") }}:</strong>
          <p class="mt-1">{{ activePdEntry.phone }}</p>
        </div>
      </div>

      <template #footer>
        <Button :label="t('EmbeddedChat.closeButton')" icon="pi pi-times" @click="showUserInfoDialog = false" />
      </template>
    </Dialog>


 
  </div>
</template>

<script setup>
/* ── imports ──────────────────────────────────────────────── */
import { ref, computed, watch, watchEffect, shallowRef, onBeforeUnmount, onMounted, nextTick } from "vue";
import { register } from "vue-advanced-chat";
import Toast from "primevue/toast";
import { useChatLogic } from "~/composables/useChatLogic";
import LoaderOverlay from "../LoaderOverlay.vue";
import LoaderSmall from "../LoaderSmall.vue";
import ReadonlyKB from "~/components/Dashboard/Components/ReadonlyKB.vue";
import * as XLSX from "xlsx";
import { saveAs } from "file-saver";
import { useI18n } from "#imports";
import ChatFilters from "./ChatFilters.vue";
import ChatSearch from "./ChatSearch.vue";
import { debounce } from "lodash";
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
const legendPanel = ref();

const toggleLegend = (event) => {
  legendPanel.value.toggle(event);
};

const toggleExport = () => {
  showExport.value = !showExport.value;
};
const showExport = ref(false);

const windowWidth = ref(0);

const isMobile = computed(() => {
  return windowWidth.value < 640;
});

const isExportVisible = computed(() => {
  return !isMobile.value || showExport.value;
});

const isExportChangeButtonVisible = computed(() => {
  return isMobile.value;
});

const updateWindowWidth = () => {
  if (typeof window !== "undefined") {
    windowWidth.value = window.innerWidth;
  }
};

/* ── Data initialization from MainContent ──────────────────── */
async function initializeChatData() {
  if (!currentEntity.value) {
    console.warn('No entity specified for initialization');
    return;
  }

  try {
    isLoadingData.value = true;
    
    // Fetch initial data
    await fetchChatData(0, {}, {});
    
    // Validate entity configuration
    const entityConfig = validateEntityConfig();
    
    if (entityConfig) {
      console.log('Entity configuration loaded:', entityConfig);
    }
    
  } catch (error) {
    console.error('Failed to initialize chat data:', error);
    parseError(error);
  } finally {
    isLoadingData.value = false;
  }
}

onMounted(async () => {
  updateWindowWidth();
  window.addEventListener("resize", updateWindowWidth);
  await initializeChatData();
});

/* ── REFS ───────────────────────────────────────────── */
const showMsgDialog = ref(false);
const selectedMsg = ref(null);
const showUserInfoDialog = ref(false);

// Room search functionality
const roomSearchQuery = ref('');
const chatSearchRef = ref(null);

// Filter metadata and chat data refs
const filterMetadata = ref(null);
const metadataLoading = ref(false);
const appliedFilters = ref({});
const appliedSearch = ref({});
const chatData = ref([]);
const totalRecords = ref(0);
const currentPage = ref(0);

// Additional processing refs from MainContent
const isLoading = ref(false);
const isLoadingData = ref(false);
const isRoomsLoading = ref(false);
const tableDataOriginal = ref([]);
const currentEntityName = ref("");
const isEntityInline = ref(false);
const pageSize = ref(20);
const searchQuery = ref("");
const selectedField = ref(null);
const dateRange = ref({ start: null, end: null });

// Request tracking to prevent duplicates
const isRequestInProgress = ref(false);
const lastRequestParams = ref("");

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
  pageSize: { type: Number, default: 20 },
});

watch(props, () => {
  console.log("props", props); // For debugging: log props changes (e.g. close chat on user_id change)
});

const toast = useToast();

/* ── Error handling from MainContent ──────────────────────── */
function parseError(error) {
  console.log('Parsing error:', error);

  if (error.response && error.response.data) {
    const data = error.response.data;
    console.log('Error data:', data);

    let toastMessage = "";

    if (data.detail) {
      if (typeof data.detail === "string") {
        toastMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        toastMessage = data.detail.map((e) => e.msg || e).join(", ");
      } else if (typeof data.detail === "object") {
        toastMessage = Object.entries(data.detail)
          .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : value}`)
          .join("; ");
      }
      
      toast.add({
        severity: "error",
        summary: t("EmbeddedChat.errorTitle", "Error"),
        detail: toastMessage,
        life: 5000,
      });

      return toastMessage;
    }

    toastMessage = data.message || error.message;

    toast.add({
      severity: "error",
      summary: t("EmbeddedChat.errorTitle", "Error"),
      detail: toastMessage,
      life: 5000,
    });

    return toastMessage;
  }

  const fallbackMessage = error.message || t("EmbeddedChat.unknownError", "Unknown error occurred");
  toast.add({
    severity: "error",
    summary: t("EmbeddedChat.errorTitle", "Error"),
    detail: fallbackMessage,
    life: 5000,
  });

  return fallbackMessage;
}

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

// Single source of truth for all chat data
const hasActiveFilters = computed(() => {
  return Object.keys(appliedFilters.value).length > 0 || 
         (appliedSearch.value?.q && appliedSearch.value.q.trim());
});

// Check if filtered results are empty
const hasEmptyFilterResults = computed(() => {
  return hasActiveFilters.value && chatRows.value.length === 0;
});

const chatRows = computed(() => {
  // Always use chatData as single source of truth
  const filteredData = chatData.value.filter((row) => !row._isBlank && row.chat_id);
  
  // If we have active filters but no results, return empty array to trigger empty state
  if (hasActiveFilters.value && filteredData.length === 0) {
    return [];
  }
  
  return filteredData;
});


const emit = defineEmits(["close-chat", "page", "refresh-chats", "data-loaded", "entity-config-loaded"]); // Added more emits

/* ── Entity configuration functions from MainContent ──────────── */
function findEntityConfig(data, groupKey, entityKey) {
  if (!groupKey || !entityKey) return null;
  if (!data[groupKey]) return null;
  return data[groupKey].entities.find((e) => e.registered_name === entityKey) || null;
}

function validateEntityConfig() {
  if (!filterMetadata.value) {
    console.warn('No metadata available for entity validation');
    return null;
  }

  const entityConfig = findEntityConfig(filterMetadata.value, currentGroup.value, currentEntity.value);
  if (!entityConfig) {
    console.warn('No valid entityConfig found for:', currentGroup.value, currentEntity.value);
    return null;
  }

  // Set entity properties
  currentEntityName.value = entityConfig.model?.verbose_name || entityConfig.model?.name || currentEntity.value;
  isEntityInline.value = entityConfig.model?.is_inline || false;
  
  // Emit entity config for parent components
  emit('entity-config-loaded', entityConfig);
  
  return entityConfig;
}

async function onPageChange(e) {
  // PrimeVue's DataTable uses zero-based 'page' in the event
  const newPage = typeof e.page !== 'undefined' ? e.page : e;
  const newPageSize = e.rows || props.pageSize || pageSize.value;
  
  
  // Update local state
  currentPage.value = newPage;
  pageSize.value = newPageSize;
  
  // Fetch new data with current filters/search state
  const response = await fetchChatData(newPage, appliedFilters.value, appliedSearch.value);
  
  // Emit to parent
  emit("page", newPage);
}

watch(props, () => {
  console.log("props", props); // For debugging: log props changes (e.g. close chat on user_id change)
});

/* ── expose refs coming from useChatLogic ──────────────────── */
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
const activePdEntry = ref(null);
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
  console.log("getChatId data", data); // For debugging: log chat ID retrieval
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
      activePdEntry.value = room?.pdEntry || null;
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

// Room search handlers for ChatSearch component
const onRoomSearch = async (searchTerm) => {
  try {
    if (!searchTerm || !searchTerm.trim()) {
      // If no search term, fetch all data
      await fetchChatData(0, appliedFilters.value, {});
      return;
    }
    
    // Use existing fetchChatData with simple search parameter
    const searchObj = { q: searchTerm.trim() };
    await fetchChatData(0, appliedFilters.value, searchObj);
  } catch (error) {
    console.error('Room search failed:', error);
  } finally {
    // Stop loading indicator in ChatSearch component
    if (chatSearchRef.value) {
      chatSearchRef.value.stopLoading();
    }
  }
};

const onRoomSearchClear = () => {
  // Reset to original data
  fetchChatData(0, appliedFilters.value, {});
  // Ensure loading state is cleared
  if (chatSearchRef.value) {
    chatSearchRef.value.stopLoading();
  }
};

// Simplified display logic - no more client-side search filtering
watch([unreadOnly, rooms], (newVal) => {
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

function stripPrefix(id = "") {
  /* TELEGRAM_599597042 → 599597042 */
  return id.replace(/^[A-Z_]+_/, "");
}

/**
 *  Turn sender_info (plus client_id) → a tidy, guaranteed-filled object
 */
function normaliseParticipant(senderInfo = {}, clientId = "") {
  const md = senderInfo.metadata || {};

  /* -------- NAME -------- */
  const username =
    senderInfo.name ??
    md.profile_name ?? // WhatsApp
    md.name ?? // Telegram duplicate
    md.username ?? // Telegram @username
    stripPrefix(clientId); // last fallback

  /* -------- AVATAR -------- */
  const avatar = senderInfo.avatar_url ?? md.avatar_url ?? "";

  /* -------- SOURCE -------- */
  let source = senderInfo.source || "";
  if (!source) {
    // Instagram sometimes comes in as “Internal”
    if (clientId.startsWith("TELEGRAM_")) source = "Telegram";
    else if (clientId.startsWith("WHATSAPP_")) source = "WhatsApp";
    else if (clientId.startsWith("INSTAGRAM_")) source = "Instagram";
    else source = "Internal";
  }

  /* -------- EXTERNAL ID / PHONE -------- */
  const externalId = senderInfo.external_id ?? stripPrefix(clientId);

  const phone =
    md.display_phone_number ?? // WhatsApp business
    (externalId.match(/^\d+$/) ? externalId : null);

  return { username, avatar, source, externalId, phone };
}

function buildRooms(chats, consultantId) {
  console.log("buildRooms", chats); // For debugging: log chat data
  const sourceAvatars = {
    Internal: "/avatars/internal.png",
    Telegram: "/avatars/telegram.png",
    "Telegram Mini-App": "/avatars/miniapp.png",
    Instagram: "/avatars/insta.png",
    Facebook: "/avatars/facebook.png",
    WhatsApp: "/avatars/whatsapp.png",
  };

  return chats.map((chat, idx) => {
    const pdEntry = chat.participants_display?.find((p) => p.client_id === chat.client_id_display) ?? chat.participants_display?.[0];

    const normalizedPd = normaliseParticipant(pdEntry?.sender_info, pdEntry?.client_id);
    console.log("chatelement", chat); // For debugging: log chat data
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
    const status_emoji = chat.status_emoji;
    const seen = chat.messages?.[chat.messages?.length - 1]?.read_by_display?.length > 0 || false;
    return {
      avatar: sourceAvatars[sourceName] || "/avatars/default.png",
      roomId: chat.chat_id,
      roomName:
        `${seen ? "" : "🔴"} ${status_emoji || ""} ${normalizedPd.username || client.id}` ||
        t("EmbeddedChat.chatFallback", { index: idx + 1 }),
      users: [clientUser, consultantUser],
      lastMessage,
      typingUsers: [],
      seen: seen,
      sourceName: sourceName,
      pdEntry: normalizedPd,
    };
  });
}

/* ── Filter metadata and chat data functionality ──────────────── */
async function fetchChatData(page = 0, filters = {}, search = {}) {
  if (!currentEntity.value) {
    console.warn('No entity specified in the route.');
    return;
  }

  // Create a unique request signature to prevent duplicates
  const requestSignature = JSON.stringify({ page, filters, search, entity: currentEntity.value });
  
  // Prevent duplicate requests only if request is currently in progress with same params
  if (isRequestInProgress.value && lastRequestParams.value === requestSignature) {
    console.log('Duplicate request prevented (same request in progress):', requestSignature);
    return;
  }

  // Set request state
  isLoading.value = true;
  isRoomsLoading.value = true;
  metadataLoading.value = true;
  isRequestInProgress.value = true;
  lastRequestParams.value = requestSignature;
  
  try {
    // First fetch metadata if not already loaded
    if (!filterMetadata.value) {
      const metadataResponse = await useNuxtApp().$api.get(`api/${currentPageName.value}/info`);
      console.log('Filter metadata response:', metadataResponse);
      filterMetadata.value = metadataResponse;
    }

    // Build URL with pagination and filters
    const params = new URLSearchParams();
    params.append('sort_by', 'updated_at');
    params.append('order', '-1');
    params.append('page', (page + 1).toString()); // API uses 1-based pagination
    params.append('page_size', (props.pageSize || pageSize.value).toString());
    
    // Add filters if any
    if (Object.keys(filters).length > 0) {
      params.append('filters', JSON.stringify(filters));
    }
    
    // Add search if any - simple format
    if (search?.q && search.q.trim()) {
      params.append('search', search.q.trim());
    }

    const url = `api/${currentPageName.value}/${currentEntity.value}/?${params.toString()}`;
    console.log('Fetching chat data from:', url);
    
    const response = await useNuxtApp().$api.get(url);
    
    // Process response data similar to MainContent
    let data = response.data?.data ? response.data.data : response.data;
    console.log('Chat data response:', response);
    console.log('Processed chat data:', data);
    
    // Validate and process data
    if (!Array.isArray(data)) {
      console.warn('Expected array data but got:', typeof data);
      data = data ? [data] : [];
    }
    
    // Update state
    chatData.value = data || [];
    tableDataOriginal.value = data || []; // Keep original for filtering
    totalRecords.value = response.data?.meta?.total_count || response.data?.meta?.total || response.total || data.length;
    currentPage.value = page;
    
    // Emit success event
    emit('data-loaded', {
      data: data,
      total: totalRecords.value,
      page: page,
      filters: filters,
      search: search
    });
    
    return response;
  } catch (error) {
    console.error('Error fetching chat data:', error);
    
    // Handle different error types
    if (error.response && error.response.status !== 404) {
      parseError(error);
    } else if (error.response?.status === 404) {
      console.warn('Chat data endpoint not found (404)');
      toast.add({
        severity: 'warn',
        summary: t('EmbeddedChat.notFound', 'Not Found'),
        detail: t('EmbeddedChat.noDataAvailable', 'No chat data available'),
        life: 3000
      });
    }
    
    // Reset state on error
    filterMetadata.value = null;
    chatData.value = [];
    tableDataOriginal.value = [];
    totalRecords.value = 0;
    
    return null;
  } finally {
    isLoading.value = false;
    isRoomsLoading.value = false;
    metadataLoading.value = false;
    isRequestInProgress.value = false;
    // Reset lastRequestParams after a short delay to allow duplicate detection during request
    setTimeout(() => {
      lastRequestParams.value = "";
    }, 100);
  }
}

// Create debounced versions to prevent rapid-fire requests
const debouncedRefreshChatList = debounce(async (resetPage = true) => {
  try {
    console.log('Debounced refresh with filters:', appliedFilters.value, 'search:', appliedSearch.value, 'resetPage:', resetPage);
    
    // Reset to page 0 only when filters change, not during pagination
    const pageToUse = resetPage ? 0 : currentPage.value;
    const response = await fetchChatData(pageToUse, appliedFilters.value, appliedSearch.value);
    
    if (response) {
      console.log('Chat response:', response);
      
      // Check if we got empty results with active filters
      const responseData = response.data || response;
      if (hasActiveFilters.value && (!responseData || responseData.length === 0)) {
        console.log('Empty filter results detected');
        toast.add({
          severity: 'info',
          summary: t('EmbeddedChat.noResultsFound', 'No Results Found'),
          detail: t('EmbeddedChat.noMatchingChats', 'No chats match your current filters'),
          life: 3000
        });
      }
      
      // Update current page if we reset
      if (resetPage) {
        currentPage.value = 0;
      }
      
      // Emit to parent for pagination and other metadata
      emit('refresh-chats', {
        data: responseData,
        meta: response.meta,
        filters: appliedFilters.value,
        search: appliedSearch.value,
        page: pageToUse,
        isEmpty: hasActiveFilters.value && (!responseData || responseData.length === 0)
      });
    }
    
  } catch (error) {
    console.error('Failed to refresh chat list with filters:', error);
    toast.add({
      severity: 'error',
      summary: 'Filter Error',
      detail: 'Failed to apply filters to chat list',
      life: 5000
    });
  }
}, 300); // 300ms debounce

async function onFiltersChanged(filters) {
  console.log('Filters changed:', filters);
  
  // Update applied filters immediately
  appliedFilters.value = filters;
  
  // Check if filters are empty - if so, clear filtered state
  if (Object.keys(filters).length === 0) {
    await clearFilters();
    return;
  }
  
  // Apply filters to the chat list with debouncing (reset to page 0)
  debouncedRefreshChatList(true);
}

// Function to clear filters and return to original data
async function clearFilters() {
  // Prevent duplicate clear operations
  if (!hasActiveFilters.value) {
    console.log('Already cleared, skipping clear operation');
    return;
  }
  
  appliedFilters.value = {};
  appliedSearch.value = {};
  
  // Reset to page 0 when clearing filters
  currentPage.value = 0;
  
  // Reload original data without filters
  await fetchChatData(0);
}

// Function to refresh chat list with filters and search (kept for backwards compatibility)
async function refreshChatList(resetPage = true) {
  // This function is now just a wrapper around the debounced version
  debouncedRefreshChatList(resetPage);
}

const currentRoomSource = computed(() => {
  return rooms.value.find((r) => r.roomId === activeRoomId.value)?.sourceName || "";
});

// Watch for route changes and reinitialize data
watch([currentGroup, currentEntity], () => {
  console.log('Route changed:', { group: currentGroup.value, entity: currentEntity.value });
  initializeChatData();
});

// Watch for chat data changes and build rooms
watch(
  chatRows,
  (rows) => {
    if (!rows.length) {
      // If we have active filters but no results, show empty state
      if (hasActiveFilters.value) {
        rooms.value = [];
        activeRoomId.value = null;
        return;
      }
      // Otherwise, just return without updating rooms
      return;
    }
    
    rooms.value = buildRooms(rows, currentUserId.value);

    // выбрать активную комнату, если ещё не выбрана
    if (!rooms.value.find((r) => r.roomId === activeRoomId.value)) {
      activeRoomId.value = rooms.value[0]?.roomId ?? null;
    }
  },
  { immediate: true }
);

// Watch for props changes that might affect data fetching
watch(() => props.pageSize, (newPageSize) => {
  if (newPageSize && newPageSize !== pageSize.value) {
    pageSize.value = newPageSize;
    fetchChatData(0, appliedFilters.value, appliedSearch.value);
  }
});
/* ── external events ───────────────────────────────────────── */
// $listen("new_message_arrived", (msg) => {
//   if (!msg || !messagesMap.value[activeRoomId.value]) return;
//   messagesMap.value[activeRoomId.value].push(msg);
// });

/* ── tidy up on unmount ───────────────────────────────────── */
onBeforeUnmount(() => {
  chatLogic.value?.destroy?.();
  if (typeof window !== "undefined") {
    window.removeEventListener("resize", updateWindowWidth);
  }
});
</script>

<style>
.vue-advanced-chat {
  box-shadow: none !important;
}
/* global stylesheet (or <style> block without "scoped") */
.vac-image-buttons .vac-button-download {
  display: none !important; /* hides the ⬇️ button everywhere */
}
</style>
<style scoped>
:deep(.vac-button-download) {
  display: none !important;
}

/* Custom slide-down animation similar to PrimeFlex */
.slide-down-enter-active {
  animation: slide-down-in 0.3s ease-out;
}

.slide-down-leave-active {
  animation: slide-down-out 0.3s ease-in;
}

@keyframes slide-down-in {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slide-down-out {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(-10px);
  }
}
</style>
