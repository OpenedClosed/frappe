<template>
  <div class="p-6 border rounded-lg shadow-sm bg-white">
    <div class="flex items-start justify-between mb-4">
      <div>
        <h3 class="text-xl font-semibold">Анкета здоровья</h3>
        <p class="text-sm text-gray-500">Медицинская информация пользователя</p>
      </div>
      <span class="px-3 py-1 text-sm font-medium rounded-full"
            :style="{ backgroundColor: itemData?.form_status.settings?.color + '20', color: itemData?.form_status.settings?.color }">
        {{ itemData?.form_status.ru }}
      </span>
    </div>

    <!-- Allergies Section with Variants -->
    <div class="mb-4">
      <div class="text-gray-500 font-semibold">Аллергии:</div>
      <div class="mt-1 text-black">
        <template v-if="itemData?.allergies && itemData.allergies.length">
          <div class="flex flex-wrap gap-2">
            <span v-for="(allergy, index) in itemData.allergies" :key="index"
                  class="px-2 py-1 border rounded bg-gray-100">
              <!-- If allergy is an object with translations, display the Russian variant -->
              <template v-if="typeof allergy === 'object'">
                {{ allergy.ru }}
              </template>
              <!-- Otherwise, display the allergy as a string -->
              <template v-else>
                {{ allergy }}
              </template>
            </span>
          </div>
        </template>
        <template v-else>
          —
        </template>
      </div>
    </div>

    <div class="mb-4">
      <div class="text-gray-500 font-semibold">Хронические заболевания:</div>
      <div class="mt-2 flex flex-wrap gap-4">
        <div v-for="(condition, index) in itemData?.chronic_conditions" :key="index"
             class="flex items-center gap-2 text-black">
          <span :class="[
              'w-3 h-3 rounded-full',
              ['Диабет', 'Астма'].includes(condition.ru) ? 'bg-red-500' : 'bg-green-500'
            ]"></span>
          {{ condition.ru }}
        </div>
      </div>
    </div>

    <div class="mb-4">
      <div class="text-gray-500 font-semibold">Статус курения:</div>
      <div class="mt-1 text-black">{{ itemData?.smoking_status.ru }}</div>
    </div>

    <div class="mb-4">
      <div class="text-gray-500 font-semibold">Текущие медикаменты:</div>
      <div class="mt-1 text-black">{{ itemData?.current_medications || '—' }}</div>
    </div>

    <div class="text-gray-500 font-semibold">Последнее обновление:</div>
    <div class="mt-1 text-black">{{ formatDate(itemData?.last_updated) }}</div>
  </div>
</template>

<script setup>
const props = defineProps({
  itemData: {
    type: Object,
    required: true,
  }
})

watch(() => props.itemData, (newVal) => {
  if (newVal) {
    console.log('Updated itemData:', newVal)
  }
}, { immediate: true })

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>
