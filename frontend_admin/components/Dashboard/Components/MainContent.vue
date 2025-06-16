<!-- pages/${currentPageName.value}/[group]/[entity]/index.vue -->
<template>
  <div
    class="flex flex-col flex-1 shadow-lg max-w-full overflow-x-auto bg-secondaryLight"
    :class="[currentPageName === 'personal_account' ? '' : '']"
  >
    <!-- Main Layout with Sidebar and DataTable -->
    <div
      class="max-w-full flex flex-row flex-1 w-full max-w-full"
      :class="[currentPageName === 'personal_account' ? 'flex-col justify-start' : 'flex-row justify-between']"
    >
      <!-- Navigation Sidebar Component -->
      <NavigationSidebar class="flex justify-start" v-if="currentPageName === 'admin'" :navItems="navItems" />

      <InfoHeader v-if="currentPageName === 'personal_account'" />
      <NavigationSidebarTabs v-if="currentPageName === 'personal_account'" :navItems="navItems" />

      <div v-if="(isLoading || isLoadingData) && currentPageName === 'personal_account'" class="flex justify-center items-center w-full h-full p-8">
        <Loader style="width: 50px; height: 50px" />
      </div>
      <div v-else class="flex flex-col flex-1 min-w-0 max-w-full">
        <!-- Check if group is "knowledge-base" -->
        <div v-if="currentGroup === 'knowledge-base'" class="flex flex-col flex-1 min-w-0 justify-start">
          <KnowledgeBase />
        </div>
        <div v-else-if="currentGroup === 'support'" class="flex flex-col flex-1 flex-1 min-h-0 min-w-0 justify-start p-4">
          <SupportPage class="m-4" />
        </div>
        <div
          v-else-if="currentEntity === 'patients_health_survey' && !currentId"
          class="flex flex-col flex-1 min-w-0 justify-start items-center p-4"
        >
          <Button
            @click="onClickCreate"
            icon="pi pi-plus"
            class="max-w-[350px]"
            :label="t('MainContent.buttons.fillHealthSurvey')"
          ></Button>
        </div>
        <div
          v-else-if="currentEntity === 'patients_main_info' && !currentId"
          class="flex flex-col flex-1 min-w-0 justify-start items-center p-4"
        >
          <Button @click="onClickCreate" icon="pi pi-plus" class="max-w-[350px]" :label="t('MainContent.buttons.fillMainInfo')"></Button>
        </div>
        <div
          v-else-if="currentEntity === 'patients_contact_info' && !currentId"
          class="flex flex-col flex-1 min-w-0 justify-start items-center p-4"
        >
          <Button @click="onClickCreate" icon="pi pi-plus" class="max-w-[350px]" :label="t('MainContent.buttons.fillContactInfo')"></Button>
        </div>
        <div
          v-else-if="currentEntity === 'patients_consents' && !currentId"
          class="flex flex-col flex-1 min-w-0 justify-start items-center p-4"
        >
          <Button @click="onClickCreate" icon="pi pi-plus" class="max-w-[350px]" :label="t('MainContent.buttons.fillConsents')"></Button>
        </div>
        <div
          v-else-if="currentEntity === 'crm_appointments' && !currentId"
          class="flex flex-col flex-1 min-w-0 justify-start items-center p-4"
        >
          <CRMTable
            :title="currentEntityName"
            :isInline="isEntityInline"
            :displayedColumns="displayedColumns"
            :tableData="tableDataOriginal"
            :isLoading="isLoading"
            :fieldOptions="fieldOptions"
            :rows="pageSize"
            :first="(currentPage - 1) * pageSize"
            :totalRecords="totalRecords"
            :paginator="true"
            @page="onPageChange"
            @exportToExcel="onExportToExcel"
            @showFilter="showFilterDialog"
            @filterChange="handleFilterChange"
          />
        </div>
        <div
          v-else-if="currentEntity === 'patients_family' && !currentId"
          class="flex w-full flex-col flex-1 min-w-0 justify-start items-center p-4"
        >
          <FamilyTable
            :title="currentEntityName"
            :isInline="isEntityInline"
            :displayedColumns="displayedColumns"
            :tableData="tableDataOriginal"
            :isLoading="isLoading"
            :fieldOptions="fieldOptions"
            :rows="pageSize"
            :first="(currentPage - 1) * pageSize"
            :totalRecords="totalRecords"
            :paginator="true"
            @page="onPageChange"
            @exportToExcel="onExportToExcel"
            @showFilter="showFilterDialog"
            @filterChange="handleFilterChange"
          />
        </div>
        <div
          v-else-if="currentEntity === 'chat_sessions' && !currentId"
          class="flex  flex-col min-w-0 max-w-full justify-start items-center m-4"
        >
          <EmbeddedChat
            class="w-full"
            v-if="filteredTableData.length > 0"
            :id="filteredTableData[0]?.chat_id"
            :chatsData="filteredTableData"
            :totalRecords="totalRecords"
            @page="changeCurrentPage"
            :isRoomsLoading="isLoading"
            @exportToExcel="onExportToExcel"
          />
        </div>

        <!-- Default behavior: Show Data Table -->
        <div v-else-if="currentEntity && !currentId" class="flex flex-col flex-1 min-w-0 justify-between m-4">
          <DynamicDataTable
            v-if="currentPageInstances > 1 || currentPageName === 'admin'"
            :title="currentEntityName"
            :isInline="isEntityInline"
            :displayedColumns="displayedColumns"
            :tableData="filteredTableData"
            :isLoading="isLoading"
            :fieldOptions="fieldOptions"
            :rows="pageSize"
            :first="(currentPage - 1) * pageSize"
            :totalRecords="totalRecords"
            :paginator="true"
            @page="onPageChange"
            @exportToExcel="onExportToExcel"
            @showFilter="showFilterDialog"
            @filterChange="handleFilterChange"
          />
        </div>

        <div v-else class="flex flex-col flex-1 min-w-0 justify-start">
          <MainForm />
        </div>
      </div>
    </div>

    <!-- Filter Dialog -->
    <Dialog
      :header="t('MainContent.dialog.filterOptions')"
      v-model:visible="showFilter"
      :modal="true"
      :closable="true"
      :style="{ width: '25rem' }"
    >
      <!-- Add additional filter options here -->
      <!-- <DateRangeFilter @applyFilter="applyDateFilter" /> -->
    </Dialog>

    <!-- Toast for Notifications -->
    <Toast />
  </div>
