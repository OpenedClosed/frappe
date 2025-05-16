<template>
  <div class="w-full flex justify-center items-center h-screen">
    <div class="p-4 m-4 bg-gray-100 dark:bg-gray-800 rounded-md shadow-md w-[30rem]">
      <form @submit.prevent="sendLogin" class="flex flex-col items-center gap-3">
        <div class="w-full flex flex-col justify-center items-center mb-4">
          <div class="flex justify-center items-center w-full">
            <div class="h-[46px] m-3">
              <img src="/main/Logo.png" alt="Logo" class="w-32 h-auto block dark:hidden bg-black p-1 rounded" />
              <img src="/main/Logo.png" alt="Logo" class="w-32 h-auto hidden dark:block" />
            </div>
          </div>
          <p class="text-center text-[20px] text-black dark:text-white font-medium mt-4 w-full">Вход в аккаунт</p>
        </div>
        <div class="w-full flex flex-col justify-start">
          <label for="audience" class="w-full text-[14px] mb-2"> Логин </label>
          <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(loginError.message) }">
            <InputText
              v-model="loginForm.username"
              required
              id="username"
              class="w-full bg-transparent border-none shadow-none h-[48px] focus:ring-0 focus:outline-none"
              placeholder="Введите ваш логин"
            />
          </div>
          <small class="text-red-500 mt-1">{{ loginError.message }}</small>
        </div>

        <div class="w-full flex flex-col justify-start">
          <label for="password" class="w-full text-[14px] mb-2"> Пароль </label>

          <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(loginError.message) }">
            <InputText
              :type="showPassword ? 'text' : 'password'"
              v-model="loginForm.password"
              required
              id="password"
              class="w-full bg-transparent border-none shadow-none h-[48px] focus:ring-0 focus:outline-none"
              placeholder="Введите ваш пароль"
            />
            <span @click="showPassword = !showPassword" class="cursor-pointer pr-4">
              <i :class="showPassword ? 'pi pi-eye-slash' : 'pi pi-eye'" />
            </span>
          </div>
          <small class="text-red-500 mt-1">{{ loginError.message }}</small>
        </div>

        <!-- <div class="flex items-center w-full p-1 my-2">
                    <Checkbox v-model="CheckboxValue" :binary="true" inputId="checkboxId" />
                    <label for="checkboxId" class="ml-2">
                        <span class="text-sm">{{ $t('login.rememberMe') }}</span>
                    </label>
                </div> -->

        <div class="w-full mt-6">
          <Button type="submit" class="w-full flex justify-center items-center">
            <p class="text-white">Войти</p>
          </Button>
        </div>

        <small v-if="currentPageName != 'admin'" class="text-[14px]">
          У вас нет аккаунта?
          <span @click="goRegistration" class="underline cursor-pointer"> Зарегистрироваться </span>
        </small>
      </form>
    </div>
  </div>
</template>

<script setup>
const showPassword = ref(false);
const { isAuthorized } = useAuthState();
const showLoginDialog = ref(false);
const CheckboxValue = ref(false);

let loginForm = ref({
  password: "",
  username: "",
});

let loginError = ref({
  message: "",
});
const { currentPageName } = usePageState();

function goRegistration() {
  console.log("currentPageName.value", currentPageName.value);
  navigateTo(`/${currentPageName.value}/registration/`);
}

function sendLogin() {
  let formData = loginForm.value;
  console.log("formData", formData);
  useNuxtApp()
    .$api.post(`api/${currentPageName.value}/login`, formData)
    .then((response) => {
      let responseData = response.data;
      console.log("Profile responseData= ", responseData);
      currentPageName.value = "admin"; // Обновляем state на 'admin'
      reloadNuxtApp({ path: "/admin", ttl: 1000 });
    })
    .catch((err) => {
      console.log("err", err);
      if (err.response) {
        loginError.value.message = err.response.data.detail;
      }
    });
}
</script>

<style>
.input-container {
  transition: outline 0.1s ease-in-out;
}

.input-container:focus-within {
  border: 1px solid rgba(239, 68, 68, 1);
  transition: outline 0.1s ease-in-out;
}

.input-container {
  outline: none;
}

/* Light mode styles */
.custom-dialog .p-dialog-header-close {
  @apply bg-[#E8E8E8] hover:bg-[#b8b8b8] text-white rounded-full w-10 h-10;
}

/* Target the SVG cross icon and change its color */
.custom-dialog .p-dialog-header-close svg {
  @apply text-white;
}

/* Customize the header */
.custom-dialog .p-dialog-header {
  text-align: right;
  padding-left: 47px;
  font-weight: normal;
}

.custom-dialog .p-dialog-header-title {
  font-weight: 400;
}

/* Dark mode styles */
.dark .custom-dialog .p-dialog-header-close {
  @apply bg-gray-600 hover:bg-gray-500 text-white rounded-full w-10 h-10;
}

.dark .custom-dialog .p-dialog-header-close svg {
  @apply text-white;
}

.dark .custom-dialog .p-dialog-header {
  @apply text-gray-300;
}

.dark .custom-dialog .p-dialog-header-title {
  @apply text-gray-300;
}
</style>
