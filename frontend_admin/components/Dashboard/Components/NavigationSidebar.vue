<template>
  <!-- Desktop Sidebar -->
  <div class="flex-1 min-w-[200px] hidden xl:flex">
    <div class="outline outline-primary dark:outline-secondary rounded-md p-2 flex flex-1 w-full">
      <ul class="flex flex-col space-y-4 w-full">
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
                class="flex items-center hover:text-primary dark:hover:text-secondary p-2 rounded-md"
                :class="{ 'border-2 border-primary dark:border-secondary': isActiveRoute(item.route) }"
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
              class="flex items-center hover:text-primary dark:hover:text-secondary p-2 rounded-md"
              @click="closeSidebar"
              :class="{ 'border-2 border-primary dark:border-secondary': isActiveRoute(`/${currentPageName}/knowledge-base`) }"
            >
              <i class="pi pi-book mr-3"></i>
              <span class="text-sm">Knowledge Base</span>
            </RouterLink>
          </ul>
          <ul class="ml-4">
            <RouterLink
              :to="`/${currentPageName}/knowledge/bot_settings`"
              class="flex items-center hover:text-primary dark:hover:text-secondary p-2 rounded-md"
              @click="closeSidebar"
              :class="{ 'border-2 border-primary dark:border-secondary': isActiveRoute(`/${currentPageName}/knowledge/bot_settings`) }"
            >
              <i class="pi pi-cog mr-3"></i>
              <span class="text-sm">Bot Settings</span>
            </RouterLink>
          </ul>
        </li>
      </ul>
    </div>
  </div>

  <!-- Mobile Sidebar (Drawer) -->
  <Sidebar v-model:visible="isSidebarOpen" header="Sidebar" class="!w-full md:!w-80 lg:!w-[30rem]">
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
                class="flex items-center hover:text-primary dark:hover:text-secondary p-2 rounded-md"
                @click="closeSidebar"
                :class="{ 'border-2 border-primary dark:border-secondary': isActiveRoute(item.route) }"
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
              class="flex items-center hover:text-primary dark:hover:text-secondary p-2 rounded-md"
              @click="closeSidebar"
              :class="{ 'border-2 border-primary dark:border-secondary': isActiveRoute(`/${currentPageName}/knowledge-base`) }"
            >
              <i class="pi pi-book mr-3"></i>
              <span class="text-sm">Knowledge Base</span>
            </RouterLink>
          </ul>
          <ul class="ml-4">
            <RouterLink
              :to="`/${currentPageName}/knowledge/bot_settings`"
              class="flex items-center hover:text-primary dark:hover:text-secondary p-2 rounded-md"
              @click="closeSidebar"
              :class="{ 'border-2 border-primary dark:border-secondary': isActiveRoute(`/${currentPageName}/knowledge/bot_settings`) }"
            >
              <i class="pi pi-cog mr-3"></i>
              <span class="text-sm">Bot Settings</span>
            </RouterLink>
          </ul>
        </li>
      </ul>
    </nav>
  </Sidebar>
</template>


<script setup>
import { defineProps, defineEmits } from "vue";
import Sidebar from "primevue/sidebar";
const { currentPageName } = usePageState()

const props = defineProps({
  navItems: {
    type: Array,
    required: true,
  },
});

watch(
  () => props.navItems,
  (newVal) => {
    console.log("props.navItems", newVal);
  }
);
const filteredNavItems = computed(() => {
  return props.navItems.filter((group) => group.header.en !== "Knowledge Base");
});

const { currentLanguage } = useLanguageState();

const emit = defineEmits(["update:visible"]);

const { isSidebarOpen } = useSidebarState();

const closeSidebar = () => {
  isSidebarOpen.value = false;
};
const route = useRoute();
const isActiveRoute = (routePath) => {
  return route.path === routePath;
};
</script>

<style scoped>
h3 {
  font-weight: 600;
}
</style>
<style>
.p-menubar .p-menubar-start .p-button-icon {
  color: white !important;
}
</style>