</template>

<script setup>
/**
 * pages/${currentPageName.value}/[group]/[entity]/index.vue
 *
 * This component uses a two-level route scheme:
 *   /${currentPageName.value}/:group/:entity
 *
 * - :group   => e.g. "users", "chats"
 * - :entity  => e.g. "users", "chat_sessions"
 *
 * It fetches adminData from /${currentPageName.value}/info, renders a sidebar (NavigationSidebar),
 * and displays data in a DynamicDataTable with optional filtering and export.
 */
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { navigateTo, useAsyncData, useNuxtApp } from "#app"; // Nuxt 3 usage
import { debounce } from "lodash";

// Components
import InfoHeader from "./Personal/InfoHeader.vue";
import NavigationSidebarTabs from "./Personal/NavigationSidebarTabs.vue";
import NavigationSidebar from "./NavigationSidebar.vue";
import DynamicDataTable from "./DynamicDataTable.vue";
import MainForm from "~/components/Dashboard/Components/Form/MainForm.vue";
import KnowledgeBase from "~/components/Dashboard/Components/KnowledgeBase.vue";
import FamilyTable from "~/components/Dashboard/Components/Personal/FamilyTable.vue";
import CRMTable from "~/components/Dashboard/Components/Personal/CRMTable.vue";
import SupportPage from "~/components/Dashboard/Components/Personal/SupportPage.vue";
import EmbeddedChat from "~/components/AdminChat/EmbeddedChat.vue";
// ------------------ State & Refs ------------------
import { useI18n } from "vue-i18n";
const { t } = useI18n();
const showFilter = ref(false);
const searchQuery = ref("");
const dateRange = ref({ start: null, end: null });
const { currentPageName, currentPageInstances } = usePageState();

const selectedField = ref(null);
const fieldOptions = ref([
  { label: "Все поля", value: null }, // Option for universal search
  // More dynamic options can be pushed here once we know the fields
]);

// Display / Table
const navItems = ref([]);
const displayedColumns = ref([]);
const tableDataOriginal = ref([]);
const isLoading = ref(false);
const isLoadingData = ref(false);
const currentEntityName = ref("");
const isEntityInline = ref(false);

