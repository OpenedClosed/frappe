<template>
  <!-- Full screen container with no overflow -->
  <div class="flex flex-1 flex-col min-h-0 xl:max-h-[89.8vh] h-full overflow-hidden">
    <Toast />
    <!-- Main container -->
    <div class="flex flex-col flex-1 overflow-hidden">
      <!-- Main block: 3 columns -->
      <div class="flex flex-1 flex-row rounded-md overflow-hidden">
        <div class="flex flex-col xl:flex-row flex-1 gap-4 justify-between overflow-hidden">
          <!-- LEFT COLUMN -->
          <div
            class="flex-0 xl:flex-1 max-h-screen p-4 flex flex-col border-2 border-primary dark:border-secondary bg-gray-50 dark:bg-gray-800 rounded-md overflow-hidden"
          >
            <label for="promptTextArea" class="font-bold mb-2">{{ $t('knowledgeBase.label.promptTextarea') }}</label>
            <!-- FORM with generatePatch submit handler -->
            <form @submit.prevent="generatePatch" class="flex flex-col flex-grow min-h-0 overflow-y-auto gap-4">
              <!-- Info button -->
              <Button
                :label="$t('knowledgeBase.button.howToUse')"
                icon="pi pi-info-circle"
                class="p-button-sm p-button-info w-full"
                @click="showInstructions = true"
              />

              <!-- TEXTAREA -->
              <Textarea id="promptTextArea" rows="15" class="w-full min-h-[150px]" required v-model="promptText" />
              <!-- NEW FILE UPLOADER -->
              <FileUpload
                name="files"
                multiple
                :customUpload="true"
                :auto="false"
                :showUploadButton="false"
                :showCancelButton="false"
                @select="onSelect"
                @remove="onRemove"
                class="p-button-outlined"
              >
              </FileUpload>

              <!-- {{ selectedFiles }} -->

              <!-- GENERATE SMART CHANGE BUTTON -->
              <Button
                type="submit"
                :disabled="isLoading"
                :label="$t('knowledgeBase.button.generateSmartChange')"
                icon="pi pi-save"
                class="p-button-sm p-button-success w-full flex justify-center items-center"
              >
                <LoaderSmall v-if="isLoading" />
              </Button>

              <!-- Кнопка для открытия диалога -->
              <Button :label="$t('knowledgeBase.button.openTestChat')" class="p-button-sm p-button-info w-full" @click="showDialog = true" />
              <Dialog
                v-model:visible="showDialog"
                :modal="true"
                :header="$t('knowledgeBase.button.openTestChat')"
                :closable="true"
                :style="{ width: '80vw', height: '80vh' }"
                contentStyle="display: flex; flex-direction: column; height: 100%;"
              >
                <iframe :src="chatUrl" style="flex: 1; border: none"></iframe>
              </Dialog>
            </form>
          </div>

          <!-- CENTER COLUMN -->
          <div
            class="flex-0 xl:flex-1 max-h-screen p-4 flex flex-col border-2 border-primary dark:border-secondary bg-gray-50 dark:bg-gray-800 rounded-md overflow-hidden"
          >
            <div class="mb-2 pb-1 flex flex-col md:flex-row border-b border-gray-400 dark:border-gray-600 justify-between items-center">
              <h2 class="text-lg font-bold border-gray-400 dark:border-gray-600 pb-1">{{ $t('knowledgeBase.header.workspacePlayground') }}</h2>
              <!-- <p class="text-sm text-gray-500 dark:text-gray-300">Last update: {{ knowledgeBaseData.update_date }}</p> -->
              <div class="flex flex-col md:flex-row gap-2">
                <Button v-if="!isEditMode" icon="pi pi-pencil" class="p-button-sm  w-full md:w-[32px]" @click="toggleEditMode" />
                <Button
                  :disabled="isLoading"
                  :label="$t('knowledgeBase.button.clearPlayground')"
                  icon="pi pi-trash"
                  class="p-button-sm p-button-warning"
                  @click="clearPlayground"
                />

                <Button
                  v-if="isEditMode"
                  :label="$t('knowledgeBase.button.addTopic')"
                  icon="pi pi-plus"
                  class="p-button-sm p-button-success min-w-[140px]"
                  @click="addTopic"
                />
              </div>
            </div>
            <!-- Scrollable content for topics -->
            <div v-if="!isEditMode" class="flex-1 overflow-y-auto">
              <div v-for="(topicValue, topicName) in knowledgeBaseData.knowledge_base" :key="topicName"  class="mb-6">
                <h3 class="font-semibold text-gray-900 dark:text-gray-200">{{ topicName }}</h3>
                <div v-if="topicValue.subtopics">
                  <div v-for="(subtopicValue, subtopicName) in topicValue.subtopics" :key="subtopicName" class="ml-4 mb-4">
                    <h4 class="font-medium text-gray-800 dark:text-gray-300">{{ subtopicName }}</h4>
                    <ul v-if="subtopicValue.questions" class="ml-4 list-disc text-sm text-gray-700 dark:text-gray-400">
                      <!-- qObj is { text: '', files: [] } -->
                      <li v-for="(qObj, questionKey) in subtopicValue.questions" :key="questionKey" class="mb-4">
                        <!-- Question & text -->
                        <div>
                          <span class="font-semibold">{{ questionKey }}:</span>
                          <span> {{ qObj.text }}</span>
                        </div>

                        <!-- Files (links) -->
                        <div v-if="qObj.files && qObj.files.length" class="mt-2 ml-2">
                          <div v-for="(fileLink, fileIndex) in qObj.files" :key="fileIndex" class="mb-1">
                            <!-- If is image, display <img/>; otherwise display link -->
                            <ImageLink :fileLink="fileLink" />
                          </div>
                        </div>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="flex-1 overflow-y-auto">
              <div v-for="(topicValue, topicName) in knowledgeBaseData.knowledge_base" :key="topicName" :id="`topic-${topicName}`" class="mb-6">
                <!-- Topic header with input and buttons -->
                <div class="flex items-center mb-2 border-b border-gray-400 dark:border-gray-600 pb-1">
                  <input
                    class="border p-1 flex-1 mr-2 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 rounded"
                    :value="topicName"
                    @blur="renameTopic(topicName, $event.target.value)"
                    @keydown.enter.prevent="renameTopic(topicName, $event.target.value)"
                  />
                  <Button icon="pi pi-minus" class="p-button-danger p-button-sm mr-2" @click="removeTopic(topicName)" />
                  <Button :label="$t('knowledgeBase.button.addSubtopic')" icon="pi pi-plus" class="p-button-success p-button-sm" @click="addSubtopic(topicName)" />
                </div>
                <!-- Subtopics and questions (similar adjustments can be applied here) -->
                <div
                  v-if="topicValue.subtopics"
                  v-for="(subtopicValue, subtopicName) in topicValue.subtopics"
                  :key="subtopicName"
                  :id="`subtopic-${topicName}-${subtopicName}`"
                  class="ml-4 mb-4"
                >
                  <div class="flex items-center mb-2">
                    <input
                      class="border p-1 flex-1 mr-2 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 rounded"
                      :value="subtopicName"
                      @blur="renameSubtopic(topicName, subtopicName, $event.target.value)"
                      @keydown.enter.prevent="renameSubtopic(topicName, subtopicName, $event.target.value)"
                    />
                    <Button icon="pi pi-minus" class="p-button-danger p-button-sm mr-2" @click="removeSubtopic(topicName, subtopicName)" />
                    <Button
                      :label="$t('knowledgeBase.button.addQuestion')"
                      icon="pi pi-plus"
                      class="p-button-success p-button-sm"
                      @click="addQuestion(topicName, subtopicName)"
                    />
                  </div>
                  <div v-if="subtopicValue.questions" class="ml-4">
                    <div
                      v-for="(questionObj, questionKey) in subtopicValue.questions"
                      :key="questionKey"
                      :id="`question-${topicName}-${subtopicName}-${questionKey}`"
                      class="mb-4 p-2 border rounded-md dark:border-gray-600"
                    >
                      <!-- Row with label + remove button -->
                      <div class="flex items-center justify-between mb-2">
                        <label class="font-semibold">{{ $t('knowledgeBase.label.question') }}:</label>
                        <Button
                          icon="pi pi-trash"
                          class="p-button-rounded p-button-text p-button-danger"
                          @click="removeQuestion(topicName, subtopicName, questionKey)"
                        />
                      </div>

                      <!-- QUESTION (the key) -->
                      <Textarea
                        :value="questionKey"
                        class="block w-full mb-2 min-h-[50px] border rounded p-2 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700"
                        @blur="renameQuestion(topicName, subtopicName, questionKey, $event.target.value)"
                      />

                      <!-- ANSWER TEXT -->
                      <label class="font-semibold">{{ $t('knowledgeBase.label.answerText') }}:</label>
                      <Textarea
                        v-model="questionObj.text"
                        class="block w-full border rounded p-2 min-h-[100px] text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 mb-2"
                      />

                      <!-- LINKS / FILES -->
                      <label class="font-semibold">{{ $t('knowledgeBase.label.linksFiles') }}:</label>
                      <ul class="mb-2">
                        <li v-for="(fileLink, fileIndex) in questionObj.files" :key="fileIndex" class="flex items-center gap-2 mb-1">
                          <!-- Each file link is just a string you can edit -->
                          <input
                            v-model="questionObj.files[fileIndex]"
                            type="text"
                            class="border p-1 flex-1 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 rounded"
                          />
                          <Button
                            icon="pi pi-minus"
                            class="p-button-danger p-button-sm"
                            @click="removeQuestionFile(topicName, subtopicName, questionKey, fileIndex)"
                          />
                        </li>
                      </ul>
                      <div v-if="localFiles.length" class="mt-4">
                        <h3>{{ $t('knowledgeBase.label.selectedFiles') }}:</h3>
                        <ul>
                          <li v-for="(file, idx) in localFiles" :key="idx">{{ file.name }} - {{ file.size }} bytes</li>
                        </ul>
                      </div>

                      <Button
                        :label="$t('knowledgeBase.button.addLink')"
                        icon="pi pi-plus"
                        class="p-button-success p-button-sm"
                        @click="addQuestionFile(topicName, subtopicName, questionKey)"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="isEditMode" class="flex flex-col gap-2 mt-2">
              <Button
                :disabled="isLoading"
                :label="$t('knowledgeBase.button.savePlayground')"
                icon="pi pi-save"
                class="p-button-sm p-button-success"
                @click="savePlayground"
              />
              <Button
                :disabled="isLoading"
                :label="$t('knowledgeBase.button.rejectPlayground')"
                icon="pi pi-times"
                class="p-button-sm p-button-danger"
                @click="rejectPlayground"
              />
            </div>
            <div v-else class="flex flex-col gap-2 mt-2">
              <Button
                :disabled="isLoading"
                :label="$t('knowledgeBase.button.transferToDatabase')"
                icon="pi pi-save"
                class="p-button-sm p-button-success"
                @click="saveChanges"
              />
              <Button
                :disabled="isLoading"
                :label="$t('knowledgeBase.button.rejectPlayground')"
                icon="pi pi-times"
                class="p-button-sm p-button-danger"
                @click="rejectPlayground"
              />
            </div>
          </div>

          <!-- RIGHT COLUMN (Readonly Copy) -->
          <div
            class="flex-0 xl:flex-1 max-h-screen p-4 flex flex-col border-2 border-primary dark:border-secondary bg-gray-50 dark:bg-gray-800 rounded-md overflow-hidden"
          >
            <h2 class="text-lg font-bold mb-2 border-b border-gray-400 dark:border-gray-600 pb-1">{{ $t('knowledgeBase.header.readonlyKnowledgeBase') }}</h2>
            <div class="flex-1 overflow-y-auto">
              <div v-for="(topicValue, topicName) in readonlyData.knowledge_base" :key="topicName" class="mb-6">
                <h3 class="font-semibold text-gray-900 dark:text-gray-200">{{ topicName }}</h3>
                <div v-if="topicValue.subtopics">
                  <div v-for="(subtopicValue, subtopicName) in topicValue.subtopics" :key="subtopicName" class="ml-4 mb-4">
                    <h4 class="font-medium text-gray-800 dark:text-gray-300">{{ subtopicName }}</h4>
                    <ul v-if="subtopicValue.questions" class="ml-4 list-disc text-sm text-gray-700 dark:text-gray-400">
                      <!-- qObj is { text: '', files: [] } -->
                      <li v-for="(qObj, questionKey) in subtopicValue.questions" :key="questionKey" class="mb-4">
                        <!-- Question & text -->
                        <div>
                          <span class="font-semibold">{{ questionKey }}:</span>
                          <span> {{ qObj.text }}</span>
                        </div>

                        <!-- Files (links) -->
                        <div v-if="qObj.files && qObj.files.length" class="mt-2 ml-2">
                          <div v-for="(fileLink, fileIndex) in qObj.files" :key="fileIndex" class="mb-1">
                            <!-- If is image, display <img/>; otherwise display link -->
                            <ImageLink :fileLink="fileLink" />
                          </div>
                        </div>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
            <div class="flex flex-col xl:flex-row gap-2">
              <!-- Export Button -->
              <Button :label="$t('knowledgeBase.button.exportJson')" icon="pi pi-download" class="p-button-sm p-button-info" @click="exportData" />

              <!-- Import Button -->
              <Button :label="$t('knowledgeBase.button.importJson')" icon="pi pi-upload" class="p-button-sm p-button-primary" @click="triggerFileInput" />

              <!-- Hidden File Input -->
              <input type="file" class="hidden" ref="fileInput" @change="importData" accept=".json" />
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- INSTRUCTIONS DIALOG -->
    <!-- INSTRUCTIONS DIALOG -->
    <Dialog
      v-model:visible="showInstructions"
      :header="$t('knowledgeBase.button.howToUse')"
      :modal="true"
      :closable="true"
      class="w-full xl:w-[50vw] m-4"
    >
      <div class="wysiwyg">
        <p>Добро пожаловать в руководство по использованию инструмента для работы с базой знаний. Вот несколько рекомендаций:</p>
        <ul>
          <li>
            <strong>Четко формулируйте запросы:</strong> Используйте ясные и конкретные формулировки, чтобы ИИ мог лучше понять ваши
            намерения.
          </li>
          <li>
            <strong>Используйте ключевые слова:</strong> Включайте ключевые слова, которые наиболее точно описывают тему или вопрос, чтобы
            улучшить результаты поиска и генерации.
          </li>
          <li>
            <strong>Проверяйте результаты:</strong> Всегда проверяйте и редактируйте сгенерированные ИИ данные, чтобы убедиться в их
            точности и релевантности.
          </li>
          <li>
            <strong>Обучение на примерах:</strong> Если возможно, предоставляйте примеры или контекст, чтобы ИИ мог лучше адаптироваться к
            вашим требованиям.
          </li>
          <li>
            <strong>Обратная связь:</strong> Делитесь обратной связью о результатах работы ИИ, чтобы улучшить его производительность в
            будущем.
          </li>
        </ul>
        <p>Следуя этим рекомендациям, вы сможете максимально эффективно использовать возможности ИИ для работы с вашей базой знаний.</p>
        <h3 class="text-center">Шаблоны запросов</h3>
        <ul>
          <li>Заполни эти данные на русском вместе с ключами и разбей всё на МНОГО вопросов тем и подтем</li>
        </ul>
        <h3 class="text-center">Инструкция</h3>
        <h1>Инструкция по работе с базой данных</h1>

        <h2>Общие сведения</h2>
        <p>Интерфейс разделен на три части:</p>
        <ul>
          <li><strong>Ввод промпта</strong> – поле для загрузки текстовых данных.</li>
          <li><strong>Промежуточная версия базы данных (Playground)</strong> – область редактирования данных.</li>
          <li><strong>Актуальная база данных</strong> – реальное хранилище данных.</li>
        </ul>

        <h2>Редактирование данных</h2>
        <p>Доступны два режима редактирования:</p>
        <ul>
          <li><strong>Ручной режим</strong> – можно добавлять темы, подтемы, вопросы и ответы.</li>
          <li><strong>Автоматический режим</strong> – ввод промпта, который заполняет структуру базы данных.</li>
        </ul>

        <h2>Применение изменений</h2>
        <p>
          После редактирования в <strong>Playground</strong> изменения можно перенести в реальную базу данных, нажав
          <strong>"Transfer to Database"</strong>.
        </p>

        <h2>Отмена изменений</h2>
        <p>Чтобы отменить внесенные изменения и вернуть Playground к исходному состоянию, нажмите <strong>"Отменить изменения"</strong>.</p>

        <h2>Работа с JSON</h2>
        <p>Доступны следующие возможности:</p>
        <ul>
          <li><strong>Скачать JSON</strong> – сохранить текущую версию базы данных.</li>
          <li><strong>Загрузить JSON</strong> – восстановить базу данных из ранее сохраненного файла.</li>
        </ul>

        <h2>Дополнительные возможности</h2>
        <p>Дизайн и функциональность интерфейса могут быть доработаны. Возможны будущие улучшения для удобства пользователей.</p>

        <div class="highlight">
          <p>
            <strong>Важно:</strong> любые изменения в Playground не затрагивают реальную базу данных, пока не будет нажата кнопка "Transfer
            to Database".
          </p>
        </div>
        <h3 class="text-center">ВАЖНО!</h3>
        <ul>
          <li>Каждый запрос независим и не учитывает предыдущие запросы.</li>
          <li>Не используйте СЛИШКОМ большие запросы.</li>
        </ul>
      </div>
    </Dialog>
  </div>
