<template>
  <div class="container mx-auto px-4 py-8 flex flex-col md:flex-row gap-6">
    <!-- Левая карточка: Бонусный счёт -->
    <div class="flex-1 bg-white rounded-lg p-6 shadow">
      <h2 class="text-2xl font-bold mb-2">Бонусный счёт</h2>
      <p class="text-sm text-gray-500 mb-6">
        Информация о бонусах пользователя
      </p>

      <!-- Текущий баланс -->
      <div class="mb-4">
        <span class="block text-gray-600 text-sm">Текущий баланс</span>
        <p class="text-4xl font-bold text-blue-600">{{ balance }}</p>
      </div>

      <!-- Реферальный код -->
      <div class="mb-4">
        <span class="block text-gray-600 text-sm">Реферальный код</span>
        <p class="text-lg font-medium">{{ referralCode }}</p>
      </div>

      <!-- Дата последнего обновления или любая дополнительная информация -->
      <div>
        <span class="block text-gray-600 text-sm">Последнее обновление</span>
        <p class="text-base text-gray-800">{{ lastUpdate }}</p>
      </div>
    </div>

    <!-- Правая карточка: История транзакций -->
    <div class="flex-1 bg-white rounded-lg p-6 shadow">
      <h2 class="text-2xl font-bold mb-2">История транзакций</h2>
      <p class="text-sm text-gray-500 mb-6">
        Последние бонусные операции
      </p>

      <!-- Список транзакций -->
      <ul class="space-y-4">
        <li 
          v-for="(txn, index) in transactions" 
          :key="index" 
          class="flex justify-between items-start"
        >
          <!-- Левая часть: тип и описание -->
          <div>
            <p 
              class="text-sm font-bold"
              :class="txn.isPositive ? 'text-green-600' : 'text-red-600'"
            >
              {{ txn.type }}
            </p>
            <p class="text-gray-700 text-sm">{{ txn.label }}</p>
          </div>

          <!-- Правая часть: сумма и дата -->
          <div class="text-right">
            <p 
              class="text-lg font-bold"
              :class="txn.isPositive ? 'text-green-600' : 'text-red-600'"
            >
              <!-- Если isPositive = true, ставим +, иначе - -->
              {{ txn.isPositive ? '+' : '-' }}{{ txn.amount }}
            </p>
            <p class="text-gray-500 text-sm">{{ txn.date }}</p>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// Пример данных. В реальном проекте вы можете получать их из API или Vuex/Pinia
const balance = ref(450)
const referralCode = ref('TVNA2023')
const lastUpdate = ref('10.06.2023, 8:20')

const transactions = ref([
  {
    type: 'Начислено',
    label: 'Реферал',
    amount: 100,
    date: '01.06.2023, 14:00',
    isPositive: true,
  },
  {
    type: 'Начислено',
    label: 'День рождения',
    amount: 200,
    date: '15.05.2023, 13:20',
    isPositive: true,
  },
  {
    type: 'Вручную',
    label: 'Скидка на консультацию',
    amount: 50,
    date: '20.05.2023, 15:35',
    isPositive: false,
  },
])
</script>

<style scoped>
/* При необходимости можно добавить дополнительные стили */
</style>