// Routing
const route = useRoute();
const router = useRouter();
const currentGroup = computed(() => route.params.group); // :group
const currentEntity = computed(() => route.params.entity); // :entity
const currentId = computed(() => route.params.id); // :entity
const { currentLanguage } = useLanguageState();
// Toast reference (PrimeVue)
const toast = useToast();
const onClickCreate = () => {
  // Чтобы узнать currentGroup, currentEntity, можем взять их из $route.params:
  const { group, entity } = router.currentRoute.value.params;

  // Переходим на: /${currentPageName.value}/..../..../id
  navigateTo(`/${currentPageName.value}/${currentGroup.value}/${currentEntity.value}/new`);
};

function changeCurrentPage(page) {
  currentPage.value = page + 1;
  console.log("page =", currentPage.value);
  fetchTableData();
}
// ------------------ Data Fetching ------------------
/**
 * Fetch adminData from /${currentPageName.value}/info
 * This is where your entire config is loaded (groups, entities, etc.).
 */

async function getAdminData() {
  isLoadingData.value = true;
  let responseData;
  try {
    const response = await useNuxtApp().$api.get(`api/${currentPageName.value}/info`);
    responseData = response.data;
    console.log("AdminData = ", responseData);
  } catch (err) {
    if (err.response) {
      console.log(err.response);
    } else {
      console.error("Error fetching admin data:", err);
    }
    isLoadingData.value = false;
  }
  isLoadingData.value = false;
  return responseData;
}

import * as XLSX from "xlsx";
const onExportToExcel = async () => {
  try {
    isLoading.value = true;

    // Fetch all data without pagination
    const response = await useNuxtApp().$api.get(`api/${currentPageName.value}/${currentEntity.value}/`);
    const fullData = response.data;

    console.log("Exporting data to Excel:", fullData);

    // Map data to match displayed columns
    const data = fullData.map((row) =>
      displayedColumns.value.reduce((acc, column) => {
        acc[column.header] = row[column.field] ?? ""; // Use headers instead of field names
        return acc;
      }, {})
    );

    // Create a worksheet from the JSON data
    const worksheet = XLSX.utils.json_to_sheet(data);

    // Auto-adjust column widths based on max text length
    const columnWidths = displayedColumns.value.map((col) => {
      const maxDataLength = Math.max(
        col.header.length, // Header text length
        ...data.map((row) => (row[col.header] ? row[col.header].toString().length : 0)) // Longest content in column
      );
      return { wch: maxDataLength + 2 }; // +2 for padding
    });

    // Apply column widths
    worksheet["!cols"] = columnWidths;

    // Create workbook & append the sheet
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Data");

    // Save as Excel file
    XLSX.writeFile(workbook, `${currentEntity.value}_export.xlsx`);

    toast.add({
      severity: "success",
      summary: t("MainContent.toast.exportSuccessSummary"),
      detail: t("MainContent.toast.exportSuccessDetail"),
      life: 3000,
    });
  } catch (error) {
    console.error("Export Error:", error);
    toast.add({
      severity: "error",
      summary: t("MainContent.toast.exportFailSummary"),
      detail: t("MainContent.toast.exportFailDetail"),
      life: 3000,
    });
  } finally {
    isLoading.value = false;
  }
};

// Use Nuxt's useAsyncData to load adminData once
const { data: adminData } = await useAsyncData("adminDataInfo", getAdminData);

/**
 * Build the navItems from the adminData structure.
 * navItems is an array of objects that your NavigationSidebar will iterate over.
 * We also track all valid (group, entity) combos for route validation.
 */
function processAdminData(data) {
  if (!data || typeof data !== "object") {
    console.warn("Invalid admin data format.");
    return [];
  }

  const processed = [];
  // We'll store valid combos for easier route validation
  const validCombos = []; // e.g. [{ group: 'users', entity: 'users' }, ...]

  Object.keys(data).forEach((groupKey) => {
    const group = data[groupKey];
    console.log("group =", group);
    const header = group.verbose_name || groupKey;
    const iconClass = group.icon || "pi pi-folder";

    // Each group can have multiple entities
    const items = group.entities.map((entity) => {
      // The route for each entity = /${currentPageName.value}/groupKey/entity.registered_name
      console.log("entity =", entity);
      const routePath = `/${currentPageName.value}/${groupKey}/${entity.registered_name}`;
      validCombos.push({ group: groupKey, entity: entity.registered_name });

      const itemName = entity.model.plural_name;
      // console.log("entity =", entity);
      return {
        name: itemName,
        route: routePath,
        iconClass: entity.model.icon || "pi pi-file",
        isInline: entity.model.is_inline,
      };
    });

    processed.push({
      header,
      icon: iconClass,
      items,
    });
  });

  navItems.value = processed;
  return validCombos;
}

