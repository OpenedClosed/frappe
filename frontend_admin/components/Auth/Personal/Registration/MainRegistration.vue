<template>
  <!-- Корневой контейнер -->
  <div class="w-full flex justify-center items-center h-screen overflow-hidden">
    <div class="p-4 m-4 bg-gray-100 dark:bg-gray-800 rounded-md shadow-md w-[30rem] h-[80vh] overflow-auto">
      <!-- Заголовок -->
      <div class="w-full flex flex-col justify-center items-center mb-4">
        <h1 class="text-center text-[20px] text-black dark:text-white font-bold">
          {{ t("PersonalMainRegistration.title") }}
        </h1>
        <p class="text-gray-500 dark:text-gray-300 text-center mt-1 text-[14px]">
          {{ t("PersonalMainRegistration.subtitle") }}
        </p>
      </div>

      <!-- Шаг 1: Форма регистрации -->
      <div v-if="!isCode">
        <form @submit.prevent="sendReg" class="flex flex-col gap-4">
          <!-- Номер телефона (required) -->
          <div>
            <label for="phone" class="block mb-1 text-[14px] text-black dark:text-white">
              {{ t("PersonalMainRegistration.phone") }} <span class="text-red-500">*</span>
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.phone }">
              <InputMask
                v-model="regForm.phone"
                id="phone"
                size="small"
                type="tel"
                required
                mask="+48 999 999 999"
                placeholder="+48 ___ ___ ___"
                :minlength="8"
                :maxlength="30"
                :placeholder="t('PersonalMainRegistration.phonePlaceholder')"
                class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
              />
            </div>
            <div class="flex flex-col">
              <small class="text-gray-500 dark:text-gray-300 mt-1 text-[12px]">
                <span class="text-gray-500 dark:text-gray-300 font-bold text-[14px] mt-1"
                  >{{ t("PersonalMainRegistration.numberImportant") }} &nbsp;</span
                >{{ t("PersonalMainRegistration.numberInfo") }}</small
              >
              <small class="text-red-500 mt-1 text-[12px]">
                {{ regError.phone }}
              </small>
            </div>
          </div>

          <!-- Email (required) -->
          <div>
            <label for="email" class="block mb-1 text-[14px] text-black dark:text-white">
              {{ t("PersonalMainRegistration.email") }}
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.email }">
              <InputText
                size="small"
                v-model="regForm.email"
                type="email"
                id="email"
                :placeholder="t('PersonalMainRegistration.emailPlaceholder')"
                class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
              />
            </div>
            <small class="text-red-500 mt-1 text-[12px]">
              {{ regError.email }}
            </small>
          </div>

          <!-- ФИО (required) -->
          <div>
            <label for="full_name" class="block mb-1 text-[14px] text-black dark:text-white">
              {{ t("PersonalMainRegistration.fullName") }} <span class="text-red-500">*</span>
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.full_name }">
              <InputText
                size="small"
                v-model="regForm.full_name"
                type="text"
                id="full_name"
                :placeholder="t('PersonalMainRegistration.fullNamePlaceholder')"
                required
                class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
              />
            </div>
            <small class="text-red-500 mt-1 text-[12px]">
              {{ regError.full_name }}
            </small>
          </div>
          <div>
            <label for="birth_date" class="block mb-1 text-[14px] text-black dark:text-white">
              {{ t("PersonalMainRegistration.birthDate") }} <span class="text-red-500">*</span>
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.birth_date }">
              <!-- PrimeVue Calendar -->
              <Calendar
                required
                v-model="regForm.birth_date"
                id="birth_date"
                :placeholder="t('PersonalMainRegistration.birthDatePlaceholder')"
                showIcon
                size="small"
                dateFormat="dd.mm.yy"
                class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
              />
            </div>
            <div class="flex flex-col">
              <small class="text-gray-500 dark:text-gray-300 mt-1 text-[12px]">
                <span class="text-gray-500 dark:text-gray-300 font-bold text-[14px] mt-1"
                  >{{ t("PersonalMainRegistration.birthImportant") }} &nbsp;</span
                >{{ t("PersonalMainRegistration.birthInfo") }}</small
              >
              <small class="text-red-500 mt-1 text-[12px]">
                {{ regError.birth_date }}
              </small>
            </div>
          </div>

          <!-- Пол -->
          <div>
            <label for="gender" class="block mb-1 text-[14px] text-black dark:text-white">
              {{ t("PersonalMainRegistration.gender") }} <span class="text-red-500">*</span>
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.gender }">
              <!-- PrimeVue Dropdown -->
              <Dropdown
                required
                v-model="regForm.gender"
                :options="genderOptions"
                optionLabel="label"
                optionValue="value"
                id="gender"
                :placeholder="t('PersonalMainRegistration.genderPlaceholder')"
                class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
              />
            </div>
            <small class="text-red-500 mt-1 text-[12px]">
              {{ regError.gender }}
            </small>
          </div>

          <!-- Пароль (required) -->
          <div>
            <label for="password" class="block mb-1 text-[14px] text-black dark:text-white">
              {{ t("PersonalMainRegistration.password") }} <span class="text-red-500">*</span>
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.password }">
              <InputText
                size="small"
                v-model="regForm.password"
                :type="passwordType"
                id="password"
                :placeholder="t('PersonalMainRegistration.passwordPlaceholder')"
                required
                class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
              />
              <!-- Кнопка-переключатель для видимости пароля -->
              <button type="button" @click="togglePasswordVisibility" class="px-2 text-gray-600 dark:text-gray-300 text-[14px]">
                <span v-if="passwordType === 'password'">{{ t("PersonalMainRegistration.show") }}</span>
                <span v-else>{{ t("PersonalMainRegistration.hide") }}</span>
              </button>
            </div>
            <div class="flex flex-col">
              <small class="text-gray-500 dark:text-gray-300 block mt-1 text-[12px]">
                {{ t("PersonalMainRegistration.passwordHint") }}
              </small>
              <small class="text-red-500 mt-1 block text-[12px]">
                {{ regError.password }}
              </small>
            </div>
          </div>

          <!-- Подтверждение пароля (required) -->
          <div>
            <label for="password_confirm" class="block mb-1 text-[14px] text-black dark:text-white">
              {{ t("PersonalMainRegistration.passwordConfirm") }} <span class="text-red-500">*</span>
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.password_confirm }">
              <InputText
                size="small"
                v-model="regForm.password_confirm"
                :type="passwordTypeConfirm"
                id="password_confirm"
                :placeholder="t('PersonalMainRegistration.passwordConfirmPlaceholder')"
                required
                class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
              />
              <!-- Кнопка-переключатель для видимости пароля -->
              <button type="button" @click="togglePasswordVisibilityConfirm" class="px-2 text-gray-600 dark:text-gray-300 text-[14px]">
                <span v-if="passwordTypeConfirm === 'password'">{{ t("PersonalMainRegistration.show") }}</span>
                <span v-else>{{ t("PersonalMainRegistration.hide") }}</span>
              </button>
            </div>
            <small class="text-red-500 mt-1 block text-[12px]">
              {{ regError.password_confirm }}
            </small>
          </div>

          <!-- Checkbox (Согласие с условиями) - required -->
          <div>
            <div class="flex items-center">
              <Checkbox v-model="regForm.accept_terms" :binary="true" inputId="agreeTerms" required class="mr-2" />
              <label for="agreeTerms" class="text-[14px] text-black dark:text-white">
                {{ t("PersonalMainRegistration.termsPrefix") }}
                <a href="#" class="underline" target="_blank">
                  {{ t("PersonalMainRegistration.termsLink") }}
                </a>
                {{ t("PersonalMainRegistration.privacyAnd") }}
                <a href="#" class="underline" target="_blank">
                  {{ t("PersonalMainRegistration.privacyLink") }}
                </a>
              </label>
            </div>
            <small class="text-red-500 mt-1 text-[12px]">
              {{ regError.accept_terms }}
            </small>
          </div>

          <!-- Кнопка регистрации -->
          <Button
            type="submit"
            :label="t('PersonalMainRegistration.registerButton')"
            class="bg-black dark:bg-gray-700 hover:bg-gray-800 text-white py-3 rounded-md w-full mt-4 border-none text-[14px]"
          />

          <!-- Ссылка на "Войти" -->
          <p class="text-center text-[14px] mt-4 text-black dark:text-white">
            {{ t("PersonalMainRegistration.alreadyHave") }}
            <span @click="goLogin" class="cursor-pointer ml-1 underline">{{ t("PersonalMainRegistration.loginLink") }}</span>
          </p>
        </form>
      </div>

      <!-- Шаг 2: Ввод кода подтверждения -->
      <div v-else>
        <h2 class="text-center text-[20px] text-black dark:text-white font-semibold mb-4">
          {{ t("PersonalMainRegistration.confirmTitle") }}
        </h2>

        <div>
          <h3 class="text-[18px] text-center">{{ t("PersonalMainRegistration.debugCode") }}</h3>
          <div class="flex flex-row items-center gap-1">
            <InputText v-model="testCode" readonly id="code" class="w-full" />
            <Button icon="pi pi-copy" @click="onCopy"></Button>
          </div>
        </div>

        <form @submit.prevent="sendCode" class="flex flex-col gap-4">
          <div>
            <label for="code" class="block mb-1 text-[14px] text-black dark:text-white">
              {{ t("PersonalMainRegistration.smsCodeLabel") }}
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.code }">
              <InputText
                size="small"
                v-model="regForm.code"
                type="text"
                id="code"
                :placeholder="t('PersonalMainRegistration.smsCodePlaceholder')"
                required
                class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none"
              />
            </div>
            <small class="text-red-500 mt-1">{{ regError.code }}</small>
          </div>

          <Button
            type="submit"
            :label="t('PersonalMainRegistration.confirmButton')"
            class="bg-black dark:bg-gray-700 hover:bg-gray-800 text-white py-3 rounded-md w-full mt-4 border-none"
          />

          <!-- Кнопка для возврата к вводу данных (если нужно) -->
          <Button type="button" :label="t('PersonalMainRegistration.cancelButton')" class="p-button-text mt-2 w-full" @click="resetForm" />
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRoute, navigateTo, reloadNuxtApp } from "#imports";
import { useI18n } from "vue-i18n";
const { t } = useI18n();
const is_loading = ref(false);
const loading_text_displayed = ref(false);
const isCode = ref(false);
// Управление видом пароля
const passwordType = ref("password");
const passwordTypeConfirm = ref("password");
const { currentLanguage } = useLanguageState();

