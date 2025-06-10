<template>
  <div class="w-full container mx-auto flex flex-col md:flex-row gap-6">
    <!-- Левая карточка: Бонусный счёт -->
    <Toast />
    <div class="flex-1 border bg-white dark:bg-secondaryDark rounded-lg p-6 shadow">
      <h2 class="text-2xl font-bold mb-2">{{ t("PointsTable.balanceCard") }}</h2>
      <p class="text-sm mb-6">
        {{ t("PointsTable.balanceSubtitle") }}
      </p>

      <!-- Текущий баланс -->
      <div class="mb-4 flex flex-row justify-between items-center">
        <span class="block text-lg font-bold"> {{ t("PointsTable.currentBalance") }}</span>
        <p class="text-4xl font-bold text-blue-600">{{ balance }}</p>
      </div>

      <div class="flex flex-col items-start w-full gap-4">
        <span class="block text-lg font-bold">{{ t("PointsTable.referralCode") }}</span>
        <div class="flex w-full">
          <InputText v-model="referralCode" readonly class="text-lg font-medium flex-1" />
          <Button icon="pi pi-copy" class="ml-2" @click="copyReferralCode" :tooltip="t('PointsTable.tooltipCopy')" />
        </div>
      </div>

      <!-- Дата последнего обновления -->
      <div class="mt-4">
        <span class="block text-sm">{{ t("PointsTable.lastUpdate") }}</span>
        <p class="text-base">{{ formattedLastUpdate }}</p>
      </div>
    </div>

    <!-- Правая карточка: История транзакций -->
    <div class="flex-1 border bg-white dark:bg-secondaryDark rounded-lg p-6 shadow">
      <h2 class="text-2xl font-bold mb-2">{{ t("PointsTable.transactionsCard") }}</h2>
      <p class="text-sm mb-6">
        {{ t("PointsTable.transactionsSubtitle") }}
      </p>

      <!-- Список транзакций -->
      <ul class="space-y-4 overflow-auto max-h-[280px] pr-4">
        <li v-for="(txn, index) in transactions" :key="index" class="flex flex-col justify-between">
          <div class="flex flex-row justify-between">
            <!-- Левая часть: тип и описание -->
            <div>
              <p class="text-sm font-bold" :style="{ color: txn.transaction_type.settings.color }">
                {{ txn.transaction_type[currentLanguage] || txn.transaction_type.en || '' }}
              </p>
              <p class="text-sm">{{ txn.title }}</p>
            </div>

            <!-- Правая часть: сумма и дата -->
            <div class="text-right">
              <p class="text-lg font-bold" :class="txn.amount > 0 ? 'text-green-600' : 'text-red-600'">
                {{ txn.amount > 0 ? "+" : "-" }}{{ txn.amount }}
              </p>
              <p class="text-sm">{{ formatDate(txn.date_time) }}</p>
            </div>
          </div>
          <Divider />
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useI18n } from "vue-i18n";
const { t } = useI18n();
const { currentLanguage } = useLanguageState();
// Props
const props = defineProps({
  itemData: {
    type: Object,
    default: () => ({}),
  },
});
const toast = useToast();
// Reactive data
const balance = ref(props.itemData.balance || 0);
const referralCode = ref(props.itemData.referral_code || "");
const lastUpdate = ref(props.itemData.last_updated || "");
const transactions = ref(props.itemData.transaction_history || []);

// Computed property for formatted last update
const formattedLastUpdate = computed(() => {
  return new Date(lastUpdate.value).toLocaleString("ru-RU", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
});

// Method to format transaction date
const formatDate = (date) => {
  return new Date(date).toLocaleString("ru-RU", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
};

// Method to copy referral code
const copyReferralCode = () => {
  navigator.clipboard.writeText(referralCode.value);
  toast.add({
    severity: "success",
    summary: t("PointsTable.toastTitle"),
    detail: t("PointsTable.toastBody"),
    life: 3000,
  });
};
</script>

<style scoped>
/* Дополнительные стили при необходимости */
</style>
