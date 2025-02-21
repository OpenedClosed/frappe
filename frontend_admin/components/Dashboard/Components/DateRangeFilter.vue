<template>
    <div class="flex flex-col gap-4 py-4  items-center md:items-start">
      <span class="font-bold h-10 flex flex-col justify-end pb-2">Фильтр по диапазону дат:</span>
  
      <!-- Выбор диапазона дат -->
      <div class="flex items-center gap-4">
        <Calendar :disabled="disabled" v-model="dates" selectionMode="range" :manualInput="false" placeholder="Выбор дат"
          dateFormat="dd.mm.yy" :minDate="minDate" :maxDate="maxDate" showIcon class="w-[15rem]" />
  
        <!-- Очистить диапазон дат -->
        <Button  icon="pi pi-times" class="p-button-rounded p-button-outlined p-button-sm" @click="clearDateFilter"
          :disabled="!dates || disabled" aria-label="Очистить диапазон дат" />
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, watch } from 'vue';
  
  const props = defineProps({
    disabled: Boolean,
    minDate: Date,
    maxDate: Date,
    dates: Array, // Dates as an array for range selection
  });
  
  const emit = defineEmits(['update:dates', 'clearDateFilter']);
  
  const dates = ref(props.dates);

  // Watch props.dates to ensure updates are reflected in the component
  watch(
    () => props.dates,
    (newValue) => {
      dates.value = newValue; // Update internal dates when prop changes
    },
    { immediate: true } // Trigger immediately to apply initial prop value
  );
  
  watch(dates, (newValue) => {
    emit('update:dates', newValue);
  });
  
  const clearDateFilter = () => {
    dates.value = null;
    emit('clearDateFilter');
  };
  
  defineExpose({
    clearDateFilter,
  });
  </script>
  
  <style scoped>
  /* Добавьте любые специфические стили для компонента DateRangeFilter здесь */
  </style>
  