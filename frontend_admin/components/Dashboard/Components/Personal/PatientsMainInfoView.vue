<template>
  <div class="p-4 rounded border shadow-sm bg-white dark:bg-secondaryDark">
    <h2 class="text-2xl font-bold mb-4">{{ t("PatientsMainInfoView.sectionTitle") }}</h2>

    <div class="flex gap-10 overflow-x-auto flex-col md:flex-row">
      <div v-for="(columnGroups, colIndex) in normalizedGroups" :key="colIndex" class="flex-1 flex flex-col gap-6">
        <div v-for="group in columnGroups" :key="group.title.en">
          <h3 class="text-lg font-bold mb-2">{{ group.title[currentLanguage] || group.title["en"] || "" }}</h3>
          <div class="flex flex-col space-y-1">
            <div v-for="field in group.fields" :key="field" class="flex items-center justify-between">
              <span class="text-sm">
                {{ getFieldTitle(field) }}
              </span>
              <span class="ml-1 font-semibold" v-html="formatFieldValue(field)" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import _ from "lodash";
import { computed, watch } from "vue";
import { useI18n } from "vue-i18n";
const { currentFrontendUrl, currentUrl } = useURLState();
/* ------------------------------------------------------------------ */
/*  props & i18n                                                      */
/* ------------------------------------------------------------------ */
const { t } = useI18n();
const { currentLanguage } = useLanguageState();

const props = defineProps({
  itemData: { type: Object, default: () => ({}) },
  fieldGroups: { type: Array, default: () => [] },
  filteredFields: { type: Array, default: () => [] },
});

/* ------------------------------------------------------------------ */
/*  meta helpers                                                      */
/* ------------------------------------------------------------------ */
const fieldMetaMap = computed(() => {
  const map = {};
  props.filteredFields.forEach((meta) => {
    map[meta.name] = meta;
  });
  return map;
});

function getFieldTitle(name) {
  const meta = fieldMetaMap.value[name];
  if (!meta) return name;
  return meta.title?.[currentLanguage.value] || meta.title?.en || name;
}

/* ------------------------------------------------------------------ */
/*  translation helper                                                */
/* ------------------------------------------------------------------ */
function translateValue(rawValue, meta) {
  // avatar special-case (early exit)
  if (meta?.type === "image") {
    return rawValue?.url ? `<img src="${currentUrl.value + rawValue.url}" alt="avatar" class="w-8 h-8 rounded-full" />` : "—";
  }

  // nullish → dash
  if (_.isNil(rawValue) || rawValue === "") return "—";

  // Dates
  if (["birth_date", "created_at", "updated_at"].includes(meta?.name)) {
    return formatDate(rawValue);
  }

  // SELECT-like fields: use label if provided
  if (meta?.choices?.length) {
    const matched = meta.choices.find((choice) => _.isEqual(choice.value, rawValue) || _.isEqual(choice.value?.en, rawValue));
    if (matched) {
      return matched.label?.[currentLanguage.value] || matched.label?.en || matched.label;
    }
  }

  // Multilang object ({ en:'', ru:'', … })
  if (_.isPlainObject(rawValue)) {
    const lang = currentLanguage.value;
    return rawValue[lang] || rawValue.en || Object.values(rawValue)[0] || "—";
  }

  // Primitive fallback
  return String(rawValue);
}

/* ------------------------------------------------------------------ */
/*  public formatter for template                                     */
/* ------------------------------------------------------------------ */
function formatFieldValue(fieldName) {
  const meta = fieldMetaMap.value[fieldName];
  const value = props.itemData[fieldName];
  return translateValue(value, meta);
}

/* ------------------------------------------------------------------ */
/*  columns layout helper                                             */
/* ------------------------------------------------------------------ */
const normalizedGroups = computed(() => {
  const cols = [...new Set(props.fieldGroups.map((g) => g.column))].sort();
  const colIndex = Object.fromEntries(cols.map((c, i) => [c, i]));
  const grouped = _.groupBy(props.fieldGroups, (g) => colIndex[g.column]);
  return Object.values(grouped);
});

/* ------------------------------------------------------------------ */
/*  util: date → dd.mm.yyyy hh:mm                                     */
/* ------------------------------------------------------------------ */
// util: date → dd.mm.yyyy  (no time)
function formatDate (date) {
  if (!date) return '—'
  const d = new Date(date)
  if (isNaN(d)) return t('PatientsMainInfoView.invalidDate')

  return `${_.padStart(d.getDate(), 2, '0')}.` +
         `${_.padStart(d.getMonth() + 1, 2, '0')}.` +
         `${d.getFullYear()}`
}


/* ------------------------------------------------------------------ */
/*  debug                                                             */
/* ------------------------------------------------------------------ */
watch(props, (p) => console.log("Props changed:", p), { immediate: true });
</script>

<style scoped>
/* Add any needed styles */
</style>