</template>

<script setup>
import { ref } from "vue";
// import Textarea from 'primevue/textarea';
// import Button from 'primevue/button';
import cloneDeep from "lodash/cloneDeep";
import ImageLink from "./ImageLink.vue";
import { useI18n } from "vue-i18n"; // Добавляем i18n

const { t } = useI18n(); // Получаем функцию перевода
const toast = useToast();
const readonlyData = ref({});
const promptText = ref("");
const selectedFiles = ref([]);
const isEditMode = ref(false);
const showInstructions = ref(false);
const isLoading = ref(false);
// Local array to store *all* selected files
const localFiles = ref([]);

function showSuccess(message) {
  toast.add({ severity: "success", summary: "Success", detail: message, life: 3000 });
}

// Error notification
function showError(message) {
  toast.add({ severity: "error", summary: "Error", detail: message, life: 3000 });
}


// This runs whenever user selects new files.
function onSelect(event) {
  // event.files => Array of newly selected File objects.
  selectedFiles.value.push(...event.files);
}

// This runs whenever user clicks the “remove” icon next to a file.
function onRemove(event) {
  // event.file => the single file that was removed.
  selectedFiles.value = selectedFiles.value.filter((f) => f !== event.file);
}

function toggleEditMode() {
  isEditMode.value = !isEditMode.value;
}

