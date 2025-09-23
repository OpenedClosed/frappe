<template>
  <div class="w-full">
    <!-- Поле ввода телефона -->
    <div>
      <label for="phone" class="block mb-1 text-[14px]">
        {{ $t("countryPhone.phone") }} <span v-if="required" class="text-red-500">*</span>
      </label>
      <div class="flex items-center border rounded-lg gap-1" :class="{ 'border-red-500': !!phoneError }">
        <!-- Отображение выбранной страны -->
        <div class="flex items-center border-gray-200 dark:border-gray-700">
          <div class="flex items-center border rounded-lg">
            <Select
              v-model="selectedCountry"
              size="small"
              :options="countries"
              :optionLabel="getCountryLabel"
              :placeholder="$t('countryPhone.selectCountry')"
              :filter="true"
              :filterMatchMode="'contains'"
              :filterFields="['name', 'code', 'iso']"
              :filterPlaceholder="$t('countryPhone.searchCountry')"
              class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
              @change="onCountryChange"
            >
              <template #value="slotProps">
                <div v-if="slotProps.value" class="flex items-center">
                  <span class="mr-2">{{ slotProps.value.flag }}</span>
                  <span>{{ slotProps.value.code }}</span>
                </div>
                <span v-else>{{ $t("countryPhone.selectCountry") }}</span>
              </template>
              <template #option="slotProps">
                <div class="flex items-center">
                  <span class="mr-2">{{ slotProps.option.flag }}</span>
                  <span>{{ slotProps.option.code }}</span>
                </div>
              </template>
            </Select>
          </div>
        </div>

        <!-- Поле ввода номера -->
        <InputMask
          v-model="phoneNumber"
          :mask="selectedCountry?.mask || '999 999 999'"
          :placeholder="selectedCountry?.placeholder || '___ ___ ___'"
          :required="required"
          size="small"
          type="tel"
          class="w-full bg-transparent border-none shadow-none focus:ring-0 focus:outline-none text-[14px]"
          @input="onPhoneInput"
        />
      </div>
      <div class="flex flex-col">
        <small class="text-gray-500 dark:text-gray-300 mt-1 text-[12px]">
          <span class="text-gray-500 dark:text-gray-300 font-bold text-[14px] mt-1"
            >{{ required ? $t("PersonalMainRegistration.phoneImportant") : $t("PersonalMainRegistration.phoneOptional") }} &nbsp;</span
          >{{ required ? $t("PersonalMainRegistration.phoneImportantInfo") : $t("PersonalMainRegistration.phoneOptionalInfo") }}</small
        >
        <small class="text-red-500 mt-1 text-[12px]">
          {{ phoneError }}
        </small>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { countries } from "~/utils/countries.js";

// Props
const props = defineProps({
  modelValue: {
    type: String,
    default: "",
  },
  country: {
    type: Object,
    default: null,
  },
  required: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
  },
  hint: {
    type: String,
    default: "",
  },
  phoneError: {
    type: String,
    default: "",
  },
});

// Emits
const emit = defineEmits(["update:modelValue", "update:country", "change"]);

// Local state management
const selectedCountry = ref(null);
const phoneNumber = ref("");

const formattedPhone = computed(() => {
  if (!selectedCountry.value || !phoneNumber.value) return "";
  return `${selectedCountry.value.code} ${phoneNumber.value}`;
});

const isValidPhone = computed(() => {
  if (!selectedCountry.value || !phoneNumber.value) return false;
  const cleanPhone = phoneNumber.value.replace(/\D/g, "");
  return cleanPhone.length >= (selectedCountry.value.minLength || 7) && cleanPhone.length <= (selectedCountry.value.maxLength || 15);
});

const phoneError = computed(() => {
  if (props.error) return props.error;
  if (phoneNumber.value && !isValidPhone.value) {
    return "countryPhone.invalidPhone";
  }
  return "";
});

// Helper functions
function setCountry(country) {
  selectedCountry.value = country;
}

function setPhone(phone) {
  phoneNumber.value = phone;
}

// Вычисляемые свойства
const getCountryLabel = (country) => {
  return `${country.flag} ${country.code}`;
};

// Методы
function onCountryChange(event) {
  const country = event.value;
  setCountry(country);

  emit("update:country", country);
  emit("change", {
    country,
    phone: phoneNumber.value,
    formattedPhone: formattedPhone.value,
    isValid: isValidPhone.value,
  });
}

function onPhoneInput(event) {
  const value = event.target.value;
  setPhone(value);

  emit("update:modelValue", formattedPhone.value);
  emit("change", {
    country: selectedCountry.value,
    phone: value,
    formattedPhone: formattedPhone.value,
    isValid: isValidPhone.value,
  });
}

// Watchers
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue !== formattedPhone.value) {
      setPhone(newValue);
    }
  }
);

watch(
  () => props.country,
  (newCountry) => {
    if (newCountry && newCountry !== selectedCountry.value) {
      setCountry(newCountry);
    }
  }
);

watch(formattedPhone, (newValue) => {
  if (newValue !== props.modelValue) {
    emit("update:modelValue", newValue);
  }
});

// Инициализация
onMounted(() => {
  // Устанавливаем начальные значения
  if (props.country) {
    setCountry(props.country);
  } else if (countries.length > 0) {
    // Устанавливаем первую страну по умолчанию
    setCountry(countries[0]);
    emit("update:country", countries[0]);
  }

  if (props.modelValue) {
    setPhone(props.modelValue);
  }
});
</script>