// ------------------ Route Validation ------------------
/**
 * Check if the current route (:group, :entity) is valid.
 * If not valid, redirect to the first available route.
 */
function validateRoute(data, validCombos) {
  const groupKeys = Object.keys(data || {});
  if (!groupKeys.length) {
    console.error("No groups found in adminData. Nothing to display.");
    toast.add({
      severity: "error",
      summary: t("MainContent.toast.errorSummary"),
      detail: t("MainContent.toast.noDataDetail"),
      life: 3000,
    });
    return;
  }

  // If route doesn't have :group or we can't find it in data => redirect to first group
  if ((!currentGroup.value || !data[currentGroup.value]) && currentGroup.value !== "knowledge-base" && currentGroup.value !== "support") {
    const firstGroup = groupKeys[0];
    const firstEntity = data[firstGroup].entities[0]?.registered_name;
    if (firstGroup && firstEntity) {
      // toast.add({
      //   severity: "warn",
      //   summary:t('MainContent.toast.invalidGroupSummary') ,
      //   detail: `${t('MainContent.toast.redirectDetail')} /${currentPageName.value}/${firstGroup}/${firstEntity}`,
      //   life: 3000,
      // });
      router.replace(`/${currentPageName.value}/${firstGroup}/${firstEntity}`);
    }
    return;
  }

  // Check if current :entity is valid within the group
  const groupConfig = data[currentGroup.value];
  if (!groupConfig) {
    // fallback
    return;
  }
  const foundEntity = groupConfig.entities.find((e) => e.registered_name === currentEntity.value);
  if (!foundEntity) {
    // If invalid entity, pick the first entity of the group
    const firstEntity = groupConfig.entities[0]?.registered_name;
    if (firstEntity) {
      // toast.add({
      //   severity: "warn",
      //   summary: "Invalid Entity",
      //   detail: `${t('MainContent.toast.redirectDetail', { route })} /${currentPageName.value}/${currentGroup.value}/${firstEntity}`,
      //   life: 3000,
      // });
      router.replace(`/${currentPageName.value}/${currentGroup.value}/${firstEntity}`);
    }
    return;
  }

  console.log("foundEntity =", foundEntity.model.max_instances_per_user);
  console.log("tableDataOriginal =", tableDataOriginal.value);

  // If we are here, the route is valid => set the "currentEntityName"
  currentEntityName.value = foundEntity.model?.verbose_name || foundEntity.model?.name || currentEntity.value;
  isEntityInline.value = foundEntity.model.is_inline;
}

/**
 * Return the entity config object from adminData for the current route.
 */
function findEntityConfig(data, groupKey, entityKey) {
  if (!groupKey || !entityKey) return null;
  if (!data[groupKey]) return null;
  return data[groupKey].entities.find((e) => e.registered_name === entityKey) || null;
}

// Add near your other refs
const currentPage = ref(1);
const pageSize = ref(12);
const totalRecords = ref(0);

function parseError(error) {
  console.log("HERE");
  console.log("Parsing error:", error);
  if (error.response && error.response.data) {
    const data = error.response.data;
    console.log("Error data:", data);

    let toastMessage = "";

    if (data.detail) {
      if (typeof data.detail === "string") {
        toastMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        toastMessage = data.detail.map((e) => e.msg || e).join(", ");
      } else if (typeof data.detail === "object") {
        const isLangKeyed = Object.keys(data.detail).every((key) => ["en", "ru", "pl", "uk", "ka", "de"].includes(key));
        if (isLangKeyed) {
          toastMessage = data.detail[currentLanguage.value] || Object.values(data.detail)[0];
        } else {
          toastMessage = Object.values(data.detail).flat().join(", ");
        }
      }

      toast.add({
        severity: "error",
        summary: t("toastMessages.errorTitle"),
        detail: toastMessage,
        life: 5000,
      });

      return toastMessage;
    }

    toastMessage = data.message || error.message;
    toast.add({
      severity: "error",
      summary: t("toastMessages.errorTitle"),
      detail: toastMessage,
      life: 5000,
    });

    return toastMessage;
  }

  const fallbackMessage = error.message || t("toastMessages.unknown");
  toast.add({
    severity: "error",
    summary: t("toastMessages.errorTitle"),
    detail: fallbackMessage,
    life: 5000,
  });

  return fallbackMessage;
}
// ------------------ Table Data Fetching & Display ------------------
/**
 * Query the actual table data from /${currentPageName.value}/:entity/
 */
