<template>
  <div class="flex px-4 py-2">
    <!-- Карточка с основными сведениями о пациенте -->
    <div class="bg-white dark:bg-neutralDark border-2 shadow rounded flex-1 flex flex-col md:flex-row justify-between items-center p-4 gap-4">
      <div class="flex flex-col md:flex-row items-center gap-4">
        <Avatar v-if="patientAvatar" :image="currentUrl  + patientAvatar " size="xlarge" shape="circle" />
        <Avatar v-else icon="pi pi-user" size="xlarge" shape="circle" />
        <div class="flex flex-col ">
          <div class="text-xl text-center md:text-start font-bold text-black dark:text-white">
            {{ patientName }}
          </div>
          <div class="text-sm text-center md:text-start">{{ t('InfoHeader.patientIdPrefix') }} {{ patientId }} • {{ t('InfoHeader.bonusPrefix') }} {{ bonusCount }}</div>
        </div>
      </div>
      <div class="flex flex-col md:flex-row items-center gap-2">
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
          class="text-white bg-primary"
          @click="toggle"
          aria-haspopup="true"
          aria-controls="overlay_tmenu"
        />
        <TieredMenu ref="menu" id="overlay_tmenu" :model="items" popup />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

// Определяем реактивные переменные с начальными значениями
const patientName = ref("Имя");
const patientId = ref("");
const patientAvatar = ref("");
const bonusCount = ref(0);
const isAdmin = ref(false);

const { currentUrl } = useURLState();

const contactInfo = ref({
  email: "",
  phone: "",
  address: "",
  pesel: "",
  documentId: "",
  emergencyContact: "",
  avatar_url: "",
});

// Получаем данные из API через useAsyncData (Nuxt 3)
const { data: headerData, error } = await useAsyncData("headerData", getHeaderData);
console.log("headerData", headerData.value);

if (headerData.value) {
  // Destructure the two objects from headerData.value
  const { responseData, responseDataMe, responseBonus } = headerData.value;
  console.log("responseDataMe", responseDataMe);
  console.log("responseData", responseData);
  console.log("responseBonus", responseBonus);
  if (responseDataMe?.role && (responseDataMe?.role === "admin" || responseDataMe?.role === "superadmin" || responseDataMe?.role === "demo_admin")) {
    isAdmin.value = true;
  }
  if (responseBonus) {
    bonusCount.value = responseBonus.balance || 0;
  }
  // Use responseData (and responseDataMe if needed) inside setData
  setData(responseData);

  // For example, if you want to log responseDataMe:
  console.log("User data =", responseDataMe);
} else if (error.value) {
  console.error("Ошибка загрузки данных:", error.value);
}

// Функция для установки полученных данных в реактивные переменные
function setData(data: any) {
  console.log("Полученные данные headerData =", data);
  // Пример: формируем полное имя из first_name и last_name (и patronymic, если есть)
  patientName.value = [data?.first_name, data?.patronymic, data?.last_name].filter(Boolean).join(" ") || "Неизвестный пациент";
  patientId.value = data?.patient_id || "";
  patientAvatar.value = data?.avatar?.url || "";

  // Если в ответе API присутствует контактная информация, устанавливаем её
  if (data?.contact) {
    contactInfo.value = {
      email: data?.contact.email || "",
      phone: data?.contact.phone || "",
      address: data?.contact.address || "",
      pesel: data?.contact.pesel || "",
      documentId: data?.contact.document_id || "",
      emergencyContact: data?.contact.emergency_contact || "",
    };
  }
}

// Функция для получения данных из API
async function getHeaderData () {
  try {
    const api = useNuxtApp().$api
    const [mainInfoRes, meRes, bonusRes] = await Promise.all([
      api.get('api/personal_account/patients_main_info/'),
      api.get('/api/users/me'),
      api.get('api/personal_account/patients_bonus_program/'),
    ])

    return {
      responseData:   mainInfoRes.data,
      responseDataMe: meRes.data,
      responseBonus:  bonusRes.data,
    }
  } catch (err) {
    if (err?.response) console.error('Ошибка API:', err.response.data)
    else               console.error(err)
    return null
  }
}

const { isSidebarOpen } = useSidebarState();
const { currentPageName } = usePageState();
// Initialize the color mode
const colorMode = useColorMode();

const userName = ref(t('InfoHeader.actions'));

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
const items = computed(() => [
   {
      label: t('InfoHeader.changeTheme'),
      icon: colorMode.preference === "dark" ? "pi pi-sun" : "pi pi-moon",
      command: toggleTheme,
    },
  {
    label: t('InfoHeader.logout'),
    icon: "pi pi-power-off",
    command: onLogout,
  },
]);

if (isAdmin.value) {
  items.value.unshift({
    label:	t('InfoHeader.adminPanel'),
    icon: "pi pi-user",
    command: () => {
      window.location.href = "/admin";
    },
  });
}


// Toggle the TieredMenu popup
const toggle = (event) => {
  menuOpen.value = !menuOpen.value;
  menu.value.toggle(event);
};



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

<style scoped>
.text-500 {
  color: var(--text-color-secondary);
}
</style>
