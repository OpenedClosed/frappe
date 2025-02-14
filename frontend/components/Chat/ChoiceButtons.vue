<template>
    <div
      class="py-4 flex flex-row w-full justify-around items-center flex-wrap gap-4 max-h-[20vh] overflow-y-auto"
    >
      <Button
        v-for="option in choiceOptions"
        :key="option"
        :label="option"
        class="p-button-outlined min-w-[160px]"
        @click="handleChoiceClick(option)"
      />
    </div>
  </template>
  
  <script setup>
  import Button from "primevue/button";
  
  const props = defineProps({
    choiceOptions: {
      type: Array,
      default: () => []
    },
    handleChoiceClick: {
      type: Function,
      required: true
    }
  });
  </script>
    