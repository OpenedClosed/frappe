<template>
  <div class="w-full flex justify-center items-center h-screen">
    <!-- Основной контейнер -->
    <div class="p-4 m-4 bg-gray-100 dark:bg-gray-800 rounded-md shadow-md w-[30rem]">
      <!-- Шаг 1: Ввод логина и пароля -->
      <form v-if="!is2FA" @submit.prevent="sendLogin" class="flex flex-col items-center gap-3">
        <!-- Заголовок / логотип -->
        <div class="w-full flex flex-col justify-center items-center mb-4">
          <p class="text-center text-[20px] text-black dark:text-white font-medium mt-4 w-full">
            {{ t("PersonalMainLogin.titleLogin") }}
          </p>
        </div>

        <!-- Login method toggle -->
        <div class="flex items-center justify-between w-full mb-3">
          <label class="text-[14px] text-black dark:text-white">
            {{ t("PersonalMainLogin.usePhoneLogin") }}
          </label>
          <InputSwitch v-model="usePhoneLogin" />
        </div>

        <!-- Email (required) -->
         <div class="w-full flex flex-col justify-start" v-if="!usePhoneLogin">
          <label for="email" class="w-full block mb-1 text-[14px] text-black dark:text-white">
            {{ t("PersonalMainLogin.email") }} <span class="text-red-500">*</span>
          </label>
          <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!loginError.email }">
            <InputText
              size="small"
              required
              v-model="loginForm.email"
              type="email"
              id="email"
              :placeholder="t('PersonalMainLogin.emailPlaceholder')"
              class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
            />
          </div>
          <small class="text-red-500 mt-1 text-[12px]">
            {{ loginError.email }}
          </small>
        </div>

        <!-- Phone (required) -->
        <div class="w-full flex flex-col justify-start" v-else>
          <label for="phone" class="w-full block mb-1 text-[14px] text-black dark:text-white">
            {{ t("PersonalMainLogin.phone") }} <span class="text-red-500">*</span>
          </label>
          <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!loginError.phone }">
            <InputMask
              v-model="loginForm.phone"
              required
              id="phone"
              size="small"
              type="tel"
              mask="+48 999 999 999"
              placeholder="+48 ___ ___ ___"
              :minlength="8"
              :maxlength="30"
              :placeholder="t('PersonalMainLogin.phonePlaceholder')"
              class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
            />
          </div>
          <small class="text-red-500 mt-1 text-[12px]">
            {{ loginError.phone }}
          </small>
        </div>

        <!-- Пароль -->
        <div class="w-full flex flex-col justify-start">
          <label for="password" class="w-full text-[14px] mb-2 text-black dark:text-white">
            {{ t("PersonalMainLogin.password") }} <span class="text-red-500">*</span>
          </label>
          <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(loginError.password) }">
            <InputText
              size="small"
              :type="showPassword ? 'text' : 'password'"
              v-model="loginForm.password"
              required
              id="password"
              class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none"
              :placeholder="t('PersonalMainLogin.passwordPlaceholder')"
            />
            <span @click="showPassword = !showPassword" class="cursor-pointer pr-4">
              <i :class="showPassword ? 'pi pi-eye-slash' : 'pi pi-eye'"></i>
            </span>
          </div>
          <small v-if="loginError.password" class="text-red-500 mt-1">{{ loginError.password }}</small>
        </div>

        <!-- Кнопка «Войти» -->
        <div class="w-full mt-6">
          <Button
            type="submit"
            :label="t('PersonalMainLogin.loginButton')"
            class="bg-black dark:bg-gray-700 hover:bg-gray-800 text-white py-3 rounded-md w-full border-none"
          />
        </div>

        <!-- Ссылка на регистрацию (если не в админке) -->
        <small v-if="currentPageName != 'admin'" class="text-[14px] text-black dark:text-white">
          {{ t("PersonalMainLogin.noAccount") }}
          <span @click="goRegistration" class="underline cursor-pointer"> {{ t("PersonalMainLogin.registerLink") }} </span>
        </small>
      </form>

      <!-- Шаг 2: Ввод 2FA кода -->
      <form v-else @submit.prevent="send2FA" class="flex flex-col items-center gap-3">
        <!-- Заголовок -->
        <div class="w-full flex flex-col justify-center items-center mb-4">
          <p class="text-center text-[20px] text-black dark:text-white font-medium mt-4 w-full">
            {{ t("PersonalMainLogin.title2FA") }}
          </p>
        </div>

        <!-- Код 2FA -->
        <div class="w-full flex flex-col justify-start">
          <label for="twofa_code" class="w-full text-[14px] mb-2 text-black dark:text-white">
            {{ t("PersonalMainLogin.twofaLabel") }} <span class="text-red-500">*</span>
          </label>
          <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(twoFAError.message) }">
            <InputText
              size="small"
              v-model="twoFAForm.code"
              required
              id="twofa_code"
              class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none"
              :placeholder="t('PersonalMainLogin.twofaPlaceholder')"
            />
          </div>
          <small class="text-red-500 mt-1">{{ twoFAError.message }}</small>
        </div>

        <!-- Кнопка «Подтвердить» -->
        <div class="w-full mt-6">
          <Button
            type="submit"
            :label="t('PersonalMainLogin.confirmButton')"
            class="bg-black dark:bg-gray-700 hover:bg-gray-800 text-white py-3 rounded-md w-full border-none"
          />
        </div>

        <!-- Кнопка «Отмена» (вернуться к вводу пароля) -->
        <Button type="button" :label="t('PersonalMainLogin.cancelButton')" class="p-button-text mt-2 w-full" @click="cancel2FA" />
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import InputText from "primevue/inputtext";
import Button from "primevue/button";
import InputMask from "primevue/inputmask";
import InputSwitch from "primevue/inputswitch";
import { useNuxtApp, useAuthState, usePageState, navigateTo, reloadNuxtApp } from "#imports";

