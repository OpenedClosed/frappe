<template>
  <!-- Filter Trigger Button -->
  <Transition name="filter-trigger" appear>
    <Button
      text
      size="small"
      @click="showFilterDialog = true"
      class="flex flex-row items-center gap-1 p-2 min-h-[2.5rem] rounded-md sm:p-3 touch-manipulation"
    >
      <Transition name="icon-rotate" mode="out-in">
        <i :key="activeFilterCount" class="pi pi-filter text-sm sm:text-base"></i>
      </Transition>
      <Transition name="badge-bounce" mode="out-in">
        <Badge 
          v-if="activeFilterCount > 0" 
          :key="activeFilterCount"
          :value="activeFilterCount.toString()" 
          severity="info" 
          class="text-xs"
        />
      </Transition>
    </Button>
  </Transition>

  <!-- Filter Dialog -->
  <Dialog
    v-model:visible="showFilterDialog"
    modal
    :style="{ width: '95vw', maxWidth: '900px' }"
    class="w-[95vw] max-w-[900px] sm:w-[90vw] md:w-[85vw] lg:w-[900px]"
  >
    <template #header>
      <div class="flex items-center justify-center gap-2 sm:gap-3 w-full p-3 sm:p-4">
        <!-- Status Icon -->
        <div class="flex items-center justify-center w-6 h-6 sm:w-8 sm:h-8 rounded-full hidden sm:flex" :class="headerIconBackgroundClasses">
          <i :class="headerStatusIconClasses" class="text-xs sm:text-sm"></i>
        </div>

        <!-- Header Content -->
        <div class="flex flex-col gap-1 flex-1 min-w-0">
          <div class="flex flex-col sm:flex-row items-center gap-1 sm:gap-2">
            <span class="text-sm sm:text-base font-semibold truncate flex items-center justify-center" :class="headerStatusTextClasses">
              {{ headerTitle }}
            </span>
            <span
              v-if="hasAnyActiveFilters() && !hasEmptyResults"
              class="text-xs px-2 py-1 rounded-full flex justify-center items-center"
              :class="headerBadgeClasses"
            >
              {{ resultsCount }} {{ $t("ChatFilterPanel.results", "results") }},
              <!-- Filter Count Badge -->
              <div
                v-if="activeFilterCount > 0"
                class="justify-center items-center text-xs bg-blue-100 dark:bg-blue-800/50 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-full whitespace-nowrap flex-shrink-0"
              >
                {{ activeFilterCount }} {{ $t("filters.activeCount", "active") }}
              </div>
            </span>
          </div>
          <span class="text-xs text-gray-600 dark:text-gray-400 flex justify-center sm:justify-start" :class="headerSubtitleClasses">
            {{ headerSubtitle }}
          </span>
        </div>
      </div>
    </template>
    <div v-if="metadata" class="rounded-lg overflow-hidden p-3 sm:p-4" :class="containerClasses">
      <!-- Main Filter Content -->
      <div class="">
        <!-- Filters Section -->
        <div class="space-y-4 sm:space-y-6">
          <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">{{ $t("filters.title", "Filters") }}</h3>

          <!-- Channel Filter -->
          <div class="space-y-2 sm:space-y-3" v-if="filterConfig.channel">
            <div class="flex items-center justify-between">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ getFilterTitle(filterConfig.channel) }}</label>
              <Button
                @click="clearChannelFilter"
                icon="pi pi-times"
                size="small"
                text
                rounded
                severity="secondary"
                :disabled="selectedFilters.channel.length === 0"
                class="w-6 h-6 p-1 text-xs touch-manipulation filter-clear-button"
                :class="{ 'opacity-40 cursor-not-allowed': selectedFilters.channel.length === 0 }"
                :aria-label="$t('filters.actions.clearChannel', 'Очистить каналы')"
              />
            </div>
            <MultiSelect
              v-model="selectedFilters.channel"
              :options="getFilterChoices(filterConfig.channel)"
              optionLabel="title"
              optionValue="value"
              :placeholder="$t('filters.channel.placeholder', 'Select channels')"
              :maxSelectedLabels="3"
              class="w-full text-sm sm:text-base"
            />
          </div>

          <!-- Date Range Filter -->
          <div class="space-y-2 sm:space-y-3" v-if="filterConfig.updated">
            <div class="flex items-center justify-between">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ getFilterTitle(filterConfig.updated) }}</label>
              <Button
                @click="clearDateFilter"
                icon="pi pi-times"
                size="small"
                text
                rounded
                severity="secondary"
                :disabled="!selectedFilters.dateRange"
                class="w-6 h-6 p-1 text-xs touch-manipulation filter-clear-button"
                :class="{ 'opacity-40 cursor-not-allowed': !selectedFilters.dateRange }"
                :aria-label="$t('filters.actions.clearDate', 'Очистить даты')"
              />
            </div>
            <div class="space-y-3">
              <Calendar
                v-model="selectedFilters.dateRange"
                selectionMode="range"
                :placeholder="$t('filters.date.placeholder', 'Select date range')"
                dateFormat="dd/mm/yy"
                class="w-full text-sm sm:text-base"
              />
              <div class="flex flex-col sm:flex-row gap-2 sm:gap-3">
                <TransitionGroup name="preset-buttons" tag="div" class="flex flex-col sm:flex-row gap-2 sm:gap-3">
                  <Button
                    v-for="preset in datePresets"
                    :key="preset.key"
                    @click="applyDatePreset(preset)"
                    :label="preset.label"
                    size="small"
                    outlined
                    class="text-xs sm:text-sm px-3 py-2 rounded-md touch-manipulation"
                  />
                  <!-- <Button
                    key="clear-date"
                    @click="clearDateFilter"
                    :label="$t('filters.clear', 'Clear')"
                    size="small"
                    severity="secondary"
                    class="text-xs sm:text-sm px-3 py-2 rounded-md touch-manipulation"
                  /> -->
                </TransitionGroup>
              </div>
            </div>
          </div>

          <!-- Status Filter (Answer status) -->
          <div class="space-y-2 sm:space-y-3" v-if="filterConfig.status">
            <div class="flex items-center justify-between">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ getFilterTitle(filterConfig.status) }}</label>
              <Button
                @click="clearStatusFilter"
                icon="pi pi-times"
                size="small"
                text
                rounded
                severity="secondary"
                :disabled="selectedFilters.status.length === 0"
                class="w-6 h-6 p-1 text-xs touch-manipulation filter-clear-button"
                :class="{ 'opacity-40 cursor-not-allowed': selectedFilters.status.length === 0 }"
                :aria-label="$t('filters.actions.clearStatus', 'Очистить статусы')"
              />
            </div>
            <div class="space-y-2">
              <div
                v-for="option in getStatusFilterOptions()"
                :key="option.value"
                class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors touch-manipulation"
              >
                <Checkbox
                  v-model="selectedFilters.status"
                  :inputId="'status_' + option.value"
                  :value="option.value"
                  class="flex-shrink-0"
                />
                <label :for="'status_' + option.value" class="text-sm sm:text-base cursor-pointer flex-1 select-none">{{
                  option.title
                }}</label>
              </div>
            </div>
          </div>

          <!-- Client Type Filter -->
          <div class="space-y-2 sm:space-y-3" v-if="filterConfig.client_type">
            <div class="flex items-center justify-between">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ getFilterTitle(filterConfig.client_type) }}</label>
              <Button
                @click="clearClientTypeFilter"
                icon="pi pi-times"
                size="small"
                text
                rounded
                severity="secondary"
                :disabled="selectedFilters.client_type.length === 0"
                class="w-6 h-6 p-1 text-xs touch-manipulation filter-clear-button"
                :class="{ 'opacity-40 cursor-not-allowed': selectedFilters.client_type.length === 0 }"
                :aria-label="$t('filters.actions.clearClientType', 'Очистить типы клиентов')"
              />
            </div>
            <div class="space-y-2">
              <div
                v-for="option in getFilterChoices(filterConfig.client_type)"
                :key="option.value"
                class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors touch-manipulation"
              >
                <Checkbox
                  v-model="selectedFilters.client_type"
                  :inputId="'client_type_' + option.value"
                  :value="option.value"
                  class="flex-shrink-0"
                />
                <label :for="'client_type_' + option.value" class="text-sm sm:text-base cursor-pointer flex-1 select-none">{{
                  option.title
                }}</label>
              </div>
            </div>
          </div>
        </div>

        <!-- Debug: Show current filter state -->
        <!-- <div v-if="showDebug" class="mt-6 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <h4 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Debug: Filter State & localStorage</h4>
          <div class="space-y-3">
            <div>
              <h5 class="text-xs font-medium text-gray-500 mb-1">Current Filters:</h5>
              <pre class="text-xs bg-white dark:bg-gray-900 p-3 rounded border overflow-x-auto">{{ JSON.stringify({ selectedFilters }, null, 2) }}</pre>
            </div>
            <div>
              <h5 class="text-xs font-medium text-gray-500 mb-1">localStorage State:</h5>
              <pre class="text-xs bg-white dark:bg-gray-900 p-3 rounded border overflow-x-auto">{{ JSON.stringify(loadFilterState(), null, 2) }}</pre>
            </div>
            <Transition name="debug-buttons" appear>
              <div class="flex gap-2">
                <Transition name="button-slide" appear :delay="100">
                  <Button 
                    @click="clearStoredState" 
                    label="Clear localStorage" 
                    size="small" 
                    severity="danger" 
                    outlined
                  />
                </Transition>
                <Transition name="button-slide" appear :delay="200">
                  <Button 
                    @click="saveFilterState" 
                    label="Save to localStorage" 
                    size="small" 
                    severity="info" 
                    outlined
                  />
                </Transition>
              </div>
            </Transition>
          </div>
        </div> -->
      </div>
    </div>
    <div v-else class="text-center py-8 px-4">
      <div v-if="metadataLoading" class="flex flex-col sm:flex-row items-center justify-center gap-3">
        <i class="pi pi-spin pi-spinner text-blue-500 text-lg"></i>
        <span class="text-sm sm:text-base text-gray-600 dark:text-gray-400">{{
          $t("ChatFilterPanel.loadingMetadata", "Loading filter metadata...")
        }}</span>
      </div>
      <div v-else class="flex flex-col sm:flex-row items-center justify-center gap-3">
        <i class="pi pi-exclamation-triangle text-red-500 text-lg"></i>
        <span class="text-sm sm:text-base text-red-500">{{ $t("ChatFilterPanel.metadataFailed", "Failed to load filter metadata") }}</span>
      </div>
    </div>

    <template #footer>
      <div
        class="flex flex-col sm:flex-row items-stretch sm:items-center justify-end w-full gap-2 sm:gap-3 p-3 sm:p-4 border-t border-gray-200 dark:border-gray-700"
      >
        <Transition name="clear-button" mode="out-in">
          <Button
            v-if="hasAnyActiveFilters()"
            key="clear-button"
            @click="clearAllFilters"
            :label="hasEmptyResults ? $t('filters.actions.reset', 'Сбросить') : $t('filters.actions.clearAll', 'Сбросить все фильтры')"
            icon="pi pi-times"
            size="small"
            text
            :severity="hasEmptyResults ? 'warning' : 'secondary'"
            class="w-full sm:w-auto justify-center py-3 px-4 text-sm rounded-lg touch-manipulation order-2 sm:order-1"
          />
        </Transition>
        
        <Transition name="apply-button" mode="out-in">
          <Button
            :key="isApplyButtonDisabled ? 'disabled' : 'enabled'"
            @click="applyFilters"
            :label="$t('filters.actions.apply', 'Применить фильтры')"
            icon="pi pi-check"
            :disabled="isApplyButtonDisabled"
            class="w-full sm:w-auto justify-center py-3 px-4 text-sm rounded-lg touch-manipulation order-1 sm:order-2"
            :class="{
              'opacity-50 cursor-not-allowed': isApplyButtonDisabled
            }"
          />
        </Transition>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useFilterMetadata } from "~/composables/useFilterMetadata";

