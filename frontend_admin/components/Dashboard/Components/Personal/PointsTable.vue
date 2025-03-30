<template>
  <div class="w-full container mx-auto px-4 py-8 flex flex-col md:flex-row gap-6">
    <!-- Левая карточка: Бонусный счёт -->
     <Toast/>
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
        <p class="text-base text-gray-800">{{ formattedLastUpdate }}</p>
      </div>
    </div>



    <!-- Правая карточка: История транзакций -->
    <div class="flex-1 bg-white rounded-lg p-6 shadow">
      <h2 class="text-2xl font-bold mb-2">История транзакций</h2>
      <p class="text-sm text-gray-500 mb-6">
        Последние бонусные операции
      </p>

      <!-- Список транзакций -->
      <ul class="space-y-4 overflow-auto max-h-[280px] pr-4">
        <li v-for="(txn, index) in transactions" :key="index" class="flex flex-col justify-between">
          <div class="flex flex-row justify-between">
            <!-- Левая часть: тип и описание -->
            <div>
              <p class="text-sm font-bold" :style="{ color: txn.transaction_type.settings.color }">
                {{ txn.transaction_type.ru }}
              </p>
              <p class="text-gray-700 text-sm">{{ txn.title }}</p>
            </div>

            <!-- Правая часть: сумма и дата -->
            <div class="text-right">
              <p class="text-lg font-bold" :class="txn.amount > 0 ? 'text-green-600' : 'text-red-600'">
                {{ txn.amount > 0 ? '+' : '-' }}{{ txn.amount }}
              </p>
              <p class="text-gray-500 text-sm">{{ formatDate(txn.date_time) }}</p>
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

// Props
const props = defineProps({
  itemData: {
    type: Object,
    default: () => ({})
  }
})
const toast = useToast();
// Reactive data
const balance = ref(props.itemData.balance || 0)
const referralCode = ref(props.itemData.referral_code || '')
const lastUpdate = ref(props.itemData.last_updated || '')
const transactions = ref(props.itemData.transaction_history || [])

// Computed property for formatted last update
const formattedLastUpdate = computed(() => {
  return new Date(lastUpdate.value).toLocaleString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
})

// Method to format transaction date
const formatDate = (date) => {
  return new Date(date).toLocaleString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Method to copy referral code
const copyReferralCode = () => {
  navigator.clipboard.writeText(referralCode.value);
  toast.add({
    severity: 'success',
    summary: 'Код скопирован',
    detail: 'Реферальный код успешно скопирован в буфер обмена!',
    life: 3000
  });
};
</script>

<style scoped>
/* Дополнительные стили при необходимости */
</style>
