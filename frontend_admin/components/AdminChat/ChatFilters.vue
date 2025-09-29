<template>
  <!-- Filter Trigger Button -->
  <Button 
    icon="pi pi-filter" 
    text 
    size="small" 
    class="self-center sm:self-auto" 
    @click="showFilterDialog = true"
    :badge="activeFilterCount > 0 ? activeFilterCount.toString() : undefined"
    badge-severity="info"
  />
  
  <!-- Filter Dialog -->
  <Dialog
    v-model:visible="showFilterDialog"
    modal
    :style="{ width: '90vw', maxWidth: '900px' }"
  >
    <template #header>
      <div class="flex items-center gap-3 w-full p-2">
        <!-- Status Icon -->
        <div class="flex items-center justify-center w-8 h-8 rounded-full" :class="headerIconBackgroundClasses">
          <i :class="headerStatusIconClasses" class="text-sm"></i>
        </div>
        
        <!-- Header Content -->
        <div class="flex flex-col gap-0.5 flex-1">
          <div class="flex items-center gap-2">
            <span class="text-base font-semibold" :class="headerStatusTextClasses">
              {{ headerTitle }}
            </span>
            <span v-if="hasAnyActiveFilters() && !hasEmptyResults" class="text-xs px-2 py-1 rounded-full" :class="headerBadgeClasses">
              {{ resultsCount }} {{ $t('ChatFilterPanel.results', 'results') }}
            </span>
          </div>
          <span class="text-xs" :class="headerSubtitleClasses">
            {{ headerSubtitle }}
          </span>
        </div>
        
        <!-- Filter Count Badge -->
        <div v-if="activeFilterCount > 0" class="text-xs bg-blue-100 dark:bg-blue-800/50 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-full">
          {{ activeFilterCount }} {{ $t('filters.activeCount', 'active') }}
        </div>
      </div>
    </template>
    <div v-if="metadata" class="rounded-lg overflow-hidden" :class="containerClasses">
    <!-- Main Filter Content -->
    <div>
    <!-- Filters Section -->
    <div class="filters-section">
      <h3>{{ $t('filters.title', 'Filters') }}</h3>
      
      <!-- Channel Filter -->
      <div class="filter-group" v-if="filterConfig.channel">
        <label>{{ getFilterTitle(filterConfig.channel) }}</label>
        <MultiSelect
          v-model="selectedFilters.channel"
          :options="getFilterChoices(filterConfig.channel)"
          optionLabel="title"
          optionValue="value"
          :placeholder="$t('filters.channel.placeholder', 'Select channels')"
          :maxSelectedLabels="3"
          class="w-full"
        />
      </div>

      <!-- Date Range Filter -->
      <div class="filter-group" v-if="filterConfig.updated">
        <label>{{ getFilterTitle(filterConfig.updated) }}</label>
        <div class="date-filter-container">
          <Calendar
            v-model="selectedFilters.dateRange"
            selectionMode="range"
            :placeholder="$t('filters.date.placeholder', 'Select date range')"
            dateFormat="dd/mm/yy"
            class="w-full"
          />
          <div class="date-presets">
            <Button 
              v-for="preset in datePresets" 
              :key="preset.key"
              @click="applyDatePreset(preset)"
              :label="preset.label"
              size="small"
              outlined
            />
            <Button 
              @click="clearDateFilter"
              :label="$t('filters.clear', 'Clear')"
              size="small"
              severity="secondary"
            />
          </div>
        </div>
      </div>

      <!-- Status Filter (Answer status) -->
      <div class="filter-group" v-if="filterConfig.status">
        <label>{{ getFilterTitle(filterConfig.status) }}</label>
        <div class="checkbox-group">
          <div 
            v-for="option in getStatusFilterOptions()" 
            :key="option.value"
            class="field-checkbox"
          >
            <Checkbox 
              v-model="selectedFilters.status"
              :inputId="'status_' + option.value"
              :value="option.value"
            />
            <label :for="'status_' + option.value">{{ option.title }}</label>
          </div>
        </div>
      </div>

      <!-- Client Type Filter -->
      <div class="filter-group" v-if="filterConfig.client_type">
        <label>{{ getFilterTitle(filterConfig.client_type) }}</label>
        <div class="checkbox-group">
          <div 
            v-for="option in getFilterChoices(filterConfig.client_type)" 
            :key="option.value"
            class="field-checkbox"
          >
            <Checkbox 
              v-model="selectedFilters.client_type"
              :inputId="'client_type_' + option.value"
              :value="option.value"
            />
            <label :for="'client_type_' + option.value">{{ option.title }}</label>
          </div>
        </div>
      </div>
    </div>

    <!-- Debug: Show current filter state -->
    <div v-if="showDebug" class="debug-section">
      <h4>Debug: Current Filter State</h4>
      <pre>{{ JSON.stringify({ selectedFilters }, null, 2) }}</pre>
    </div>
    </div>
    </div>
    <div v-else class="text-center py-4">
      <div v-if="metadataLoading" class="flex items-center justify-center gap-2">
        <i class="pi pi-spin pi-spinner text-blue-500"></i>
        <span class="text-gray-600 dark:text-gray-400">{{ $t('ChatFilterPanel.loadingMetadata', 'Loading filter metadata...') }}</span>
      </div>
      <div v-else class="flex items-center justify-center gap-2">
        <i class="pi pi-exclamation-triangle text-red-5-500"></i>
        <span class="text-red-500">{{ $t('ChatFilterPanel.metadataFailed', 'Failed to load filter metadata') }}</span>
      </div>
    </div>
    
    <template #footer>
      <div class="flex items-center justify-end w-full gap-2">
          <Button 
            v-if="hasAnyActiveFilters()"
            @click="clearAllFilters"
            :label="$t('actions.clear', 'Clear All')" 
            icon="pi pi-times" 
            size="small" 
            text 
            :severity="hasEmptyResults ? 'warning' : 'secondary'"
          />
          <Button 
            @click="applyFilters"
            :label="$t('actions.apply', 'Apply Filters')"
            icon="pi pi-check"
          />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFilterMetadata } from '~/composables/useFilterMetadata'

