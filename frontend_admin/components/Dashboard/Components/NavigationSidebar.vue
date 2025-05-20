<template>
  <!-- ░░ Desktop sidebar ░░ -->
  <div class="hidden xl:block m-4 transition-all duration-300" :class="isCollapsed ? 'w-[60px]' : 'min-w-[200px]'">
    <div class="rounded-xl shadow-thicc p-2 flex flex-col bg-white dark:bg-secondary h-full w-full">
      <!-- collapse / expand button -->
      <button
        class="p-2 self-end text-xl hover:text-primary "
        @click="isCollapsed = !isCollapsed"
        v-tooltip.bottom="isCollapsed ? t('NavigationSidebar.tooltip.expand') : t('NavigationSidebar.tooltip.collapse')"
      >
        <i :class="isCollapsed ? 'pi pi-angle-double-right' : 'pi pi-angle-double-left'"></i>
      </button>

      <ul class="flex flex-col py-1 space-y-4 w-full overflow-y-auto">
        <!-- dynamic groups -->
        <li v-for="group in filteredNavItems" :key="group.header.en" class="w-full">
          <!-- group header -->
          <h3 v-if="!isCollapsed" class="text-md uppercase mb-2 flex items-center px-2 font-semibold">
            <i class="mr-2" :class="group.icon"></i>
            {{ group.header[currentLanguage] || group.header.en }}
          </h3>

          <!-- collapsed header separator -->
          <div v-else class="border-t border-gray-200  my-3" />

          <!-- nav items -->
          <ul class="flex flex-col space-y-2" :class="isCollapsed ? 'items-center' : 'ml-4'">
            <li v-for="item in group.items" :key="item.route">
              <RouterLink
                :to="item.route"
                class="flex items-center rounded-md p-2 transition-colors"
                :class="[
                  isCollapsed ? 'justify-center' : '',
                  isActiveRoute(item.route)
                    ? 'border-2 border-primary'
                    : 'hover:text-primary ',
                ]"
                v-tooltip.right="item.name[currentLanguage] || item.name.en"
              >
                <i :class="item.iconClass"></i>
                <span v-if="!isCollapsed" class="ml-3 text-sm truncate">
                  {{ item.name[currentLanguage] || item.name.en }}
                </span>
              </RouterLink>
            </li>
          </ul>
        </li>

        <!-- hard-coded Admin settings -->
        <li v-if="currentPageName === 'admin'">
          <h3 v-if="!isCollapsed" class="text-md uppercase mb-2 flex items-center px-2 font-semibold">
            <i class="mr-2 pi pi-calendar-plus"></i>
            {{t('NavigationSidebar.headers.settings')}}
          </h3>
          <ul :class="isCollapsed ? 'items-center' : 'ml-4'">
            <RouterLink
              :to="`/${currentPageName}/knowledge-base`"
              class="flex items-center rounded-md p-2 transition-colors"
              :class="[
                isCollapsed ? 'justify-center' : '',
                isActiveRoute(`/${currentPageName}/knowledge-base`)
                  ? 'border-2 border-primary'
                  : 'hover:text-primary ',
              ]"
              v-tooltip.right="t('NavigationSidebar.links.knowledgeBase')"
            >
              <i class="pi pi-book"></i>
              <span v-if="!isCollapsed" class="ml-3 text-sm">{{t('NavigationSidebar.links.knowledgeBase')}}</span>
            </RouterLink>

            <RouterLink
              :to="`/${currentPageName}/knowledge/bot_settings`"
              class="flex items-center rounded-md p-2 transition-colors mt-2"
              :class="[
                isCollapsed ? 'justify-center' : '',
                isActiveRoute(`/${currentPageName}/knowledge/bot_settings`)
                  ? 'border-2 border-primary'
                  : 'hover:text-primary ',
              ]"
              v-tooltip.right="t('NavigationSidebar.links.botSettings')"
            >
              <i class="pi pi-cog"></i>
              <span v-if="!isCollapsed" class="ml-3 text-sm">{{t('NavigationSidebar.links.botSettings')}}</span>
            </RouterLink>
          </ul>
        </li>
      </ul>
    </div>
  </div>

  <!-- ░░ Mobile drawer (unchanged) ░░ -->
  <!-- Mobile Sidebar (Drawer) -->
  <Sidebar v-model:visible="isSidebarOpen" :header="t('NavigationSidebar.headers.sidebar')" class="!w-full md:!w-80 lg:!w-[30rem]">
    <nav class="p-4">
      <ul class="space-y-4">
        <!-- Hardcoded Knowledge Base -->

        <!-- Dynamic Navigation Items -->
        <li v-for="group in filteredNavItems" :key="group.header">
          <h3 class="text-md uppercase flex justify-start text-ellipsis items-center mb-2 px-2">
            <i class="mr-2 flex" :class="group.icon"></i>
            {{ group.header[currentLanguage] || group.header["en"] }}
          </h3>
          <ul class="flex flex-col ml-4 space-y-2">
            <li v-for="item in group.items" :key="item.name" class="flex items-center">
              <RouterLink
                :to="item.route"
                class="flex items-center hover:text-primary  p-2 rounded-md"
                @click="closeSidebar"
                :class="{ 'border-2 border-primary': isActiveRoute(item.route) }"
              >
                <i :class="item.iconClass" class="mr-3"></i>
                <span class="text-sm">{{ item.name[currentLanguage] || item.name["en"] }}</span>
              </RouterLink>
            </li>
          </ul>
        </li>
        <li v-if="currentPageName === 'admin'">
          <h3 class="text-md uppercase flex justify-start text-ellipsis items-center mb-2 px-2">
            <i class="mr-2 flex pi pi-calendar-plus"></i>
            Settings
          </h3>
          <ul class="ml-4">
            <RouterLink
              :to="`/${currentPageName}/knowledge-base`"
              class="flex items-center hover:text-primary  p-2 rounded-md"
              @click="closeSidebar"
              :class="{ 'border-2 border-primary': isActiveRoute(`/${currentPageName}/knowledge-base`) }"
            >
              <i class="pi pi-book mr-3"></i>
              <span class="text-sm">{{t('NavigationSidebar.links.knowledgeBase')}}</span>
            </RouterLink>
          </ul>
          <ul class="ml-4">
            <RouterLink
              :to="`/${currentPageName}/knowledge/bot_settings`"
              class="flex items-center hover:text-primary  p-2 rounded-md"
              @click="closeSidebar"
              :class="{ 'border-2 border-primary': isActiveRoute(`/${currentPageName}/knowledge/bot_settings`) }"
            >
              <i class="pi pi-cog mr-3"></i>
              <span class="text-sm">{{t('NavigationSidebar.links.botSettings')}}</span>
            </RouterLink>
          </ul>
        </li>
      </ul>
    </nav>
  </Sidebar>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import Sidebar from "primevue/sidebar";