import { useErrorParser } from "~/composables/useErrorParser.js";
const { parseAxiosError } = useErrorParser();

// язык пользователя из состояния
const fallbackLang = "en";

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

const regForm = ref({
  phone: "",
  email: "",
  full_name: "",
  birth_date: null, // 👈 новое поле
  gender: "", // 👈 новое поле
  password: "",
  password_confirm: "",
  accept_terms: false,
});

const regError = ref({
  phone: "",
  email: "",
  full_name: "",
  birth_date: "", // 👈 новое поле
  gender: "", // 👈 новое поле
  password: "",
  password_confirm: "",
  accept_terms: "",
  code: "",
});
/*--- варианты для Dropdown (Enum → value) ---*/
const genderOptions = [
  { label: t("PersonalMainRegistration.genderMale"), value: "male" },
  { label: t("PersonalMainRegistration.genderFemale"), value: "female" },
];

function onCopy() {
  navigator.clipboard.writeText(testCode.value);
}

const CheckboxValue = ref(true);
const passwordFieldType = ref("password");
const passwordFieldTypeConfirm = ref("password");

function togglePasswordVisibility() {
  passwordType.value = passwordType.value === "password" ? "text" : "password";
}

function togglePasswordVisibilityConfirm() {
  passwordTypeConfirm.value = passwordTypeConfirm.value === "password" ? "text" : "password";
}
function goNoCode() {
  regForm.value = {
    phone: "",
    email: "",
    full_name: "",
    birth_date: null, // 👈
    gender: "", // 👈
    password: "",
    password_confirm: "",
    accept_terms: false,
  };
  isCode.value = false;
}