// PrimeVue components
import MultiSelect from 'primevue/multiselect'
import Calendar from 'primevue/calendar'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Dialog from 'primevue/dialog'

const { t, locale } = useI18n()
const { processFilterConfig, createChatSessionFilters } = useFilterMetadata()

// Props
interface Props {
  metadata: any
  showDebug?: boolean
  hasActiveFilters?: boolean
  hasEmptyResults?: boolean
  resultsCount?: number
  metadataLoading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showDebug: false,
  hasActiveFilters: false,
  hasEmptyResults: false,
  resultsCount: 0,
  metadataLoading: false
})

// Emits
const emit = defineEmits<{
  filtersChanged: [filters: any]
  clearFilters: []
}>()

// Extract filter configuration from metadata
const filterConfig = computed(() => {
  // Use the composable to process metadata if available
  if (props.metadata) {
    const { filters } = processFilterConfig(props.metadata)
    
    if (filters.length === 0) {
      // Fallback to static configuration
      const staticConfig = createChatSessionFilters()
      return staticConfig.filters.reduce((acc, filter) => {
        acc[filter.key] = filter
        return acc
      }, {} as any)
    }
    
    return filters.reduce((acc, filter) => {
      acc[filter.key] = filter
      return acc
    }, {} as any)
  }
  
  // Fallback to static configuration
  const staticConfig = createChatSessionFilters()
  return staticConfig.filters.reduce((acc, filter) => {
    acc[filter.key] = filter
    return acc
  }, {} as any)
})

// Types
interface FilterState {
  channel: string[]
  dateRange: Date[] | null
  status: string[]
  client_type: string[]
}

// Reactive filter state
const selectedFilters = reactive<FilterState>({
  channel: [],
  dateRange: null,
  status: [],
  client_type: []
})

// Dialog state
const showFilterDialog = ref(false)

// Active filter count for badge
const activeFilterCount = computed(() => {
  let count = 0
  
  if (selectedFilters.channel.length > 0) count++
  if (selectedFilters.dateRange) count++
  if (selectedFilters.status.length > 0) count++
  if (selectedFilters.client_type.length > 0) count++
  
  return count
})

// Helper functions
const getFilterTitle = (filterDef: any): string => {
  return filterDef?.title || ''
}

const getFilterChoices = (filterDef: any) => {
  return filterDef?.choices || []
}

