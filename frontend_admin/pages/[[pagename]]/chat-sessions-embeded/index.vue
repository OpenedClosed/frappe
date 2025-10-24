<template>
  <div class="p-4">
    <EmbeddedChat 
      :entity="'chat_sessions'"
      :group="'chats'"
    />
  </div>
</template>

<script setup lang="ts">
import EmbeddedChat from "~/components/AdminChat/EmbeddedChat.vue";
</script>
