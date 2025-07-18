<template>
  <div class="p-4 rounded border bg-white dark:bg-secondaryDark shadow-sm">
    <!-- Заголовок страницы -->
    <div class="mb-6 space-y-2">
      <h1 class="text-xl font-bold">{{ t("ContactInfoView.title") }}</h1>
      <InfoBanner v-if="!allFieldsPresent" infoKey="contactInfoClosed">
           {{ t("ContactInfoView.fillPersonalInfoNotice") }}
      </InfoBanner>
    </div>
    <!-- Контейнер, разбивающий на 2 колонки -->
    <div class="flex flex-row gap-8">
      <!-- Левая колонка -->
      <div class="flex-1 flex flex-col space-y-4">
        <!-- Email -->
        <div>
          <label class="block text-[13px] font-normal">
            {{ t("ContactInfoView.email") }}
          </label>
          <span class="text-[15px] font-bold">
            {{ itemData.email || "—" }}
          </span>
        </div>

        <!-- Phone -->
        <div>
          <label class="block text-[13px] font-normal">
            {{ t("ContactInfoView.phone") }}
          </label>
          <span class="text-[15px] font-bold">
            {{ formatPhone(itemData.phone) || "—" }}
          </span>
        </div>

        <!-- Address -->
        <div>
          <label class="block text-[13px] font-normal">
            {{ t("ContactInfoView.address") }}
          </label>
          <span class="text-[15px] font-bold">
            {{ itemData.address || "—" }}
          </span>
        </div>

        <!-- PESEL -->
        <div>
          <label class="block text-[13px] font-normal">
            {{ t("ContactInfoView.pesel") }}
          </label>
          <span class="text-[15px] font-bold">
            {{ itemData.pesel || "—" }}
          </span>
        </div>
        <!-- Passport -->
        <div>
          <label class="block text-[13px] font-normal">
            {{ t("ContactInfoView.passport") }}
          </label>
          <span class="text-[15px] font-bold">
            {{ itemData.passport || "—" }}
          </span>
        </div>
      </div>

      <!-- Правая колонка -->
      <div class="flex-1 flex flex-col space-y-4">
        <!-- Emergency Contact -->
        <div>
          <label class="block text-[13px] font-normal">
            {{ t("ContactInfoView.emergency") }}
          </label>
          <span class="text-[15px] font-bold flex flex-row items-center gap-2">
            {{ itemData.emergency_contact_name }} {{ formatPhone(itemData.emergency_contact_phone) }}
            <div v-if="itemData.emergency_contact_name && itemData.emergency_contact_phone" class="flex items-center">
              <div v-if="itemData.emergency_contact_consent" class="mt-2">
                <div class="bg-green-400 border border-green-400 py-2 rounded mb-2 w-[20px] h-[20px]"></div>
              </div>
              <div v-else class="mt-2">
                <div class="bg-red-400 border border-red-400 py-2 rounded mb-2 w-[20px] h-[20px]"></div>
              </div>
            </div>
            <div v-else>—</div>
          </span>
        </div>

        <!-- Last Update -->
        <div>
          <label class="block text-[12px] font-normal">
            {{ t("ContactInfoView.lastUpdate") }}
          </label>
          <span class="text-[14px] font-bold text-[#4F4F59]">
            {{ formatDate(itemData.updated_at) || "—" }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import _ from "lodash";
import { useI18n } from "vue-i18n";
import InfoBanner from "./InfoBanner.vue";
const { t } = useI18n();
/**
 * Props for receiving data from the parent component
 */
const props = defineProps({
  itemData: {
    type: Object,
    default: () => ({}),
  },
});


/**
 * Helper function to format dates with time
 */
function formatDate(date) {
  if (!date) return "—";
  try {
    const parsedDate = new Date(date);
    if (_.isDate(parsedDate) && !isNaN(parsedDate)) {
      return `${_.padStart(parsedDate.getDate(), 2, "0")}.${_.padStart(
        parsedDate.getMonth() + 1,
        2,
        "0"
      )}.${parsedDate.getFullYear()} ${_.padStart(parsedDate.getHours(), 2, "0")}:${_.padStart(parsedDate.getMinutes(), 2, "0")}`;
    }
    return "Invalid date";
  } catch (error) {
    console.error("Invalid date:", date);
    return "Invalid date";
  }
}
function formatPhone(phone) {
  if (!phone) return "";
  // Remove all non-digit characters except leading +
  let cleaned = phone.replace(/[^\d+]/g, "");
  if (cleaned[0] !== "+") cleaned = "+" + cleaned.replace(/^\+/, "");
  // Extract parts
  const match = cleaned.match(/^\+(\d{2})(\d{3})(\d{3})(\d{3})$/);
  if (match) {
    return `+${match[1]} (${match[2]}) ${match[3]}-${match[4]}`;
  }
  return phone; // fallback to original if not match
}
const requiredFields = [
  "email",
  "phone",
  "emergency_contact_name",
  "emergency_contact_phone",
  "emergency_contact_consent",
  "country",
  "region",
  "city",
  "street",
  "building_number",
  "apartment",
  "zip",
  "address",
];


const allFieldsPresent = computed(() =>
  requiredFields.every( field =>
    props.itemData[field] !== null &&
    props.itemData[field] !== undefined &&
    props.itemData[field] !== ""))
</script>

<style scoped>
/* Add additional styles if necessary */
</style>
