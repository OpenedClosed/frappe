<template>
  <div>
    <Toast />

    <div class="flex justify-center items-center w-full h-full p-8" v-if="isLoading || isLoadingData || !entityTitle?.en">
      <Loader style="width: 50px; height: 50px" />
    </div>
    <div v-else-if="isForm" class="p-4">
      <!-- {{ inlineDef.verbose_name[currentLanguage] || inlineDef.verbose_name?.en || " "  }} -->
      <h2 class="text-xl font-bold mb-4">
        {{ isNewItem ? t("MainForm.createPrefix") : t("MainForm.detailPrefix") }}:
        {{ entityTitle[currentLanguage] || entityTitle?.en || " " }}
      </h2>

      <!-- Global error -->
      <!-- <div v-if="errorMessage" class="my-2 p-2 bg-red-100 text-red-700 rounded">
        {{ errorMessage }}
      </div> -->

      <!-- DynamicForm component -->
      <div v-if="currentEntity === 'patients_main_info' && !isNewItem && isReadOnly">
        <PatientsMainInfoView
          v-if="itemData && Object.keys(itemData).length > 0"
          :itemData="itemData"
          :fieldGroups="fieldGroups"
          :filteredFields="filteredFields"
        />
      </div>
      <div v-else-if="currentEntity === 'patients_contact_info' && !isNewItem && isReadOnly">
        <ContactInfoView v-if="itemData && Object.keys(itemData).length > 0" :itemData="itemData" />
      </div>
      <div v-else-if="currentEntity === 'patients_health_survey' && !isNewItem && isReadOnly">
        <PatientsHealthSurveyView v-if="itemData && Object.keys(itemData).length > 0" :itemData="itemData" />
      </div>
      <div v-else-if="currentEntity === 'patients_consents' && !isNewItem && isReadOnly">
        <AgreesPanel v-if="itemData && Object.keys(itemData).length > 0" :filteredFields="filteredFields" :itemData="itemData" />
      </div>
      <div v-else-if="currentEntity === 'patients_bonus_program' && !isNewItem && isReadOnly">
        <PointsTable v-if="itemData && Object.keys(itemData).length > 0" :itemData="itemData" />
      </div>

      <div class="flex flex-col" v-else>
        <DynamicForm
          :fields="filteredFields"
          :fieldGroups="fieldGroups"
          :modelValue="itemData"
          :read-only="isReadOnly"
          :isNewItem="isNewItem"
          :fieldErrors="fieldErrors"
          @update:modelValue="updateItemData"
        />

        <!-- 2) Inlines rendering -->
        <!-- {{ inlines }} -->
        <div v-for="inlineDef in inlines" :key="inlineDef.name" class="mt-8">
          <div>
            <h3 class="text-lg font-bold mb-2">
              {{ inlineDef.verbose_name[currentLanguage] || inlineDef.verbose_name?.en || " " }}
            </h3>

            <InlineList
              :inlineDef="inlineDef"
              :parentEntity="currentEntity"
              :parentId="currentId"
              :items="itemData[inlineDef.field]"
              :readOnly="isReadOnly"
              @reloadParent="reloadCurrentData"
            />
          </div>
        </div>

      
      </div>
        <!-- Control Buttons -->
        <div class="mt-4 flex flex-col md:flex-row gap-2">
          <!-- Existing item: edit, save and delete -->
          <template v-if="!isNewItem">
            <!-- Show edit/save only if update is allowed -->
            <Button v-if="isReadOnly && allowCrudActions.update" :label="t('MainForm.edit')" icon="pi pi-pencil" @click="toggleEditMode" />
            <Button v-else-if="!isReadOnly && allowCrudActions.update" :label="t('MainForm.save')" icon="pi pi-save" @click="saveItem" />
            <!-- Show delete button only if delete is allowed -->
            <Button
              v-if="allowCrudActions.delete"
              :label="t('MainForm.delete')"
              icon="pi pi-trash"
              class="p-button-danger"
              @click="deleteItem"
            />
          </template>

          <!-- New record: create -->
          <Button v-else-if="allowCrudActions.create" :label="t('MainForm.create')" icon="pi pi-check" @click="createItem" />

          <!-- Special button for chat_sessions entity -->
          <Button
            v-if="currentEntity === 'chat_sessions'"
            :label="t('MainForm.openChat')"
            icon="pi pi-comments"
            @click="openChat(itemData?.chat_id)"
          />

          <!-- Navigation: go back to list -->
          <Button
            v-if="currentPageInstances > 1 || currentPageInstances === null"
            :label="t('MainForm.backToList')"
            icon="pi pi-arrow-left"
            class="p-button-text"
            @click="goBack"
          />
        </div>
    </div>

    <!-- Chat view -->
    <div v-else class="flex flex-col justify-between">
      <EmbeddedChat v-if="itemData.chat_id" :id="itemData.chat_id" :user_id="itemData.client[0].client_id || null" />
      <div class="w-full mt-4">
        <Button :label="t('MainForm.backToList')" icon="pi pi-arrow-left" @click="goToFormView" />
      </div>
    </div>
  </div>
