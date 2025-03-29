<template>
  <div class="flex">
    <!-- Карточка с основными сведениями о пациенте -->
    <div class="bg-white dark:bg-neutralDark border-2 shadow rounded flex-1 flex flex-row justify-start items-center p-4 gap-4">
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
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

// Определяем реактивные переменные с начальными значениями
const patientName = ref("Загрузка...");
const patientId = ref("");
const bonusCount = ref(0);

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
  setData(headerData.value);
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
  let responseData;
  try {
    const response = await useNuxtApp().$api.get(`api/personal_account/patients_main_info/`);
    responseData = response.data;
    console.log("Profile responseData =", responseData);
  } catch (err: any) {
    if (err.response) {
      console.error("Ошибка API:", err.response.data);
    }
  }
  return responseData;
}
</script>

<style scoped>
.text-500 {
  color: var(--text-color-secondary);
}
</style>
