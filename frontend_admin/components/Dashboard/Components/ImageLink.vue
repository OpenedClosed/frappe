<script setup>
import { ref } from 'vue';

const props = defineProps({
  fileLink: {
    type: String,
    required: true
  }
});

const hasError = ref(false);

function handleError() {
  hasError.value = true;
}
</script>

<template>
  <div>
    <!-- Display the image if it loads successfully -->
    <img
      v-if="!hasError"
      :src="fileLink"
      @error="handleError"
      alt="Image"
      class="max-w-xs border rounded"
    />
    <!-- Fallback: display a clickable link if the image fails to load -->
    <a
      v-else
      :href="fileLink"
      class="text-blue-500 underline"
      target="_blank"
      rel="noopener noreferrer"
    >
    {{fileLink}}
    </a>
  </div>
</template>