import Tooltip from "primevue/tooltip";
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const { currentPageName } = usePageState();
const { currentLanguage } = useLanguageState();
const { isSidebarOpen } = useSidebarState();
const route = useRoute();

defineOptions({
  directives: { Tooltip }, // PrimeVue tooltip
});

const props = defineProps({
  navItems: { type: Array, required: true },
});

/* ── collapse state ── */
const isCollapsed = ref(false);

/* ── Load collapsed state from localStorage on mount ── */
onMounted(() => {
  const saved = localStorage.getItem("sidebar-collapsed");
  if (saved !== null) {
    isCollapsed.value = saved === "true"; // localStorage stores strings
  }
});

/* ── Save collapsed state to localStorage on change ── */
watch(isCollapsed, (newVal) => {
  localStorage.setItem("sidebar-collapsed", newVal.toString());
});

/* ── filter out Knowledge Base group ── */
const filteredNavItems = computed(() => props.navItems.filter((group) => group.header.en !== "Knowledge Base"));

/* ── helpers ── */
const isActiveRoute = (path) => route.path === path;
const closeSidebar = () => {
  isSidebarOpen.value = false;
};

watch(
  () => props.navItems,
  (val) => console.log("navItems updated", val)
);
</script>

<style scoped>
h3 {
  font-weight: 600;
}
</style>

