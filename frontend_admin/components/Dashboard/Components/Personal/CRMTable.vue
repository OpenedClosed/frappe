<!-- ~/components/VisitsTable.vue -->
<template>
  <div class="flex flex-col w-full gap-4 p-6 border-2 rounded-lg shadow-sm">
    <!-- Title -->
    <div class="flex flex-row gap-4 justify-start items-center" v-if="title">
      <h2 class="text-3xl font-semibold">
        {{ typeof title === "object" ? title[currentLanguage] || title.en : title }}
      </h2>
    </div>
    <InfoBanner v-if="!allFieldsPresent && crmBannerText" infoKey="crmBannerTextClosed">
      {{ crmBannerText }}
    </InfoBanner>

    <!-- Spinner while loading -->
    <div v-if="isLoading" class="flex justify-center p-8">
      <ProgressSpinner style="width: 50px; height: 50px" />
    </div>

    <!-- Visits list -->
    <div
      v-for="visit in tableData"
      :key="visit.id"
      class="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg border border-gray-200"
    >
      <!-- Date & time -->
      <div class="flex items-center gap-4">
        <i class="pi pi-calendar text-2xl text-primary-500" />
        <div class="flex flex-col">
          <span class="text-lg font-semibold">{{ formatDate(visit.visit_date) }}</span>
          <span class="text-sm text-gray-500">{{ visit.start }}–{{ visit.end }}</span>
        </div>
      </div>

      <!-- Doctor & status -->
      <div class="flex-1 flex flex-col md:flex-row md:items-center gap-2 md:gap-4">
        <span class="text-base">{{ visit.doctor }}</span>

        <span v-if="visit.status" class="inline-block px-3 py-1 rounded-full text-sm font-medium" :class="getStatusClass(visit.status)">
          {{ localize(visit.status) }}
        </span>
      </div>
    </div>

    <!-- Empty state -->
    <p v-if="!isLoading && tableData.length === 0" class="text-center text-gray-500">
      {{ t("CRMtable.empty") }}
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRouter, useRoute } from "#app";
import { useI18n } from "vue-i18n";
import InfoBanner from "./InfoBanner.vue";
const {  crmBannerText } = usePageState();

/* ---------- Props ---------- */
const props = defineProps({
  title: [String, Object],
  tableData: { type: Array, required: true },
  isLoading: { type: Boolean, default: false },

  /* pagination */
  paginator: { type: Boolean, default: false },
  first: { type: Number, default: 0 },
  rows: { type: Number, default: 10 },
  totalRecords: { type: Number, default: 0 },
});

/* ---------- Emits ---------- */
const emit = defineEmits(["page"]);

/* ---------- Composables ---------- */
const router = useRouter();
const route = useRoute();
const { t } = useI18n();
const { currentLanguage } = useLanguageState();

/* ---------- Helpers ---------- */
function formatDate(dateStr) {
  const d = new Date(dateStr);
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();
  return `${day}.${month}.${year}`; // → dd.mm.yyyy
}

function localize(obj) {
  if (typeof obj === "string") return obj;
  return obj?.[currentLanguage.value] || obj?.en || "";
}

function getStatusClass(statusObj) {
  // Fallback to English for class mapping
  const en = typeof statusObj === "string" ? statusObj : statusObj?.en;
  switch (en) {
    case "Confirmed":
    case "Подтверждён":
      return "text-green-700 bg-green-100";
    case "Cancelled":
    case "Отменён":
      return "text-red-700 bg-red-100";
    default:
      return "text-gray-700 bg-gray-100";
  }
}

function onPage(evt) {
  emit("page", evt);
}

function onClickEdit(id) {
  router.push({ name: "visit-id", params: { id } });
}
</script>

<style scoped>
/* Add any scoped styles you need here */
</style>
