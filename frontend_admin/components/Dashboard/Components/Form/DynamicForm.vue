<template>
  <div>
    <!-- Iterate over field groups -->
    <div v-for="group in groupedFields" :key="group.title.en">
      <div
        v-if="!group.fields.every((field) => isDisabled(field)) || !isNewItem"
        class="mb-6 bg-neutralLight  border border-neutralDark  rounded-lg p-6 shadow"
      >
        <!-- Group header -->
        <h2 class="text-2xl font-bold text-primaryDark mb-2">
          {{ group.title?.[currentLanguage] || group.title?.en || "" }}
        </h2>

        <p v-if="group.help_text" class="text-base  mb-4">
          {{ group.help_text[currentLanguage] || group.help_text.en || "" }}
        </p>
        <!-- {{ internalValue }} -->

        <!-- Render fields for this group -->
        <div class="p-fluid flex flex-wrap gap-4">
          <div v-for="field in group.fields" :key="field.name" class="field flex flex-col w-full md:w-1/2">
            <!-- Field label -->
            <label :for="field.name" class="font-semibold mb-2 flex items-center">
              {{ field.title[currentLanguage] || field.title["en"] }}

              <span
                v-if="field.help_text && Object.keys(field.help_text).length > 0"
                class="inline-flex items-center ml-2 cursor-pointer"
                v-tooltip="field.help_text[currentLanguage] || field.help_text['en']"
              >
                <i class="pi pi-question-circle text-gray-600 dark:text-gray-300"></i>
              </span>

              <span v-if="field.required" class="text-red-500 ml-1">*</span>
            </label>

            <!-- Field element -->
            <div class="flex flex-row gap-2 w-full">
              <!-- 1) Select -->
              <Dropdown
                v-if="field.type === 'select'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :options="transformChoices(field.choices)"
                optionValue="value"
                optionLabel="label"
                :disabled="isDisabled(field)"
                class="w-full"
                @change="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />
              <!-- 9) Rating field -->
              <Rating
                v-else-if="field.type === 'rating'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :disabled="isDisabled(field)"
                :stars="5"
                :iconOn="field.default?.type === 'emoji' ? 'pi pi-smile' : 'pi pi-star-fill'"
                :iconOff="field.default?.type === 'emoji' ? 'pi pi-frown' : 'pi pi-star'"
                class="w-full"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />
              <!-- 10) Datetime field -->
              <Calendar
                v-else-if="field.type === 'datetime'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :disabled="isDisabled(field)"
                showTime
                dateFormat="yy-mm-dd"
                class="w-full"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />

              <!-- 2) MultiSelect -->
              <MultiSelect
                v-else-if="field.type === 'multiselect'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :options="transformChoices(field.choices)"
                optionValue="value"
                optionLabel="label"
                :disabled="isDisabled(field)"
                class="w-full"
                @change="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />
              <!-- Tag Cloud Field -->
              <Chips
                v-else-if="field.type === 'tag_cloud'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :disabled="isDisabled(field)"
                class="w-full"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                placeholder="Enter tags..."
              />
              <!-- Autocomplete Field -->
              <AutoComplete
                v-else-if="field.type === 'autocomplete'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :suggestions="autocompleteSuggestions"
                field="name"
                :disabled="isDisabled(field)"
                class="w-full"
                @complete="onAutoComplete"
                @change="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                placeholder="Enter a country..."
              />

              <!-- Multi Files Upload Field -->
              <div v-else-if="field.type === 'multifile'" class="w-full">
                <!-- Если файлов ещё нет -->
                <div v-if="!internalValue[field.name] || internalValue[field.name].length === 0">
                  <FileUpload
                    :id="field.name"
                    mode="basic"
                    :disabled="isDisabled(field)"
                    :auto="true"
                    :multiple="true"
                    :maxFileSize="5242880"
                    @upload="(e) => onMultiFileUploadComplete(e, field.name)"
                    class="w-full"
                    choose-label="Загрузить"
                    :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                  />
                </div>
                <!-- Если файлы уже загружены -->
                <div v-else class="flex flex-col gap-2">
                  <div class="flex flex-col gap-2">
                    <div
                      v-for="(file, index) in internalValue[field.name]"
                      :key="index"
                      class="flex items-center justify-between border p-2 rounded"
                    >
                      <a :href="currentUrl + file.url" target="_blank" class="underline">
                        {{ file.name || "Скачать файл" }}
                      </a>
                      <Button
                        :disabled="isDisabled(field)"
                        icon="pi pi-times"
                        severity="danger"
                        @click="removeMultiFile(field.name, index)"
                      />
                    </div>
                  </div>
                  <div class="mt-2">
                    <FileUpload
                      :id="field.name + '-upload'"
                      mode="basic"
                      accept="*/*"
                      :disabled="isDisabled(field)"
                      :auto="true"
                      :multiple="true"
                      :maxFileSize="5242880"
                      @upload="(e) => onMultiFileUploadComplete(e, field.name)"
                      class="w-full"
                      choose-label="Добавить файлы"
                      :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                    />
                  </div>
                </div>
              </div>
              <!-- Цветовой мультиселект с квадратиками -->

              <!-- 3) Boolean (checkbox) -->
              <div v-else-if="field.type === 'boolean'" class="flex items-center gap-2">
                <Checkbox
                  :id="field.name"
                  v-model="internalValue[field.name]"
                  :disabled="isDisabled(field)"
                  @change="emitUpdate"
                  binary
                  :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                />
                <label :for="field.name">
                  {{ field.title[currentLanguage] || field.title["en"] }}
                </label>
              </div>

              <div v-else-if="field.type === 'checkbox_group'" class="w-full">
                <div class="flex flex-col gap-2">
                  <div v-for="option in field.choices" :key="option.value" class="flex items-center">
                    <Checkbox
                      :id="`${field.name}-${option.value}`"
                      v-model="internalValue[field.name]"
                      :value="option.value"
                      :disabled="isDisabled(field)"
                      class="mr-2"
                      :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                    />
                    <label :for="`${field.name}-${option.value}`">
                      {{ option.label }}
                    </label>
                  </div>
                </div>
              </div>
              <div v-else-if="field.type === 'drag_and_drop'" class="w-full">
                <!-- {{ field.choices }} -->
                <!-- <draggable
    v-model="field.choices"
    :options="{ animation: 200 }"
    tag="div"
    @end="emitUpdate"
  >

    <template #item="{ element }">
              <div class="flex items-center p-3 mb-2 bg-white border rounded hover:bg-gray-50">
                <i class="pi pi-bars handle mr-2 text-gray-500 cursor-move"></i>
                <span>{{ element.label[currentLanguage] || element.label.en }}</span>
              </div>
            </template>
  </draggable> -->

                <!-- <draggable 
           v-model="internalValue[field.name]"
            item-key="letter"
            :animation="200"
            ghost-class="ghost"
            drag-class="drag"
            handle=".handle"
          >
            <template #item="{ element }">
              <div class="flex items
              -center p-3 mb-2 bg-white border rounded hover:bg-gray-50">
                <i class="pi pi-bars
                handle mr-2 text-gray-500 cursor-move"></i>
                <span>{{ element.label[currentLanguage] || element.label.en }}</span>
              </div>
            </template>
          </draggable> -->
              </div>

              <!-- Single File Upload Field -->
              <div v-else-if="field.type === 'file'" сlass="w-full">
                <!-- If no file is uploaded -->
                <div v-if="!internalValue[field.name]">
                  <FileUpload
                    :id="field.name"
                    mode="basic"
                    :disabled="isDisabled(field)"
                    :auto="true"
                    :multiple="false"
                    accept="*"
                    :maxFileSize="5242880"
                    @upload="(e) => onFileUploadComplete(e, field.name)"
                    class="w-full"
                    choose-label="Загрузить"
                    :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                  />
                </div>
                <!-- If file is uploaded, display file link and remove button -->
                <div v-else class="flex flex-col gap-2 w-full">
                  <a :href="currentUrl + internalValue[field.name].url" target="_blank" class="underline">
                    {{ internalValue[field.name].name || "Скачать файл" }}
                  </a>
                  <div class="flex gap-2 w-full">
                    <Button
                      :disabled="isDisabled(field)"
                      label="Удалить"
                      icon="pi pi-times"
                      severity="danger"
                      @click="removeFile(field.name)"
                      class="w-full"
                    />
                  </div>
                </div>
              </div>
              <!-- Calendar (Date) Field -->
              <Calendar
                v-else-if="field.type === 'calendar'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :disabled="isDisabled(field)"
                dateFormat="dd.mm.yy"
                class="w-full"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />
              <!-- Date & Time Field -->
              <Calendar
                v-else-if="field.type === 'calendar_time'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :disabled="isDisabled(field)"
                showTime
                dateFormat="dd.mm.yy"
                class="w-full"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />

              <!-- 4) Image -->
              <div v-else-if="field.type === 'image'" class="w-full">
                <div v-if="!internalValue[field.name]?.url">
                  <FileUpload
                    :id="field.name"
                    :maxFileSize="5242880"
                    mode="basic"
                    accept="image/*"
                    :disabled="isDisabled(field)"
                    :auto="true"
                    :multiple="false"
                    @upload="(e) => onUploadComplete(e, field.name)"
                    class="w-full"
                    choose-label="Загрузить"
                    :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                  />
                </div>
                <div v-else class="flex flex-col gap-2">
                  <img
                    :src="currentUrl + internalValue[field.name].url"
                    alt="preview"
                    class="max-h-40 object-contain border rounded shadow"
                  />
                  <div class="flex gap-2">
                    <Button
                      :disabled="isDisabled(field)"
                      label="Удалить"
                      icon="pi pi-times"
                      severity="danger"
                      @click="removeImage(field.name)"
                    />
                  </div>
                </div>
              </div>

              <!-- Range Slider Field -->
              <Slider
                v-else-if="field.type === 'range_value'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :range="true"
                :disabled="isDisabled(field)"
                :min="field.settings?.min || field.default?.min_value || 0"
                :max="field.settings?.max || field.default?.max_value || 100"
                class="w-full my-4"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />

              <!-- Multi Images Field -->
              <div v-else-if="field.type === 'multiimage'" class="w-full">
                <!-- If no images have been uploaded yet -->
                <div v-if="!internalValue[field.name] || internalValue[field.name].length === 0">
                  <FileUpload
                    :id="field.name"
                    mode="basic"
                    accept="image/*"
                    :disabled="isDisabled(field)"
                    :auto="true"
                    :multiple="true"
                    :maxFileSize="5242880"
                    @upload="(e) => onMultiUploadComplete(e, field.name)"
                    class="w-full"
                    choose-label="Загрузить"
                    :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                  />
                </div>
                <!-- If images exist, display them and allow additional uploads -->
                <div v-else class="flex flex-col gap-2">
                  <div class="flex flex-wrap gap-2">
                    <div v-for="(image, index) in internalValue[field.name]" :key="index" class="relative">
                      <img :src="currentUrl + image.url" alt="preview" class="max-h-40 object-contain border rounded shadow" />
                      <Button
                        :disabled="isDisabled(field)"
                        icon="pi pi-times"
                        severity="danger"
                        @click="removeMultiImage(field.name, index)"
                        class="absolute top-0 right-0"
                      />
                    </div>
                  </div>
                  <div class="mt-2">
                    <FileUpload
                      :id="field.name + '-upload'"
                      mode="basic"
                      accept="image/*"
                      :disabled="isDisabled(field)"
                      :auto="true"
                      :multiple="true"
                      :maxFileSize="5242880"
                      @upload="(e) => onMultiUploadComplete(e, field.name)"
                      class="w-full"
                      choose-label="Добавить изображения"
                      :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                    />
                  </div>
                </div>
              </div>

              <!-- 4.5) JSON editor -->
              <div v-else-if="field.type === 'json'" class="w-full">
                <json-editor
                  v-if="!isDisabled(field)"
                  :id="field.name"
                  height="400"
                  class="w-full"
                  :mode="isDisabled(field) ? 'view' : 'text'"
                  :queryLanguagesIds="queryLanguages"
                  v-model="internalValue[field.name]"
                  :disabled="isDisabled(field)"
                  @error="onError"
                  @focus="onFocus"
                  @blur="onBlur"
                />
                <Textarea
                  v-else
                  :id="field.name"
                  v-model="jsonString[field.name]"
                  :disabled="true"
                  class="w-full min-h-[200px] bg-gray-100 dark:bg-gray-800 dark:text-white p-2 rounded border dark:border-gray-700"
                  :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
                />
              </div>
              <!-- Location Field using nuxt-maplibre -->
              <div v-else-if="field.type === 'location'" class="w-full">
                <MglMap
                  :map-style="style"
                  :center="center"
                  :zoom="zoom"
                  style="height: 300px; width: 100%"
                  @click="(e) => onMapClick(e, field.name)"
                >
                  <MglNavigationControl />
                  <MglMarker v-if="internalValue[field.name]" :position="[internalValue[field.name].lng, internalValue[field.name].lat]" />
                </MglMap>
              </div>

              <!-- Textarea Field -->
              <Textarea
                v-else-if="field.type === 'textarea'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :disabled="isDisabled(field)"
                rows="5"
                class="w-full"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />
              <!-- 11) WYSIWYG Field -->
              <!-- <Editor v-else-if="field.type === 'wysiwyg'" :id="field.name" v-model="internalValue[field.name]"
              :disabled="isDisabled(field)" class="w-full" @input="emitUpdate"
              :class="{ 'p-invalid': parsedFieldErrors[field.name] }" /> -->

              <!-- <InputText v-else-if="field.type === 'string'" :id="field.name" v-model="internalValue[field.name]"
                :disabled="isDisabled(field)" class="w-full" @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }" /> -->

              <!-- 5) String -->
              <InputText
                v-else-if="field.type === 'string' || field.type === 'unknown'"
                :id="field.name"
                v-model="getLocalizedField(field.name).value"
                :disabled="isDisabled(field)"
                class="w-full"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />
              <!-- 7) Email -->
              <InputText
                v-else-if="field.type === 'email'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :disabled="isDisabled(field)"
                type="email"
                class="w-full"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />
              <!-- 7) Phone -->
              <!-- Phone with mask (international variant supported) -->
              <InputMask
                v-else-if="field.type === 'phone'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :disabled="isDisabled(field)"
                :mask="field.settings?.mask ? field.settings?.mask : '+999 999 999 9999'"
                class="w-full"
                @update:modelValue="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />
              <!-- 8) Password field -->
              <Password
                v-else-if="field.type === 'password'"
                :id="field.name"
                v-model="internalValue[field.name]"
                :disabled="isDisabled(field)"
                toggle-mask
                class="w-full"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />

              <!-- 6) Fallback for unknown types -->
              <InputText
                v-else
                :id="field.name"
                v-model="internalValue[field.name]"
                :disabled="isDisabled(field)"
                class="w-full"
                @input="emitUpdate"
                :class="{ 'p-invalid': parsedFieldErrors[field.name] }"
              />
              <Button
                v-if="!isDisabled(field) && (field.type === 'select' || field.type === 'string')"
                @click="resetField(field)"
                icon="pi pi-times"
                class="p-button-sm"
              />
            </div>

            <!-- Field error message -->
            <div v-if="parsedFieldErrors[field.name]" class="text-red-500 dark:text-red-400 text-sm mt-1" :id="`${field.name}-error`">
              {{ parsedFieldErrors[field.name] }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch, ref } from "vue";
