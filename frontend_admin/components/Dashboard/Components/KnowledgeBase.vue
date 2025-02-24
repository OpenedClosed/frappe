<template>
  <!-- Full screen container with no overflow -->
  <div class="flex flex-1 flex-col min-h-0 max-h-[89.8vh] h-full overflow-hidden">
    <!-- Main container -->
    <div class="flex flex-col flex-1 overflow-hidden">
      <!-- Main block: 3 columns -->
      <div class="flex flex-1 flex-row rounded-md overflow-hidden">
        <div class="flex flex-1 gap-4 justify-between overflow-hidden">
          <!-- LEFT COLUMN -->
          <div
            class="flex-1 p-4 flex flex-col border-2 border-primary dark:border-secondary bg-gray-50 dark:bg-gray-800 rounded-md overflow-hidden"
          >
            <label for="promptTextArea" class="font-bold mb-2">Textarea for prompt</label>
            <!-- Ensure the textarea container can shrink and scroll if needed -->
            <form @submit.prevent="generatePatch" class="flex flex-col flex-grow min-h-0 overflow-y-auto gap-4">
              <Button
                label="How to use this instrument?"
                icon="pi pi-info-circle"
                class="p-button-sm p-button-info w-full"
                @click="showInstructions = true"
              />
              <Textarea id="promptTextArea" rows="15" class="w-full min-h-[150px]" required v-model="promptText" />
              <Button
                type="submit"
                :disabled="isLoading"
                label="Generate smart change"
                icon="pi pi-save"
                class="p-button-sm p-button-success w-full flex justify-center items-center"
                ><LoaderSmall v-if="isLoading"
              /></Button>
            </form>
          </div>

          <!-- CENTER COLUMN -->
          <div
            class="flex-1 p-4 flex flex-col border-2 border-primary dark:border-secondary bg-gray-50 dark:bg-gray-800 rounded-md overflow-hidden"
          >
            <div class="mb-2 pb-1 flex flex-row border-b border-gray-400 dark:border-gray-600 justify-between items-center">
              <h2 class="text-lg font-bold border-gray-400 dark:border-gray-600 pb-1">Workspace playground</h2>
              <!-- <p class="text-sm text-gray-500 dark:text-gray-300">Last update: {{ knowledgeBaseData.update_date }}</p> -->
              <div class="flex flex-row gap-2">
                <Button v-if="!isEditMode" icon="pi pi-pencil" class="p-button-sm" @click="toggleEditMode" />
                <Button
                  :disabled="isLoading"
                  label="Clear Playground"
                  icon="pi pi-trash"
                  class="p-button-sm p-button-warning"
                  @click="clearPlayground"
                />

                <Button
                  v-if="isEditMode"
                  label="Add Topic"
                  icon="pi pi-plus"
                  class="p-button-sm p-button-success min-w-[140px]"
                  @click="addTopic"
                />
              </div>
            </div>
            <!-- Scrollable content for topics -->
            <div v-if="!isEditMode" class="flex-1 overflow-y-auto">
              <div v-for="(topicValue, topicName) in knowledgeBaseData.knowledge_base" :key="topicName" class="mb-6">
                <h3 class="font-semibold text-gray-900 dark:text-gray-200">{{ topicName }}</h3>
                <div v-if="topicValue.subtopics">
                  <div v-for="(subtopicValue, subtopicName) in topicValue.subtopics" :key="subtopicName" class="ml-4 mb-4">
                    <h4 class="font-medium text-gray-800 dark:text-gray-300">{{ subtopicName }}</h4>
                    <ul v-if="subtopicValue.questions" class="ml-4 list-disc text-sm text-gray-700 dark:text-gray-400">
                      <li v-for="(answer, question) in subtopicValue.questions" :key="question">
                        <span class="font-semibold">{{ question }}:</span> {{ answer }}
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="flex-1 overflow-y-auto">
              <div v-for="(topicValue, topicName) in knowledgeBaseData.knowledge_base" :key="topicName" class="mb-6">
                <!-- Topic header with input and buttons -->
                <div class="flex items-center mb-2 border-b border-gray-400 dark:border-gray-600 pb-1">
                  <input
                    class="border p-1 flex-1 mr-2 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 rounded"
                    :value="topicName"
                    @blur="renameTopic(topicName, $event.target.value)"
                    @keydown.enter.prevent="renameTopic(topicName, $event.target.value)"
                  />
                  <Button icon="pi pi-minus" class="p-button-danger p-button-sm mr-2" @click="removeTopic(topicName)" />
                  <Button label="Add Subtopic" icon="pi pi-plus" class="p-button-success p-button-sm" @click="addSubtopic(topicName)" />
                </div>
                <!-- Subtopics and questions (similar adjustments can be applied here) -->
                <div
                  v-if="topicValue.subtopics"
                  v-for="(subtopicValue, subtopicName) in topicValue.subtopics"
                  :key="subtopicName"
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
                      label="Add Question"
                      icon="pi pi-plus"
                      class="p-button-success p-button-sm"
                      @click="addQuestion(topicName, subtopicName)"
                    />
                  </div>
                  <div v-if="subtopicValue.questions" class="ml-4">
                    <div
                      v-for="(answer, question) in subtopicValue.questions"
                      :key="question"
                      class="mb-4 p-2 border rounded-md dark:border-gray-600"
                    >
                      <div class="flex items-center justify-between mb-2">
                        <label class="font-semibold">Question:</label>
                        <Button
                          icon="pi pi-trash"
                          class="p-button-rounded p-button-text p-button-danger"
                          @click="removeQuestion(topicName, subtopicName, question)"
                        />
                      </div>

                      <!-- Updating the question (key) -->
                      <Textarea
                        :value="question"
                        class="block w-full mb-2 min-h-[50px] border rounded p-2 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700"
                        @blur="renameQuestion(topicName, subtopicName, question, $event.target.value)"
                      />

                      <label class="font-semibold">Answer:</label>

                      <!-- Updating the answer (value) -->
                      <Textarea
                        v-model="subtopicValue.questions[question]"
                        class="block w-full border rounded p-2 min-h-[100px] text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="isEditMode" class="flex flex-col gap-2 mt-2">
              <Button
                :disabled="isLoading"
                label="Save Playground"
                icon="pi pi-save"
                class="p-button-sm p-button-success"
                @click="savePlayground"
              />
              <Button
                :disabled="isLoading"
                label="Reject Playground"
                icon="pi pi-times"
                class="p-button-sm p-button-danger"
                @click="rejectPlayground"
              />
            </div>
            <div v-else class="flex flex-col gap-2 mt-2">
              <Button
                :disabled="isLoading"
                label="Transfer to database"
                icon="pi pi-save"
                class="p-button-sm p-button-success"
                @click="saveChanges"
              />
              <Button
                :disabled="isLoading"
                label="Reject Playground"
                icon="pi pi-times"
                class="p-button-sm p-button-danger"
                @click="rejectPlayground"
              />
            </div>
          </div>

          <!-- RIGHT COLUMN (Readonly Copy) -->
          <div
            class="flex-1 p-4 flex flex-col border-2 border-primary dark:border-secondary bg-gray-50 dark:bg-gray-800 rounded-md overflow-hidden"
          >
            <h2 class="text-lg font-bold mb-2 border-b border-gray-400 dark:border-gray-600 pb-1">Readonly Knowledge Base</h2>
            <div class="flex-1 overflow-y-auto">
              <div v-for="(topicValue, topicName) in readonlyData.knowledge_base" :key="topicName" class="mb-6">
                <h3 class="font-semibold text-gray-900 dark:text-gray-200">{{ topicName }}</h3>
                <div v-if="topicValue.subtopics">
                  <div v-for="(subtopicValue, subtopicName) in topicValue.subtopics" :key="subtopicName" class="ml-4 mb-4">
                    <h4 class="font-medium text-gray-800 dark:text-gray-300">{{ subtopicName }}</h4>
                    <ul v-if="subtopicValue.questions" class="ml-4 list-disc text-sm text-gray-700 dark:text-gray-400">
                      <li v-for="(answer, question) in subtopicValue.questions" :key="question">
                        <span class="font-semibold">{{ question }}:</span> {{ answer }}
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
            <div class="flex gap-2">
              <!-- Export Button -->
              <Button label="Export JSON" icon="pi pi-download" class="p-button-sm p-button-info" @click="exportData" />

              <!-- Import Button -->
              <Button label="Import JSON" icon="pi pi-upload" class="p-button-sm p-button-primary" @click="triggerFileInput" />

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
      header="Как использовать инструмент"
      :modal="true"
      :closable="true"
      :style="{ width: '50vw' }"
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

