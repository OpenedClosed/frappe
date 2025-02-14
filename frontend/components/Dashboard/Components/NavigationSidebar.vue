<template>
  <!-- Desktop Sidebar -->
  <div class="flex-1 min-w-[200px] hidden xl:flex">
    <div class="outline outline-primary dark:outline-secondary rounded-md p-2 flex flex-1 w-full">
      <ul class="flex flex-col space-y-4 w-full">
        <li v-for="group in navItems" :key="group.header">
          <!-- Группа заголовок -->
          <h3 class="text-md uppercase flex justify-start text-ellipsis items-center mb-2 px-2">
            <i class="mr-2 flex" :class="group.icon"></i>
            {{ group.header[currentLanguage] || group.header['en'] }}
          </h3>
          <!-- Элементы группы -->
          <ul class="flex flex-col ml-4 space-y-2">
            <li v-for="item in group.items" :key="item.name" class="flex items-center">
              <!-- {{item}} -->
              <RouterLink
                :to="item.route"
                class="flex items-center hover:text-primary dark:hover:text-secondary p-2 rounded-md"
                :class="{
                  'border-2 border-primary dark:border-secondary': isActiveRoute(item.route),
                }"
              >
                <i :class="item.iconClass" class="mr-3"></i>
                <span class="text-sm">{{ item.name[currentLanguage] || item.name['en']}}</span>
              </RouterLink>
            </li>
          </ul>
        </li>
      </ul>
    </div>
  </div>

  <!-- Mobile Sidebar (Drawer) -->
  <Sidebar v-model:visible="isSidebarOpen" header="Sidebar" class="!w-full md:!w-80 lg:!w-[30rem]">
    <nav class="p-4">
      <ul class="space-y-4">
        <li v-for="group in navItems" :key="group.header">
          <!-- Группа заголовок -->
          <h3 class="text-md uppercase flex justify-start text-ellipsis items-center mb-2 px-2">
            <i class="mr-2 flex" :class="group.icon"></i>
            {{ group.header }}
          </h3>
          <!-- Элементы группы -->
          <ul class="flex flex-col ml-4 space-y-2">
            <li v-for="item in group.items" :key="item.name" class="flex items-center">
              <!-- {{item}} -->
              <RouterLink
                :to="item.route"
                class="flex items-center hover:text-primary dark:hover:text-secondary p-2 rounded-md"
                @click="closeSidebar"
                :class="{
                  'border-2 border-primary dark:border-secondary': isActiveRoute(item.route),
                }"
              >
                <i :class="item.iconClass" class="mr-3"></i>
                <span class="text-sm">{{ item.name }}</span>
              </RouterLink>
            </li>
          </ul>
        </li>
      </ul>
    </nav>
  </Sidebar>
</template>

<script setup>
import { defineProps, defineEmits } from "vue";
import Sidebar from "primevue/sidebar";

const props = defineProps({
  navItems: {
    type: Array,
    required: true,
  },
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