</template>

<script setup>
import DynamicForm from "~/components/Dashboard/Components/Form/DynamicForm.vue";
import EmbeddedChat from "~/components/AdminChat/EmbeddedChat.vue";
import InlineList from "~/components/Dashboard/Components/Form/InlineList.vue";
import PatientsMainInfoView from "~/components/Dashboard/Components/Personal/PatientsMainInfoView.vue";
import ContactInfoView from "~/components/Dashboard/Components/Personal/ContactInfoView.vue";
import PatientsHealthSurveyView from "~/components/Dashboard/Components/Personal/PatientsHealthSurveyView.vue";
import AgreesPanel from "~/components/Dashboard/Components/Personal/AgreesPanel.vue";
import PointsTable from "~/components/Dashboard/Components/Personal/PointsTable.vue";
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter, useAsyncData } from "#imports";
import _ from "lodash";
import { useI18n } from "vue-i18n";
const { t } = useI18n();
import { useToast } from "primevue/usetoast";
const toast = useToast();

// ------------------ State & Refs ------------------
const route = useRoute();
const router = useRouter();
const nuxtApp = useNuxtApp();
const inlines = ref([]);

const currentChatId = ref("");
const isForm = ref(true);
const isLoading = ref(false);
const isLoadingData = ref(false);
const itemData = ref({});
const isReadOnly = ref(true);
const errorMessage = ref("");
const fieldErrors = ref({});
const allowCrudActions = ref({});

// URL params
const currentGroup = computed(() => route.params.group);
const currentEntity = computed(() => route.params.entity);
const currentId = computed(() => route.params.id);
const isNewItem = computed(() => currentId.value === "new");
const entityTitle = ref({});
const fieldGroups = ref([]);
const { currentLanguage } = useLanguageState();
// Fields for the form
const fields = ref([]);

// Reference to store original data for diffing changes
const originalData = ref({});
const { currentPageName, currentPageInstances } = usePageState();

// ------------------ Lifecycle & Data Loading ------------------
async function getAdminData() {
  isLoadingData.value = true;
  let responseData;
  try {
    const response = await nuxtApp.$api.get(`api/${currentPageName.value}/info`);
    responseData = response.data;
    console.log("AdminData = ", responseData);
  } catch (err) {
    if (err.response) {
      console.log(err.response);
    } else {
      console.error("Error fetching admin data:", err);
    }
    isLoadingData.value = false;
  }
  isLoadingData.value = false;
  return responseData;
}

const { data: adminData } = await useAsyncData("adminData", getAdminData);

const filteredFields = computed(() => {
  // If this is a new item, filter out fields marked as readonly
  if (isNewItem.value) {
    return fields.value.filter((field) => !field.read_only);
  }
  // Otherwise, use all fields (for edit mode, for example)
  return fields.value;
});

watch(filteredFields, (newValue) => {
  console.log("filteredFields.value", filteredFields.value);
  console.log("itemData.value", itemData.value);
});

