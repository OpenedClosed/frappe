<template>
  <div class="card">
    <!-- <Menubar class="border-none" :model="items" /> -->
  </div>
  <slot />
</template>

<script setup>
  import { ref } from "vue";
  import { useToast } from "primevue/usetoast";

  const items = ref([
    {
      label: "Базовая регистрация",
      icon: "pi pi-plus-circle",
      command: () => {
        navigateTo("/create/registration_basic");
        // window.location.href ='/create/registration_basic'
      },
    },
    {
      label: "Расширенная регистрация",
      icon: "pi pi-plus-circle",
      command: () => {
        navigateTo("/create/registration_advanced");
        // window.location.href ='/create/registration_advanced'
      },
    },

    {
      label: "Вход",
      icon: "pi pi-sign-in",
      command: () => {
        navigateTo("/login");
        // window.location.href ='/login'
      },
    },

    {
      label: "Мой профиль базовый",
      icon: "pi pi-user",
      command: () => {
        navigateTo("/profile/me/registration_basic/");
        // window.location.href ='/profile/me/registration_basic/'
      },
    },
    {
      label: "Мой профиль расширенный",
      icon: "pi pi-user",
      command: () => {
        navigateTo("/profile/me/networking/");
        // window.location.href ='/profile/me/networking/'
      },
    },
    {
      label: "Поиск",
      icon: "pi pi-search",
      command: () => {
        navigateTo("/search/networking");
        // window.location.href ='/search/networking'
      },
    },
    {
      label: "Потенциальные действия",
      icon: "pi pi-map",
      command: () => {
        navigateTo("/potential");
        // window.location.href ='/search/networking'
      },
    },
    {
      label: "Уведомления",
      icon: "pi pi-comment",
      command: () => {
        navigateTo("/notifications");
        // window.location.href ='/search/networking'
      },
    },
  ]);
</script>
