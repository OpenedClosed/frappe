<template>
  <div class="p-6 border rounded-lg shadow-sm bg-white dark:bg-secondaryDark">
    <!-- Заголовок и описание -->
    <h2 class="text-xl font-semibold mb-1">{{ t('AgreesPanel.title') }}</h2>
    <p class=" mb-4">{{ t('AgreesPanel.subtitle') }}</p>

    <!-- Список согласий -->
    <ul>
      <li v-for="(consent, index) in consents" :key="index" class="flex items-center mb-2">
        <!-- Цветной кружок: зеленый если заполнено, красный если нет -->
        <span
          :class="consent.status ? 'bg-green-500' : 'bg-red-500'"
          class="inline-block w-3 h-3 rounded-full mr-2"
        ></span>
        <!-- Текст согласия -->
        <span>{{ consent.title }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { defineProps, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()


const props = defineProps({
  itemData: {
    type: Object,
    required: true,
  },
  filteredFields: {
    // filteredFields is expected to be an array of field definitions
    type: Array,
    required: true,
  }
})

// Отслеживаем изменение данных для отладки (необязательно)
watch(
  () => props,
  (newVal) => {
    if (newVal) {
      console.log('Updated itemData:', props.itemData)
      console.log('Updated filteredFields:', props.filteredFields)
    }
  },
  { immediate: true }
)

// Функция для форматирования даты
function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Создаем вычисляемое свойство, которое собирает все варианты согласий
// и определяет, заполнено оно или нет.
const consents = computed(() => {
  // Находим определение поля согласий в filteredFields
  const consentField = props.filteredFields.find(field => field.name === "consents")
  if (!consentField || !consentField.choices) return []

  // Создаем набор согласий, которые пользователь заполнил
  // Здесь мы используем русские переводы для сравнения
  const filledConsents = new Set((props.itemData.consents || []).map(c => c.ru))

  // Проходим по всем доступным вариантам согласий и определяем их статус
  return consentField.choices.map(choice => ({
    title: choice.label.ru, // Отображаем название на русском языке
    status: filledConsents.has(choice.value.ru) // true, если согласие заполнено
  }))
})
</script>