/**
 * Загружает данные таблицы (или объект) с API.
 * Если max_instances_per_user === 1, то после получения ответа
 * сразу редиректим либо на форму создания, либо на форму редактирования.
 */
const fetchTableData = async () => {
  if (!currentEntity.value) {
    console.warn("No entity specified in the route.");
    return;
  }

  // Находим конфиг сущности, чтобы понять, single-instance она или нет
  const entityConfig = findEntityConfig(adminData.value, currentGroup.value, currentEntity.value);
  if (!entityConfig) {
    console.warn("No valid entityConfig found.");
    return;
  }

  isLoading.value = true;
  try {
    // let url = currentEntity.value === 'chat_sessions'?  `api/${currentPageName.value}/${currentEntity.value}/?page_size=30&order=-1` : `api/${currentPageName.value}/${currentEntity.value}/?page_size=${pageSize.value}&page=${currentPage.value}&order=-1`;
    let url = `api/${currentPageName.value}/${currentEntity.value}/?page_size=${pageSize.value}&page=${currentPage.value}&order=-1`;
    const response = await useNuxtApp().$api.get(url);

    let data = response.data.data ? response.data.data : response.data; // То, что вернёт бекенд
    console.log("MainData response.data =", response.data);
    console.log("MainData data =", data);
    // Если это single-instance сущность:
    currentPageInstances.value = entityConfig.model?.max_instances_per_user;
    if (entityConfig.model.max_instances_per_user === 1) {
      // Сервер может вернуть объект, а не массив
      if (!Array.isArray(data)) {
        data = data ? [data] : [];
      }
      if (!currentId.value && route.params.id !== "new") {
        // Если в ответе данные пусты, отправляем на создание
        if (data.length === 0) {
          navigateTo(`/${currentPageName.value}/${currentGroup.value}/${currentEntity.value}/new`);
          return; // прерываем дальнейшую отрисовку таблицы
        } else {
          // Если объект есть, у него должен быть id – редиректим на /:id
          console.log("data =", data);
          const recordId = data[0]?.id;
          if (recordId) {
            navigateTo(`/${currentPageName.value}/${currentGroup.value}/${currentEntity.value}/${recordId}`);
            return; // прерываем дальнейшую отрисовку таблицы
          } else {
            // На всякий случай, если id нет – тогда тоже создаём
            navigateTo(`/${currentPageName.value}/${currentGroup.value}/${currentEntity.value}/new`);
            return;
          }
        }
      }
    }

    // Иначе обычный сценарий: сохраняем массив данных и показываем таблицу
    tableDataOriginal.value = data || [];
    totalRecords.value = response.data.meta?.total_count || 0;
  } catch (error) {
    console.error("Error fetching table data:", error);
    if (error.response && error.response.status != 404) {
      parseError(error);
    }
  } finally {
    isLoading.value = false;
  }
};

function onPageChange(event) {
  // PrimeVue's DataTable uses zero-based 'page' in the event
  currentPage.value = event.page + 1; // Convert to 1-based
  pageSize.value = event.rows;
  fetchTableData();
}

/**
 * Based on the current entity config, build "displayedColumns" from the entity.model.list_display.
 */
function setupColumns(entityConfig) {
  if (!entityConfig || !entityConfig.model || !entityConfig.model.list_display) {
    displayedColumns.value = [];
    return;
  }

  // Map columns dynamically from entity config
  displayedColumns.value = entityConfig.model.list_display.map((field) => {
    // Find the field details
    const fieldConfig = entityConfig.model.fields.find((f) => f.name === field);
    console.log("fieldConfig =", fieldConfig);
    return {
      field,
      header: fieldConfig?.title[currentLanguage.value], // Fallback if title is missing
    };
  });
}

/**
 * Simple helper to capitalize the first letter of a string.
 */
function capitalizeFirstLetter(string) {
  return string.charAt(0).toUpperCase() + string.slice(1);
}

/**
 * Computed property that returns the table data after applying the search filter
 * and also appends blank rows if needed (to fill up to pageSize.value).
 */
