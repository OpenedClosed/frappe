<template>
  <div class="p-4 rounded border shadow-sm bg-white dark:bg-secondaryDark">
    <h2 class="text-2xl font-bold mb-4">{{ t('PatientsMainInfoView.sectionTitle') }}</h2>

    <div class="flex gap-10">
      <div
        v-for="(columnGroups, colIndex) in normalizedGroups"
        :key="colIndex"
        class="flex-1 flex flex-col gap-6"
      >
        <div v-for="group in columnGroups" :key="group.title.en">
          <h3 class="text-lg font-bold mb-2">{{ group.title[currentLanguage] || group.title['en'] || ''  }}</h3>
          <div class="flex flex-col space-y-1">
            <div
              v-for="field in group.fields"
              :key="field"
              class="flex items-center justify-between"
            >
              <span class="text-sm">
                 {{ getFieldTitle(field) }}
              </span>
              <span
                class="ml-1 font-semibold"
                v-html="formatFieldValue(field)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import _ from 'lodash'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
const { currentLanguage } = useLanguageState();
const { t } = useI18n()

const props = defineProps({
  itemData: {
    type: Object,
    default: () => ({})
  },
  fieldGroups: {},
  filteredFields: {},
})

// Создаем словарь мета-информации по названию поля
const fieldMetaMap = computed(() => {
  const map = {}
  props.filteredFields.forEach((meta) => {
    map[meta.name] = meta
  })
  return map
})

// Получить заголовок поля на нужном языке
function getFieldTitle(fieldName) {
  const meta = fieldMetaMap.value[fieldName]
  if (!meta) return fieldName
  return meta.title?.[currentLanguage.value] || meta.title?.en || fieldName
}

watch(props, (newData) => {
  console.log('Props changed:', newData)
}, { immediate: true })

// Normalize and group fieldGroups by logical column index
const normalizedGroups = computed(() => {
  const uniqueCols = [...new Set(props.fieldGroups.map(g => g.column))].sort((a, b) => a - b)
  const columnMap = Object.fromEntries(uniqueCols.map((col, i) => [col, i]))
  const grouped = _.groupBy(props.fieldGroups, g => columnMap[g.column])
  return Object.values(grouped)
})

// Format individual field values
function formatFieldValue(field) {
  const value = props.itemData[field]

  if (field === 'birth_date' || field === 'created_at' || field === 'updated_at') {
    return formatDate(value)
  }

  if (field === 'gender') {
    return value?.[currentLanguage.value] || value?.en || value || '—'
  }

  if (field === 'avatar') {
    return value?.url
      ? `<img src="${value.url}" alt="avatar" class="w-8 h-8 rounded-full" />`
      : '—'
  }

  return value !== null && value !== undefined && value !== '' ? String(value) : '—'
}

// Format date into dd.mm.yyyy hh:mm
function formatDate(date) {
  if (!date) return '—'
  try {
    const parsed = new Date(date)
    if (_.isDate(parsed) && !isNaN(parsed)) {
      return `${_.padStart(parsed.getDate(), 2, '0')}.${_.padStart(parsed.getMonth() + 1, 2, '0')}.${parsed.getFullYear()} ${_.padStart(parsed.getHours(), 2, '0')}:${_.padStart(parsed.getMinutes(), 2, '0')}`
    }
    return t('PatientsMainInfoView.invalidDate')
  } catch (e) {
    console.error('Invalid date:', date)
    return t('PatientsMainInfoView.invalidDate')
  }
}
</script>

<style scoped>
/* Add any needed styles */
</style>