const showDialog = ref(false);
const isLocalhost = window.location.hostname === "localhost";
const chatUrl = isLocalhost ? "http://localhost:4000/chats/telegram-chat" : `${window.location.protocol}//${window.location.hostname}/chats/telegram-chat`;

async function isImage(url) {
  try {
    const response = await fetch(url, { method: "HEAD" });

    if (!response.ok) return false;

    const contentType = response.headers.get("content-type");
    return contentType && contentType.startsWith("image/");
  } catch (error) {
    console.error("Error checking image URL:", error);
    return false;
  }
}

const knowledgeBaseData = ref({
  knowledge_base: {
    // "Booking & Availability 🏷": {
    //   subtopics: {
    //     "General Info 🌐": {
    //       questions: {
    //         "What are the prices and is there availability?": "Hello! ...",
    //         "How do I make a booking?": "Hello! ...",
    //       },
    //     },
    //   },
    // },
  },
  update_date: "",
  brief_questions: {},
});

const baseData = await useAsyncData("baseData", getBaseData);

if (baseData.data) {
  if (baseData.data.value) {
    setData(baseData.data.value);
  }
}
function setData(data) {
  if (data) {
    console.log("baseData data= ", data);
    knowledgeBaseData.value.knowledge_base = data.knowledge_base;
    readonlyData.value = cloneDeep(knowledgeBaseData.value);
  }
}