const readonlyData = ref({});
const promptText = ref("");

const isEditMode = ref(false);
const showInstructions = ref(false);
const isLoading = ref(false);

function toggleEditMode() {
  isEditMode.value = !isEditMode.value;
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

  // Check if the new question already exists
  if (subtopic.questions[newQuestion]) {
    alert("This question already exists!");
    return;
  }

  // Create a new key-value pair and delete the old one
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

// Добавить новую тему (без prompt)
function addTopic() {
  let baseName = "New Topic";
  let index = 1;
  let newName = baseName;

  // Ищем уникальное имя, если уже существует
  while (knowledgeBaseData.value.knowledge_base[newName]) {
    index++;
    newName = `${baseName} ${index}`;
  }

  // Создаём пустую тему
  knowledgeBaseData.value.knowledge_base[newName] = {
    subtopics: {},
  };
}

// Удалить тему
function removeTopic(topicName) {
  if (confirm(`Remove topic "${topicName}"?`)) {
    delete knowledgeBaseData.value.knowledge_base[topicName];
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

  // Убедимся, что `questions` создаётся сразу
  topic.subtopics[newName] = {
    questions: {},
  };
}

// Удалить подтему
function removeSubtopic(topicName, subtopicName) {
  if (confirm(`Remove subtopic "${subtopicName}" from "${topicName}"?`)) {
    const topic = knowledgeBaseData.value.knowledge_base[topicName];
    if (topic && topic.subtopics[subtopicName]) {
      delete topic.subtopics[subtopicName];
    }
  }
}

// Добавить вопрос (без prompt)
function addQuestion(topicName, subtopicName) {
  const topic = knowledgeBaseData.value.knowledge_base[topicName];
  if (!topic) return;
  const subtopic = topic.subtopics[subtopicName];
  if (!subtopic) return;

  // Убедимся, что объект `questions` существует
  if (!subtopic.questions) {
    subtopic.questions = {};
  }

  let baseName = "New Question";
  let index = 1;
  let newName = baseName;

  // Проверяем уникальность имени вопроса
  while (subtopic.questions.hasOwnProperty(newName)) {
    index++;
    newName = `${baseName} ${index}`;
  }

  console.log("newName=", newName);

  // Обновляем объект `questions`, чтобы Vue мог отследить изменения
  subtopic.questions = {
    ...subtopic.questions,
    [newName]: "", // Добавляем новый вопрос
  };

  // Полностью обновляем `knowledge_base`, чтобы Nuxt/Vue отследил изменение
  knowledgeBaseData.value.knowledge_base = { ...knowledgeBaseData.value.knowledge_base };
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
}

// Удалить вопрос
function removeQuestion(topicName, subtopicName, questionKey) {
  if (confirm(`Remove question "${questionKey}"?`)) {
    const topic = knowledgeBaseData.value.knowledge_base[topicName];
    if (!topic) return;
    const subtopic = topic.subtopics[subtopicName];
    if (!subtopic) return;

    delete subtopic.questions[questionKey];
  }
}

function getChanges() {
  const oldData = readonlyData.value.knowledge_base;
  const newData = knowledgeBaseData.value.knowledge_base;
  const patchData = {};
  console.log("newData=", newData);
  console.log("oldData=", oldData);

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
              subtopicDiff[question] = null; // Помечаем как удаленный
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
          topicDiff[subtopic] = null; // Помечаем как удаленный
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
      patchData[topic] = null; // Помечаем как удаленный
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
  } catch (error) {
    console.error("Ошибка при обновлении базы знаний:", error);
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
    }
  } catch (error) {
    console.error("Ошибка при обновлении базы знаний:", error);
  }
}

function clearPlayground() {
  if (confirm("Are you sure you want to clear the Playground? This action cannot be undone.")) {
    knowledgeBaseData.value.knowledge_base = {};
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
}
function saveChanges() {
  saveDatabase();
}

async function generatePatch() {
  console.log("promptText.value=", promptText.value);

  isLoading.value = true;
  try {
    console.log("Отправка изменений:", knowledgeBaseData.value.knowledge_base);
    const response = await useNuxtApp().$api.post("/api/knowledge/generate_patch", {
      user_message: promptText.value,
      // user_info: "user_info",
      base_data: knowledgeBaseData.value.knowledge_base,
    });
    console.log("response.data=", response.data);
    updatePlayground(response.data);
    isLoading.value = false;
  } catch (error) {
    console.error("Ошибка при обновлении базы знаний:", error);
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