import InputText from "primevue/inputtext";
import Dropdown from "primevue/dropdown";
import MultiSelect from "primevue/multiselect";
import Checkbox from "primevue/checkbox";
import FileUpload from "primevue/fileupload";
import Button from "primevue/button";
import Textarea from "primevue/textarea";
import draggable from "vuedraggable";
// If using nuxt-jsoneditor:
// import JSONEditor from 'nuxt-jsoneditor'

const { currentUrl } = useURLState(); // Your composable for base URL or something similar
const { currentLanguage } = useLanguageState(); // Your composable for current language

const props = defineProps({
  fields: {
    type: Array,
    required: true,
  },
  fieldGroups: {
    type: Array,
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
  // An object with errors: { fieldName: "Error text" }
  fieldErrors: {
    default: () => ({}),
  },
});

function isObjectValue(fieldName) {
  const value = getLocalizedField(fieldName).value;
  // If the value exists and its type is object, return true.
  return value && typeof value === "object";
}
// Your localization function
function localizeData(data, lang) {
  if (Array.isArray(data)) {
    return data.map((item) => localizeData(item, lang));
  } else if (data && typeof data === "object") {
    if (data.hasOwnProperty("en") && data.hasOwnProperty("ru")) {
      let localized = data[lang] || data["en"];
      try {
        const parsed = JSON.parse(localized);
        if (parsed && typeof parsed === "object" && (parsed.hasOwnProperty(lang) || parsed.hasOwnProperty("en"))) {
          localized = parsed[lang] || parsed["en"];
        }
      } catch (e) {
        // Not a JSON string, leave as is.
      }
      return localized;
    } else {
      const result = {};
      for (const key in data) {
        result[key] = localizeData(data[key], lang);
      }
      return result;
    }
  }
  return data;
}

function getLocalizedField(fieldName) {
  return computed({
    get() {
      return localizeData(internalValue[fieldName], currentLanguage.value);
    },
    set(newValue) {
      // If the stored value is an object (language object), update the current language only.
      if (internalValue[fieldName] && typeof internalValue[fieldName] === "object") {
        internalValue[fieldName][currentLanguage.value] = newValue;
      } else {
        internalValue[fieldName] = newValue;
      }
      emitUpdate();
    },
  });
}

watch(
  () => props.fields,
  (newVal) => {
    console.log("Fields changed:", newVal);
  },
  { deep: true }
);
watch(
  () => props.fieldGroups,
  (newVal) => {
    console.log("fieldGroups:", newVal);
  },
  { deep: true }
);
const jsonString = computed(() => {
  return Object.keys(internalValue).reduce((acc, key) => {
    acc[key] = JSON.stringify(internalValue[key], null, 2);
    return acc;
  }, {});
});

const groupedFields = computed(() => {
  // If fieldGroups is not provided, return a default group with all fields.
  if (!props.fieldGroups || props.fieldGroups.length === 0) {
    return [
      {
        title: { en: "", ru: "" },
        help_text: { en: "", ru: "" },
        fields: props.fields,
      },
    ];
  }

  // Map each group to include its corresponding fields.
  return props.fieldGroups.map((group) => {
    return {
      ...group,
      // Filter the fields whose name is included in the group's fields array.
      fields: props.fields.filter((field) => group.fields.includes(field.name)),
    };
  });
});

let parsedFieldErrors = ref({});
// A copy of the initial modelValue to allow resetting
const originalValue = ref({ ...props.modelValue });

// Reset logic for a single field
function resetField(field) {
  // Reset only this field to original
  internalValue[field.name] = originalValue.value[field.name] ?? null;
  emitUpdate();
}

watch(
  () => props.fieldErrors,
  (newVal) => {
    console.log("props.fieldErrors", newVal);

    if (!newVal || typeof newVal !== "string") {
      console.warn("Skipping parsing, fieldErrors is not a string:", newVal);
      parsedFieldErrors.value = newVal;
      return;
    }

    try {
      // 1️⃣ Replace single quotes with double quotes for valid JSON format
      let fixed = newVal.replace(/'/g, '"').replace(/^(\s*)(\d+):\s*\{/, '$1"$2": {');

      // 2️⃣ Wrap the string in `{}` to make it a valid JSON object
      fixed = `{${fixed}}`;

      // 3️⃣ Parse the JSON string
      let parsed = JSON.parse(fixed);

      console.log("Parsed object:", parsed);

      if (parsed["400"]) {
        console.log("Parsed 400 errors:", parsed["400"]);
        parsedFieldErrors.value = parsed["400"];
      }
    } catch (err) {
      console.error("JSON parse error:", err, "Raw input:", newVal);
    }
  },
  { deep: true }
);
watch(
  () => parsedFieldErrors.value,
  async (newVal) => {
    await nextTick();

    const fieldNames = Object.keys(newVal);
    if (!fieldNames.length) return;

    // Grab the last field with an error (or the first, if you prefer).
    const lastField = fieldNames[fieldNames.length - 1];
    const errorElement = document.getElementById(`${lastField}-error`);
    if (errorElement) {
      errorElement.scrollIntoView({
        behavior: "smooth",
        block: "center", // Position it in the middle of the viewport vertically
        inline: "center", // ...and horizontally if needed
      });
    }
  },
  { deep: true }
);

const emit = defineEmits(["update:modelValue"]);

// Local reactive state so we don't mutate props directly
const internalValue = reactive({ ...props.modelValue });

// Allowed languages for the JSON editor
const queryLanguages = ref(["javascript", "lodash", "jmespath"]);

function getLocalizedText(field, currentLanguage) {
  if (!field || !field[currentLanguage]) {
    return "";
  }

  const value = field[currentLanguage];

  // If it's a string, let's see if it looks like JSON
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);

      // If the parsed object also has an `en` or `ru` inside, return that
      if (typeof parsed === "object" && parsed[currentLanguage]) {
        return parsed[currentLanguage];
      }
      // Otherwise, return the entire parsed value as a string
      return typeof parsed === "string" ? parsed : value;
    } catch (err) {
      // If it's not valid JSON, just return it “as is”
      return value;
    }
  }

  // If `field[currentLanguage]` is not a string, maybe it’s already an object
  // or something else. We return it directly, or convert to a string as needed.
  return String(value);
}
// Watch for external modelValue changes
watch(
  () => props.modelValue,
  (newVal) => {
    Object.assign(internalValue, newVal);
  },
  { deep: true }
);