const getStatusFilterOptions = () => {
  const statusFilter = filterConfig.value.status
  return statusFilter?.choices || []
}

const getLocalizedValue = (value: any): string => {
  if (!value) return ''
  if (typeof value === 'string') return value
  
  const currentLocale = locale.value || 'en'
  return value[currentLocale] || value['en'] || ''
}

// Date presets - use the composable's filter configuration
const datePresets = computed(() => {
  const updatedFilter = filterConfig.value.updated
  if (updatedFilter?.presets) {
    return updatedFilter.presets
  }
  
  // Fallback to default presets
  return [
    {
      key: 'week',
      label: t('filters.date.presets.week', 'Last Week'),
      days: 7
    },
    {
      key: 'month', 
      label: t('filters.date.presets.month', 'Last Month'),
      days: 30
    },
    {
      key: 'quarter',
      label: t('filters.date.presets.quarter', 'Last 3 Months'),
      days: 90
    }
  ]
})

// Date preset functions
const applyDatePreset = (preset: any) => {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(endDate.getDate() - preset.days)
  
  selectedFilters.dateRange = [startDate, endDate]
}

const clearDateFilter = () => {
  selectedFilters.dateRange = null
}

// Filter actions
const applyFilters = () => {
  const filters = buildFiltersObject()
  
  emit('filtersChanged', filters)
}

const clearAllFilters = () => {
  // Clear filters
  selectedFilters.channel = []
  selectedFilters.dateRange = null
  selectedFilters.status = []
  selectedFilters.client_type = []
  
  // Emit cleared state
  emit('filtersChanged', {})
  emit('clearFilters')
}

// Build filter object for API
const buildFiltersObject = () => {
  const filters: any = {}
  
  // Channel filter
  if (selectedFilters.channel.length > 0) {
    filters.channel = selectedFilters.channel
  }
  
  // Date range filter
  if (selectedFilters.dateRange && Array.isArray(selectedFilters.dateRange) && selectedFilters.dateRange.length === 2) {
    filters.updated = {
      from: selectedFilters.dateRange[0].toISOString(),
      to: selectedFilters.dateRange[1].toISOString()
    }
  }
  
  // Status filter
  if (selectedFilters.status.length > 0) {
    filters.status = selectedFilters.status
  }
  
  // Client type filter
  if (selectedFilters.client_type.length > 0) {
    filters.client_type = selectedFilters.client_type
  }
  
  return filters
}

// Watch for changes and auto-emit
// You can uncomment these if you want real-time filtering
// watch([selectedFilters, searchFields], () => {
//   applyFilters()
// }, { deep: true })

// Status styling computed properties
const containerClasses = computed(() => ({
  'border-gray-200 dark:border-gray-700': !props.hasActiveFilters,
  'border-blue-200 dark:border-blue-800': props.hasActiveFilters && !props.hasEmptyResults,
  'border-yellow-200 dark:border-yellow-800': props.hasActiveFilters && props.hasEmptyResults,
}));