// PrimeVue components
import MultiSelect from "primevue/multiselect";
import Calendar from "primevue/calendar";
import Button from "primevue/button";
import Badge from "primevue/badge";
import Checkbox from "primevue/checkbox";
import InputText from "primevue/inputtext";
import Dialog from "primevue/dialog";

const { t, locale } = useI18n();
const { processFilterConfig, createChatSessionFilters } = useFilterMetadata();

// Props
interface Props {
  metadata: any;
  showDebug?: boolean;
  hasActiveFilters?: boolean;
  hasEmptyResults?: boolean;
  resultsCount?: number;
  metadataLoading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  showDebug: false,
  hasActiveFilters: false,
  hasEmptyResults: false,
  resultsCount: 0,
  metadataLoading: false,
});

// Emits
const emit = defineEmits<{
  filtersChanged: [filters: any];
  clearFilters: [];
  filtersLoaded: [loaded: boolean];
}>();

// Extract filter configuration from metadata
const filterConfig = computed(() => {
  // Use the composable to process metadata if available
  if (props.metadata) {
    const { filters } = processFilterConfig(props.metadata);

    if (filters.length === 0) {
      // Fallback to static configuration
      const staticConfig = createChatSessionFilters();

      console.log("Using static filter config as fallback:", staticConfig);
      return staticConfig.filters.reduce((acc, filter) => {
        acc[filter.key] = filter;
        return acc;
      }, {} as any);
    }

    return filters.reduce((acc, filter) => {
      acc[filter.key] = filter;
      return acc;
    }, {} as any);
  }

  // Fallback to static configuration
  const staticConfig = createChatSessionFilters();
  return staticConfig.filters.reduce((acc, filter) => {
    acc[filter.key] = filter;
    return acc;
  }, {} as any);
});

