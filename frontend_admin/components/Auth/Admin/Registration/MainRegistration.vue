<template>
  <div class="w-full flex justify-center items-center h-screen overflow-hidden">
    <div class="p-4 m-4 bg-gray-100 dark:bg-gray-800 rounded-md shadow-md w-[30rem] h-[80vh] overflow-auto">
      <template v-if="!isCode">
        <form @submit.prevent="sendReg" class="flex flex-col items-center gap-3">
          <!-- Заголовок с логотипом -->
          <div class="w-full flex flex-col justify-center items-center mb-4">
            <div class="flex justify-center items-center w-full">
              <div class="h-[46px] m-3">
                <img src="/main/Logo.png" alt="Logo" class="w-32 h-auto block dark:hidden" />
                <img src="/main/Logo.png" alt="Logo" class="w-32 h-auto hidden dark:block" />
              </div>
            </div>
            <p class="text-center text-[20px] text-black dark:text-white font-medium mt-4 w-full">{{ t('MainRegistration.titleRegister') }}</p>
          </div>

          <!-- E-mail -->
          <div class="w-full flex flex-col justify-start">
            <label for="email" class="w-full text-[14px] mb-2">{{ t('MainRegistration.email') }}</label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(regError.email) }">
              <InputText
                v-model="regForm.email"
                type="email"
                required
                id="email"
                :placeholder="t('MainRegistration.emailPlaceholder')"
                class="w-full bg-transparent border-none shadow-none h-[48px] focus:ring-0 focus:outline-none"
              />
            </div>
            <small class="text-red-500 mt-1">{{ regError.email }}</small>
          </div>

          <!-- Phone -->
          <div class="w-full flex flex-col justify-start">
            <label for="phone" class="w-full text-[14px] mb-2">{{ t('MainRegistration.phone') }}</label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(regError.phone) }">
              <InputText
                v-model="regForm.phone"
                type="phone"
                required
                id="phone"
                :placeholder="t('MainRegistration.phonePlaceholder')"
                class="w-full bg-transparent border-none shadow-none h-[48px] focus:ring-0 focus:outline-none"
              />
            </div>
            <small class="text-red-500 mt-1">{{ regError.phone }}</small>
          </div>

          <!-- First Name -->
          <div class="w-full flex flex-col justify-start">
            <label for="first_name" class="w-full text-[14px] mb-2">{{ t('MainRegistration.firstName') }}</label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(regError.first_name) }">
              <InputText
                v-model="regForm.first_name"
                type="text"
                required
                id="first_name"
                :placeholder="t('MainRegistration.firstNamePlaceholder')"
                class="w-full bg-transparent border-none shadow-none h-[48px] focus:ring-0 focus:outline-none"
              />
            </div>
            <small class="text-red-500 mt-1">{{ regError.first_name }}</small>
          </div>

          <!-- Last Name -->
          <div class="w-full flex flex-col justify-start">
            <label for="last_name" class="w-full text-[14px] mb-2">{{ t('MainRegistration.lastName') }}</label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(regError.last_name) }">
              <InputText
                v-model="regForm.last_name"
                type="text"
                required
                id="last_name"
                :placeholder="t('MainRegistration.lastNamePlaceholder')"
                class="w-full bg-transparent border-none shadow-none h-[48px] focus:ring-0 focus:outline-none"
              />
            </div>
            <small class="text-red-500 mt-1">{{ regError.last_name }}</small>
          </div>

          <!-- Birth Date -->
          <div class="w-full flex flex-col justify-start">
            <label for="birth_date" class="w-full text-[14px] mb-2">{{ t('MainRegistration.birthDate') }}</label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(regError.birth_date) }">
              <InputText
                v-model="regForm.birth_date"
                type="date"
                required
                id="birth_date"
                :placeholder="t('MainRegistration.birthDatePlaceholder')"
                class="w-full bg-transparent border-none shadow-none h-[48px] focus:ring-0 focus:outline-none"
              />
            </div>
            <small class="text-red-500 mt-1">{{ regError.birth_date }}</small>
          </div>

          <!-- City -->
          <div class="w-full flex flex-col justify-start">
            <label for="city" class="w-full text-[14px] mb-2">{{ t('MainRegistration.city') }}</label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(regError.city) }">
              <InputText
                v-model="regForm.city"
                type="text"
                required
                id="city"
                :placeholder="t('MainRegistration.cityPlaceholder')" 
                class="w-full bg-transparent border-none shadow-none h-[48px] focus:ring-0 focus:outline-none"
              />
            </div>
            <small class="text-red-500 mt-1">{{ regError.city }}</small>
          </div>

          <!-- Gender -->
          <div class="w-full flex flex-col justify-start">
            <label for="gender" class="w-full text-[14px] mb-2">{{ t('MainRegistration.gender') }}</label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': Boolean(regError.gender) }">
              <InputText
                v-model="regForm.gender"
                type="text"
                required
                id="gender"
                :placeholder="t('MainRegistration.genderPlaceholder')"
                class="w-full bg-transparent border-none shadow-none h-[48px] focus:ring-0 focus:outline-none"
              />
            </div>
            <small class="text-red-500 mt-1">{{ regError.gender }}</small>
          </div>

          <!-- Checkbox для согласия с условиями -->
          <div class="w-full flex items-center">
            <Checkbox
              :binary="true"
              required
              v-model="CheckboxValue"
              inputId="terms"
              class="mr-2"
              :class="{ 'p-invalid': Boolean(regError.terms) }"
            />
            <label for="terms" class="text-[14px] text-black dark:text-white">
             {{ t('MainRegistration.termsLabel') }}
              <a href="https://quam.cc/termsofuse" target="_blank" class="underline"> {{ t('MainRegistration.termsLink') }}</a>
               {{ t('MainRegistration.termsAnd') }}
              <a href="https://quam.cc/privacy" target="_blank" class="underline"> {{ t('MainRegistration.privacyLink') }}</a>
            </label>
          </div>
          <small class="text-red-500 mt-1">{{ regError.terms }}</small>

          <!-- Кнопка регистрации -->
          <div class="w-full mt-6">
            <Button type="submit" class="w-full flex justify-center items-center">
              <p class="text-white">{{ t('MainRegistration.registerButton') }}</p>
            </Button>
          </div>

          <!-- Ссылка на логин -->
          <small class="text-[14px]">
            {{ t('MainRegistration.alreadyHaveAccount') }}
            <span @click="goLogin" class="underline cursor-pointer"> {{ t('MainRegistration.goToLogin') }} </span>
          </small>
        </form>
      </template>

      <template v-else>
        <div>
          <h3 class="text-[18px] text-center">{{ t('MainRegistration.codeTitle') }}</h3>
          <div class="flex flex-row items-center gap-1">
            <InputText v-model="testCode" readonly id="code" class="w-full" />
            <Button icon="pi pi-copy" @click="onCopy"></Button>
          </div>
        </div>

        <form @submit.prevent="sendCode" class="flex flex-col items-center gap-3">
          <!-- Заголовок для подтверждения кода -->
          <div class="w-full flex flex-col justify-center items-center mb-4">
            <div class="flex justify-center items-center w-full">
              <div class="h-[46px] m-3">
                <img src="/main/Logo.png" alt="Logo" class="w-32 h-auto block dark:hidden" />
                <img src="/main/Logo.png" alt="Logo" class="w-32 h-auto hidden dark:block" />
              </div>
            </div>
            <p class="text-center text-[20px] text-black dark:text-white font-medium mt-4 w-full">{{ t('MainRegistration.codeConfirmTitle') }}</p>
          </div>

          <!-- Поле ввода кода -->
          <div class="w-full flex flex-col justify-center items-center space-y-3">
            <p for="code" class="font-bold text-lg w-full text-center">{{ t('MainRegistration.enterCodePrompt') }}</p>

            <InputOtp required :length="6" v-model="regForm.code" id="code" :class="{ 'p-invalid': Boolean(regError.code) }" />
            <small class="text-red-500 mt-1">{{ regError.code }}</small>
          </div>

          <!-- Кнопка подтверждения -->
          <div class="w-full mt-6">
            <Button type="submit" class="w-full flex justify-center items-center">
              <p class="text-white">{{ t('MainRegistration.codeConfirmButton') }}</p>
            </Button>
          </div>

          <!-- Ссылка для повторной отправки кода -->
          <div class="text-center text-[14px]">
            <p>{{ t('MainRegistration.codeResendHelp1') }}</p>
            <p>
              {{ t('MainRegistration.codeResendHelp2') }}
              <a @click="goNoCode" class="underline cursor-pointer"> {{ t('MainRegistration.codeResendHelp2') }} </a>
            </p>
          </div>
        </form>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRoute, navigateTo, reloadNuxtApp } from "#imports";