async function getBaseData() {
  let responseData;
  await useNuxtApp()
    .$api.get(`/api/knowledge/knowledge_base`)
    .then((response) => {
      responseData = response.data;
      console.log("Profile responseData= ", responseData);
    })
    .catch((err) => {
      if (err.response) {
        console.log(err.response.data);
      }
    });
  return responseData;
}

function renameQuestion(topicName, subtopicName, oldQuestion, newQuestion) {
  if (!newQuestion || newQuestion === oldQuestion) return;

  const topic = knowledgeBaseData.value.knowledge_base[topicName];
  if (!topic || !topic.subtopics) return;

  const subtopic = topic.subtopics[subtopicName];
  if (!subtopic || !subtopic.questions) return;

  // Check if the new question key already exists
  if (subtopic.questions[newQuestion]) {
    alert("This question already exists!");
    return;
  }

  // Move entire object { text, files } to the new key
  subtopic.questions[newQuestion] = subtopic.questions[oldQuestion];
  delete subtopic.questions[oldQuestion];
}

/**
 * Преобразуем { q1: a1, q2: a2 } в массив [{ tempQuestion:'q1', tempAnswer:'a1' }, ...]
 */
function transformToArray(questionsObj) {
  return Object.entries(questionsObj).map(([key, value]) => ({
    tempQuestion: key,
    tempAnswer: value,
  }));
}

