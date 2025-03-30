<template>
  <div
    class="flex flex-col h-[80vh] dark:bg-[#131415] bg-[#f8f9fa]"

  >
    <!-- Toast для уведомлений -->
    <Toast class="max-w-[18rem] md:max-w-full" />
    <!-- Сам чат -->
    <vue-advanced-chat
      auto-scroll='{
    "send": { "new": true, "newAfterScrollUp": true },
    "receive": { "new": true, "newAfterScrollUp": true }
  }'
      :height="isMobile ? '' : '100%'"
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
      :theme="colorMode?.preference"
      
    >
    <div slot="room-header-avatar">
        <div>
          <Avatar icon="pi pi-user" class="mr-2" size="large" style="background-color: #ece9fc; color: #2a1261" shape="circle" />
        </div>
      </div>
      <div slot="room-header-info">
        <div>
          <h2 class="font-bold max-w-[15rem] md:max-w-full truncate">User id: {{ user_id }}</h2>
          <!-- <p>Time left: {{ formatTime(countdown) }}</p> -->
        </div>
      </div>
    </vue-advanced-chat>


  </div>
</template>

<script setup>
import { ref, watch, computed } from "vue";
import { defineEmits } from "vue";
import { register } from "vue-advanced-chat";
const colorMode = useColorMode();
register();
const { rooms } = useHeaderState();
// PrimeVue
import Toast from "primevue/toast";

// Подключаем наш composable
import { useChatLogic } from "~/composables/useChatLogic";

let props = defineProps({
  id: {
    type: String,
  },
  user_id: {
    type: String,
  },
});

const emit = defineEmits(["close-chat"]);

// Единственная функция, которую удобнее оставить в этом компоненте,
// так как она связана с событием на родителя.
function closeChat() {
  emit("close-chat");
}

const { $event, $listen } = useNuxtApp();


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

// Reactive references for chat logic
let chatLogicRefs = ref(null);

// Watch for `id` and initialize `useChatLogic` when it's available
watch(
  () => props.id,
  (newId) => {
    if (newId) {
      chatLogicRefs.value = useChatLogic({ isTelegram: props.isTelegram, chat_id: newId });
    }
  },
  { immediate: true }
);

// Access chat logic refs only after initialization
const t = computed(() => chatLogicRefs.value?.t);
const isMobile = computed(() => chatLogicRefs.value?.isMobile);
const isIphone = computed(() => chatLogicRefs.value?.isIphone);
const currentUserId = computed(() => chatLogicRefs.value?.currentUserId);
const activeRoomId = computed(() => chatLogicRefs.value?.activeRoomId);
const messages = computed(() => chatLogicRefs.value?.messages);
const messagesLoaded = computed(() => chatLogicRefs.value?.messagesLoaded);
const choiceOptions = computed(() => chatLogicRefs.value?.choiceOptions);
const isChoiceStrict = computed(() => chatLogicRefs.value?.isChoiceStrict);
const timerExpired = computed(() => chatLogicRefs.value?.timerExpired);
const textMessagesJson = computed(() => chatLogicRefs.value?.textMessagesJson);
const updateMessages = computed(() => chatLogicRefs.value?.updateMessages);
const fetchMessages = computed(() => chatLogicRefs.value?.fetchMessages);
const sendMessage = computed(() => chatLogicRefs.value?.sendMessage);
const toggleChatMode = computed(() => chatLogicRefs.value?.toggleChatMode);
const handleChoiceClick = computed(() => chatLogicRefs.value?.handleChoiceClick);
const reloadPage = computed(() => chatLogicRefs.value?.reloadPage);
const refreshChat = computed(() => chatLogicRefs.value?.refreshChat);

$listen("new_message_arrived", async (message) => {
  console.log("new_message:", message);
  if (message) {
    updateMessages.value?.(message);
  }
});

</script>

<style scoped>
/* Перенесите нужные стили из вашего SFC */
.iphone-margin {
  margin-bottom: 20px;
  padding-bottom: env(safe-area-inset-bottom);
}
</style>

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
