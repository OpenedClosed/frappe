<template>
  <div class="w-full flex justify-center items-center h-screen">

    <!-- Основной контейнер -->
    <div class="p-4 m-4 bg-gray-100 dark:bg-gray-800 rounded-md shadow-md w-[30rem]">
      <!-- Шаг 1: Ввод логина и пароля -->
      <form v-if="!is2FA" @submit.prevent="sendLogin" class="flex flex-col items-center gap-3">
        <!-- Заголовок / логотип -->
        <div class="w-full flex flex-col justify-center items-center mb-4">
          <p class="text-center text-[20px] text-black dark:text-white font-medium mt-4 w-full">
            Вход в аккаунт
          </p>
        </div>
        
        <!-- Логин (например, телефон) -->
        <div class="w-full flex flex-col justify-start">
          <label for="phone" class="w-full text-[14px] mb-2 text-black dark:text-white">
            Телефон 
          </label>
          <div class="input-container flex items-center border rounded-lg"
               :class="{ 'p-invalid': Boolean(loginError.message) }"
          >
          <InputMask
        v-model="loginForm.phone"
        id="phone"
        type="tel"
        required
        mask="+9 (999) 999-99-99"
        placeholder="Введите ваш телефон"
        class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none"
      />
          </div>
          <small class="text-red-500 mt-1">{{ loginError.message }}</small>
        </div>

        <!-- Пароль -->
        <div class="w-full flex flex-col justify-start">
          <label for="password" class="w-full text-[14px] mb-2 text-black dark:text-white">
            Пароль
          </label>
          <div class="input-container flex items-center border rounded-lg"
               :class="{ 'p-invalid': Boolean(loginError.message) }"
          >
            <InputText size="small"
              :type="showPassword ? 'text' : 'password'"
              v-model="loginForm.password"
              required
              id="password"
              class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none"
              placeholder="Введите ваш пароль"
            />
            <span @click="showPassword = !showPassword" class="cursor-pointer pr-4">
              <i :class="showPassword ? 'pi pi-eye-slash' : 'pi pi-eye'"></i>
            </span>
          </div>
          <small class="text-red-500 mt-1">{{ loginError.message }}</small>
        </div>

        <!-- Кнопка «Войти» -->
        <div class="w-full mt-6">
          <Button type="submit" label="Войти"
                  class="bg-black dark:bg-gray-700 hover:bg-gray-800 text-white py-3 rounded-md w-full border-none" />
        </div>

        <!-- Ссылка на регистрацию (если не в админке) -->
        <small v-if="currentPageName != 'admin'" class="text-[14px] text-black dark:text-white">
          У вас нет аккаунта?
          <span @click="goRegistration" class="underline cursor-pointer"> Зарегистрироваться </span>
        </small>
      </form>

      <!-- Шаг 2: Ввод 2FA кода -->
      <form v-else @submit.prevent="send2FA" class="flex flex-col items-center gap-3">
        <!-- Заголовок -->
        <div class="w-full flex flex-col justify-center items-center mb-4">
          <p class="text-center text-[20px] text-black dark:text-white font-medium mt-4 w-full">
            Подтверждение входа
          </p>
        </div>

        <!-- Код 2FA -->
        <div class="w-full flex flex-col justify-start">
          <label for="twofa_code" class="w-full text-[14px] mb-2 text-black dark:text-white">
            Код из SMS / почты
          </label>
          <div class="input-container flex items-center border rounded-lg"
               :class="{ 'p-invalid': Boolean(twoFAError.message) }"
          >
            <InputText size="small"
              v-model="twoFAForm.code"
              required
              id="twofa_code"
              class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none"
              placeholder="Введите код"
            />
          </div>
          <small class="text-red-500 mt-1">{{ twoFAError.message }}</small>
        </div>

        <!-- Для отладки: вывести код, если бэкенд вернул debug_code -->
        <div class="w-full flex flex-col" v-if="debugCode">
          <label class="text-[14px] text-black dark:text-white">
            Тестовый код:
          </label>
          <div class="flex items-center gap-2">
            <InputText :value="debugCode" readonly class="w-full" />
            <Button icon="pi pi-copy" @click="copyDebugCode" />
          </div>
        </div>

        <!-- Кнопка «Подтвердить» -->
        <div class="w-full mt-6">
          <Button type="submit" label="Подтвердить"
                  class="bg-black dark:bg-gray-700 hover:bg-gray-800 text-white py-3 rounded-md w-full border-none" />
        </div>

        <!-- Кнопка «Отмена» (вернуться к вводу пароля) -->
        <Button type="button" label="Отмена"
                class="p-button-text mt-2 w-full"
                @click="cancel2FA"
        />
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { useNuxtApp, useAuthState, usePageState, navigateTo, reloadNuxtApp } from '#imports'