function isDisabled(field) {
  return props.readOnly || field.read_only;
}

// Convert array of choices to correct { label, value } format
function transformChoices(choices = []) {
  return choices?.map((choice) => {
    let { label, value } = choice;
    if (typeof label === "object" && label !== null) {
      label = label[currentLanguage.value] || label.en || "";
    } else if (typeof label === "string") {
      // Attempt to parse JSON-encoded label
      try {
        const parsed = JSON.parse(label);
        if (parsed && typeof parsed === "object") {
          label = parsed[currentLanguage] || parsed.en || "";
        }
      } catch (e) {
        // If parsing fails, just leave label as is
      }
    }
    return { label, value };
  });
}
function transformColorChoices(choices) {
  return Array.isArray(choices)
    ? choices.map((choice) => {
        const label = choice.label?.[currentLanguage.value] || choice.label?.en || "";
        const color = choice.value?.settings?.color || "";
        console.log("Color choice:", {
          label,
          value: color, // must match v-model items!
        });
        return {
          label,
          value: color, // must match v-model items!
        };
      })
    : [];
}

function emitUpdate() {
  console.log("internalValue", internalValue);
  emit("update:modelValue", { ...internalValue });
}

// JSON Editor handlers
function onError(error) {
  console.error("JSON Editor error:", error);
}
function onFocus() {}
function onBlur() {
  // Emit changes on blur, for example
  emitUpdate();
}

