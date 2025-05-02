<!-- components/DynamicDataTable.vue -->
<template>
  <div>
    <!-- Фильтры и управление таблицей -->
    <div class="max-w-full mb-4">
      <div class="outline outline-primary  rounded-md p-2">
        <div class="flex flex-col xl:flex-row items-center md:justify-between gap-4">
          <h2 class="font-bold text-lg ml-2">{{ title[currentLanguage] || title['en'] || '' }}</h2>
          <!-- <Dropdown
            class="min-w-[14rem]"
            v-model="internalSelectedField"
            :options="fieldOptions"
            placeholder="Select Field"
            @change="onFilterChange"
          />
          <InputText class="min-w-[14rem]" v-model="internalSearchQuery" placeholder="Search..." @input="onFilterChange" />
          <Button class="min-w-[14rem] xl:min-w-[8rem]" label="Filter" icon="pi pi-filter" @click="emitShowFilter" /> -->
          <div class="flex flex-col xl:flex-row items-center gap-4">
            <Button
            v-if="currentPageName === 'admin'"
              label="Экспорт в Excel"
              icon="pi pi-file-excel"
              class="p-button-success bg-green-600 hover:bg-green-500 text-white min-w-[14rem] xl:min-w-[8rem]"
              @click="onExportToExcel"
            />
            <Button :disabled="isInline" :label="createLabel" icon="pi pi-plus" class="p-button-success text-white  min-w-[14rem] xl:min-w-[8rem]" @click="onClickCreate" />
          </div>
        </div>
      </div>
    </div>

    <!-- Таблица данных -->
    <div
      :class="{ 'justify-end': isLoading, 'mb-4': isLoading, 'justify-center': !isLoading }"
      class="flex flex-col justify-center items-center max-w-full overflow-x-auto"
    >
      <DataTable
        :loading="isLoading"
        :value="tableData"
        :paginator="paginator"
        :rows="rows"
        :totalRecords="totalRecords"
        :first="first"
        :lazy="true"
        @page="onPageHandler"
        class="max-w-full w-full"
      >
        <template v-for="column in displayedColumns" :key="column.field">
          <Column class="h-[4rem]" :field="column.field" :header="column.header" :filter="true">
            <template #body="slotProps">
              <p
  :class="[getAlignmentClass(slotProps.data[column.field]), { 'font-bold': isTotalRow(slotProps.data) }]"
  class="truncate max-w-[10rem] overflow-hidden"
>
  {{
    column.field.toLowerCase().includes("date") || column.field.toLowerCase().includes("created")
      ? formatDate(slotProps.data[column.field])
      : getLocalizedValue(slotProps.data[column.field], currentLanguage.value) || " "
  }}
</p>

            </template>
          </Column>
        </template>
        <!-- Добавляем колонку "Actions" с кнопкой шестерёнки -->
        <Column header=" " bodyClass="text-center">
          <template #body="slotProps">
            <div class="flex items-center justify-end" v-if="!slotProps.data._isBlank">
              <Button
                icon="pi pi-cog"
                class="p-button-rounded p-button-text p-button-sm"
                @click="onClickEdit(slotProps.data)"
                aria-label="Edit"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { debounce } from "lodash";
import { navigateTo } from "#app";
const router = useRouter();

const { currentPageName } = usePageState()
const { currentLanguage } = useLanguageState();

