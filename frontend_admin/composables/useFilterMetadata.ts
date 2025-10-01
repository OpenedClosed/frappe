import { computed } from 'vue'
import { useLanguageState } from './state'
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
  const { t } = useI18n()
  const { currentLanguage } = useLanguageState()

  const getLocalizedValue = (value: any): string => {
    if (!value) return ''
    if (typeof value === 'string') return value
    
    const currentLocale = currentLanguage.value || 'en'
    return value[currentLocale] || value['en'] || ''
  }

  const processFilterConfig = (metadata: any) => {

    console.log('Processing filter config with metadata:', metadata)
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
          processedFilter.placeholder = t('filters.channel.placeholder')
          break
        case 'updated':
          processedFilter.type = 'daterange'
          processedFilter.component = 'Calendar'
          processedFilter.placeholder = t('filters.updated.placeholder')
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
    
    // Default search field translations
    return [
      {
        key: 'messageContent',
        label: t('filters.search.messageContent.label'),
        placeholder: t('filters.search.messageContent.placeholder'),
        paths: ['messages.message']
      },
      {
        key: 'clientName',
        label: t('filters.search.clientName.label'),
        placeholder: t('filters.search.clientName.placeholder'),
        paths: ['client_name_display']
      },
      {
        key: 'companyName',
        label: t('filters.search.companyName.label'),
        placeholder: t('filters.search.companyName.placeholder'),
        paths: ['company_name']
      },
      {
        key: 'chatId',
        label: t('filters.search.chatId.label'),
        placeholder: t('filters.search.chatId.placeholder'),
        paths: ['chat_id']
      }
    ]
  }

  // Extract filter translations from metadata (keeping for backward compatibility)
  const extractFilterTranslations = (metadata: any) => {
    const filters = metadata?.data?.filters
    if (!filters) return null

    const extractedTranslations: any = {}

    // Extract from each filter
    Object.keys(filters).forEach(filterKey => {
      const filter = filters[filterKey]
      
      if (filter.label) {
        extractedTranslations[`${filterKey}_label`] = filter.label
      }
      
      if (filter.placeholder) {
        extractedTranslations[`${filterKey}_placeholder`] = filter.placeholder
      }
      
      if (filter.choices) {
        Object.keys(filter.choices).forEach(choiceKey => {
          extractedTranslations[`${filterKey}_${choiceKey}`] = filter.choices[choiceKey]
        })
      }
    })

    console.log('Extracted filter translations from metadata:', extractedTranslations)
    return extractedTranslations
  }

  // Create filter configuration based on your provided metadata
  const createChatSessionFilters = (metadata?: any) => {
    console.log('createChatSessionFilters called with metadata:', !!metadata)
    console.log('Current language in createChatSessionFilters:', currentLanguage.value)
    
    // If metadata is provided, use processFilterConfig to get properly localized filters
    if (metadata) {
      const processedResult = processFilterConfig(metadata)
      if (processedResult.filters.length > 0) {
        return processedResult
      }
    }
    
    // Fallback static configuration using i18n translations
    const currentLocale = currentLanguage.value || 'ru'
    console.log('Using static config with locale:', currentLocale)
    
    return {
      filters: [
        {
          key: 'channel',
          type: 'multiselect' as const,
          title: t('filters.channel.title'),
          component: 'MultiSelect' as const,
          placeholder: t('filters.channel.placeholder'),
          choices: [
            { value: 'Telegram', title: t('filters.channel.choices.telegram') },
            { value: 'WhatsApp', title: t('filters.channel.choices.whatsapp') },
            { value: 'Web', title: t('filters.channel.choices.website') },
            { value: 'Instagram', title: t('filters.channel.choices.instagram') },
            { value: 'Internal', title: t('filters.channel.choices.internal') }
          ]
        },
        {
          key: 'updated',
          type: 'daterange' as const,
          title: t('filters.updated.title'),
          component: 'Calendar' as const,
          placeholder: t('filters.updated.placeholder'),
          choices: [],
          presets: [
            { 
              key: 'week', 
              label: t('filters.updated.presets.week'), 
              days: 7 
            },
            { 
              key: 'month', 
              label: t('filters.updated.presets.month'), 
              days: 30 
            },
            { 
              key: 'quarter', 
              label: t('filters.updated.presets.quarter'), 
              days: 90 
            }
          ]
        },
        {
          key: 'status',
          type: 'computed' as const,
          title: t('filters.status.title'),
          component: 'Checkbox' as const,
          choices: [
            { value: 'unanswered', title: t('filters.status.choices.unanswered') },
            { value: 'answered', title: t('filters.status.choices.answered') }
          ]
        },
        {
          key: 'client_type',
          type: 'checkbox' as const,
          title: t('filters.clientType.title'),
          component: 'Checkbox' as const,
          choices: [
            { value: 'lead', title: t('filters.clientType.choices.lead') },
            { value: 'account', title: t('filters.clientType.choices.account') }
          ]
        }
      ],
      searchFields: [
        {
          key: 'messageContent',
          label: t('filters.search.messageContent.label'),
          placeholder: t('filters.search.messageContent.placeholder')
        },
        {
          key: 'clientName',
          label: t('filters.search.clientName.label'),
          placeholder: t('filters.search.clientName.placeholder')
        },
        {
          key: 'companyName',
          label: t('filters.search.companyName.label'),
          placeholder: t('filters.search.companyName.placeholder')
        },
        {
          key: 'chatId',
          label: t('filters.search.chatId.label'),
          placeholder: t('filters.search.chatId.placeholder')
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