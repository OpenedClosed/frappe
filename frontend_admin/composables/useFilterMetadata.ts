import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface FilterChoice {
  value: string
  title: string
}

interface FilterConfig {
  type: string
  title: string
  choices?: FilterChoice[]
  paths?: string[]
  mapping?: Record<string, any>
  kind?: string
}

interface ProcessedFilter {
  key: string
  type: 'multiselect' | 'checkbox' | 'daterange' | 'computed'
  title: string
  component: 'MultiSelect' | 'Checkbox' | 'Calendar'
  choices: FilterChoice[]
  placeholder?: string
}

export function useFilterMetadata() {
  const { locale } = useI18n()

  const getLocalizedValue = (value: any): string => {
    if (!value) return ''
    if (typeof value === 'string') return value
    
    const currentLocale = locale.value || 'en'
    return value[currentLocale] || value['en'] || ''
  }

  const processFilterConfig = (metadata: any) => {
    const filterConfig = metadata?.chats?.entities?.[0]?.model?.query_ui?.filters?.config || {}
    const searchConfig = metadata?.chats?.entities?.[0]?.model?.query_ui?.search?.config || {}
    
    const processedFilters: ProcessedFilter[] = []

    // Process each filter
    Object.entries(filterConfig).forEach(([key, config]: [string, any]) => {
      const filterDef = config as FilterConfig
      
      let processedFilter: ProcessedFilter = {
        key,
        type: getFilterType(filterDef),
        title: getLocalizedValue(filterDef.title),
        component: getComponentType(filterDef),
        choices: []
      }

      // Process choices for regular filters
      if (filterDef.choices) {
        processedFilter.choices = filterDef.choices.map((choice: any) => ({
          value: choice.value,
          title: getLocalizedValue(choice.title)
        }))
      }

      // Process computed filters (like status)
      if (filterDef.mapping) {
        processedFilter.choices = Object.entries(filterDef.mapping).map(([value, config]: [string, any]) => ({
          value,
          title: getLocalizedValue(config.title)
        }))
      }

      // Add specific configurations
      switch (key) {
        case 'channel':
          processedFilter.placeholder = 'Select channels'
          break
        case 'updated':
          processedFilter.type = 'daterange'
          processedFilter.component = 'Calendar'
          processedFilter.placeholder = 'Select date range'
          break
        case 'status':
          processedFilter.type = 'computed'
          processedFilter.component = 'Checkbox'
          break
        case 'client_type':
          processedFilter.type = 'checkbox'
          processedFilter.component = 'Checkbox'
          break
      }

      processedFilters.push(processedFilter)
    })

    return {
      filters: processedFilters,
      searchFields: getSearchFields(searchConfig)
    }
  }

  const getFilterType = (config: FilterConfig): ProcessedFilter['type'] => {
    if (config.type === 'multienum') return 'multiselect'
    if (config.type === 'range') return 'daterange'
    if (config.kind === 'computed_to_search') return 'computed'
    return 'checkbox'
  }

  const getComponentType = (config: FilterConfig): ProcessedFilter['component'] => {
    if (config.type === 'multienum') return 'MultiSelect'
    if (config.type === 'range') return 'Calendar'
    return 'Checkbox'
  }

  const getSearchFields = (searchConfig: any) => {
    const fields = searchConfig?.fields || []
    
    return [
      {
        key: 'messageContent',
        label: 'Search in messages',
        placeholder: 'Search in message content',
        paths: ['messages.message']
      },
      {
        key: 'clientName',
        label: 'Search by client name',
        placeholder: 'Search by client name',
        paths: ['client_name_display']
      },
      {
        key: 'companyName',
        label: 'Search by company',
        placeholder: 'Search by company name',
        paths: ['company_name']
      },
      {
        key: 'chatId',
        label: 'Search by Chat ID',
        placeholder: 'Enter chat ID',
        paths: ['chat_id']
      }
    ]
  }

  // Create filter configuration based on your provided metadata
  const createChatSessionFilters = () => {
    return {
      filters: [
        {
          key: 'channel',
          type: 'multiselect' as const,
          title: 'Channel',
          component: 'MultiSelect' as const,
          placeholder: 'Select channels',
          choices: [
            { value: 'Telegram', title: 'Telegram' },
            { value: 'WhatsApp', title: 'WhatsApp' },
            { value: 'Web', title: 'Website' },
            { value: 'Instagram', title: 'Instagram' },
            { value: 'Internal', title: 'Internal' }
          ]
        },
        {
          key: 'updated',
          type: 'daterange' as const,
          title: 'Updated',
          component: 'Calendar' as const,
          placeholder: 'Select date range',
          choices: [],
          presets: [
            { key: 'week', label: 'Last Week', days: 7 },
            { key: 'month', label: 'Last Month', days: 30 },
            { key: 'quarter', label: 'Last 3 Months', days: 90 }
          ]
        },
        {
          key: 'status',
          type: 'computed' as const,
          title: 'Answer',
          component: 'Checkbox' as const,
          choices: [
            { value: 'unanswered', title: 'Unanswered' },
            { value: 'answered', title: 'Answered' }
          ]
        },
        {
          key: 'client_type',
          type: 'checkbox' as const,
          title: 'Type',
          component: 'Checkbox' as const,
          choices: [
            { value: 'lead', title: 'Lead' },
            { value: 'account', title: 'Account' }
          ]
        }
      ],
      searchFields: [
        {
          key: 'messageContent',
          label: 'Search in messages',
          placeholder: 'Search in message content'
        },
        {
          key: 'clientName',
          label: 'Search by client name',
          placeholder: 'Search by client name'
        },
        {
          key: 'companyName',
          label: 'Search by company',
          placeholder: 'Search by company name'
        },
        {
          key: 'chatId',
          label: 'Search by Chat ID',
          placeholder: 'Enter chat ID'
        }
      ]
    }
  }

  return {
    processFilterConfig,
    createChatSessionFilters,
    getLocalizedValue
  }
}

export type { FilterChoice, FilterConfig, ProcessedFilter }