// Types
interface FilterState {
  channel: string[];
  dateRange: Date[] | null;
  status: string[];
  client_type: string[];
}

// Reactive filter state
const selectedFilters = reactive<FilterState>({
  channel: [],
  dateRange: null,
  status: [],
  client_type: [],
});

// Dialog state
const showFilterDialog = ref(false);

// Filters loaded state
const filtersLoadedState = ref(false);

// localStorage integration
const STORAGE_KEY = 'chat-filters-state';

interface StoredFilterState {
  filters: {
    channel: string[];
    dateRange: string[] | null; // Stored as ISO strings
    status: string[];
    client_type: string[];
  };
  searchQueries: Record<string, string>;
  panelExpanded: boolean;
  lastUpdated: string;
}

// Load filter state from localStorage
const loadFilterState = (): StoredFilterState | null => {
  try {
    if (typeof window === 'undefined') return null;
    
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    
    const parsed = JSON.parse(stored) as StoredFilterState;
    
    // Check if data is not too old (7 days)
    const lastUpdated = new Date(parsed.lastUpdated);
    const now = new Date();
    const daysDiff = (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60 * 24);
    
    if (daysDiff > 7) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    
    return parsed;
  } catch (error) {
    console.warn('Failed to load filter state from localStorage:', error);
    return null;
  }
};

