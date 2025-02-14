<template>
  <div class="w-full flex items-center justify-between">
    <div class="flex flex-row items-center gap-2">
      <!-- Left Section: Title -->
      <h2 class="font-bold">DenisDrive</h2>
        <!-- Toggle Container -->
        <div class="flex items-center gap-2 bg-light dark:bg-gray-300 px-4  py-1 md:py-2 rounded-lg shadow ml-4">
          <span class="text-lg font-medium">{{ t("chatMode.manual") }}</span>
          
          <!-- PrimeVue InputSwitch with Tailwind classes -->
          <InputSwitch
            v-model="isAutoMode" 
            :class="inputSwitchClasses"
          />

          <span class="text-lg font-medium">{{ t("chatMode.auto") }}</span>
        </div>
    </div>
    <!-- Right Section: Toggle + Menu Button -->
    <div class="flex items-center gap-4">
      <!-- Button to open the menu (TieredMenu) -->
      <Button icon="pi pi-bars" class="p-button-rounded p-button-text" @click="$refs.menu.toggle($event)" />

      <!-- TieredMenu as a popover with Refresh/Close actions -->
      <TieredMenu :model="menuItems" popup ref="menu" />
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, computed } from "vue";
import { useI18n } from "vue-i18n";
import Button from "primevue/button";
import InputSwitch from "primevue/inputswitch";

const { isAutoMode } =  useChatState()

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

});

const emit = defineEmits(["toggle-chat-mode"]);

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
    label: t("closeChat"),
    icon: "pi pi-times",
    command: () => props.closeChat(),
    visible: !props.isTelegram,
  },
]);


watch(isAutoMode, (newValue) => {
  console.log("Manual mode changed to:", newValue);
  emit("toggle-chat-mode", newValue);
});

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
</script>

<style scoped>
/* If you need to override default PrimeVue switch colors */
.p-inputswitch-slider {
  /* Example: default slider color */
  background-color: #d1d5db; /* Tailwind gray-300 */
}

.p-inputswitch-checked .p-inputswitch-slider {
  /* Example: toggled (Auto) slider color */
  background-color: #4caf50; /* or your brand color */
}
</style>
