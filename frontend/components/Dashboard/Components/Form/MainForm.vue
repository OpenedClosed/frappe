<template>
  <div>
    <!-- If we are in "form" view -->
    <div v-if="isForm" class="p-4">
      <h2 class="text-xl font-bold mb-4">{{ isNewItem ? "Создание новой записи" : "Детальная запись" }}: {{ entityTitle }}</h2>

      <!-- Global error -->
      <div v-if="errorMessage" class="my-2 p-2 bg-red-100 text-red-700 rounded">
        {{ errorMessage }}
      </div>

      <p v-if="isLoading">Загрузка данных...</p>

      <div v-else>
        <!-- DynamicForm component -->
        <DynamicForm
          :fields="filteredFields"
          :modelValue="itemData"
          :read-only="isReadOnly"
          :isNewItem="isNewItem"
          :fieldErrors="fieldErrors"
          @update:modelValue="updateItemData"
        />

        <!-- 2) Inlines rendering -->
        <div  v-for="inlineDef in inlines" :key="inlineDef.name" class="mt-8">
          <div v-if="itemData[inlineDef.field].length > 0">
            <h3 class="text-lg font-bold mb-2">
              {{ inlineDef.plural_name.en || inlineDef.name }}
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

        <!-- Control Buttons -->
        <div class="mt-4 flex flex-col md:flex-row gap-2">
          <!-- Existing item: edit, save and delete -->
          <template v-if="!isNewItem">
            <Button v-if="isReadOnly" label="Редактировать" icon="pi pi-pencil" @click="toggleEditMode" />
            <Button v-else label="Сохранить" icon="pi pi-save" @click="saveItem" />
            <Button label="Удалить" icon="pi pi-trash" class="p-button-danger" @click="deleteItem" />
          </template>

          <!-- New record: create -->
          <Button v-else label="Создать запись" icon="pi pi-check" @click="createItem" />

          <!-- Special button for chat_sessions entity -->
          <Button  v-if="currentEntity === 'chat_sessions'" label="Открыть чат" icon="pi pi-comments" @click="openChat(itemData?.chat_id)" />

          <!-- Navigation: go back to list -->
          <Button label="Назад к списку" icon="pi pi-arrow-left" class="p-button-text" @click="goBack" />
        </div>
      </div>
    </div>

    <!-- Chat view -->
    <div v-else class="flex flex-col justify-between">
      <EmbeddedChat :id="itemData.chat_id" :user_id="itemData.client_id" />
      <div class="w-full mt-4">
        <Button label="Назад к записи" icon="pi pi-arrow-left" @click="goToFormView" />
      </div>
    </div>
  </div>
</template>

<script setup>
import DynamicForm from "~/components/Dashboard/Components/Form/DynamicForm.vue";
import EmbeddedChat from "~/components/AdminChat/EmbeddedChat.vue";
import InlineList from "~/components/Dashboard/Components/Form/InlineList.vue";
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter, useAsyncData } from "#imports";

// ------------------ State & Refs ------------------
const route = useRoute();
const router = useRouter();
const nuxtApp = useNuxtApp();
const inlines = ref([]);

const currentChatId = ref("");
const isForm = ref(true);
const isLoading = ref(false);
const itemData = ref({});
const isReadOnly = ref(true);
const errorMessage = ref("");
const fieldErrors = ref({});

// URL params
const currentGroup = computed(() => route.params.group);
const currentEntity = computed(() => route.params.entity);
const currentId = computed(() => route.params.id);
const isNewItem = computed(() => currentId.value === "new");
const entityTitle = computed(() => currentEntity.value);

// Fields for the form
const fields = ref([]);

// Reference to store original data for diffing changes
const originalData = ref({});