// Save filter state to localStorage
const saveFilterState = () => {
  try {
    if (typeof window === 'undefined') return;
    
    const stateToSave: StoredFilterState = {
      filters: {
        channel: selectedFilters.channel,
        dateRange: selectedFilters.dateRange ? 
          selectedFilters.dateRange.map(date => date?.toISOString() || '') : 
          null,
        status: selectedFilters.status,
        client_type: selectedFilters.client_type,
      },
      searchQueries: {}, // Can be extended for search functionality
      panelExpanded: showFilterDialog.value,
      lastUpdated: new Date().toISOString(),
    };
    
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
  } catch (error) {
    console.warn('Failed to save filter state to localStorage:', error);
  }
};

// Restore filter state from localStorage
const restoreFilterState = () => {
  const stored = loadFilterState();
  console.log("Loaded stored data:", stored);
  if (!stored) return;
  
  try {
    // Restore filters
    selectedFilters.channel = stored.filters.channel || [];
    selectedFilters.status = stored.filters.status || [];
    selectedFilters.client_type = stored.filters.client_type || [];
    
    console.log("Restored basic filters:", {
      channel: selectedFilters.channel,
      status: selectedFilters.status,
      client_type: selectedFilters.client_type
    });
    
    // Restore date range with proper Date objects
    if (stored.filters.dateRange && Array.isArray(stored.filters.dateRange)) {
      console.log("Original dateRange from storage:", stored.filters.dateRange);
      
      const dates = stored.filters.dateRange
        .map(dateStr => dateStr ? new Date(dateStr) : null)
        .filter(date => date && !isNaN(date.getTime())) as Date[];
      
      console.log("Converted dates:", dates);
      selectedFilters.dateRange = dates.length === 2 ? dates : null;
      console.log("Final dateRange:", selectedFilters.dateRange);
    }
    
    // Restore panel state
    showFilterDialog.value = stored.panelExpanded || false;
    
    console.log('Filter state restored from localStorage', selectedFilters);
  } catch (error) {
    console.warn('Failed to restore filter state:', error);
  }
};

