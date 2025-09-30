<template>
  <div class="flex flex-col flex-1 min-h-0 p-4 rounded border bg-white dark:bg-secondaryDark shadow-sm">
    <h1 class="text-2xl font-bold mb-4">{{ t("SupportPage.title") }}</h1>
    <Button v-if="isMobile" :label="t('SupportPage.openSupportChat')" icon="pi pi-comments" @click="showDialog = true" class="mb-4 w-full md:w-auto" />
    <iframe v-else :src="chatUrl" style="flex: 1; border: none"></iframe>
    <Dialog v-if="isMobile" v-model:visible="showDialog" :modal="true" :draggable="false" :closable="true" :style="dialogStyle" :breakpoints="{ '640px': '100vw' }" :maximizable="true" :fullScreen="isMobile" :header="t('SupportPage.chatHeader')">
      <iframe :src="chatUrl" style="width:100%;height:80vh;border:none;"></iframe>
    </Dialog>
  </div>
</template>

<script setup>
import { onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
const { t } = useI18n();
// Add any necessary logic here (e.g., fetching support data)
const isLocalhost = window.location.hostname === "localhost";
const { currentFrontendUrl } = useURLState();
const chatUrl = isLocalhost ? `${currentFrontendUrl.value}/chats/telegram-chat` : `${currentFrontendUrl.value}/chats/telegram-chat`;

const showDialog = ref(false);
const isMobile = ref(false);
const dialogStyle = computed(() => (isMobile.value ? { width: '100vw', height: '100vh', padding: 0 } : { width: '700px' }));

onMounted(() => {
  isMobile.value = window.innerWidth <= 768;
  window.addEventListener('resize', () => {
    isMobile.value = window.innerWidth <= 768;
  });
});
onBeforeUnmount(() => {
  window.removeEventListener('resize', () => {
    isMobile.value = window.innerWidth <= 768;
  });
});
</script>

<style scoped></style>
