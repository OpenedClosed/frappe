<template>
  <div class="p-fluid flex flex-wrap gap-4">
    <!-- Iterate over fields passed via props.fields -->
    <div
      v-for="field in fields"
      :key="field.name"
      class="field flex flex-col w-full md:w-1/2"
    >
      <!-- Label -->
      <label :for="field.name" class="block font-semibold mb-2">
        {{ field.title[currentLanguage]|| field.title['en'] }}
        <span v-if="field.required" class="text-red-500">*</span>
      </label>

      <!-- Field Input -->
      <div>
        <!-- 1) If field has choices, use Dropdown -->
        <Dropdown
          v-if="hasChoices(field)"
          :id="field.name"
          v-model="internalValue[field.name]"
          :options="field.choices"
          optionValue="value"
          optionLabel="label"
          :disabled="isDisabled(field)"
          class="w-full"
          @change="emitUpdate"
        />

        <!-- 2) If type is boolean, use Checkbox -->
        <div v-else-if="field.type === 'boolean'" class="flex items-center gap-2">
          <Checkbox
            :id="field.name"
            v-model="internalValue[field.name]"
            :disabled="isDisabled(field)"
            @change="emitUpdate"
            binary
          />
          <label :for="field.name">{{ field.title[currentLanguage]|| field.title['en'] }}</label>
        </div>

        <!-- 3) If type is string, use InputText -->
        <InputText
          v-else-if="field.type === 'string'"
          :id="field.name"
          v-model="internalValue[field.name]"
          :disabled="isDisabled(field)"
          class="w-full"
          @input="emitUpdate"
        />

        <!-- 4) Default to InputText for other types -->
        <InputText
          v-else
          :id="field.name"
          v-model="internalValue[field.name]"
          :disabled="isDisabled(field)"
          class="w-full"
          @input="emitUpdate"
        />
      </div>

      <!-- Error messages for this field -->
      <div
        v-if="fieldErrors[field.name]"
        class="text-red-500 text-sm mt-1"
        :id="`${field.name}-error`"
      >
        {{fieldErrors[field.name]}}
      </div>
    </div>
  </div>
</template>

<script setup>
import { isReadonly, reactive, watch } from "vue";
import InputText from "primevue/inputtext";
import Dropdown from "primevue/dropdown";
import Checkbox from "primevue/checkbox";
const { currentLanguage } = useLanguageState();
const props = defineProps({
  fields: {
    type: Array,
    required: true,
  },
  modelValue: {
    type: Object,
    default: () => ({}),
  },
  readOnly: {
    type: Boolean,
    default: false,
  },
  isNewItem: {
    type: Boolean,
    default: false,
  },
  // Prop to accept field-specific errors keyed by field id/name
  fieldErrors: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(["update:modelValue"]);
const internalValue = reactive({ ...props.modelValue });

watch(
  () => props.modelValue,
  (newVal) => {
    Object.assign(internalValue, newVal);
  },
  { deep: true }
);

function hasChoices(field) {
  return Array.isArray(field.choices) && field.choices.length > 0;
}

function isDisabled(field) {
  return props.readOnly || field.read_only;
}

function emitUpdate() {
  emit("update:modelValue", { ...internalValue });
}
</script>

<style scoped>
.field label {
  margin-bottom: 0.25rem;
}
</style>
