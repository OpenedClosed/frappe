import { watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { usePrimeVue } from 'primevue/config';

export const usePrimeVueLocale = () => {
  const { locale, t } = useI18n();
  const primevue = usePrimeVue();

  // Locale-specific configurations that can't be translated
  const localeSpecificConfig = {
    en: {
      firstDayOfWeek: 1,
      dateFormat: 'dd/mm/yy'
    },
    ru: {
      firstDayOfWeek: 1,
      dateFormat: 'dd.mm.yy'
    },
    de: {
      firstDayOfWeek: 1,
      dateFormat: 'dd.mm.yy'
    },
    pl: {
      firstDayOfWeek: 1,
      dateFormat: 'dd.mm.yy'
    },
    be: {
      firstDayOfWeek: 1,
      dateFormat: 'dd.mm.yy'
    },
    uk: {
      firstDayOfWeek: 1,
      dateFormat: 'dd.mm.yy'
    },
    ka: {
      firstDayOfWeek: 1,
      dateFormat: 'dd.mm.yy'
    }
  };

  // Single object with i18n translations using t()
  const primeVueLocaleConfig = computed(() => ({
    startsWith: t('primevue.startsWith'),
    contains: t('primevue.contains'),
    notContains: t('primevue.notContains'),
    endsWith: t('primevue.endsWith'),
    equals: t('primevue.equals'),
    notEquals: t('primevue.notEquals'),
    noFilter: t('primevue.noFilter'),
    lt: t('primevue.lt'),
    lte: t('primevue.lte'),
    gt: t('primevue.gt'),
    gte: t('primevue.gte'),
    dateIs: t('primevue.dateIs'),
    dateIsNot: t('primevue.dateIsNot'),
    dateBefore: t('primevue.dateBefore'),
    dateAfter: t('primevue.dateAfter'),
    clear: t('primevue.clear'),
    apply: t('primevue.apply'),
    matchAll: t('primevue.matchAll'),
    matchAny: t('primevue.matchAny'),
    addRule: t('primevue.addRule'),
    removeRule: t('primevue.removeRule'),
    accept: t('primevue.accept'),
    reject: t('primevue.reject'),
    choose: t('primevue.choose'),
    upload: t('primevue.upload'),
    cancel: t('primevue.cancel'),
    completed: t('primevue.completed'),
    pending: t('primevue.pending'),
    dayNames: [
      t('primevue.dayNames.sunday'),
      t('primevue.dayNames.monday'),
      t('primevue.dayNames.tuesday'),
      t('primevue.dayNames.wednesday'),
      t('primevue.dayNames.thursday'),
      t('primevue.dayNames.friday'),
      t('primevue.dayNames.saturday')
    ],
    dayNamesShort: [
      t('primevue.dayNamesShort.sunday'),
      t('primevue.dayNamesShort.monday'),
      t('primevue.dayNamesShort.tuesday'),
      t('primevue.dayNamesShort.wednesday'),
      t('primevue.dayNamesShort.thursday'),
      t('primevue.dayNamesShort.friday'),
      t('primevue.dayNamesShort.saturday')
    ],
    dayNamesMin: [
      t('primevue.dayNamesMin.sunday'),
      t('primevue.dayNamesMin.monday'),
      t('primevue.dayNamesMin.tuesday'),
      t('primevue.dayNamesMin.wednesday'),
      t('primevue.dayNamesMin.thursday'),
      t('primevue.dayNamesMin.friday'),
      t('primevue.dayNamesMin.saturday')
    ],
    monthNames: [
      t('primevue.monthNames.january'),
      t('primevue.monthNames.february'),
      t('primevue.monthNames.march'),
      t('primevue.monthNames.april'),
      t('primevue.monthNames.may'),
      t('primevue.monthNames.june'),
      t('primevue.monthNames.july'),
      t('primevue.monthNames.august'),
      t('primevue.monthNames.september'),
      t('primevue.monthNames.october'),
      t('primevue.monthNames.november'),
      t('primevue.monthNames.december')
    ],
    monthNamesShort: [
      t('primevue.monthNamesShort.january'),
      t('primevue.monthNamesShort.february'),
      t('primevue.monthNamesShort.march'),
      t('primevue.monthNamesShort.april'),
      t('primevue.monthNamesShort.may'),
      t('primevue.monthNamesShort.june'),
      t('primevue.monthNamesShort.july'),
      t('primevue.monthNamesShort.august'),
      t('primevue.monthNamesShort.september'),
      t('primevue.monthNamesShort.october'),
      t('primevue.monthNamesShort.november'),
      t('primevue.monthNamesShort.december')
    ],
    chooseYear: t('primevue.chooseYear'),
    chooseMonth: t('primevue.chooseMonth'),
    chooseDate: t('primevue.chooseDate'),
    prevDecade: t('primevue.prevDecade'),
    nextDecade: t('primevue.nextDecade'),
    prevYear: t('primevue.prevYear'),
    nextYear: t('primevue.nextYear'),
    prevMonth: t('primevue.prevMonth'),
    nextMonth: t('primevue.nextMonth'),
    prevHour: t('primevue.prevHour'),
    nextHour: t('primevue.nextHour'),
    prevMinute: t('primevue.prevMinute'),
    nextMinute: t('primevue.nextMinute'),
    prevSecond: t('primevue.prevSecond'),
    nextSecond: t('primevue.nextSecond'),
    am: t('primevue.am'),
    pm: t('primevue.pm'),
    today: t('primevue.today'),
    weekHeader: t('primevue.weekHeader'),
    weak: t('primevue.weak'),
    medium: t('primevue.medium'),
    strong: t('primevue.strong'),
    passwordPrompt: t('primevue.passwordPrompt'),
    ...localeSpecificConfig[locale.value as keyof typeof localeSpecificConfig] || localeSpecificConfig.en
  }));

  // Function to update PrimeVue locale
  const updatePrimeVueLocale = () => {
    if (primevue.config.locale) {
      Object.assign(primevue.config.locale, primeVueLocaleConfig.value);
    }
  };

  // Watch for locale changes and update PrimeVue
  watch(
    [locale, primeVueLocaleConfig],
    () => {
      updatePrimeVueLocale();
    },
    { immediate: true }
  );

  return {
    updatePrimeVueLocale,
    primeVueLocaleConfig
  };
};