// Image upload handling
function onUploadComplete(event, fieldName) {
  console.log("Upload complete:", event);

  const formData = new FormData();
  event.files.forEach((file) => {
    formData.append("file", file);
  });

  const { $api } = useNuxtApp();
  $api
    .post("/api/basic/upload_file", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    })
    .then((response) => {
      console.log("Upload successful:", response);
      const imageUrl = response.data?.file_path;
      if (imageUrl) {
        internalValue[fieldName] = { url: imageUrl };
        emitUpdate();
      }
    })
    .catch((error) => {
      console.error("Upload failed:", error);
    });
}
function onMultiUploadComplete(event, fieldName) {
  console.log("Multi-upload complete:", event);
  const formData = new FormData();
  event.files.forEach((file) => {
    formData.append("file", file);
  });

  const { $api } = useNuxtApp();
  $api
    .post("/api/basic/upload_file", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    })
    .then((response) => {
      console.log("Multi-upload successful:", response);
      const imageUrl = response.data?.file_path;
      if (imageUrl) {
        // Initialize the field array if it doesn't exist
        if (!internalValue[fieldName]) {
          internalValue[fieldName] = [];
        }
        internalValue[fieldName].push({ url: imageUrl });
        emitUpdate();
      }
    })
    .catch((error) => {
      console.error("Multi-upload failed:", error);
    });
}

