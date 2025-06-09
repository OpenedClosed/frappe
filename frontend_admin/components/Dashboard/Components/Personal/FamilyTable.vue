<template>
  <div class="flex flex-col w-full gap-4 p-6 border-2 rounded-lg shadow-sm">
    <div class="flex flex-row gap-4 justify-start items-center">
      <h2 class="text-3xl font-semibold" v-if="title">
        {{ typeof title === "object" ? title[currentLanguage] || title.en : title }}
      </h2>
      <Button @click="onClickCreate" :label="t('FamilyTable.addMember')" size="small" icon="pi pi-plus" class=""></Button>
    </div>
    <div
      v-if="tableData && tableData.length > 0"
      v-for="(member, index) in tableData"
      :key="index"
      class="flex items-center justify-between p-4 rounded-lg border border-gray-200 gap-4"
    >
      <div class="flex-1 flex flex-row justify-start items-center gap-4">
        <Avatar icon="pi pi-user" class="mr-2" size="medium" shape="circle" />
        <div class="flex flex-col">
          <div class="text-xl font-bold text-black dark:text-white">
            {{ member.member_name || t("FamilyTable.nameUnknown") }}
          </div>
          <div class="text-sm">
            {{ t("FamilyTable.idPrefix") }} {{ member.phone }} •
            {{ member.relationship?.[currentLanguage] || member.relationship?.en || t("FamilyTable.relationshipUnknown") }}
          </div>
        </div>
      </div>
      <div v-if="member.status" class="inline-block px-3 py-1 rounded-full text-sm font-medium text-blue-600 bg-blue-100">
        {{ member.status?.[currentLanguage] || member.status?.en || t("FamilyTable.statusUnknown") }}
      </div>
      <!-- REQUEST-TYPE CHIP -->
      <div
        v-if="member.request_type"
        :class="['inline-block px-3 py-1 rounded-full text-sm font-medium', getRequestTypeClass(member.request_type)]"
      >
        {{ member.request_type?.[currentLanguage] || member.request_type?.en || t("FamilyTable.statusUnknown") }}
      </div>
      <div v-if="member.bonus_balance" class="inline-block px-3 py-1 rounded-full text-sm font-medium text-blue-600 bg-blue-100">
        {{ member.bonus_balance }} {{ t("FamilyTable.bonusSuffix") }}
      </div>
      <div v-else class="inline-block px-3 py-1 rounded-full text-sm font-medium text-blue-600 bg-blue-100">
        {{ t("FamilyTable.noBonus") }}
      </div>
      <Button
        icon="pi pi-user-edit"
        class="p-button-text p-button-md"
        @click="onClickEdit(member.id)"
        :aria-label="t('FamilyTable.editAria')"
      />
    </div>
    <Paginator
      v-if="paginator"
      :first="first"
      :rows="rows"
      :totalRecords="totalRecords"
      @page="onPage"
      class=""
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { navigateTo } from "#app";

// Example composables; adapt to your environment
const router = useRouter();
const { currentPageName } = usePageState();
const { currentLanguage } = useLanguageState();

import { useI18n } from "vue-i18n";
const { t } = useI18n();

// Accept the same props you had before
const props = defineProps({
  title: {
    type: [String, Object],
    required: true,
  },
  tableData: {
    type: Array,
    required: true,
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
  isInline: {
    type: Boolean,
    default: false,
  },

   /* pagination-specific props (all forwarded from the parent) */
  paginator: { type: Boolean, default: false },
  first: { type: Number, default: 0 },           // offset
  rows: { type: Number, default: 10 },           // rows per page
  totalRecords: { type: Number, default: 0 },    // total items
});
console.log("props.tableData", props.tableData);
watch(props, (newValue) => {
  console.log("props.tableData:", props.tableData);
});
const route = useRoute();
const currentGroup = computed(() => route.params.group);
const currentEntity = computed(() => route.params.entity);
const currentId = computed(() => route.params.id);

// Emit if you still need "exportToExcel" or other events
const emit = defineEmits(['page',"exportToExcel"]);
function onExportToExcel() {
  emit("exportToExcel");
}

function getRequestTypeClass(reqTypeObj) {
  // Try EN first; if missing, grab any value
  const en = reqTypeObj?.en ?? Object.values(reqTypeObj ?? {})[0] ?? "";
  switch (en) {
    case "Incoming request":
      return "text-green-700 bg-green-100";
    case "Outgoing request":
      return "text-yellow-700 bg-yellow-100";
    default:
      return "text-gray-700 bg-gray-100";
  }
}

function onPage(evt) {
  emit('page', evt); // evt = { first, rows, page }
}

// Example of using a computed label for "Create" / "Add"
const createLabel = computed(() => (currentPageName.value === "admin" ? "Создать" : "Добавить"));
function onClickEdit(id) {
  // Переходим на: /${currentPageName.value}/..../..../id
  router.push(`/${currentPageName.value}/${currentGroup.value}/${currentEntity.value}/${id}`);
}

function onClickCreate() {
  const { group, entity } = router.currentRoute.value.params;
  router.push(`/${currentPageName.value}/${group}/${entity}/new`);
}

// Example localization helper
function getLocalizedValue(fieldObj, lang) {
  if (!fieldObj) return "";
  if (typeof fieldObj === "string") {
    try {
      const parsed = JSON.parse(fieldObj);
      return parsed[lang] || parsed["en"] || fieldObj;
    } catch {
      return fieldObj;
    }
  }
  if (typeof fieldObj === "object") {
    const rawValue = fieldObj[lang] || fieldObj["en"] || "";
    return rawValue;
  }
  return fieldObj;
}
</script>

<style scoped>
/* Adjust or remove these as needed */
</style>
