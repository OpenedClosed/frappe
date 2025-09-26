<template>
  <div class="filter-metadata-parser">
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

    <!-- Search Section -->
    <div class="search-section">
      <h3>{{ $t('search.title', 'Search') }}</h3>
      
      <!-- Message Content Search -->
      <div class="search-group">
        <label>{{ $t('search.messages.label', 'Search in messages') }}</label>
        <InputText
          v-model="searchFields.messageContent"
          :placeholder="$t('search.messages.placeholder', 'Search in message content')"
          class="w-full"
        />
      </div>

      <!-- Client Name Search -->
      <div class="search-group">
        <label>{{ $t('search.client.label', 'Search by client name') }}</label>
        <InputText
          v-model="searchFields.clientName"
          :placeholder="$t('search.client.placeholder', 'Search by client name')"
          class="w-full"
        />
      </div>

      <!-- Company Name Search -->
      <div class="search-group">
        <label>{{ $t('search.company.label', 'Search by company') }}</label>
        <InputText
          v-model="searchFields.companyName"
          :placeholder="$t('search.company.placeholder', 'Search by company name')"
          class="w-full"
        />
      </div>

      <!-- Chat ID Search -->
      <div class="search-group">
        <label>{{ $t('search.chatId.label', 'Search by Chat ID') }}</label>
        <InputText
          v-model="searchFields.chatId"
          :placeholder="$t('search.chatId.placeholder', 'Enter chat ID')"
          class="w-full"
        />
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="action-buttons">
      <Button 
        @click="applyFilters"
        :label="$t('actions.apply', 'Apply Filters')"
        icon="pi pi-check"
      />
      <Button 
        @click="clearAllFilters"
        :label="$t('actions.clear', 'Clear All')"
        icon="pi pi-times"
        severity="secondary"
      />
    </div>

    <!-- Debug: Show current filter state -->
    <div v-if="showDebug" class="debug-section">
      <h4>Debug: Current Filter State</h4>
      <pre>{{ JSON.stringify({ selectedFilters, searchFields }, null, 2) }}</pre>
    </div>
  </div>
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

const { t, locale } = useI18n()
const { processFilterConfig, createChatSessionFilters } = useFilterMetadata()

// Props
interface Props {
  metadata: any
  showDebug?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showDebug: false
})

// Emits
const emit = defineEmits<{
  filtersChanged: [filters: any]
  searchChanged: [search: any]
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

const searchConfig = computed(() => {
  // Use the composable to get search configuration
  if (props.metadata) {
    const { searchFields } = processFilterConfig(props.metadata)
    
    if (searchFields && searchFields.length > 0) {
      return { fields: searchFields }
    }
  }
  
  // Fallback to static configuration
  const staticConfig = createChatSessionFilters()
  return { fields: staticConfig.searchFields }
})

// Types
interface FilterState {
  channel: string[]
  dateRange: Date[] | null
  status: string[]
  client_type: string[]
}

interface SearchState {
  messageContent: string
  clientName: string
  companyName: string
  chatId: string
}

// Reactive filter state
const selectedFilters = reactive<FilterState>({
  channel: [],
  dateRange: null,
  status: [],
  client_type: []
})

// Reactive search state
const searchFields = reactive<SearchState>({
  messageContent: '',
  clientName: '',
  companyName: '',
  chatId: ''
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
  const search = buildSearchObject()
  
  emit('filtersChanged', filters)
  emit('searchChanged', search)
}

const clearAllFilters = () => {
  // Clear filters
  selectedFilters.channel = []
  selectedFilters.dateRange = null
  selectedFilters.status = []
  selectedFilters.client_type = []
  
  // Clear search
  searchFields.messageContent = ''
  searchFields.clientName = ''
  searchFields.companyName = ''
  searchFields.chatId = ''
  
  // Emit cleared state
  emit('filtersChanged', {})
  emit('searchChanged', {})
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

// Build search object for API
const buildSearchObject = () => {
  const searchTerms = []
  
  if (searchFields.messageContent.trim()) {
    searchTerms.push(searchFields.messageContent.trim())
  }
  
  if (searchFields.clientName.trim()) {
    searchTerms.push(searchFields.clientName.trim())
  }
  
  if (searchFields.companyName.trim()) {
    searchTerms.push(searchFields.companyName.trim())
  }
  
  if (searchFields.chatId.trim()) {
    searchTerms.push(searchFields.chatId.trim())
  }
  
  return {
    q: searchTerms.join(' '),
    mode: 'partial',
    logic: 'and'
  }
}

// Watch for changes and auto-emit
// You can uncomment these if you want real-time filtering
// watch([selectedFilters, searchFields], () => {
//   applyFilters()
// }, { deep: true })
</script>

<style scoped>
.filter-metadata-parser {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
}

.filters-section,
.search-section {
  margin-bottom: 2rem;
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.filter-group,
.search-group {
  margin-bottom: 1rem;
}

.filter-group label,
.search-group label {
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

.action-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 2rem;
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
  
  .action-buttons {
    flex-direction: column;
  }
}
</style>