<template>
  <div class="card">
    <Menubar class="rounded-none bg-primaryHeader outline-none border-none">
      <template #start>
        <div class="flex flex-row items-center justify-between">
          <Button
            text
            icon="pi pi-bars color-black dark:color-white"
            class="xl:!hidden !block"
            @click="isSidebarOpen = true"
            :aria-label="t('Topbar.aria.menu')"
          />
          <div v-if="currentPageName === 'admin'" class="flex items-center justify-center md:justify-start ml-2">
            <img src="/main/Logo.png" :alt="t('Topbar.alt.logo')" class="w-24 h-auto block dark:hidden" />
            <img src="/main/Logo.png" :alt="t('Topbar.alt.logo')" class="w-24 h-auto hidden dark:block" />
          </div>
          <div v-else class="flex items-center justify-center md:justify-start ml-2">
            <h3 class="text-white text-lg font-bold">{{t('Topbar.titles.personalAccount')}}</h3>
          </div>
        </div>
      </template>
      <template #end>
        <div class="flex items-center gap-2">
          <Dropdown
            v-model="selectedLocale"
            :options="languageOptions"
            optionLabel="name"
            optionValue="code"
            class="min-w-42 text-sm"
            @change="onLocaleChange($event.value)"
            :pt="{
              input: { class: 'bg-transparent text-white border-none' },
              panel: { class: 'min-w-[10rem]' },
            }"
          />
          <Button
            text
            :icon="menuOpen ? 'pi pi-angle-up' : 'pi pi-angle-down'"
            type="button"
            :label="userName"
            class="text-white"
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
import { useI18n } from "#imports";
const { t } = useI18n()
const { isSidebarOpen } = useSidebarState();
const { currentPageName } = usePageState();
// Initialize the color mode
const colorMode = useColorMode();

const userName = ref(t('Topbar.user.defaultName'));

function toggleTheme() {
  colorMode.preference = colorMode.preference === "dark" ? "light" : "dark";
  updateTheme();
}

function updateTheme() {
  // const systemTheme =
  //   colorMode.preference != "dark" ? "aura-light-cyan" : "aura-dark-cyan";
  // //console.log("systemTheme", systemTheme)
  // const themeLink = document.getElementById("theme-link");
  // //console.log(themeLink)
  // themeLink.setAttribute("href", `/${systemTheme}/theme.css`);
  // //console.log(themeLink)
}

// Logout function with API request
async function onLogout() {
  try {
    await useNuxtApp().$api.post(`/api/${currentPageName.value}/logout`, {}, { withCredentials: true });

    reloadNuxtApp({ path: `/${currentPageName.value}/login/`, ttl: 1000 });
  } catch (error) {
    console.error("Logout failed:", error);
  }
}

// Reference for the menu component and its open state
const menu = ref(null);
const menuOpen = ref(false);

// Use a computed property for the menu items so that the icon updates reactively.
const items = computed(() => {
  const menuItems = [
    {
      label: t('Topbar.menu.changeTheme'),
      icon: colorMode.preference === "dark" ? "pi pi-sun" : "pi pi-moon",
      command: toggleTheme,
    },
    {
      label: t('Topbar.menu.logout'),
      icon: "pi pi-power-off",
      command: onLogout,
    },
  ];

  if (currentPageName.value === "admin") {
    menuItems.unshift({
      label: 	t('Topbar.menu.toPersonal'),
      icon: "pi pi-user",
      command: () => {
        window.location.href = "/personal_account";
      },
    });
  } else {
    menuItems.unshift({
      label: t('Topbar.menu.toAdmin'),
      icon: "pi pi-user",
      command: () => {
        window.location.href = "/admin";
      },
    });
  }

  return menuItems;
});

// Toggle the TieredMenu popup
const toggle = (event) => {
  menuOpen.value = !menuOpen.value;
  menu.value.toggle(event);
};

const userData = await useAsyncData("userData", getUserData);

if (userData.data) {
  console.log("userData= ", userData.data);
  if (userData.data.value) {
    setData(userData.data.value);
  }
}
function setData(data) {
  if (data) {
    console.log("userData data= ", data);
    if (data) {
      userName.value = `${data.username}`;
    }
  }
}

async function getUserData() {
  let responseData;
  await useNuxtApp()
    .$api.get(`/api/users/me`)
    .then((response) => {
      responseData = response.data;
      console.log("Profile responseData= ", responseData);
    })
    .catch((err) => {
      if (err.response) {
        console.log(err.response.data);
      }
    });
  return responseData;
}

const { locale, locales, setLocale, setLocaleCookie } = useI18n()

const selectedLocale = ref(locale.value)

const languageOptions = locales.value.map((l) => ({
  code: l.code,
  name: l.name || l.code.toUpperCase(),
}))

function onLocaleChange(code) {
  setLocale(code)
  setLocaleCookie(code)
  selectedLocale.value = code
}
</script>