// ------------------ Lifecycle & Data Loading ------------------
async function getAdminData() {
  let responseData;
  try {
    const response = await nuxtApp.$api.get("api/admin/info");
    responseData = response.data;
    console.log("AdminData = ", responseData);
  } catch (err) {
    if (err.response) {
      console.log(err.response);
    } else {
      console.error("Error fetching admin data:", err);
    }
  }
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

    // Find entity configuration
    const entityConfig = findEntityConfig();
    if (!entityConfig) {
      console.error("Entity configuration not found in adminData");
      return;
    }

    // Get fields and filter only detail fields
    const allFields = entityConfig.model.fields || [];
    const detailFields = entityConfig.model.detail_fields || [];

    // Filter fields based on detail_fields
    fields.value = allFields.filter((field) => detailFields.includes(field.name));

    // *** Get any inlines ***
    inlines.value = entityConfig.model.inlines || [];

    if (!isNewItem.value) {
      // Edit mode: fetch existing data and store its original snapshot
      await fetchItemData(currentId.value);
      isReadOnly.value = true;
    } else {
      // New item: set default values and clone as original data
      itemData.value = fields.value.reduce((acc, field) => {
        acc[field.name] = field.default || null;
        return acc;
      }, {});
      originalData.value = JSON.parse(JSON.stringify(itemData.value));
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
    const res = await nuxtApp.$api.get(`api/admin/${currentEntity.value}/${id}`);
    itemData.value = res.data;
    // Save a deep copy of the fetched data for later diffing
    originalData.value = JSON.parse(JSON.stringify(res.data));
    console.log("Данные загружены:", res.data);
  } catch (error) {
    console.error("Ошибка при загрузке:", error);
    errorMessage.value = parseError(error);
  } finally {
    isLoading.value = false;
  }
}

// Returns only fields that have been changed
function getChangedFields() {
  const changed = {};
  for (const key in itemData.value) {
    if (itemData.value[key] !== originalData.value[key]) {
      changed[key] = itemData.value[key];
    }
  }
  return changed;
}

async function saveItem() {
  errorMessage.value = "";
  fieldErrors.value = {};

  // Compute only the changed fields
  const changedFields = getChangedFields();

  // If there are no changes, do not proceed
  if (Object.keys(changedFields).length === 0) {
    isReadOnly.value = true;
    console.log("Нет изменений для сохранения.");
    return;
  }
  console.log("changedFields", changedFields);
  try {
    await nuxtApp.$api.patch(`api/admin/${currentEntity.value}/${currentId.value}`, changedFields);
    console.log("Изменения сохранены");
    // Update originalData to the new saved state
    originalData.value = JSON.parse(JSON.stringify(itemData.value));
    isReadOnly.value = true;
  } catch (error) {
    console.error("Ошибка при сохранении:", error);
    errorMessage.value = parseError(error);
  }
}

async function createItem() {
  errorMessage.value = "";
  fieldErrors.value = {};

  // Формируем объект, исключая поля с readOnly: true
  const dataToSend = {};
  console.log("fields", fields.value);
  fields.value.forEach((field) => {
    // Если мы создаём новую запись и поле помечено как readOnly – пропускаем его
    if (!(isNewItem.value && field.read_only)) {
      dataToSend[field.name] = itemData.value[field.name];
    }
  });
  console.log("Data to send:", dataToSend);

  try {
    const res = await nuxtApp.$api.post(`api/admin/${currentEntity.value}/`, dataToSend);
    console.log("Запись создана:", res.data);
    router.push(`/admin/${currentGroup.value}/${currentEntity.value}/${res.data.id}`);
  } catch (error) {
    console.error("Ошибка при создании:", error);
    errorMessage.value = parseError(error);
  }
}

async function deleteItem() {
  const confirmation = confirm("Вы действительно хотите удалить эту запись?");
  if (!confirmation) return;

  errorMessage.value = "";
  fieldErrors.value = {};
  try {
    await nuxtApp.$api.delete(`api/admin/${currentEntity.value}/${currentId.value}`);
    console.log("Запись удалена");
    goBack();
  } catch (error) {
    console.error("Ошибка при удалении:", error);
    errorMessage.value = parseError(error);
  }
}

// ------------------ Navigation ------------------
function goBack() {
  router.push(`/admin/${currentGroup.value}/${currentEntity.value}`);
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
    if (data.detail) {
      fieldErrors.value = data.detail;
    }
    return data.message || data.detail || error.message;
  }
  return error.message || "Неизвестная ошибка";
}
</script>
