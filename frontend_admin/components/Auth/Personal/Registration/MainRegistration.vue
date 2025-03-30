<template>
  <!-- Корневой контейнер -->
  <div class="w-full flex justify-center items-center h-screen overflow-hidden">
    <div class="p-4 m-4 bg-gray-100 dark:bg-gray-800 rounded-md shadow-md w-[30rem] h-[80vh] overflow-auto">
      <!-- Заголовок -->
      <div class="w-full flex flex-col justify-center items-center mb-4">
        <h1 class="text-center text-[20px] text-black dark:text-white font-bold">
          Регистрация
        </h1>
        <p class="text-gray-500 dark:text-gray-300 text-center mt-1 text-[14px]">
          Создайте новую учетную запись
        </p>
      </div>

      <!-- Шаг 1: Форма регистрации -->
      <div v-if="!isCode">
        <form @submit.prevent="sendReg" class="flex flex-col gap-4">

          <!-- Номер телефона (required) -->
          <div>
            <label for="phone" class="block mb-1 text-[14px] text-black dark:text-white">
              Номер телефона <span class="text-red-500">*</span>
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.phone }">
              <InputMask
                v-model="regForm.phone"
                id="phone"
                type="tel"
                required
                mask="+48 (999) 999-99-99"
                placeholder="Введите ваш телефон"
                class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
              />
            </div>
            <small class="text-red-500 mt-1 text-[12px]">
              {{ regError.phone }}
            </small>
          </div>

          <!-- Email (required) -->
          <div>
            <label for="email" class="block mb-1 text-[14px] text-black dark:text-white">
              Email  
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.email }">
              <InputText size="small" v-model="regForm.email" type="email" id="email" placeholder="mail@example.com"
                 class="w-full bg-transparent border-none shadow-none px-2 focus:ring-0 focus:outline-none text-[14px]" />
            </div>
            <small class="text-red-500 mt-1 text-[12px]">
              {{ regError.email }}
            </small>
          </div>

          <!-- ФИО (required) -->
          <div>
            <label for="full_name" class="block mb-1 text-[14px] text-black dark:text-white">
              ФИО <span class="text-red-500">*</span>
            </label>
            <div class="input-container flex items-center border rounded-lg"
              :class="{ 'p-invalid': !!regError.full_name }">
              <InputText size="small" v-model="regForm.full_name" type="text" id="full_name"
                placeholder="Иванов Иван Иванович" required
                class="w-full bg-transparent border-none shadow-none px-2 focus:ring-0 focus:outline-none text-[14px]" />
            </div>
            <small class="text-red-500 mt-1 text-[12px]">
              {{ regError.full_name }}
            </small>
          </div>

          <!-- Пароль (required) -->
          <div>
            <label for="password" class="block mb-1 text-[14px] text-black dark:text-white">
              Пароль <span class="text-red-500">*</span>
            </label>
            <div class="input-container flex items-center border rounded-lg"
              :class="{ 'p-invalid': !!regError.password }">
              <InputText size="small" v-model="regForm.password" :type="passwordType" id="password"
                placeholder="Минимум 10 символов" required
                class="w-full bg-transparent border-none shadow-none px-2 focus:ring-0 focus:outline-none text-[14px]" />
              <!-- Кнопка-переключатель для видимости пароля -->
              <button type="button" @click="togglePasswordVisibility" class="px-2 text-gray-600 dark:text-gray-300 text-[14px]">
                <span v-if="passwordType === 'password'">Показать</span>
                <span v-else>Скрыть</span>
              </button>
            </div>
            <small class="text-gray-500 block mt-1 text-[12px]">
              Минимум 10 символов, включая заглавные, строчные буквы, цифры
              и спецсимволы
            </small>
            <small class="text-red-500 mt-1 block text-[12px]">
              {{ regError.password }}
            </small>
          </div>

          <!-- Подтверждение пароля (required) -->
          <div>
            <label for="password_confirm" class="block mb-1 text-[14px] text-black dark:text-white">
              Подтверждение пароля <span class="text-red-500">*</span>
            </label>
            <div class="input-container flex items-center border rounded-lg"
              :class="{ 'p-invalid': !!regError.password_confirm }">
              <InputText size="small" v-model="regForm.password_confirm" :type="passwordTypeConfirm"
                id="password_confirm" placeholder="Повторите пароль" required
                class="w-full bg-transparent border-none shadow-none px-2 focus:ring-0 focus:outline-none text-[14px]" />
              <!-- Кнопка-переключатель для видимости пароля -->
              <button type="button" @click="togglePasswordVisibilityConfirm"
                class="px-2 text-gray-600 dark:text-gray-300 text-[14px]">
                <span v-if="passwordTypeConfirm === 'password'">Показать</span>
                <span v-else>Скрыть</span>
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
                Я согласен с
                <a href="#" class="underline" target="_blank">
                  Условиями использования
                </a>
                и
                <a href="#" class="underline" target="_blank">
                  Политикой конфиденциальности
                </a>
              </label>
            </div>
            <small class="text-red-500 mt-1 text-[12px]">
              {{ regError.accept_terms }}
            </small>
          </div>

          <!-- Кнопка регистрации -->
          <Button type="submit" label="Зарегистрироваться"
            class="bg-black dark:bg-gray-700 hover:bg-gray-800 text-white py-3 rounded-md w-full mt-4 border-none text-[14px]" />

          <!-- Ссылка на "Войти" -->
          <p class="text-center text-[14px] mt-4 text-black dark:text-white">
            Уже есть аккаунт?
            <span @click="goLogin" class="cursor-pointer ml-1 underline">Войти</span>
          </p>
        </form>
      </div>

      <!-- Шаг 2: Ввод кода подтверждения -->
      <div v-else>

        <h2 class="text-center text-[20px] text-black dark:text-white font-semibold mb-4">
          Подтвердите регистрацию
        </h2>

        <div>
          <h3 class="text-[18px] text-center">Тестовый код (Потом будет с почты)</h3>
          <div class="flex flex-row items-center gap-1">
            <InputText v-model="testCode" readonly id="code" class="w-full" />
            <Button icon="pi pi-copy" @click="onCopy"></Button>
          </div>
        </div>

        <form @submit.prevent="sendCode" class="flex flex-col gap-4">
          <div>
            <label for="code" class="block mb-1 text-[14px] text-black dark:text-white">
              Код из SMS
            </label>
            <div class="input-container flex items-center border rounded-lg" :class="{ 'p-invalid': !!regError.code }">
              <InputText size="small" v-model="regForm.code" type="text" id="code" placeholder="Введите код из SMS"
                required class="w-full bg-transparent border-none shadow-none px-2 focus:ring-0 focus:outline-none" />
            </div>
            <small class="text-red-500 mt-1">{{ regError.code }}</small>
          </div>

          <Button type="submit" label="Подтвердить"
            class="bg-black dark:bg-gray-700 hover:bg-gray-800 text-white py-3 rounded-md w-full mt-4 border-none" />

          <!-- Кнопка для возврата к вводу данных (если нужно) -->
          <Button type="button" label="Отменить" class="p-button-text mt-2 w-full" @click="resetForm" />
        </form>
      </div>
    </div>
  </div>
