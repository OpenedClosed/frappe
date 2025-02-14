<template>
  <div class="card">
    <Menubar class="rounded-none">
      <template #start>
        <div class="flex flex-row items-center justify-between">
          <Button text icon="pi pi-bars" class="xl:hidden" @click="isSidebarOpen = true" aria-label="Menu" />
          <div class="flex items-center justify-center md:justify-start ml-2">
            <img src="/main/Logo.png" alt="Logo" class="w-24 h-auto" />
          </div>
        </div>
      </template>
      <template #end>
        <div class="flex items-center gap-2">
          <Button
            text
            :icon="menuOpen ? 'pi pi-angle-up' : 'pi pi-angle-down'"
            type="button"
            label="Администратор"
            @click="toggle"
            aria-haspopup="true"
            aria-controls="overlay_tmenu"
          />
          <TieredMenu ref="menu" id="overlay_tmenu" :model="items" popup />
        </div>
      </template>
    </Menubar>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import Theme from "~/components/Dashboard/Components/Theme.vue";


const { isSidebarOpen } = useSidebarState();

// Initialize the color mode
const colorMode = useColorMode();



function toggleTheme() {
  colorMode.preference = colorMode.preference === "dark" ? "light" : "dark";
  updateTheme();
}

function updateTheme() {
  const systemTheme =
    colorMode.preference != "dark" ? "aura-light-cyan" : "aura-dark-cyan";
  //console.log("systemTheme", systemTheme)
  const themeLink = document.getElementById("theme-link");
  //console.log(themeLink)
  themeLink.setAttribute("href", `/${systemTheme}/theme.css`);
  //console.log(themeLink)
}


// Logout function with API request
async function onLogout() {
  try {
    await useNuxtApp().$api.post("/api/admin/logout", {}, { withCredentials: true });

    reloadNuxtApp({ path: "/admin/login/", ttl: 1000 });
  } catch (error) {
    console.error("Logout failed:", error);
  }
}

// Reference for the menu component and its open state
const menu = ref(null);
const menuOpen = ref(false);

// Use a computed property for the menu items so that the icon updates reactively.
const items = computed(() => [
  {
    label: "Сменить тему",
    icon: colorMode.preference === 'dark' ? 'pi pi-sun' : 'pi pi-moon',
    command: toggleTheme,
  },
  {
    label: "Выйти",
    icon: "pi pi-power-off",
    command: onLogout,
  },
]);

// Toggle the TieredMenu popup
const toggle = (event) => {
  menuOpen.value = !menuOpen.value;
  menu.value.toggle(event);
};
</script>
