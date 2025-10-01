<template>
  <div class="p-3">
    <InputGroup>
      <InputGroupAddon>
        <i v-if="!isLoading" class="pi pi-search"></i>
        <i v-else class="pi pi-spin pi-spinner"></i>
      </InputGroupAddon>
      <InputText
        v-model="searchQuery"
        :placeholder="placeholder"
        class="w-full"
        :disabled="disabled"
        @input="onSearchInput"
        @keyup.enter="onSearchEnter"
      />
      <InputGroupAddon>
        <Button
          :icon="isLoading ? 'pi pi-spin pi-spinner' : 'pi pi-times'"
          text
          size="small"
          class="p-1"
          @click="clearSearch"
          :disabled="!searchQuery || isLoading"
          :loading="isLoading && !searchQuery"
        />
      </InputGroupAddon>
    </InputGroup>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue';
import { debounce } from 'lodash';
import InputGroup from 'primevue/inputgroup';
import InputGroupAddon from 'primevue/inputgroupaddon';
import InputText from 'primevue/inputtext';
import Button from 'primevue/button';

// Props
const props = defineProps({
  placeholder: {
    type: String,
    default: 'Search...'
  },
  debounceTime: {
    type: Number,
    default: 300
  },
  modelValue: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  loadingText: {
    type: String,
    default: 'Searching...'
  }
});

// Emits
const emit = defineEmits(['update:modelValue', 'search', 'clear', 'search-enter']);

// Local state
const searchQuery = ref(props.modelValue);
const isLoading = ref(false);

// Watch for loading prop changes
watch(() => props.loading, (newLoading) => {
  isLoading.value = newLoading;
});

// Debounced search function
const debouncedSearch = debounce((searchTerm) => {
  isLoading.value = true;
  emit('search', searchTerm);
}, props.debounceTime);

// Input handler
const onSearchInput = (event) => {
  const value = event.target.value;
  searchQuery.value = value;
  emit('update:modelValue', value);
  
  if (!props.disabled) {
    debouncedSearch(value);
  }
};

// Enter key handler for immediate search
const onSearchEnter = () => {
  if (!props.disabled && !isLoading.value) {
    // Cancel any pending debounced search and search immediately
    debouncedSearch.cancel();
    isLoading.value = true;
    emit('search-enter', searchQuery.value);
    emit('search', searchQuery.value);
  }
};

// Clear search
const clearSearch = () => {
  if (isLoading.value) return; // Prevent clearing during search
  
  searchQuery.value = '';
  emit('update:modelValue', '');
  emit('clear');
  
  if (!props.disabled) {
    // Cancel any pending debounced search
    debouncedSearch.cancel();
    isLoading.value = false;
    emit('search', '');
  }
};

// Method to stop loading (can be called from parent)
const stopLoading = () => {
  isLoading.value = false;
};

// Expose method to parent component
defineExpose({
  stopLoading
});

// Watch for external changes to modelValue
watch(() => props.modelValue, (newValue) => {
  searchQuery.value = newValue;
});

// Cleanup debounced function on unmount
onBeforeUnmount(() => {
  debouncedSearch?.cancel?.();
});
</script>

<style scoped>
/* Add any search-specific styling here */
</style>