import { useI18n } from 'vue-i18n';

const { t } = useI18n();


const is_loading = ref(false);
const loading_text_displayed = ref(false);
const isCode = ref(false);

let regForm = ref({
  email: "",
  phone: "",
  first_name: "",
  last_name: "",
  birth_date: "",
  city: "",
  gender: "",
  code: "",
});

let regError = ref({
  email: "",
  phone: "",
  first_name: "",
  last_name: "",
  birth_date: "",
  city: "",
  gender: "",
  code: "",
  terms: "",
});

function onCopy() {
  navigator.clipboard.writeText(testCode.value);
}

const CheckboxValue = ref(true);
const passwordFieldType = ref("password");
const passwordFieldTypeConfirm = ref("password");

function togglePasswordVisibility() {
  passwordFieldType.value = passwordFieldType.value === "password" ? "text" : "password";
}
function togglePasswordVisibilityConfirm() {
  passwordFieldTypeConfirm.value = passwordFieldTypeConfirm.value === "password" ? "text" : "password";
}

function goNoCode() {
  regForm.value = {
    email: "",
    phone: "",
    first_name: "",
    last_name: "",
    birth_date: "",
    city: "",
    gender: "",
    code: "",
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
    regError.value.terms = t('MainRegistration.error.terms');
    return;
  }

  regError.value = {
    email: "",
    phone: "",
    first_name: "",
    last_name: "",
    birth_date: "",
    city: "",
    gender: "",
    code: "",
    terms: "",
  };
  const { currentPageName } = usePageState();
  is_loading.value = true;
  loading_text_displayed.value = false;
  let formData = regForm.value;
  useNuxtApp()
    .$api.post(`/api/${currentPageName.value}/register`, formData)
    .then((response) => {
      isCode.value = true;
      is_loading.value = false;
      const responceData = response.data;
      console.log("responceData", responceData);
      testCode.value = responceData?.code_for_test;
    })
    .catch((err) => {
      console.log("err", err);
      if (err.response && err.response.data.errors) {
        const errors = err.response.data.errors;
        regError.value.email = errors.email || "";
        regError.value.phone = errors.phone || "";
        regError.value.first_name = errors.first_name || "";
        regError.value.last_name = errors.last_name || "";
        regError.value.birth_date = errors.birth_date || "";
        regError.value.city = errors.city || "";
        regError.value.gender = errors.gender || "";
        regError.value.terms = errors.agreeToTerms || "";
      }
      is_loading.value = false;
    });
}