import { useI18n } from "vue-i18n";

const { currentLanguage } = useLanguageState();

const { t } = useI18n();

import { useErrorParser } from "~/composables/useErrorParser.js";
const { parseAxiosError } = useErrorParser();
/**
 * Управление видимостью пароля
 */
const showPassword = ref(false);

// Toggle between email and phone login
const usePhoneLogin = ref(false);

// Keep loginForm.via in sync with toggle
watch(usePhoneLogin, (newVal) => {
  loginForm.value.via = newVal ? "phone" : "email";
});

/**
 * Для отслеживания текущего шага
 * is2FA = false → форма логина/пароля
 * is2FA = true  → форма ввода одноразового кода
 */
const is2FA = ref(false);

/**
 * Данные формы (шаг 1)
 */
let loginForm = ref({
  email: "",
  phone: "",
  password: "",
  via: "email",
});

/**
 * Ошибка (шаг 1)
 */
let loginError = ref({
  email: "",
  phone: "",
  password: "",
});

/**
 * Данные формы (шаг 2)
 */
let twoFAForm = ref({
  code: "",
});

/**
 * Ошибка (шаг 2)
 */
let twoFAError = ref({
  message: "",
});

/**
 * Для debug-кода, который сервер может вернуть (напр. для теста)
 */
const debugCode = ref("");

/**
 * Текущая «страница» (admin, personal_account и т.д.)
 */
const { currentPageName } = usePageState();

/**
 * При клике на «Зарегистрироваться»
 */
function goRegistration() {
  navigateTo(`/${currentPageName.value}/registration/`);
}

function pickError(err) {
  if (!err) return "";

  // 1) строка
  if (typeof err === "string") return err;

  // 2) массив строк
  if (Array.isArray(err)) return err[0] || "";

  // 3) объект вида { en:"...", ru:"..." }
  if (typeof err === "object") {
    return err[currentLanguage.value] || err[fallbackLang] || Object.values(err)[0] || "";
  }
  return "";
}

/**
 * 1. Отправляет логин/пароль на /login
 * 2. Если успех → сервер вернёт «2FA code sent»
 * 3. Переходим к форме ввода кода
 */
function sendLogin() {
  // Очищаем ошибки
  loginError.value.email = "";
  loginError.value.phone = "";
  loginError.value.password = "";
  debugCode.value = "";

  let formData = {
    via: loginForm.value.via,
    email: loginForm.value.via === "email" ? loginForm.value.email.trim() : undefined,
    phone: loginForm.value.via === "phone" ? loginForm.value.phone.trim() : undefined,
    password: loginForm.value.password,
  };
  console.log("Шаг 1 (login) formData:", formData);

  useNuxtApp()
    .$api.post(`api/${currentPageName.value}/login`, formData)
    .then((response) => {
      let responseData = response.data;
      console.log("Шаг 1 (login) ответ: ", responseData);
      // Предполагаем, что если ответ содержит "2FA code sent", значит требуется код
      // И сервер может вернуть debug_code (только для отладки)
      if (responseData.debug_code) {
        debugCode.value = responseData.debug_code;
      }
      is2FA.value = true; // Переключаемся на форму ввода кода
    })
    .catch((err) => {
      console.error("sendLogin error", err);
      parseAxiosError(err, loginError.value); // reactive error object
    });
}

/**
 * 1. Отправляет code на /login_confirm
 * 2. Если успех → Logged in
 * 3. Редиректим на /admin (или другую нужную страницу)
 */
function send2FA() {
  twoFAError.value.message = "";
  let formData = {
    via: loginForm.value.via,
    email: loginForm.value.via === "email" ? loginForm.value.email.trim() : undefined,
    phone: loginForm.value.via === "phone" ? loginForm.value.phone.trim() : undefined,
    code: twoFAForm.value.code.trim(),
  };
  console.log("Шаг 2 (2FA) formData:", formData);

  useNuxtApp()
    .$api.post(`api/${currentPageName.value}/login_confirm`, formData)
    .then((response) => {
      let responseData = response.data;
      console.log("Шаг 2 (2FA) ответ:", responseData);
      // Если успех — "Logged in", есть access_token и т.д.
      reloadNuxtApp({ path: `/${currentPageName.value}`, ttl: 1000 });
    })
    .catch((err) => {
      console.error("send2FA error", err);
      parseAxiosError(err, loginError.value); // reactive error object
    });
}

/**
 * Кнопка «Отмена» в форме 2FA: вернуться назад
 */
function cancel2FA() {
  // Сбрасываем форму 2FA
  twoFAForm.value.code = "";
  twoFAError.value.message = "";

  // Можно очистить и шаг 1, если нужно
  // loginForm.value.email = ''
  // loginForm.value.password = ''
  // loginError.value.message = ''

  // Возвращаемся к первому шагу
  is2FA.value = false;
}

/**
 * Скопировать debug-код в буфер обмена (для удобства теста)
 */
function copyDebugCode() {
  navigator.clipboard.writeText(debugCode.value);
}
</script>

<style scoped>
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

/* Светлая тема (по умолчанию) */
.custom-dialog .p-dialog-header-close {
  @apply bg-[#E8E8E8] hover:bg-[#b8b8b8] text-white rounded-full w-10 h-10;
}
.custom-dialog .p-dialog-header-close svg {
  @apply text-white;
}
.custom-dialog .p-dialog-header {
  text-align: right;
  padding-left: 47px;
  font-weight: normal;
}
.custom-dialog .p-dialog-header-title {
  font-weight: 400;
}

/* Тёмная тема */
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
