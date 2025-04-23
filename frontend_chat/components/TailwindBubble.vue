<!-- TailwindBubble.vue -->
<template>
  <div>
    <!-- If the message is from the current user, right-aligned bubble -->
    <div v-if="isFromCurrentUser" class="flex justify-end mb-1">
      <div class="bg-blue-500 text-white px-3 py-2 rounded-l-lg rounded-br-lg max-w-xs break-words shadow">
        <p class="text-sm whitespace-pre-line">{{ message.content }}</p>
      </div>
    </div>

    <!-- Otherwise, left-aligned bubble -->
    <div v-else class="flex justify-start mb-1">
      <div class="bg-gray-200 text-gray-900 px-3 py-2 rounded-r-lg rounded-bl-lg max-w-xs break-words shadow">
        <p class="text-sm whitespace-pre-line">{{ message.content }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
  import { computed } from "vue";

  let props = defineProps({
    message: {
      type: Object,
      required: true,
    },
    currentUserId: {
      type: String,
      required: true,
    },
  });

  const isFromCurrentUser = computed(() => {
    return props.message.senderId === props.currentUserId;
  });
</script>