function removeMultiImage(fieldName, index) {
  if (Array.isArray(internalValue[fieldName])) {
    internalValue[fieldName].splice(index, 1);
    emitUpdate();
  }
}

function removeImage(fieldName) {
  internalValue[fieldName] = null;
  emitUpdate();
}

function clearImageAndUpload(fieldName) {
  internalValue[fieldName] = null;
}

function onFileUploadComplete(event, fieldName) {
  console.log("File upload complete:", event);
  const formData = new FormData();
  event.files.forEach((file) => {
    formData.append("file", file);
  });

  // Get the original file from the event (for single file upload, it's the first file)
  const originalFile = event.files[0];

  const { $api } = useNuxtApp();
  $api
    .post("/api/basic/upload_file", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    })
    .then((response) => {
      console.log("File upload successful:", response);
      // Assume response.data contains file_path and optionally file_name
      const fileUrl = response.data?.file_path;
      // Use the file name from the response if available,
      // otherwise, fallback to the original file name
      const fileName = response.data?.file_name || originalFile.name;
      if (fileUrl) {
        internalValue[fieldName] = { url: fileUrl, name: fileName };
        emitUpdate();
      }
    })
    .catch((error) => {
      console.error("File upload failed:", error);
    });
}

function removeFile(fieldName) {
  internalValue[fieldName] = null;
  emitUpdate();
}

