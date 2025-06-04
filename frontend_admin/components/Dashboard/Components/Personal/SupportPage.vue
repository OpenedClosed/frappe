<template>
  <div class="flex flex-col flex-1 min-h-0 p-4 rounded border bg-white dark:bg-secondaryDark shadow-sm">
    <h1 class="text-2xl font-bold mb-4">{{ t("SupportPage.title") }}</h1>
    <iframe :src="chatUrl" style="flex: 1; border: none"></iframe>
  </div>
</template>

<script setup>
import { useI18n } from "vue-i18n";
const { t } = useI18n();
// Add any necessary logic here (e.g., fetching support data)
const isLocalhost = window.location.hostname === "localhost";
const { currentFrontendUrl } = useURLState();
const chatUrl = isLocalhost ? `${currentFrontendUrl.value}/chats/telegram-chat` : `${currentFrontendUrl.value}/chats/telegram-chat`;
</script>

<style scoped></style>