function sendCode() {
  let formData = regForm.value;
  // const referral_code = localStorage.getItem('referral_code');
  let url = `api/${currentPageName.value}/register_confirm`;
  // if (referral_code) {
  //   url += `?referral_code=${referral_code}`;
  // }
  useNuxtApp()
    .$api.post(url, formData)
    .then((response) => {
      // const subscription_id = localStorage.getItem('subscription_id');
      // if (subscription_id) {
      //   if (referral_code && is_payment) {
      //     reloadNuxtApp({ path: `/payment?subscription_id=${subscription_id}&referral_code=${referral_code}`, ttl: 1000 });
      //   } else {
      //     reloadNuxtApp({ path: `/payment?subscription_id=${subscription_id}`, ttl: 1000 });
      //   }
      // } else {
      //   reloadNuxtApp({ path: "/dashboard", ttl: 1000 });
      // }
      let responceData = response.data;
      console.log("responceData", responceData);
      currentPageName.value = "admin"; // Обновляем state на 'admin'
      navigateTo(`/${currentPageName.value}/`);
    })
    .catch((err) => {
      console.log("err", err);
      if (err.response) {
        if (err.response.data.errors) {
          regError.value.code = err.response.data.errors.code;
        }
        if (err.response.data.detail) {
          regError.value.code = err.response.data.detail;
        }
      }
    });
}

onMounted(() => {
  if (currentPageName.value != "personal_account") {
    navigateTo(`/${currentPageName.value}/login/`);
  }
});
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
</style>
