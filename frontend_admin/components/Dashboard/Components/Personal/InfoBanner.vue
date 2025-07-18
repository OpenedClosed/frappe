<template>
  <div v-if="visible" class="flex items-start relative mb-2">
    <p
      class="flex text-[16px] font-semibold text-blue-700 bg-blue-50 border-l-4 border-blue-400 px-4 py-2 rounded shadow-sm justify-between items-center gap-2"
    >
      <slot />
      <Button icon="pi pi-times" class="p-2 ml-2 mt-1" @click="close" size="small" aria-label="Close" />
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted, defineProps } from "vue";

const props = defineProps({
  infoKey: { type: String, required: true }
});

const visible = ref(false);

onMounted(() => {
  visible.value = localStorage.getItem(props.infoKey) !== "1";
});

function close() {
  visible.value = false;
  localStorage.setItem(props.infoKey, "1");
}
</script>