// Clear localStorage
const clearStoredState = () => {
  try {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch (error) {
    console.warn('Failed to clear stored filter state:', error);
  }
};

// Active filter count for badge
const activeFilterCount = computed(() => {
  let count = 0;

  if (selectedFilters.channel.length > 0) count++;
  if (selectedFilters.dateRange) count++;
  if (selectedFilters.status.length > 0) count++;
  if (selectedFilters.client_type.length > 0) count++;

  return count;
});

// Helper functions
const getFilterTitle = (filterDef: any): string => {
  return filterDef?.title || "";
};

const getFilterChoices = (filterDef: any) => {
  return filterDef?.choices || [];
};

const getStatusFilterOptions = () => {
  const statusFilter = filterConfig.value.status;
  return statusFilter?.choices || [];
};

const getLocalizedValue = (value: any): string => {
  if (!value) return "";
  if (typeof value === "string") return value;

  const currentLocale = locale.value || "en";
  return value[currentLocale] || value["en"] || "";
};

// Date presets - use the composable's filter configuration
const datePresets = computed(() => {
  const updatedFilter = filterConfig.value.updated;
  if (updatedFilter?.presets) {
    return updatedFilter.presets;
  }

  // Fallback to default presets
  return [
    {
      key: "week",
      label: t("filters.date.presets.week", "Last Week"),
      days: 7,
    },
    {
      key: "month",
      label: t("filters.date.presets.month", "Last Month"),
      days: 30,
    },
    {
      key: "quarter",
      label: t("filters.date.presets.quarter", "Last 3 Months"),
      days: 90,
    },
  ];
});

// Date preset functions
const applyDatePreset = (preset: any) => {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(endDate.getDate() - preset.days);

  selectedFilters.dateRange = [startDate, endDate];
};

const clearDateFilter = () => {
  if (selectedFilters.dateRange) {
    selectedFilters.dateRange = null;
    // Automatically apply filters after clearing
    applyFilters();
  }
};

// Individual filter clear methods
const clearChannelFilter = () => {
  if (selectedFilters.channel.length > 0) {
    selectedFilters.channel = [];
    // Automatically apply filters after clearing
    applyFilters();
  }
};

const clearStatusFilter = () => {
  if (selectedFilters.status.length > 0) {
    selectedFilters.status = [];
    // Automatically apply filters after clearing
    applyFilters();
  }
};

const clearClientTypeFilter = () => {
  if (selectedFilters.client_type.length > 0) {
    selectedFilters.client_type = [];
    // Automatically apply filters after clearing
    applyFilters();
  }
};

// Filter actions
const applyFilters = () => {
  const filters = buildFiltersObject();

  emit("filtersChanged", filters);

};

const clearAllFilters = () => {
  // Clear filters
  selectedFilters.channel = [];
  selectedFilters.dateRange = null;
  selectedFilters.status = [];
  selectedFilters.client_type = [];

  // Clear localStorage
  clearStoredState();

  // Emit cleared state
  emit("filtersChanged", {});
  emit("clearFilters");

};

// Build filter object for API
const buildFiltersObject = () => {
  const filters: any = {};

  // Channel filter
  if (selectedFilters.channel.length > 0) {
    filters.channel = selectedFilters.channel;
  }

  // Date range filter
  if (selectedFilters.dateRange && Array.isArray(selectedFilters.dateRange) && selectedFilters.dateRange.length === 2) {
    const [startDate, endDate] = selectedFilters.dateRange;
    if (startDate && endDate) {
      filters.updated = {
        from: startDate.toISOString(),
        to: endDate.toISOString(),
      };
    }
  }

  // Status filter
  if (selectedFilters.status.length > 0) {
    filters.status = selectedFilters.status;
  }

  // Client type filter
  if (selectedFilters.client_type.length > 0) {
    filters.client_type = selectedFilters.client_type;
  }

  return filters;
};

// Check if filters are loaded and ready
const filtersLoaded = computed(() => {
  const loaded = !props.metadataLoading && props.metadata && filterConfig.value && Object.keys(filterConfig.value).length > 0;
  return loaded;
});

// Watch for filter changes and save to localStorage
watch(
  selectedFilters,
  () => {
    saveFilterState();
  },
  { deep: true }
);

// Watch for dialog state changes and save to localStorage
watch(
  showFilterDialog,
  () => {
    saveFilterState();
  }
);

// Watch for filters loaded state and emit to parent
watch(
  filtersLoaded,
  (loaded) => {
    filtersLoadedState.value = loaded;
    emit("filtersLoaded", loaded);
  },
  { immediate: true }
);

// Initialize component
onMounted(() => {
  // Restore filter state from localStorage
  restoreFilterState();
  
  // If filters were restored and have values, emit them
  if (hasAnyActiveFilters()) {
    const filters = buildFiltersObject();
    emit("filtersChanged", filters);
  }
});

// Watch for changes and auto-emit
// You can uncomment these if you want real-time filtering
// watch([selectedFilters, searchFields], () => {
//   applyFilters()
// }, { deep: true })

// Status styling computed properties
const containerClasses = computed(() => ({
  "border-gray-200 dark:border-gray-700": !props.hasActiveFilters,
  "border-blue-200 dark:border-blue-800": props.hasActiveFilters && !props.hasEmptyResults,
  "border-yellow-200 dark:border-yellow-800": props.hasActiveFilters && props.hasEmptyResults,
}));

const filterStatusClasses = computed(() => {
  if (props.hasEmptyResults) {
    return "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800";
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800"
    : "bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800";
});

const iconBackgroundClasses = computed(() => {
  if (props.hasEmptyResults) {
    return "bg-yellow-100 dark:bg-yellow-800/30";
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters ? "bg-blue-100 dark:bg-blue-800/30" : "bg-gray-100 dark:bg-gray-800/30";
});

const statusIconClasses = computed(() => {
  if (props.hasEmptyResults) {
    return "pi pi-exclamation-triangle text-yellow-600 dark:text-yellow-400";
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters ? "pi pi-filter text-blue-600 dark:text-blue-400" : "pi pi-sliders-h text-gray-600 dark:text-gray-400";
});

const statusTextClasses = computed(() => {
  if (props.hasEmptyResults) {
    return "text-yellow-800 dark:text-yellow-200";
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters ? "text-blue-800 dark:text-blue-200" : "text-gray-800 dark:text-gray-200";
});

const subtitleClasses = computed(() => {
  if (props.hasEmptyResults) {
    return "text-yellow-600 dark:text-yellow-400";
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters ? "text-blue-600 dark:text-blue-400" : "text-gray-600 dark:text-gray-400";
});

const badgeClasses = computed(() => ({
  "bg-blue-100 dark:bg-blue-800/50 text-blue-700 dark:text-blue-300": !props.hasEmptyResults,
}));

// Status messages
const statusTitle = computed(() => {
  if (props.hasEmptyResults) {
    return t("ChatFilterPanel.noResultsFound", "No Results Found");
  }

  // Check if any filters are actually active
  const hasFilters = hasAnyActiveFilters();
  return hasFilters ? t("ChatFilterPanel.filtersActive", "Filters Active") : t("ChatFilterPanel.filterPanel", "Filter Panel");
});

const statusSubtitle = computed(() => {
  if (props.hasEmptyResults) {
    return t("ChatFilterPanel.tryDifferentFilters", "Try different filters or search terms");
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? t("ChatFilterPanel.showingFilteredResults", "Showing filtered results")
    : t("ChatFilterPanel.configureFilters", "Configure your filters and search criteria");
});

// Helper function to check if any filters are actually active
const hasAnyActiveFilters = () => {
  console.log("Checking active filters:", {
    channel: selectedFilters.channel,
    dateRange: selectedFilters.dateRange,
    status: selectedFilters.status,
    client_type: selectedFilters.client_type,
    channelLength: selectedFilters.channel.length,
    dateRangeExists: selectedFilters.dateRange !== null,
    statusLength: selectedFilters.status.length,
    clientTypeLength: selectedFilters.client_type.length
  });
  
  const hasFilters = (
    selectedFilters.channel.length > 0 ||
    selectedFilters.dateRange !== null ||
    selectedFilters.status.length > 0 ||
    selectedFilters.client_type.length > 0
  );
  
  console.log("Has any active filters:", hasFilters);
  return hasFilters;
};

// Debug computed property for button state
const isApplyButtonDisabled = computed(() => {
  const disabled = props.hasEmptyResults && hasAnyActiveFilters();
  console.log("Apply button disabled:", {
    hasEmptyResults: props.hasEmptyResults,
    hasAnyActiveFilters: hasAnyActiveFilters(),
    disabled
  });
  return disabled;
});

// Header-specific computed properties for dialog header styling
const headerIconBackgroundClasses = computed(() => {
  if (props.hasEmptyResults) {
    return "bg-yellow-100 dark:bg-yellow-800/30";
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters ? "bg-blue-100 dark:bg-blue-800/30" : "bg-gray-100 dark:bg-gray-800/30";
});

const headerStatusIconClasses = computed(() => {
  if (props.hasEmptyResults) {
    return "pi pi-exclamation-triangle text-yellow-600 dark:text-yellow-400";
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters ? "pi pi-filter text-blue-600 dark:text-blue-400" : "pi pi-sliders-h text-gray-600 dark:text-gray-400";
});

const headerStatusTextClasses = computed(() => {
  if (props.hasEmptyResults) {
    return "text-yellow-800 dark:text-yellow-200";
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters ? "text-blue-800 dark:text-blue-200" : "text-gray-800 dark:text-gray-200";
});

const headerSubtitleClasses = computed(() => {
  if (props.hasEmptyResults) {
    return "text-yellow-600 dark:text-yellow-400";
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters ? "text-blue-600 dark:text-blue-400" : "text-gray-600 dark:text-gray-400";
});

const headerBadgeClasses = computed(() => ({
  "bg-blue-100 dark:bg-blue-800/50 text-blue-700 dark:text-blue-300": !props.hasEmptyResults,
}));

// Header title and subtitle
const headerTitle = computed(() => {
  if (props.hasEmptyResults) {
    return t("ChatFilterPanel.noResultsFound", "No Results Found");
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters ? t("ChatFilterPanel.filtersActive", "Filters Active") : t("ChatFilterPanel.filterPanel", "Filter Panel");
});

const headerSubtitle = computed(() => {
  if (props.hasEmptyResults) {
    return t("ChatFilterPanel.tryDifferentFilters", "Try different filters or search terms");
  }

  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? t("ChatFilterPanel.showingFilteredResults", "Showing filtered results")
    : t("ChatFilterPanel.configureFilters", "Configure your filters and search criteria");
});
</script>

<style scoped>
/* Minimal custom styles - most styling is now handled by Tailwind */

/* Touch manipulation for better mobile experience */
.touch-manipulation {
  touch-action: manipulation;
}

/* Individual filter reset button styling */
.filter-clear-button {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.filter-clear-button:hover:not(:disabled) {
  background-color: rgba(239, 68, 68, 0.1);
  color: rgb(239, 68, 68);
}

.filter-clear-button:active:not(:disabled) {
  transform: scale(0.95);
}

.filter-clear-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  pointer-events: none;
}

/* Mobile-specific button adjustments */
@media (max-width: 640px) {
  .filter-clear-button {
    min-width: 32px;
    min-height: 32px;
  }
  
  .filter-clear-button:hover:not(:disabled) {
    background-color: transparent;
  }
  
  .filter-clear-button:active:not(:disabled) {
    background-color: rgba(239, 68, 68, 0.1);
    transform: scale(0.9);
  }
}

/* Vue Transition Animations */

/* Filter trigger button animation */
.filter-trigger-enter-active,
.filter-trigger-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.filter-trigger-enter-from {
  opacity: 0;
  transform: scale(0.9) translateY(-10px);
}

.filter-trigger-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(10px);
}

/* Icon rotation animation */
.icon-rotate-enter-active,
.icon-rotate-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.icon-rotate-enter-from {
  opacity: 0;
  transform: rotate(-180deg) scale(0.5);
}

.icon-rotate-leave-to {
  opacity: 0;
  transform: rotate(180deg) scale(0.5);
}

/* Badge bounce animation */
.badge-bounce-enter-active {
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.badge-bounce-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.badge-bounce-enter-from {
  opacity: 0;
  transform: scale(0) translateY(-20px);
}

.badge-bounce-leave-to {
  opacity: 0;
  transform: scale(0) translateY(20px);
}

/* Preset buttons group animation */
.preset-buttons-move,
.preset-buttons-enter-active,
.preset-buttons-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.preset-buttons-enter-from {
  opacity: 0;
  transform: translateX(-30px) scale(0.9);
}

.preset-buttons-leave-to {
  opacity: 0;
  transform: translateX(30px) scale(0.9);
}

/* Debug buttons animation */
.debug-buttons-enter-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.debug-buttons-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.debug-buttons-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.debug-buttons-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

/* Button slide animation */
.button-slide-enter-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.button-slide-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.button-slide-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.button-slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

/* Footer buttons animations */
.clear-button-enter-active,
.clear-button-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.clear-button-enter-from {
  opacity: 0;
  transform: translateX(-30px) scale(0.9);
}

.clear-button-leave-to {
  opacity: 0;
  transform: translateX(-30px) scale(0.9);
}

.apply-button-enter-active,
.apply-button-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.apply-button-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.apply-button-leave-to {
  opacity: 0;
  transform: translateY(-20px) scale(0.95);
}

/* Hover animations */
.touch-manipulation:hover {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  transform: translateY(-2px);
}

.touch-manipulation:active {
  transition: all 0.1s cubic-bezier(0.4, 0, 0.2, 1);
  transform: translateY(0) scale(0.98);
}

/* Mobile optimizations */
@media (max-width: 640px) {
  .touch-manipulation:hover {
    transform: none;
  }
  
  .touch-manipulation:active {
    transform: scale(0.95);
  }
}

/* Custom scrollbar for better mobile scrolling */
.max-h-\[60vh\]::-webkit-scrollbar,
.max-h-\[70vh\]::-webkit-scrollbar {
  width: 6px;
}

.max-h-\[60vh\]::-webkit-scrollbar-track,
.max-h-\[70vh\]::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.max-h-\[60vh\]::-webkit-scrollbar-thumb,
.max-h-\[70vh\]::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.dark .max-h-\[60vh\]::-webkit-scrollbar-track,
.dark .max-h-\[70vh\]::-webkit-scrollbar-track {
  background: #374151;
}

.dark .max-h-\[60vh\]::-webkit-scrollbar-thumb,
.dark .max-h-\[70vh\]::-webkit-scrollbar-thumb {
  background: #6b7280;
}

/* Ensure PrimeVue components respect Tailwind sizing */
:deep(.p-dialog) {
  border-radius: 0.75rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

:deep(.p-dialog-header) {
  border-radius: 0.75rem 0.75rem 0 0;
}

:deep(.p-dialog-footer) {
  border-radius: 0 0 0.75rem 0.75rem;
}

/* Mobile-specific overrides for PrimeVue components */
@media (max-width: 640px) {
  :deep(.p-dialog) {
    margin: 0.5rem;
    width: calc(100vw - 1rem) !important;
    max-height: 90vh;
  }

  :deep(.p-dialog-content) {
    padding: 0;
  }

  :deep(.p-dialog-header) {
    padding: 0;
  }

  :deep(.p-dialog-footer) {
    padding: 0;
  }
}
</style>
