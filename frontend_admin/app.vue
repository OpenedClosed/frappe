<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>
<script setup>
import { useI18n } from "#imports";
const { setLocale, locale } = useI18n();
const { currentLanguage } = useLanguageState();

// Initialize PrimeVue locale configuration
usePrimeVueLocale();

console.log("locale", locale.value);
if (locale.value) {
  currentLanguage.value = locale.value;
}

watch(locale, (newVal) => {
  currentLanguage.value = newVal;
  console.log("locale", locale.value);
});
</script>
