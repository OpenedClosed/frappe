<template>
  <div
    class="flex flex-col dark:bg-[#131415] bg-[#f8f9fa]"
    :class="{
      '': isTelegram,
      ' max-h-full h-svh': !isTelegram,
    }"
    :style="isTelegram ? 'height: var(--tg-viewport-stable-height)' : ''"
  >
    <!-- Toast для уведомлений -->
    <Toast class="max-w-[18rem] md:max-w-full" />
    <!-- Сам чат -->
    <vue-advanced-chat
      :class="[{ 'iphone-margin': showIphoneMargin }]"
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
      @focusin="handleFocus($event, true)"
      :selected-room-id="activeRoomId"
      @focusout="handleFocus($event, false)"
      :single-room="true"
      :show-audio="false"
      :show-files="false"
      :show-footer="!isChoiceStrict && !timerExpired"
      :text-messages="textMessagesJson"
      :theme="colorMode.preference"
      @send-message="sendMessage($event.detail[0])"
      @fetch-messages="fetchMessages($event.detail[0])"
    >
      <div slot="room-header-info" class="w-full">
        <ChatHeader
          :isTelegram="isTelegram"
          :refreshChat="refreshChat"
          :closeChat="closeChat"
          :rooms="rooms"
          :currentUserId="currentUserId"
          @toggle-chat-mode="toggleChatMode($event)"
        />
      </div>
    </vue-advanced-chat>

    <!-- Кнопки выбора (если есть варианты и таймер не истёк) -->
    <ChoiceButtons
      v-if="choiceOptions.length && !timerExpired"
      :choiceOptions="choiceOptions"
      :handleChoiceClick="handleChoiceClick"
    />
    <CommandsSection />

    <!-- Кнопка "Начать заново" (если таймер истёк) -->
    <ReloadButton v-if="timerExpired" :reloadLabel="t('chatAgain')" :reloadPage="reloadPage" />
  </div>
</template>

<script setup>
  import { defineEmits } from "vue";
  import { register } from "vue-advanced-chat";
  const colorMode = useColorMode();
  register();
  const { rooms } = useHeaderState();
  // PrimeVue
  import Toast from "primevue/toast";

  // Локальные компоненты
  import ChatHeader from "~/components/Chat/ChatHeader.vue";
  import ChoiceButtons from "~/components/Chat/ChoiceButtons.vue";
  import CommandsSection from "~/components/Chat/CommandsSection.vue";
  import ReloadButton from "~/components/Chat/ReloadButton.vue";

  // Подключаем наш composable
  import { useChatLogic } from "~/composables/useChatLogic";

  const props = defineProps({
    isTelegram: {
      type: Boolean,
      default: false,
    },
  });

  const emit = defineEmits(["close-chat"]);

  // Единственная функция, которую удобнее оставить в этом компоненте,
  // так как она связана с событием на родителя.
  function closeChat() {
    emit("close-chat");
  }

  const { $event, $listen } = useNuxtApp();
  $listen("command-clicked", async (command) => {
    handleChoiceClick(command);
  });

  $listen("new_message_arrived", async (message) => {
    console.log("new_message:", message);
    if (message) {
      updateMessages(message);
    }
  });
  $listen("choice_options_arrived", async (options) => {
    // console.log("choice_options:", options);
    if (options) {
      choiceOptions.value = options;
    }
  });

  const isTextareaFocused = ref(false);

  function handleFocus(e, value) {
    const el = e.target;
    if (el?.classList?.contains("vac-textarea")) {
      isTextareaFocused.value = value;
    }
  }

  const showIphoneMargin = computed(() => isIphone.value && !isTextareaFocused.value);
  // Получаем из composable все нужные refs и методы
  // (кроме closeChat - его оставляем здесь локально)
  const {
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
    updateMessages,
    fetchMessages,
    sendMessage,
    toggleChatMode,
    handleChoiceClick,
    reloadPage,
    refreshChat,
  } = useChatLogic({ isTelegram: props.isTelegram });
</script>

<style scoped>
  /* Перенесите нужные стили из вашего SFC */
  /* keeps some air for the iPhone safe‑area */
  .iphone-margin {
    margin-bottom: 20px;
    padding-bottom: env(safe-area-inset-bottom);
  }

  /* keyboard open → the input (a descendant) is focused */
  .iphone-margin:focus-within {
    margin-bottom: 0; /* or whatever value you prefer */
    padding-bottom: 0;
  }
</style>

<style>
  body {
    font-family: "Quicksand", sans-serif;
    overflow: hidden;
    background-color: #f8f9fa;
  }

  @media (prefers-color-scheme: dark) {
    body {
      background-color: #121212 !important;
    }
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