function onMultiFileUploadComplete(event, fieldName) {
  console.log("Multi-file upload complete:", event);
  const formData = new FormData();

  // Iterate through each file and append both file and its name if needed.
  event.files.forEach((file) => {
    formData.append("file", file);
    // Optionally, you could also send the file name to your server:
    // formData.append("fileName", file.name);
  });

  const { $api } = useNuxtApp();
  $api
    .post("/api/basic/upload_file", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    })
    .then((response) => {
      console.log("Multi-file upload successful:", response);
      // Assume the response returns details for each uploaded file,
      // or a single file detail if only one file is processed.
      // For each file uploaded, you can use file.name from event.files
      // if your response doesn't contain it.
      event.files.forEach((file) => {
        const fileUrl = response.data?.file_path; // Or match response data per file if available
        const fileName = response.data?.file_name || file.name;
        if (fileUrl) {
          if (!internalValue[fieldName]) {
            internalValue[fieldName] = [];
          }
          internalValue[fieldName].push({ url: fileUrl, name: fileName });
        }
      });
      emitUpdate();
    })
    .catch((error) => {
      console.error("Multi-file upload failed:", error);
    });
}

function removeMultiFile(fieldName, index) {
  if (Array.isArray(internalValue[fieldName])) {
    internalValue[fieldName].splice(index, 1);
    emitUpdate();
  }
}
const autocompleteSuggestions = ref([]);