const createLabel = computed(() => {
  return currentPageName.value === "admin" ? "Создать" : "Добавить";
});
const props = defineProps({
  title: {
    required: true,
  },
  displayedColumns: {
    type: Array,
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
  fieldOptions: {
    type: Array,
    default: () => [],
  },
  isInline: {
    type: Boolean,
    default: false,
  },

  // Pagination-related props
  paginator: {
    type: Boolean,
    default: false,
  },
  rows: {
    type: Number,
    default: 10,
  },
  totalRecords: {
    type: Number,
    default: 0,
  },
  first: {
    type: Number,
    default: 0,
  },

  // (Optional) these come from the parent's search binding
  searchQuery: {
    type: String,
    default: "",
  },
  selectedField: {
    type: [String, null],
    default: null,
  },
});
console.log("props", props.fieldOptions);


// Add the "createNew" event to the emitted events
const emit = defineEmits(["showFilter", "filterChange", "page",'exportToExcel']);

function onExportToExcel() {
  emit("exportToExcel");
}
/**
 * Safely get a localized string from an object that may contain nested JSON.
 *
 * @param {Object|String} fieldObj  The object or string that holds localized data.
 * @param {String} lang            Current language code (e.g. "ru" or "en").
 * @return {String}                Localized string to display.
 */
 function getLocalizedValue(fieldObj, lang) {
  // Default lang to "en" if not provided
  lang = lang || "en";
  
  if (!fieldObj) return "";

  // If fieldObj is a string, try to parse it as JSON
  if (typeof fieldObj === "string") {
    try {
      const parsedObj = JSON.parse(fieldObj);
      if (parsedObj && typeof parsedObj === "object") {
        // Check if the key exists before returning
        return parsedObj[lang] !== undefined
          ? parsedObj[lang]
          : parsedObj["en"] !== undefined
          ? parsedObj["en"]
          : fieldObj;
      }
      return fieldObj;
    } catch (e) {
      return fieldObj;
    }
  }

  // If fieldObj is an object, safely check for the keys
  if (typeof fieldObj === "object") {
    if (fieldObj[lang] !== undefined) return fieldObj[lang];
    if (fieldObj["en"] !== undefined) return fieldObj["en"];
  }
  
  return "";
}

// Handler for the plus button click event:
const onClickCreate = () => {
  // Чтобы узнать currentGroup, currentEntity, можем взять их из $route.params:
  const { group, entity } = router.currentRoute.value.params;

  // Переходим на: /${currentPageName.value}/..../..../id
  router.push(`/${currentPageName.value}/${group}/${entity}/new`);
};
const onPageHandler = (event) => {
  // event.page is 0-based index
  // event.rows is the new 'rows per page'
  // event.first is 0-based index of the first row in the new page
  emit("page", event);
};
// Внутренние состояния для управления фильтрами
const internalSearchQuery = ref(props.searchQuery || "");
const internalSelectedField = ref(props.selectedField || null);

// Watch для синхронизации внешних пропсов с внутренними состояниями
watch(
  () => props.searchQuery,
  (newVal) => {
    internalSearchQuery.value = newVal;
  }
);
watch(
  () => props.selectedField,
  (newVal) => {
    internalSelectedField.value = newVal;
  }
);

// Обработчик изменения фильтров с дебаунсом
const debouncedFilterChange = debounce(() => {
  emit("filterChange", {
    searchQuery: internalSearchQuery.value,
    selectedField: internalSelectedField.value,
  });
}, 300);

const onFilterChange = () => {
  debouncedFilterChange();
};

function onClickEdit(rowData) {
  // Предположим, в вашем объекте rowData есть поле "id", которое нужно передавать
  // Если поле называется как-то иначе (например, _id), замените тут на нужное.
  const id = rowData.id;

  // Чтобы узнать currentGroup, currentEntity, можем взять их из $route.params:
  const { group, entity } = router.currentRoute.value.params;

  // Переходим на: /${currentPageName.value}/..../..../id
  router.push(`/${currentPageName.value}/${group}/${entity}/${id}`);
}
// Эмитирование события для открытия диалога фильтрации
const emitShowFilter = () => {
  emit("showFilter");
};

// Фильтрация данных таблицы на основе поиска и выбранного поля
const filteredTableData = computed(() => {
  if (!internalSearchQuery.value || !internalSelectedField.value) return props.tableData;

  return props.tableData.filter((row) => {
    const fieldValue = row[internalSelectedField.value];
    if (fieldValue) {
      return fieldValue.toString().toLowerCase().includes(internalSearchQuery.value.toLowerCase());
    }
    return false;
  });
});

// Функция форматирования даты
const formatDate = (date) => {
  if (!date || date === " ") return " ";
  const parsedDate = new Date(date);
  const day = String(parsedDate.getDate()).padStart(2, "0");
  const month = String(parsedDate.getMonth() + 1).padStart(2, "0");
  const year = String(parsedDate.getFullYear()).slice(-2);
  return `${day}.${month}.${year}`;
};

// Функция форматирования значения
const formatValue = (value) => {
  return value;
};

// Класс выравнивания
const getAlignmentClass = (input) => {
  if (typeof input === "number") {
    return "text-right";
  }
  if (typeof input === "string") {
    const trimmedInput = input.trim();
    if (trimmedInput.endsWith("%")) {
      const numberPart = trimmedInput.slice(0, -1).trim();
      const parsedNumber = parseFloat(numberPart);
      if (!isNaN(parsedNumber) && isFinite(parsedNumber)) {
        return "text-right";
      }
    }
  }
  return "text-left";
};

// Функция проверки, является ли строка итоговой
const isTotalRow = (data) => {
  // Реализуйте логику определения итоговой строки, если требуется
  return false;
};
</script>

<style scoped>
/* Добавьте стили при необходимости */
</style>