</template>


<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, navigateTo, reloadNuxtApp } from '#imports';

const is_loading = ref(false);
const loading_text_displayed = ref(false);
const isCode = ref(false);
// Управление видом пароля
const passwordType = ref('password')
const passwordTypeConfirm = ref('password')

const regForm = ref({
  phone: '',
  email: '',
  full_name: '',
  password: '',
  password_confirm: '',
  accept_terms: false,
})

const regError = ref({
  phone: '',
  email: '',
  full_name: '',
  password: '',
  password_confirm: '',
  accept_terms: '',
  code: '',
})

function onCopy() {
  navigator.clipboard.writeText(testCode.value);
}

const CheckboxValue = ref(true);
const passwordFieldType = ref('password');
const passwordFieldTypeConfirm = ref('password');

function togglePasswordVisibility() {
  passwordType.value =
    passwordType.value === 'password' ? 'text' : 'password'
}

function togglePasswordVisibilityConfirm() {
  passwordTypeConfirm.value =
    passwordTypeConfirm.value === 'password' ? 'text' : 'password'
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
    code: '',
  };
  isCode.value = false;
}

const testCode = ref("")
const { currentPageName } = usePageState()
const route = useRoute();
const is_payment = route.query.is_payment === 'true';

function goLogin() {
  console.log('currentPageName.value', currentPageName.value);
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
    email: "",
    phone: "",
    first_name: "",
    last_name: "",
    birth_date: "",
    city: "",
    gender: "",
    code: '',
    terms: "",
  };
  const { currentPageName } = usePageState()
  is_loading.value = true;
  loading_text_displayed.value = false;
  let formData = regForm.value;
  useNuxtApp().$api
    .post(`/api/${currentPageName.value}/register`, formData)
    .then((response) => {
      isCode.value = true;
      is_loading.value = false;
      const responceData = response.data;
      console.log('responceData', responceData);
      testCode.value = responceData?.debug_code;
    })
    .catch((err) => {
      console.log('err', err);
      if (err.response && err.response.data.errors) {
        const errors = err.response.data.errors;
        console.log('errors', errors);
        regError.value.email = errors.email || '';
        regError.value.phone = errors.phone || '';
        regError.value.first_name = errors.first_name || '';
        regError.value.last_name = errors.last_name || '';
        regError.value.birth_date = errors.birth_date || '';
        regError.value.city = errors.city || '';
        regError.value.gender = errors.gender || '';
        regError.value.terms = errors.agreeToTerms || '';
        regError.value.password_confirm = errors.password_confirm || '';
        regError.value.password = errors.password || '';
      }
      is_loading.value = false;
    });
}
const { isAuthorized } = useAuthState();

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
      console.log('responceData', responceData);
      reloadNuxtApp({ path: `/${currentPageName.value}`, ttl: 1000 })
    })
    .catch((err) => {
      console.log('err', err);
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
function resetForm() {
  regForm.value = {
    phone: '',
    email: '',
    full_name: '',
    password: '',
    password_confirm: '',
    accept_terms: false,
  }
  code.value = ''
  Object.keys(regError.value).forEach((field) => {
    regError.value[field] = ''
  })
  isCodeStep.value = false
}

onMounted(() => {
  if (currentPageName.value != 'personal_account') {
   reloadNuxtApp({ path: `/${currentPageName.value}/login/`, ttl: 1000 });
  }
});
</script>