const filterStatusClasses = computed(() => {
  if (props.hasEmptyResults) {
    return 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800';
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
    : 'bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800';
});

const iconBackgroundClasses = computed(() => {
  if (props.hasEmptyResults) {
    return 'bg-yellow-100 dark:bg-yellow-800/30';
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? 'bg-blue-100 dark:bg-blue-800/30'
    : 'bg-gray-100 dark:bg-gray-800/30';
});

const statusIconClasses = computed(() => {
  if (props.hasEmptyResults) {
    return 'pi pi-exclamation-triangle text-yellow-600 dark:text-yellow-400';
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? 'pi pi-filter text-blue-600 dark:text-blue-400'
    : 'pi pi-sliders-h text-gray-600 dark:text-gray-400';
});

const statusTextClasses = computed(() => {
  if (props.hasEmptyResults) {
    return 'text-yellow-800 dark:text-yellow-200';
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? 'text-blue-800 dark:text-blue-200'
    : 'text-gray-800 dark:text-gray-200';
});

const subtitleClasses = computed(() => {
  if (props.hasEmptyResults) {
    return 'text-yellow-600 dark:text-yellow-400';
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? 'text-blue-600 dark:text-blue-400'
    : 'text-gray-600 dark:text-gray-400';
});

const badgeClasses = computed(() => ({
  'bg-blue-100 dark:bg-blue-800/50 text-blue-700 dark:text-blue-300': !props.hasEmptyResults,
}));

// Status messages
const statusTitle = computed(() => {
  if (props.hasEmptyResults) {
    return t('ChatFilterPanel.noResultsFound', 'No Results Found');
  }
  
  // Check if any filters are actually active
  const hasFilters = hasAnyActiveFilters();
  return hasFilters 
    ? t('ChatFilterPanel.filtersActive', 'Filters Active')
    : t('ChatFilterPanel.filterPanel', 'Filter Panel');
});

const statusSubtitle = computed(() => {
  if (props.hasEmptyResults) {
    return t('ChatFilterPanel.tryDifferentFilters', 'Try different filters or search terms');
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? t('ChatFilterPanel.showingFilteredResults', 'Showing filtered results')
    : t('ChatFilterPanel.configureFilters', 'Configure your filters and search criteria');
});

// Helper function to check if any filters are actually active
const hasAnyActiveFilters = () => {
  return (
    selectedFilters.channel.length > 0 ||
    selectedFilters.dateRange !== null ||
    selectedFilters.status.length > 0 ||
    selectedFilters.client_type.length > 0
  );
};

// Header-specific computed properties for dialog header styling
const headerIconBackgroundClasses = computed(() => {
  if (props.hasEmptyResults) {
    return 'bg-yellow-100 dark:bg-yellow-800/30';
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? 'bg-blue-100 dark:bg-blue-800/30'
    : 'bg-gray-100 dark:bg-gray-800/30';
});

const headerStatusIconClasses = computed(() => {
  if (props.hasEmptyResults) {
    return 'pi pi-exclamation-triangle text-yellow-600 dark:text-yellow-400';
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? 'pi pi-filter text-blue-600 dark:text-blue-400'
    : 'pi pi-sliders-h text-gray-600 dark:text-gray-400';
});

const headerStatusTextClasses = computed(() => {
  if (props.hasEmptyResults) {
    return 'text-yellow-800 dark:text-yellow-200';
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? 'text-blue-800 dark:text-blue-200'
    : 'text-gray-800 dark:text-gray-200';
});

const headerSubtitleClasses = computed(() => {
  if (props.hasEmptyResults) {
    return 'text-yellow-600 dark:text-yellow-400';
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? 'text-blue-600 dark:text-blue-400'
    : 'text-gray-600 dark:text-gray-400';
});

const headerBadgeClasses = computed(() => ({
  'bg-blue-100 dark:bg-blue-800/50 text-blue-700 dark:text-blue-300': !props.hasEmptyResults,
}));

// Header title and subtitle
const headerTitle = computed(() => {
  if (props.hasEmptyResults) {
    return t('ChatFilterPanel.noResultsFound', 'No Results Found');
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters 
    ? t('ChatFilterPanel.filtersActive', 'Filters Active')
    : t('ChatFilterPanel.filterPanel', 'Filter Panel');
});

const headerSubtitle = computed(() => {
  if (props.hasEmptyResults) {
    return t('ChatFilterPanel.tryDifferentFilters', 'Try different filters or search terms');
  }
  
  const hasFilters = hasAnyActiveFilters();
  return hasFilters
    ? t('ChatFilterPanel.showingFilteredResults', 'Showing filtered results')
    : t('ChatFilterPanel.configureFilters', 'Configure your filters and search criteria');
});
</script>

<style scoped>
.filter-metadata-parser {
  max-width: 800px;
  margin: 0 auto;
}

.filters-section {
  margin-bottom: 2rem;
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.filter-group {
  margin-bottom: 1rem;
}

.filter-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.date-filter-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.date-presets {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.debug-section {
  margin-top: 2rem;
  padding: 1rem;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.debug-section pre {
  background-color: #fff;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
}

h3 {
  color: #333;
  margin-bottom: 1rem;
}

h4 {
  color: #666;
  margin-bottom: 0.5rem;
}

/* Responsive */
@media (max-width: 768px) {
  .filter-metadata-parser {
    padding: 0.5rem;
  }
  
  .date-presets {
    flex-direction: column;
  }
}
</style>