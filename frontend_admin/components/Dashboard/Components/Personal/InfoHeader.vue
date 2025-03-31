<template>
  <div class="flex">
    <!-- Карточка с основными сведениями о пациенте -->
    <div class="bg-white dark:bg-neutralDark border-2 shadow rounded flex-1 flex flex-row justify-between items-center p-4 gap-4">
     <div class="flex items-center gap-4">
      <Avatar icon="pi pi-user" class="mr-2" size="xlarge" shape="circle" />
      <div class="flex flex-col">
        <div class="text-xl font-bold text-black dark:text-white">
          {{ patientName }}
        </div>
        <div class="text-sm">
          ID пациента: {{ patientId }} • Бонусов: {{ bonusCount }}
        </div>
      </div>
     </div>
      <div class="flex items-center gap-2">
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

// Определяем реактивные переменные с начальными значениями
const patientName = ref("Имя");
const patientId = ref("");
const bonusCount = ref(0);
const isAdmin = ref(false);

const contactInfo = ref({
  email: "",
  phone: "",
  address: "",
  pesel: "",
  documentId: "",
  emergencyContact: "",
});

// Получаем данные из API через useAsyncData (Nuxt 3)
const { data: headerData, error } = await useAsyncData('headerData', getHeaderData);

if (headerData.value) {
  // Destructure the two objects from headerData.value
  const { responseData, responseDataMe } = headerData.value;
  console.log("responseDataMe", responseDataMe);
  if (responseDataMe.role && (responseDataMe.role === "admin" || responseDataMe.role === "superadmin")) {
    isAdmin.value = true;
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
  patientName.value = [data.first_name, data.patronymic, data.last_name]
    .filter(Boolean)
    .join(" ") || "Неизвестный пациент";
  patientId.value = data.patient_id || "";
  bonusCount.value = data.bonus_count || 0;

  // Если в ответе API присутствует контактная информация, устанавливаем её
  if(data.contact) {
    contactInfo.value = {
      email: data.contact.email || "",
      phone: data.contact.phone || "",
      address: data.contact.address || "",
      pesel: data.contact.pesel || "",
      documentId: data.contact.document_id || "",
      emergencyContact: data.contact.emergency_contact || "",
    };
  }
}

// Функция для получения данных из API
async function getHeaderData() {
  let responseDataMe;
  let responseData;
  try {
    const response = await useNuxtApp().$api.get(`api/personal_account/patients_main_info/`);
    const response_me = await useNuxtApp().$api.get(`/api/users/me`);
    responseData = response.data;
    responseDataMe = response_me.data;
    console.log("Profile responseData =", responseData);
  } catch (err: any) {
    if (err.response) {
      console.error("Ошибка API:", err.response.data);
    }
  }
  return { responseData, responseDataMe };
}

const { isSidebarOpen } = useSidebarState();
const { currentPageName } = usePageState()
// Initialize the color mode
const colorMode = useColorMode();

const userName = ref("Действия");

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
    label: "Выйти",
    icon: "pi pi-power-off",
    command: onLogout,
  },
]);

if (isAdmin.value) {
  items.value.unshift({
    label: "В админ панель",
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

</script>

<style scoped>
.text-500 {
  color: var(--text-color-secondary);
}
</style>