// Export JSON data as a file
function exportData() {
  const jsonData = JSON.stringify(knowledgeBaseData.value.knowledge_base, null, 2);
  const blob = new Blob([jsonData], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "knowledge_base.json";
  a.click();

  URL.revokeObjectURL(url);
}

const fileInput = ref(null);

function triggerFileInput() {
  fileInput.value.click();
}

// Import JSON data from a file
function importData(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const importedData = JSON.parse(e.target.result);
      if (typeof importedData === "object" && importedData !== null) {
        knowledgeBaseData.value.knowledge_base = importedData;
        knowledgeBaseData.value.update_date = new Date().toISOString();
      } else {
        alert("Invalid JSON structure");
      }
    } catch (error) {
      alert("Error parsing JSON file");
    }
  };
  reader.readAsText(file);
}

/** ======================== Методы для добавления/удаления ======================== **/
const lastAddedElement = ref(null);

// Добавить новую тему (без prompt)
function addTopic() {
  let baseName = "New Topic";
  let index = 1;
  let newName = baseName;

  while (knowledgeBaseData.value.knowledge_base[newName]) {
    index++;
    newName = `${baseName} ${index}`;
  }

  knowledgeBaseData.value.knowledge_base[newName] = {
    subtopics: {},
  };

  // Set reference to newly added topic
  nextTick(() => {
    lastAddedElement.value = document.getElementById(`topic-${newName}`);
    if (lastAddedElement.value) {
      lastAddedElement.value.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });
  showSuccess("Topic added successfully");
}


// Удалить тему
function removeTopic(topicName) {
  if (confirm(t("knowledgeBase.removeTopic", { topicName }))) { 
    delete knowledgeBaseData.value.knowledge_base[topicName];
    showSuccess("Topic removed successfully");
  }
  else {
    showError("Topic not removed");
  }
}

function addSubtopic(topicName) {
  const topic = knowledgeBaseData.value.knowledge_base[topicName];
  if (!topic) return;

  let baseName = "New Subtopic";
  let index = 1;
  let newName = baseName;

  while (topic.subtopics[newName]) {
    index++;
    newName = `${baseName} ${index}`;
  }

  topic.subtopics[newName] = {
    questions: {},
  };

  nextTick(() => {
    lastAddedElement.value = document.getElementById(`subtopic-${topicName}-${newName}`);
    if (lastAddedElement.value) {
      lastAddedElement.value.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });
  showSuccess("Subtopic added successfully");
}


// Удалить подтему
function removeSubtopic(topicName, subtopicName) {
  if (confirm(t("knowledgeBase.removeSubtopic", { subtopicName, topicName }))) {
    const topic = knowledgeBaseData.value.knowledge_base[topicName];
    if (topic && topic.subtopics[subtopicName]) {
      delete topic.subtopics[subtopicName];
      showSuccess("Subtopic removed successfully");
    }
    else {
      showError("Subtopic not removed");
    }
  }
}

function addQuestion(topicName, subtopicName) {
  const topic = knowledgeBaseData.value.knowledge_base[topicName];
  if (!topic) return;
  const subtopic = topic.subtopics[subtopicName];
  if (!subtopic) return;

  if (!subtopic.questions) {
    subtopic.questions = {};
  }
  
  let baseName = "New Question";
  let index = 1;
  let newName = baseName;

  while (subtopic.questions.hasOwnProperty(newName)) {
    index++;
    newName = `${baseName} ${index}`;
  }

  subtopic.questions[newName] = {
    text: "",
    files: [],
  };

  nextTick(() => {
    lastAddedElement.value = document.getElementById(`question-${topicName}-${subtopicName}-${newName}`);
    if (lastAddedElement.value) {
      lastAddedElement.value.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });
  showSuccess("Question added successfully");
}

function addQuestionFile(topicName, subtopicName, question) {
  const questionObj = knowledgeBaseData.value.knowledge_base[topicName].subtopics[subtopicName].questions[question];
  if (!questionObj.files) {
    questionObj.files = [];
  }
  // For a new empty link, push an empty string "" or some default text
  questionObj.files.push("");
  showSuccess("File added successfully");
}

function removeQuestionFile(topicName, subtopicName, question, fileIndex) {
  const questionObj = knowledgeBaseData.value.knowledge_base[topicName].subtopics[subtopicName].questions[question];
  if (questionObj?.files) {
    questionObj.files.splice(fileIndex, 1);
  }
  showSuccess("File removed successfully");
}

// Method to update the `questions` object reactively
function updateQuestion(topicName, subtopicName, index, newValue, field) {
  const topic = knowledgeBaseData.value.knowledge_base[topicName];
  if (!topic) return;
  const subtopic = topic.subtopics[subtopicName];
  if (!subtopic || !subtopic.questions) return;

  // Convert object to array, update value, and convert back to object
  const questionKeys = Object.keys(subtopic.questions);
  const questionKey = questionKeys[index];

  if (field === "question") {
    // Update question key
    const newQuestions = { ...subtopic.questions };
    newQuestions[newValue] = newQuestions[questionKey]; // Copy old value to new key
    delete newQuestions[questionKey]; // Delete old key
    subtopic.questions = newQuestions;
  } else if (field === "answer") {
    // Update answer text
    subtopic.questions[questionKey] = newValue;
  }
  showSuccess("Question updated successfully");
}

// Удалить вопрос
function removeQuestion(topicName, subtopicName, questionKey) {
  if (confirm(t("knowledgeBase.removeQuestion", { questionKey }))) {
    const topic = knowledgeBaseData.value.knowledge_base[topicName];
    if (!topic) return;
    const subtopic = topic.subtopics[subtopicName];
    if (!subtopic) return;

    delete subtopic.questions[questionKey];
    showSuccess("Question removed successfully");
  }
  else {
    showError("Question not removed");
  }
}

function getChanges() {
  const oldData = readonlyData.value.knowledge_base;
  const newData = knowledgeBaseData.value.knowledge_base;
  const patchData = {};

  if (!oldData) {
    return newData;
  }

  for (const topic in newData) {
    if (!oldData[topic]) {
      // Новая тема полностью
      patchData[topic] = { ...newData[topic] };
    } else {
      // Проверяем изменения в подтемах
      const topicDiff = {};

      for (const subtopic in newData[topic].subtopics) {
        if (!oldData[topic].subtopics || !oldData[topic].subtopics[subtopic]) {
          // Новая подтема
          topicDiff[subtopic] = { ...newData[topic].subtopics[subtopic] };
        } else {
          // Проверяем вопросы в подтеме
          const subtopicDiff = {};
          const oldQuestions = oldData[topic].subtopics[subtopic].questions || {};
          const newQuestions = newData[topic].subtopics[subtopic].questions || {};

          for (const question in newQuestions) {
            if (!oldQuestions.hasOwnProperty(question)) {
              // Новый вопрос
              subtopicDiff[question] = newQuestions[question];
            } else if (oldQuestions[question] !== newQuestions[question]) {
              // Измененный вопрос
              subtopicDiff[question] = newQuestions[question];
            }
          }

          // Удаленные вопросы
          for (const question in oldQuestions) {
            if (!newQuestions.hasOwnProperty(question)) {
              subtopicDiff[question] = { _delete: true }; // Указываем, что вопрос удален
            }
          }

          if (Object.keys(subtopicDiff).length > 0) {
            topicDiff[subtopic] = { questions: subtopicDiff };
          }
        }
      }

      // Удаленные подтемы
      for (const subtopic in oldData[topic].subtopics) {
        if (!newData[topic].subtopics.hasOwnProperty(subtopic)) {
          topicDiff[subtopic] = { _delete: true }; // Указываем, что подтема удалена
        }
      }

      if (Object.keys(topicDiff).length > 0) {
        patchData[topic] = { subtopics: topicDiff };
      }
    }
  }

  // Удаленные темы
  for (const topic in oldData) {
    if (!newData.hasOwnProperty(topic)) {
      patchData[topic] = { _delete: true }; // Указываем, что тема удалена
    }
  }

  return Object.keys(patchData).length > 0 ? patchData : null;
}

// Метод для обновления базы знаний
async function updatePlayground(data) {
  const changes = getChanges();
  console.log("knowledgeBaseData.value.knowledge_base=", knowledgeBaseData.value.knowledge_base);
  console.log("changes=", changes);
  if (!changes && !data) {
    console.log("Нет изменений для отправки.");
    isEditMode.value = false;
    return;
  }

  try {
    console.log("Отправка изменений:", changes);

    let patchData = {
      patch_data: {
        knowledge_base: data ? data : changes,
      },
      base_data: knowledgeBaseData.value.knowledge_base,
    };
    console.log("patchData", patchData);
    console.log(" data ? data : changes,", data ? "data" : "changes");
    const response = await useNuxtApp().$api.patch("/api/knowledge/knowledge_base", patchData);

    knowledgeBaseData.value.knowledge_base = response.data.knowledge.knowledge_base;

    console.log("Успешное обновление базы знаний:", response.data);
    isEditMode.value = false;
    showSuccess("Knowledge base updated successfully");
  } catch (error) {
    console.error("Ошибка при обновлении базы знаний:", error);
    showError("Knowledge base not updated");
  }
}
// Метод для обновления базы знаний
async function saveDatabase() {
  try {
    console.log("Отправка изменений:", knowledgeBaseData.value.knowledge_base);
    const response = await useNuxtApp().$api.put("/api/knowledge/knowledge_base/apply", {
      knowledge_base: knowledgeBaseData.value.knowledge_base,
    });
    const data = await getBaseData();
    if (data) {
      console.log("baseData data= ", data);
      knowledgeBaseData.value.knowledge_base = data.knowledge_base;
      readonlyData.value = cloneDeep(knowledgeBaseData.value);
      setTimeout(() => {
        isDirty.value = false; // Mark as saved
      }, 300);
      showSuccess("Knowledge base saved successfully");
    }
  } catch (error) {
    console.error("Ошибка при обновлении базы знаний:", error);
    showError("Knowledge base not saved");
  }
}

function clearPlayground() {
  if (confirm(t("knowledgeBase.clearPlayground"))) {
    knowledgeBaseData.value.knowledge_base = {};
    showSuccess("Playground cleared successfully");
  }
}

function savePlayground() {
  updatePlayground();
}
function rejectPlayground() {
  isEditMode.value = false;
  // clear data to readonlyData
  let temp = readonlyData.value.knowledge_base;
  knowledgeBaseData.value.knowledge_base = temp;
  showSuccess("Playground rejected successfully");
}
let isDirty = ref(false);

watch(
  knowledgeBaseData,
  () => {
    isDirty.value = true;
  },
  { deep: true }
);

function beforeUnloadHandler(event) {
  if (isDirty.value) {
    event.preventDefault();
    event.returnValue = t("knowledgeBase.unsavedChanges");
  }
}

onMounted(() => {
  window.addEventListener("beforeunload", beforeUnloadHandler);
});

onUnmounted(() => {
  window.removeEventListener("beforeunload", beforeUnloadHandler);
});

// Reset `isDirty` after saving
function saveChanges() {
  saveDatabase();
}
async function generatePatch() {
  // 1. Prepare FormData
  const formData = new FormData();

  // 2. Append any other fields if needed:
  formData.append("user_message", promptText.value);
  formData.append("base_data_json", JSON.stringify(knowledgeBaseData.value.knowledge_base));
  console.log("selectedFiles.value=", selectedFiles.value);
  // 3. Append files
  selectedFiles.value.forEach((file) => {
    formData.append("files", file, file.name);
  });

  // 4. Send via API
  try {
    isLoading.value = true;
    const response = await useNuxtApp().$api.post("/api/knowledge/generate_patch", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    // handle success
    updatePlayground(response.data);
    showSuccess("Patch generated successfully");
  } catch (error) {
    // handle error
    showError("Patch not generated");
  } finally {
    isLoading.value = false;
  }
}

/** ======================== Методы для ПЕРЕИМЕНОВАНИЯ ======================== **/
 
// Переименовать тему
function renameTopic(oldName, newName) {
  if (!newName || newName === oldName) return;
  knowledgeBaseData.value.knowledge_base[newName] = knowledgeBaseData.value.knowledge_base[oldName];
  delete knowledgeBaseData.value.knowledge_base[oldName];
}

// Переименовать подтему
function renameSubtopic(topicName, oldSubtopicName, newSubtopicName) {
  if (!newSubtopicName || newSubtopicName === oldSubtopicName) return;
  const topic = knowledgeBaseData.value.knowledge_base[topicName];
  if (!topic || !topic.subtopics) return;

  topic.subtopics[newSubtopicName] = topic.subtopics[oldSubtopicName];
  delete topic.subtopics[oldSubtopicName];
}
</script>

<style scoped>
/* Tailwind (или ваши кастомные стили) */
</style>