onMounted(() => {
  initPage();
  const queryFormState = route.query.isForm;
  // Default to true if not provided
  isForm.value = queryFormState !== "false";
});
async function initPage() {
  try {
    errorMessage.value = "";
    fieldErrors.value = {};

    if (!adminData.value) {
      console.error("AdminData is not loaded");
      return;
    }

    const entityConfig = findEntityConfig();
    if (!entityConfig) {
      console.error("Entity configuration not found in adminData");
      return;
    }
    console.log("entityConfig:", entityConfig?.model?.plural_name);
    entityTitle.value = entityConfig.model.plural_name;
    // Set allowed CRUD actions from the backend config
    allowCrudActions.value = entityConfig.model.allow_crud_actions || {};

    // Get fields and filter only detail fields
    const allFields = entityConfig.model.fields || [];
    const detailFields = entityConfig.model.detail_fields || [];

    fields.value = allFields.filter((field) => detailFields.includes(field.name));

    // Store field groups
    console.log("entityConfig.model.field_groups", entityConfig.model.field_groups);
    fieldGroups.value = entityConfig.model.field_groups || []; // Store field groups

    inlines.value = entityConfig.model.inlines || [];

    if (!isNewItem.value) {
      await fetchItemData(currentId.value);
      console.log("currentPageName.value", currentPageName.value);

      if (currentPageName.value == "admin") {
        if (currentPageInstances.value === 1) {
          isReadOnly.value = true;
        } else {
          isReadOnly.value = false;
        }
      } else {
        isReadOnly.value = true;
      }
    } else {
      itemData.value = fields.value.reduce((acc, field) => {
        acc[field.name] = field.default || null;
        return acc;
      }, {});
      console.log("itemData:", itemData.value);
      originalData.value = itemData.value;
      isReadOnly.value = false;
    }
  } catch (error) {
    console.error("Error initializing page:", error);
    errorMessage.value = parseError(error);
  }
}

function findEntityConfig() {
  const group = adminData.value[currentGroup.value];
  if (!group) return null;
  return group.entities.find((entity) => entity.registered_name === currentEntity.value);
}

function reloadCurrentData() {
  // Just call fetchItemData again
  fetchItemData(currentId.value);
}

// ------------------ Form Handlers ------------------
function updateItemData(updatedValue) {
  itemData.value = updatedValue;
}

function toggleEditMode() {
  isReadOnly.value = !isReadOnly.value;
}

function openChat(chatId) {
  if (chatId) {
    currentChatId.value = chatId;
    setFormState(false);
  }
}

// ------------------ API Calls ------------------
async function fetchItemData(id) {
  isLoading.value = true;
  errorMessage.value = "";
  fieldErrors.value = {};
  try {
    const res = await nuxtApp.$api.get(`api/${currentPageName.value}/${currentEntity.value}/${id}`);
    itemData.value = res.data;
    // Save a deep copy of the fetched data for later diffing
    originalData.value = res.data;
    console.log("ItemData", res.data);
  } catch (error) {
    console.error("Ошибка при загрузке:", error);
    errorMessage.value = parseError(error);
  } finally {
    isLoading.value = false;
  }
}

function getChangedFields() {
  const changed = {};
  // Gather inline field names (so we can skip them)
  const inlineFields = inlines.value.map((inline) => inline.field);

  for (const key in itemData.value) {
    // Skip inline fields
    if (inlineFields.includes(key)) continue;

    // Compare deeply using Lodash
    console.log("itemData.value[key]", itemData.value[key]);
    console.log(" originalData.value[key]", originalData.value[key]);
    if (!_.isEqual(itemData.value[key], originalData.value[key])) {
      changed[key] = itemData.value[key];
      console.log("itemData.value[key]", itemData.value[key]);
    }
  }
  return changed;
}