function onAutoComplete(event) {
  // Define a static list of countries. You could also fetch this from an API.
  const countries = [
    { name: "United States" },
    { name: "Canada" },
    { name: "United Kingdom" },
    { name: "Australia" },
    { name: "Germany" },
    { name: "France" },
    { name: "Spain" },
    { name: "Italy" },
    { name: "Brazil" },
    { name: "India" },
  ];

  // Filter the countries by checking if the country name includes the query text.
  autocompleteSuggestions.value = countries.filter((country) => country.name.toLowerCase().includes(event.query.toLowerCase()));
}

const style = "https://api.maptiler.com/maps/streets/style.json?key=cQX2iET1gmOW38bedbUh";
const center = [-1.559482, 47.21322];
const zoom = 8;

function onMapClick(e, fieldName) {
  // Extract lng/lat from the click event (adjust based on how MglMap returns the event)
  const { lng, lat } = e.lngLat || {};
  if (lng && lat) {
    internalValue[fieldName] = { lng, lat };
    emitUpdate();
  }
}
</script>

<style scoped>
.field label {
  margin-bottom: 0.25rem;
}

.ghost {
  opacity: 0.5;
  background: #c8ebfb;
}

.drag {
  opacity: 0.9;
}

.handle {
  cursor: move;
}

.flip-list-move {
  transition: transform 0.5s;
}

.no-move {
  transition: transform 0s;
}

:deep(.p-dialog-content) {
  @apply dark:bg-gray-800;
}

.dark .ghost {
  background: #1e3a8a;
  opacity: 0.5;
}

.dark .bg-white {
  @apply bg-gray-700;
}

.dark .hover\:bg-gray-50:hover {
  @apply hover:bg-gray-600;
}
</style>
