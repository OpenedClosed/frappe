<template>
  <!-- Main horizontal navigation container -->
  <nav class="w-full px-4 pb-4">
    <ul class="flex bg-neutralLight dark:bg-neutralDark shadow-sm rounded-lg items-center space-x-4 p-1">
      <!-- Loop over each “group” -->
      <li v-for="group in filteredNavItems" :key="group.header" class="flex items-center overflow-x-auto">
        <!-- Loop over each item within the group, displayed horizontally -->
        <ul class="flex items-center space-x-3">
          <li v-for="item in group.items" :key="item.name">
            <RouterLink
              :to="item.route"
              class="inline-flex gap-1 items-center px-3 py-2 text-sm text-black dark:text-white hover:text-primaryDark dark:hover:text-primaryLight hover:bg-neutral dark:hover:bg-neutralDark mx-1 rounded transition-colors duration-150"
              :class="{
                'border-2 border-primary text-primary dark:text-primaryLight font-semibold bg-white dark:bg-neutral rounded-lg active':
                  isActiveRoute(item.route),
              }"
            >
              <i :class="item.iconClass" class="mr-1"></i>
              {{ item.name[currentLanguage] || item.name["en"] }}
            </RouterLink>
          </li>
          <!-- Hardcoded Support link -->
          <li>
            <RouterLink
              to="/personal_account/support/support"
              class="inline-flex items-center px-3 py-2 text-sm text-black dark:text-white hover:text-primaryDark dark:hover:text-primaryLight hover:bg-neutral dark:hover:bg-neutralDark mx-1 rounded transition-colors duration-150"
              :class="{
                'border-2 border-primary text-primary dark:text-primaryLight font-semibold bg-white dark:bg-neutral rounded-lg active':
                  isActiveRoute('/personal_account/support/support'),
              }"
            >
              <i class="pi pi-info-circle mr-1"></i>
              {{ t("NavigationSidebarTabs.support") }}
            </RouterLink>
          </li>
        </ul>
      </li>
    </ul>
  </nav>
</template>

<script setup>
import { defineProps, computed, watch, onMounted } from "vue";
import { useRoute } from "vue-router";

import { useI18n } from "vue-i18n";
const { t } = useI18n();

const route = useRoute();
const { currentLanguage } = useLanguageState();

const props = defineProps({
  navItems: {
    type: Array,
    required: true,
  },
});

// Optionally filter out unwanted groups:
const filteredNavItems = computed(() => {
  return props.navItems.filter((group) => group.header.en !== "Knowledge Base");
});

const isActiveRoute = (routePath) => {
  // Simple check for exact match
  return route.path.includes(routePath);
};

// Scroll to the element with the 'active' class on route change
watch(
  () => route,
  async () => {
    await nextTick();
    const activeEl = document.querySelector(".active");
    if (activeEl && activeEl.scrollIntoView) {
      activeEl.scrollIntoView({ behavior: "auto", inline: "center", block: "nearest" });
    }
  },
  { immediate: true }
);

onMounted(async () => {
  await nextTick();
  // Initial scroll to active element
  const activeEl = document.querySelector(".active");
  if (activeEl && activeEl.scrollIntoView) {
    activeEl.scrollIntoView({ behavior: "auto", inline: "center", block: "nearest" });
  }
});
</script>
