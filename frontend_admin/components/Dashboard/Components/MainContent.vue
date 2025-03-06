<!-- pages/admin/[group]/[entity]/index.vue -->
<template>
  <div class="flex flex-col flex-1 shadow-lg max-w-full overflow-x-auto">
    <!-- Main Layout with Sidebar and DataTable -->
    <div class="max-w-full flex flex-row flex-1 w-full gap-4 p-4 justify-center">
      <!-- Navigation Sidebar Component -->
      <NavigationSidebar :navItems="navItems" />

      <!-- Check if group is "knowledge-base" -->
      <div v-if="currentGroup === 'knowledge-base'" class="flex flex-col basis-11/12 min-w-0 justify-start">
        <KnowledgeBase />
      </div>

      <!-- Default behavior: Show Data Table -->
      <div v-else-if="currentEntity && !currentId" class="flex flex-col basis-11/12 min-w-0 justify-between">
        <DynamicDataTable
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

      <div v-else class="flex flex-col basis-11/12 min-w-0 justify-start">
        <MainForm />
      </div>
    </div>

    <!-- Filter Dialog -->
    <Dialog header="Filter Options" v-model:visible="showFilter" :modal="true" :closable="true" :style="{ width: '25rem' }">
      <!-- Add additional filter options here -->
      <!-- <DateRangeFilter @applyFilter="applyDateFilter" /> -->
    </Dialog>

    <!-- Toast for Notifications -->
    <Toast ref="toast" position="top-right" />
  </div>
</template>

<script setup>
/**
 * pages/admin/[group]/[entity]/index.vue
 *
 * This component uses a two-level route scheme:
 *   /admin/:group/:entity
 *
 * - :group   => e.g. "users", "chats"
 * - :entity  => e.g. "users", "chat_sessions"
 *
 * It fetches adminData from /admin/info, renders a sidebar (NavigationSidebar),
 * and displays data in a DynamicDataTable with optional filtering and export.
 */
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAsyncData, useNuxtApp } from "#app"; // Nuxt 3 usage
import { debounce } from "lodash";

// Components
import NavigationSidebar from "./NavigationSidebar.vue";
import DynamicDataTable from "./DynamicDataTable.vue";
import MainForm from "~/components/Dashboard/Components/Form/MainForm.vue";
import KnowledgeBase from "~/components/Dashboard/Components/KnowledgeBase.vue";

// ------------------ State & Refs ------------------
const showFilter = ref(false);
const searchQuery = ref("");
const dateRange = ref({ start: null, end: null });

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
const toast = ref(null);

// ------------------ Data Fetching ------------------
/**
 * Fetch adminData from /admin/info
 * This is where your entire config is loaded (groups, entities, etc.).
 */
async function getAdminData() {
  let responseData;
  try {
    const response = await useNuxtApp().$api.get("api/admin/info");
    responseData = response.data;
    console.log("AdminData = ", responseData);
  } catch (err) {
    if (err.response) {
      console.log(err.response);
    } else {
      console.error("Error fetching admin data:", err);
    }
  }
  return responseData;
}

import * as XLSX from "xlsx";

const onExportToExcel = async () => {
  try {
    isLoading.value = true;

    // Fetch all data without pagination
    const response = await useNuxtApp().$api.get(`api/admin/${currentEntity.value}/`);
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

    toast.value?.add({
      severity: "success",
      summary: "Export Successful",
      detail: "Data exported to Excel successfully",
      life: 3000,
    });
  } catch (error) {
    console.error("Export Error:", error);
    toast.value?.add({
      severity: "error",
      summary: "Export Failed",
      detail: "Failed to export data.",
      life: 3000,
    });
  } finally {
    isLoading.value = false;
  }
};

// Use Nuxt's useAsyncData to load adminData once
const { data: adminData } = await useAsyncData("adminData", getAdminData);

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
      // The route for each entity = /admin/groupKey/entity.registered_name
      const routePath = `/admin/${groupKey}/${entity.registered_name}`;
      validCombos.push({ group: groupKey, entity: entity.registered_name });

      const itemName = entity.model.verbose_name;
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
    toast.value?.add({
      severity: "error",
      summary: "Error",
      detail: "No available data.",
      life: 3000,
    });
    return;
  }

  // If route doesn't have :group or we can't find it in data => redirect to first group
  if ((!currentGroup.value || !data[currentGroup.value]) && currentGroup.value !== "knowledge-base") {
    const firstGroup = groupKeys[0];
    const firstEntity = data[firstGroup].entities[0]?.registered_name;
    if (firstGroup && firstEntity) {
      toast.value?.add({
        severity: "warn",
        summary: "Invalid Group",
        detail: `Redirecting to: /admin/${firstGroup}/${firstEntity}`,
        life: 3000,
      });
      router.replace(`/admin/${firstGroup}/${firstEntity}`);
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
      toast.value?.add({
        severity: "warn",
        summary: "Invalid Entity",
        detail: `Redirecting to: /admin/${currentGroup.value}/${firstEntity}`,
        life: 3000,
      });
      router.replace(`/admin/${currentGroup.value}/${firstEntity}`);
    }
    return;
  }

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
const pageSize = ref(10);
const totalRecords = ref(0);

// ------------------ Table Data Fetching & Display ------------------
/**
 * Query the actual table data from /admin/:entity/
 */
const fetchTableData = async () => {
  if (!currentEntity.value) {
    console.warn("No entity specified in the route.");
    return;
  }
  isLoading.value = true;

  try {
    // Use query parameters for pagination
    const response = await useNuxtApp().$api.get(
      `api/admin/${currentEntity.value}/?page_size=${pageSize.value}&page=${currentPage.value}&order=-1`,
      {
        params: {
          page: currentPage.value,
          page_size: pageSize.value,
        },
      }
    );

    tableDataOriginal.value = response.data.data; // All records for this page
    totalRecords.value = response.data.meta.total_count;

    console.log("tableDataOriginal =", tableDataOriginal.value);
    console.log("Pagination meta =", response.data.meta);
  } catch (error) {
    console.error("Error fetching table data:", error);
    toast.value?.add({
      severity: "error",
      summary: "Error",
      detail: "Failed to load table data.",
      life: 3000,
    });
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