/**
 * Управление видимостью пароля
 */
const showPassword = ref(false)

/**
 * Для отслеживания текущего шага
 * is2FA = false → форма логина/пароля
 * is2FA = true  → форма ввода одноразового кода
 */
const is2FA = ref(false)

/**
 * Данные формы (шаг 1)
 */
let loginForm = ref({
  phone: '',
  password: '',
})

/**
 * Ошибка (шаг 1)
 */
let loginError = ref({
  message: '',
})

/**
 * Данные формы (шаг 2)
 */
let twoFAForm = ref({
  code: '',
})

/**
 * Ошибка (шаг 2)
 */
let twoFAError = ref({
  message: '',
})

/**
 * Для debug-кода, который сервер может вернуть (напр. для теста)
 */
const debugCode = ref('')

/**
 * Текущая «страница» (admin, personal_account и т.д.)
 */
const { currentPageName } = usePageState()

/**
 * При клике на «Зарегистрироваться»
 */
function goRegistration() {
  navigateTo(`/${currentPageName.value}/registration/`)
}

/**
 * 1. Отправляет логин/пароль на /login
 * 2. Если успех → сервер вернёт «2FA code sent»
 * 3. Переходим к форме ввода кода
 */
function sendLogin() {
  // Очищаем ошибки
  loginError.value.message = ''
  debugCode.value = ''

  let formData = loginForm.value
  console.log('Шаг 1 (login) formData:', formData)

  useNuxtApp().$api
    .post(`api/${currentPageName.value}/login`, formData)
    .then(response => {
      let responseData = response.data
      console.log('Шаг 1 (login) ответ: ', responseData)
      // Предполагаем, что если ответ содержит "2FA code sent", значит требуется код
      // И сервер может вернуть debug_code (только для отладки)
      if (responseData.debug_code) {
        debugCode.value = responseData.debug_code
      }
      is2FA.value = true  // Переключаемся на форму ввода кода
    })
    .catch(err => {
      console.log('Ошибка (login):', err)
      if (err.response) {
        // Если бэкенд отдает detail { "password": "..."} или { "phone": "..." }
        // упростим логику и просто выводим detail как message
        loginError.value.message =
          typeof err.response.data.detail === 'string'
            ? err.response.data.detail
            : JSON.stringify(err.response.data.detail)
      }
    })
}

/**
 * 1. Отправляет code на /login_confirm
 * 2. Если успех → Logged in
 * 3. Редиректим на /admin (или другую нужную страницу)
 */
function send2FA() {
  twoFAError.value.message = ''
  let formData = {
    // Важно: сервер, как правило, требует тот же phone/phone,
    // чтобы понять, для кого подтверждаем код
    phone: loginForm.value.phone.trim(),
    code: twoFAForm.value.code.trim(),
  }
  console.log('Шаг 2 (2FA) formData:', formData)

  useNuxtApp().$api
    .post(`api/${currentPageName.value}/login_confirm`, formData)
    .then(response => {
      let responseData = response.data
      console.log('Шаг 2 (2FA) ответ:', responseData)
      // Если успех — "Logged in", есть access_token и т.д.
      reloadNuxtApp({ path: `/${currentPageName.value}`, ttl: 1000 })
    })
    .catch(err => {
      console.log('Ошибка (login_confirm):', err)
      if (err.response) {
        twoFAError.value.message =
          typeof err.response.data.detail === 'string'
            ? err.response.data.detail
            : JSON.stringify(err.response.data.detail)
      }
    })
}

/**
 * Кнопка «Отмена» в форме 2FA: вернуться назад
 */
function cancel2FA() {
  // Сбрасываем форму 2FA
  twoFAForm.value.code = ''
  twoFAError.value.message = ''

  // Можно очистить и шаг 1, если нужно
  // loginForm.value.phone = ''
  // loginForm.value.password = ''
  // loginError.value.message = ''

  // Возвращаемся к первому шагу
  is2FA.value = false
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