const filteredTableData = computed(() => {
  let data = tableDataOriginal.value || [];

  // 1) Filter by selectedField (if not null) and searchQuery
  if (selectedField.value && searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    data = data.filter((row) => {
      const value = row[selectedField.value];
      return value ? value.toString().toLowerCase().includes(query) : false;
    });
  }
  // 2) Otherwise, if searchQuery but no selectedField => search all fields
  else if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    data = data.filter((row) => Object.values(row).some((val) => (val ? val.toString().toLowerCase().includes(query) : false)));
  }

  // 3) [Optional] Additional filtering (e.g., date range)...

  // 4) Append blank rows if needed
  const currentRowCount = data.length;
  if (currentRowCount < pageSize.value) {
    const blankRow = Object.fromEntries(displayedColumns.value.map((col) => [col.field, ""]));
    for (let i = 0; i < pageSize.value - currentRowCount; i++) {
      data.push({ ...blankRow, _isBlank: true });
    }
  }

  return data;
});

// ------------------ Filtering & Dialogs ------------------
const showFilterDialog = () => {
  showFilter.value = true;
};

const handleFilterChange = ({ searchQuery: sq, selectedField: sf }) => {
  searchQuery.value = sq;
  selectedField.value = sf;
};

// If you implement a date range filter:
function applyDateFilter(dateRangeData) {
  dateRange.value = dateRangeData;
  // Implement your date-based filtering in filteredTableData if needed
}

// ------------------ Excel Export ------------------
const exportToExcel = () => {
  // Convert data to a worksheet
  const ws = XLSX.utils.json_to_sheet(filteredTableData.value);

  // Calculate column widths
  const columnWidths = displayedColumns.value.map((col) => {
    const headerLength = col.header.length;
    const maxDataLength = Math.max(...filteredTableData.value.map((row) => (row[col.field] ? row[col.field].toString().length : 0)));
    return { wch: Math.max(headerLength, maxDataLength) + 2 };
  });
  ws["!cols"] = columnWidths;

  // Build workbook & export
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "LotusData");
  const fileName = `LotusData_${new Date().toISOString()}.xlsx`;
  XLSX.writeFile(wb, fileName);
};

// ------------------ Global Event Listeners (optional) ------------------
const { $listen } = useNuxtApp();

$listen("reloadTable", () => {
  fetchTableData();
});

$listen("exportToExcel", () => {
  exportToExcel();
});

// ------------------ Lifecycle ------------------
/**
 * Whenever we get adminData or the route changes, we must:
 * 1) Validate the route.
 * 2) Setup columns for the current entity.
 * 3) Fetch table data.
 */
onMounted(() => {
  initPage();
});

// Re-run init if route changes (e.g., from one group/entity to another)
watch([currentGroup, currentEntity], () => {
  initPage();
});

function initPage() {
  if (!adminData.value) {
    return;
  }

  // 1) Build sidebar & combos if not already done
  const validCombos = processAdminData(adminData.value);

  // 2) Validate the route and set the "currentEntityName"
  validateRoute(adminData.value, validCombos);

  // 3) Find the current entity config
  const entityConfig = findEntityConfig(adminData.value, currentGroup.value, currentEntity.value);
  // 4) Build displayed columns
  setupColumns(entityConfig);

  // 5) Optionally update fieldOptions for filtering (like a drop-down of fields):
  fieldOptions.value = [
    { label: "Все поля", value: null },
    ...displayedColumns.value.map((col) => ({
      label: col.header,
      value: col.field,
    })),
  ];

  // 6) Finally fetch the data
  fetchTableData();
}
</script>

<style scoped>
/* Modify or keep as desired */
.p-datatable.p-datatable-gridlines .p-paginator-bottom {
  border-width: 0 0 0 0;
}

.p-button.p-button-outlined {
  color: #6c757d;
  border: 1px solid #dee2e6;
  background-color: transparent;
}

.p-button.p-button-outlined:hover {
  background-color: #f8f9fa;
  border-color: #ced4da;
}

/* Remove the dark background of the DataTable loader */
.p-datatable-loading-overlay {
  background-color: transparent !important;
  /* Make background transparent */
}

/* Optional: Customize the spinner color or size */
.p-datatable-loader .p-spinner {
  /* Example: Change spinner color to blue */
  border-top-color: blue;
}

/* Styling for blank rows (if implemented in DynamicDataTable) */
.blank-row {
  background-color: #f9f9f9;
  /* Light grey background for blank rows */
}

.blank-row td {
  color: transparent;
  /* Make text invisible */
}

.blank-row:hover {
  background-color: #f1f1f1;
  /* Prevent hover effects on blank rows */
}
</style>
