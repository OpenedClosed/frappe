<template>
  <div class="w-full container mx-auto px-4 py-8 flex flex-col md:flex-row gap-6">
    <!-- Левая карточка: Бонусный счёт -->
    <div class="flex-1 bg-white rounded-lg p-6 shadow">
      <h2 class="text-2xl font-bold mb-2">Бонусный счёт</h2>
      <p class="text-sm text-gray-500 mb-6">
        Информация о бонусах пользователя
      </p>

      <!-- Текущий баланс -->
      <div class="mb-4 flex flex-row justify-between items-center">
        <span class="block text-gray-600 text-lg font-bold">Текущий баланс:</span>
        <p class="text-4xl font-bold text-blue-600">{{ balance }}</p>
      </div>



      <div class="flex flex-col items-start w-full gap-4">
        <span class="block text-gray-600 text-lg font-bold">Реферальный код:</span>
        <div class="flex w-full">
          <InputText v-model="referralCode" readonly class="text-lg font-medium flex-1" />
          <Button icon="pi pi-copy" class="ml-2" @click="copyReferralCode" tooltip="Copy Referral Code" />
        </div>
      </div>

      <!-- Дата последнего обновления -->
      <div class="mt-4">
        <span class="block text-gray-600 text-sm">Последнее обновление</span>
        <p class="text-base text-gray-800">{{ lastUpdate }}</p>
      </div>
    </div>

    <!-- Divider between cards: vertical for desktop, horizontal for mobile -->
    <p-divider layout="vertical" class="hidden md:block"></p-divider>
    <p-divider layout="horizontal" class="block md:hidden"></p-divider>

    <!-- Правая карточка: История транзакций -->
    <div class="flex-1 bg-white rounded-lg p-6 shadow">
      <h2 class="text-2xl font-bold mb-2">История транзакций</h2>
      <p class="text-sm text-gray-500 mb-6">
        Последние бонусные операции
      </p>

      <!-- Список транзакций -->
      <ul class="space-y-4">
        <li v-for="(txn, index) in transactions" :key="index" class="flex flex-col justify-between ">
          <div class="flex flex-row justify-between">
            <!-- Левая часть: тип и описание -->
            <div>
              <p class="text-sm font-bold" :class="txn.isPositive ? 'text-green-600' : 'text-red-600'">
                {{ txn.type }}
              </p>
              <p class="text-gray-700 text-sm">{{ txn.label }}</p>
            </div>

            <!-- Правая часть: сумма и дата -->
            <div class="text-right">
              <p class="text-lg font-bold" :class="txn.isPositive ? 'text-green-600' : 'text-red-600'">
                {{ txn.isPositive ? '+' : '-' }}{{ txn.amount }}
              </p>
              <p class="text-gray-500 text-sm">{{ txn.date }}</p>
            </div>
          </div>
          <Divider />
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'


const balance = ref(450)
const referralCode = ref('TVNA2023')

function copyReferralCode() {
  navigator.clipboard.writeText(referralCode.value)
}
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
/* Дополнительные стили при необходимости */
</style>
