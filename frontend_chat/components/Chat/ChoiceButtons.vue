<template>
  <div
    class="buttons-background py-4 flex flex-row w-full justify-around items-center flex-wrap gap-4 max-h-[20vh] overflow-y-auto"
  >
    <Button
      v-for="(option, index) in choiceOptions"
      :key="index"
      :label="Array.isArray(option) ? option[0] : option"
      class="p-button-outlined min-w-[160px]"
      @click="() => handleChoiceClick(Array.isArray(option) ? option[1] : option)"
    />
  </div>
</template>

<script setup>
  import Button from "primevue/button";
  import { watch } from "vue";

  const props = defineProps({
    choiceOptions: {
      type: Array,
      default: () => [],
    },
    handleChoiceClick: {
      type: Function,
      required: true,
    },
  });

  watch(
    () => props.choiceOptions,
    (newVal) => {
      console.log("ChoiceButtons: choiceOptions changed", newVal);
    }
  );
</script>

<style>
  .buttons-background {
    font-family: "Quicksand", sans-serif;
    overflow: hidden;
    background-color: #f8f9fa;
  }

  @media (prefers-color-scheme: dark) {
    .buttons-background {
      background-color: #131415 !important;
    }
  }
</style>
