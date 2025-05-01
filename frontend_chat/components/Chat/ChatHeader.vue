<template>
  <div class="w-full flex items-center justify-between">
    <!-- {{ rooms }} -->
    <div class="flex flex-row items-center gap-2">
      <!-- Left Section: Title --> 
      <!-- {{ currentUrl+botHeaderData.avatar }} -->
      <div class="min-w-[3rem] w-12 h-12 flex-shrink-0">
        <Avatar
          :image="currentUrl + botHeaderData?.avatar || ' '"
          class="mr-2 w-full h-full object-cover"
          size="large"
          shape="circle"
        />
      </div>
      <div class="flex flex-row items-center gap-2">
        <h2 class="font-bold hidden md:block">{{ botHeaderData?.app_name || " " }}</h2>
        <h2 class="font-bold max-w-[100px] block md:hidden truncate text-nowrap">
          {{ botHeaderData?.app_name || " " }}
        </h2>
        <p v-if="typingUserNames.length" class="animate-pulse hidden md:block">is typing...</p>
        <p v-if="typingUserNames.length" class="animate-pulse block md:hidden">...</p>
      </div>
      <!-- Toggle Container -->
      <div class="flex items-center gap-2 bg-light dark:bg-gray-700 px-4 py-[2px] md:py-[2px] rounded-lg shadow ml-4">
        <span class="text-2xl font-medium">🧑‍💻</span>

        <!-- PrimeVue InputSwitch with Tailwind classes -->
        <InputSwitch v-model="isAutoMode" :class="inputSwitchClasses" @change="changeMode" />

        <span class="text-2xl font-medium">🚀</span>
      </div>
    </div>
    <!-- Right Section: Toggle + Menu Button -->
    <div class="flex items-center gap-1">
      <!-- Button to open the menu (TieredMenu) -->
      <Button icon="pi pi-bars" class="p-button-rounded p-button-text p-button-sm" @click="$refs.menu.toggle($event)" />
      <Button v-if="!isTelegram" icon="pi pi-times" class="p-button-rounded p-button-text p-button-sm" @click="props.closeChat()" />

      <!-- TieredMenu as a popover with Refresh/Close actions -->
      <TieredMenu ref="menu" :model="menuItems" popup style="z-index: 10000" />
    </div>
  </div>
</template>

<script setup>
  import { defineProps, defineEmits, computed } from "vue";
  import { useI18n } from "vue-i18n";
  import Button from "primevue/button";
  import InputSwitch from "primevue/inputswitch";
  const { currentUrl } = useURLState();
  const { rooms, botHeaderData } = useHeaderState();

  const { isAutoMode } = useChatState();

  const { t } = useI18n();

  const props = defineProps({
    refreshChat: {
      type: Function,
      required: true,
    },
    closeChat: {
      type: Function,
      required: true,
    },
    isTelegram: {
      type: Boolean,
      default: false,
    },
    currentUserId: {
      required: true,
    },
  });

  // Computed property to get typing usernames excluding the current user
  const typingUserNames = computed(() => {
    // Here we assume you are looking at the first room; adjust if handling multiple rooms.
    const room = rooms.value[0];
    if (!room || !room.typingUsers) {
      return [];
    }
    return room.typingUsers.filter((user) => user.id !== props.currentUserId).map((user) => user.username);
  });
  const emit = defineEmits(["toggle-chat-mode"]);
  const { $event, $listen } = useNuxtApp();
  const menuItems = computed(() => [
    // {
    //   separator: true, // draws a line
    // },
    {
      label: t("newChat"),
      icon: "pi pi-replay",
      command: () => props.refreshChat(),
    },
    {
      label: t("showCommands"),
      icon: "pi pi-send",
      command: () => $event("show-commands"),
    },
    // {
    //   label: t("closeChat"),
    //   icon: "pi pi-times",
    //   command: () => props.closeChat(),
    //   visible: !props.isTelegram,
    // },
  ]);

  function changeMode() {
    console.log("Manual mode changed to:", isAutoMode.value);
    emit("toggle-chat-mode", isAutoMode.value);
  }

  /**
   * We want 'autoMode' to be the reverse of 'isAutoMode':
   *   - autoMode = true  => isAutoMode = false
   *   - autoMode = false => isAutoMode = true
   */
  const autoMode = computed({
    get() {
      return isAutoMode.value;
    },
    set(value) {
      // When user toggles, emit the updated "manual" state
      // value=true => auto => manual=false
      emit("toggle-chat-mode", !value);
    },
  });

  // Optional: some Tailwind classes for your InputSwitch
  const inputSwitchClasses = computed(() => [
    // You can include any custom Tailwind classes here
    // e.g. 'border-2 border-blue-500 hover:bg-blue-100'
  ]);

  const headerData = await useAsyncData("headerData", getHeaderData);

  if (headerData.data) {
    if (headerData.data.value) {
      setData(headerData.data.value);
    }
  }
  function setData(data) {
    if (data) {
      console.log("headerData data= ", data);
      botHeaderData.value = data;
    }
  }

  async function getHeaderData() {
    let responseData;
    await useNuxtApp()
      .$api.get(`api/knowledge/bot_info`)
      .then((response) => {
        responseData = response.data;
        console.log("header responseData= ", responseData);
      })
      .catch((err) => {
        if (err.response) {
          // //console.log(err.response.data)
        }
      });
    return responseData;
  }
</script>

<style scoped>
  /* If you need to override default PrimeVue switch colors */
  .p-inputswitch-slider {
    /* Example: default slider color */
    background-color: #d1d5db;
    /* Tailwind gray-300 */
  }

  .p-inputswitch-checked .p-inputswitch-slider {
    /* Example: toggled (Auto) slider color */
    background-color: #4caf50;
    /* or your brand color */
  }
</style>