const testCode = ref("");
const { currentPageName } = usePageState();
const route = useRoute();
const is_payment = route.query.is_payment === "true";

function goLogin() {
  console.log("currentPageName.value", currentPageName.value);
  if (is_payment) {
    navigateTo(`/${currentPageName.value}/login?is_payment=true`);
  } else {
    navigateTo(`/${currentPageName.value}/login/`);
  }
}

function sendReg() {
  if (!CheckboxValue.value) {
    regError.value.terms = "You must agree to the Terms of Service.";
    return;
  }

  regError.value = {
    phone: "",
    email: "",
    full_name: "",
    birth_date: null, // 👈
    gender: "", // 👈
    password: "",
    password_confirm: "",
    accept_terms: false,
  };
  const { currentPageName } = usePageState();
  is_loading.value = true;
  loading_text_displayed.value = false;
  let formData = regForm.value;
  console.log("formData", formData);
  useNuxtApp()
    .$api.post(`/api/${currentPageName.value}/register`, formData)
    .then((response) => {
      isCode.value = true;
      is_loading.value = false;
      const responceData = response.data;
      console.log("responceData", responceData);
      testCode.value = responceData?.debug_code;
    })
    .catch((err) => {
      console.error("sendReg error", err);
      parseAxiosError(err, regError.value); // reactive error object
    });
}
const { isAuthorized } = useAuthState();

function sendCode() {
  let formData = regForm.value;
  let url = `api/${currentPageName.value}/register_confirm`;

  useNuxtApp()
    .$api.post(url, formData)
    .then((response) => {
      let responceData = response.data;
      console.log("responceData", responceData);
      reloadNuxtApp({ path: `/${currentPageName.value}`, ttl: 1000 });
    })
    .catch((err) => {
      console.error("sendCode error", err);
      parseAxiosError(err, regError.value); // reactive error object
    });
}
function resetForm() {
  regForm.value = {
    phone: "",
    email: "",
    full_name: "",
    password: "",
    password_confirm: "",
    accept_terms: false,
  };
  code.value = "";
  Object.keys(regError.value).forEach((field) => {
    regError.value[field] = "";
  });
  isCodeStep.value = false;
}

onMounted(() => {
  if (currentPageName.value != "personal_account") {
    reloadNuxtApp({ path: `/${currentPageName.value}/login/`, ttl: 1000 });
  }
});
</script>