async function saveItem() {
  errorMessage.value = "";
  fieldErrors.value = {};

  // Gather only the fields that actually changed
  const changedFields = getChangedFields();

  if (Object.keys(changedFields).length === 0) {
    isReadOnly.value = true;
    console.log("Нет изменений для сохранения.");
    return;
  }

  // Filter out null or undefined values from the changedFields
  const sanitizedFields = Object.fromEntries(Object.entries(changedFields).filter(([_, val]) => val != null));

  console.log("changedFields (sanitized):", sanitizedFields);

  try {
    await nuxtApp.$api.patch(`api/${currentPageName.value}/${currentEntity.value}/${currentId.value}`, sanitizedFields);
    console.log("Изменения сохранены");
    originalData.value = itemData.value; // Update original data
    isReadOnly.value = true;
  } catch (error) {
    console.error("Ошибка при сохранении:", error);
    errorMessage.value = parseError(error);
  }
}

async function createItem() {
  errorMessage.value = "";
  fieldErrors.value = {};

  // Build the data object from fields, excluding readOnly for new items
  let dataToSend = {};
  fields.value.forEach((field) => {
    if (!(isNewItem.value && field.read_only)) {
      dataToSend[field.name] = itemData.value[field.name];
    }
  });

  // Filter out any fields that are `null` or `undefined`
  dataToSend = Object.fromEntries(Object.entries(dataToSend).filter(([_, val]) => val != null));

  console.log("Data to send:", dataToSend);

  try {
    const res = await nuxtApp.$api.post(`api/${currentPageName.value}/${currentEntity.value}/`, dataToSend);
    console.log("Запись создана:", res.data);
    router.push(`/${currentPageName.value}/${currentGroup.value}/${currentEntity.value}/${res.data.id}`);
  } catch (error) {
    console.error("Ошибка при создании:", error);
    errorMessage.value = parseError(error);
  }
}

async function deleteItem() {
  const confirmation = confirm(t("MainForm.confirmDelete"));
  if (!confirmation) return;

  errorMessage.value = "";
  fieldErrors.value = {};
  try {
    await nuxtApp.$api.delete(`api/${currentPageName.value}/${currentEntity.value}/${currentId.value}`);
    console.log("Запись удалена");
    goBack();
  } catch (error) {
    console.error("Ошибка при удалении:", error);
    errorMessage.value = parseError(error);
  }
}

// ------------------ Navigation ------------------
function goBack() {
  router.push(`/${currentPageName.value}/${currentGroup.value}/${currentEntity.value}`);
}

function setFormState(state) {
  isForm.value = state;
  router.replace({
    query: {
      ...route.query,
      isForm: state,
    },
  });
}

function goToFormView() {
  setFormState(true);
}

// ------------------ Helpers ------------------
function parseError(error) {
  if (error.response && error.response.data) {
    const data = error.response.data;
    console.log("Error data:", data);

    let toastMessage = "";

    if (data.detail) {
      fieldErrors.value = data.detail;

      if (typeof data.detail === "string") {
        toastMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        toastMessage = data.detail.map((e) => e.msg || e).join(", ");
      } else if (typeof data.detail === "object") {
        const isLangKeyed = Object.keys(data.detail).every((key) => ["en", "ru", "pl", "uk", "ka", "de"].includes(key));
        if (isLangKeyed) {
          toastMessage = data.detail[currentLanguage.value] || Object.values(data.detail)[0];
        } else {
          toastMessage = Object.values(data.detail).flat().join(", ");
        }
      }

      toast.add({
        severity: "error",
        summary: t("toastMessages.errorTitle"),
        detail: toastMessage,
        life: 5000,
      });

      return toastMessage;
    }

    toastMessage = data.message || error.message;
    toast.add({
      severity: "error",
      summary: t("toastMessages.errorTitle"),
      detail: toastMessage,
      life: 5000,
    });

    return toastMessage;
  }

  const fallbackMessage = error.message || t("toastMessages.unknown");
  toast.add({
    severity: "error",
    summary: t("toastMessages.errorTitle"),
    detail: fallbackMessage,
    life: 5000,
  });

  return fallbackMessage;
}
</script>
