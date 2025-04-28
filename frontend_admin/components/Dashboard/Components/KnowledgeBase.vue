<template>
  <!-- Full screen container with no overflow -->
  <div class="flex flex-1 flex-col min-h-0 xl:max-h-[90vh] h-full">
    <Toast />
    <!-- Main container -->
    <div class="flex flex-col flex-1 overflow-hidden">
      <!-- Main block: 3 columns -->
      <div class="flex flex-1 flex-row rounded-md overflow-hidden">
        <div class="flex flex-col xl:flex-row flex-1 gap-8 justify-between overflow-hidden">
          <!-- LEFT COLUMN -->
          <div class="flex-0 xl:flex-1 max-h-screen flex flex-col bg-white dark:bg-gray-800 rounded-xl overflow-hidden shadow-thicc m-4">
            <section>
              <header
                class="flex items-center justify-between gap-2 px-4 py-3 border-b border-secondaryDark bg-secondaryLight dark:bg-secondaryDark max-h-[60px] h-[60px]"
              >
                <div class="flex items-center gap-2">
                  <i class="pi pi-folder-open text-2xl"></i>
                  <h2 class="font-semibold text-xl">Context sources</h2>
                </div>
                <div class="flex justify-center items-center">
                  <i class="pi pi-info-circle text-xl cursor-pointer" @click="showInstructions = true"></i>
                </div>
              </header>
              <div class="flex flex-col gap-4 p-4 h-full">
                <div>
                  <div class="flex gap-3 mb-4">
                    <!-- поиск -->
                    <div class="p-input-icon-left flex-1">
                      <IconField>
                        <InputIcon class="pi pi-search" />
                        <InputText v-model="searchTerm" icon="pi pi-search" placeholder="Search of sources…" class="w-full" />
                      </IconField>
                    </div>

                    <!-- добавить -->
                    <Button
                      label="Add context"
                      icon="pi pi-plus"
                      class="flex-shrink-0 px-6 py-3 text-base font-semibold bg-gray-900 border-0 rounded-lg text-white"
                      @click="openContextDialog"
                    />
                  </div>
                  <ul class="flex flex-col gap-2 max-h-40 overflow-y-auto mb-4">
                    <li v-for="ctx in contextList" :key="ctx.id" class="p-2 border rounded flex items-center justify-between gap-3">
                      <!-- иконка + заголовок -->
                      <div class="flex items-center gap-2 flex-1">
                        <i :class="typeIcon(ctx.type)"></i>
                        <span class="truncate">{{ ctx.title }}</span>
                      </div>

                      <!-- DROPDOWN PURPOSE -->
                      <Dropdown
                        v-model="ctx.purpose"
                        :options="contextPurposes"
                        optionLabel="label"
                        optionValue="value"
                        class="p-dropdown-sm w-24"
                        @change="(e) => onPurposeChange(ctx, e.value)"
                      />

                      <!-- delete -->
                      <Button icon="pi pi-trash" class="p-button-rounded p-button-text p-button-sm" @click="deleteContext(ctx.id)" />
                    </li>
                  </ul>

                  <!-- ================= Dialog ================= -->
                  <Dialog
                    v-model:visible="showContextDialog"
                    header="Add context"
                    :modal="true"
                    :closable="true"
                    :style="{ width: '40vw' }"
                  >
                    <div class="flex flex-col gap-3">
                      <!-- тип -->
                      <Dropdown
                        v-model="newCtx.type"
                        :options="contextTypes"
                        optionLabel="label"
                        optionValue="value"
                        class="w-full"
                        placeholder="Select type"
                      />

                      <!-- необязательный заголовок -->
                      <InputText v-model="newCtx.title" class="w-full" placeholder="Title (optional)" />

                      <!-- динамическое поле по типу -->
                      <Textarea
                        v-if="newCtx.type === 'text'"
                        v-model="newCtx.text"
                        rows="5"
                        class="w-full"
                        placeholder="Paste the text here"
                      />

                      <InputText v-else-if="newCtx.type === 'url'" v-model="newCtx.url" class="w-full" placeholder="https://example.com" />

                      <div v-else-if="newCtx.type === 'file'">
                        <FileUpload
                          name="file"
                          :customUpload="true"
                          :auto="false"
                          :showUploadButton="false"
                          :showCancelButton="false"
                          accept="image/*,application/pdf,application/zip"
                          @select="onCtxFileSelect"
                        />
                        <p v-if="newCtx.file" class="text-sm mt-2">{{ newCtx.file.name }} — {{ newCtx.file.size }} bytes</p>
                      </div>

                      <!-- кнопки -->
                      <div class="flex justify-end gap-2 mt-4">
                        <Button label="Cancel" class="p-button-text" @click="showContextDialog = false" />
                        <Button
                          label="Add"
                          icon="pi pi-check"
                          class="p-button-success"
                          :disabled="!canSubmitContext"
                          @click="submitContext"
                        />
                      </div>
                    </div>
                  </Dialog>
                </div>
              </div>
            </section>
            <section>
              <header
                class="flex items-center justify-between gap-2 px-4 py-3 border-y border-secondaryDark bg-secondaryLight dark:bg-secondaryDark max-h-[60px] h-[60px]"
              >
                <div class="flex items-center gap-2">
                  <i class="pi pi-pencil text-2xl"></i>
                  <h2 class="font-semibold text-xl">Query field</h2>
                </div>
                <div class="flex justify-center items-center">
                  <i class="pi pi-info-circle text-xl cursor-pointer" @click="showInstructions = true"></i>
                </div>
              </header>
              <div class="flex flex-col gap-4 p-4 h-full">
                <!-- FORM with generatePatch submit handler -->
                <form @submit.prevent="generatePatch" class="flex flex-col flex-grow min-h-0 overflow-y-auto gap-4">
                  <!-- TEXTAREA -->
                  <Textarea id="promptTextArea" class="w-full min-h-[150px] max-h-[40vh]" required v-model="promptText" />

                  <!-- GENERATE SMART CHANGE BUTTON -->
                  <Dropdown
                    v-model="selectedModel"
                    :options="aiModels"
                    optionLabel="label"
                    optionValue="value"
                    class="w-full"
                    placeholder="Select AI Model"
                  />
                  <Button
                    type="submit"
                    :disabled="isLoading"
                    label="Generate smart change"
                    icon="pi pi-save"
                    class="w-full flex justify-center items-center"
                  >
                    <LoaderSmall v-if="isLoading" />
                  </Button>
                </form>
              </div>
            </section>
          </div>

          <!-- CENTER COLUMN -->
          <div class="flex-0 xl:flex-1 max-h-screen flex flex-col bg-white dark:bg-gray-800 rounded-xl shadow-thicc m-4 max-h-full">
            <section class="rounded-xl flex flex-col flex-1 overflow-hidden">
              <header
                class="flex items-center justify-between gap-2 px-4 py-3 border-b border-secondaryDark bg-secondaryLight dark:bg-secondaryDark max-h-[60px] h-[60px]"
              >
                <div class="flex items-center gap-2">
                  <i class="pi pi-file-edit text-2xl"></i>
                  <h2 class="font-semibold text-xl">Playground</h2>
                </div>

                <div class="flex justify-center items-center gap-4">
                  <div class="flex flex-row gap-2">
                    <!-- Review-changes button -->
                    <Button class="p-button-sm flex items-center justify-center gap-2 min-w-[210px] max-h-[37px]" @click="reviewChanges">
                      <div v-if="!isLoading" class="flex items-center gap-2">
                        <i class="pi pi-eye"></i>
                        <p>Review changes</p>

                        <Badge v-if="changesTotal" :value="changesTotal" severity="info" class="ml-2" />
                      </div>
                      <LoaderSmall v-else />
                    </Button>

                    <Button v-if="!isEditMode" icon="pi pi-pencil" class="p-button-sm" @click="toggleEditMode" />
                    <Button :disabled="isLoading" icon="pi pi-trash" class="p-button-sm" @click="clearPlayground" />
                    <Button v-if="isEditMode" label="Add topic" icon="pi pi-plus" class="p-button-sm" @click="addTopic" />
                  </div>
                  <i class="pi pi-info-circle text-xl cursor-pointer" @click="showInstructions = true"></i>
                </div>
              </header>
              <div class="flex flex-col gap-4 p-4 h-full overflow-y-auto">
                <div class="flex flex-1 min-h-0 overflow-y-auto" v-if="Object.keys(knowledgeBaseData.knowledge_base).length || isEditMode">
                  <!-- Read-only display if not editing -->
                  <div v-if="!isEditMode" class="flex-1 overflow-y-auto">
                    <div v-for="(topicValue, topicName) in knowledgeBaseData.knowledge_base" :key="topicName" class="mb-6">
                      <h3 class="font-semibold text-gray-900 dark:text-gray-200">{{ topicName }}</h3>
                      <div v-if="topicValue.subtopics">
                        <div v-for="(subtopicValue, subtopicName) in topicValue.subtopics" :key="subtopicName" class="ml-4 mb-4">
                          <h4 class="font-medium text-gray-800 dark:text-gray-300">{{ subtopicName }}</h4>
                          <ul v-if="subtopicValue.questions" class="ml-4 list-disc text-sm text-gray-700 dark:text-gray-400">
                            <li v-for="(qObj, questionKey) in subtopicValue.questions" :key="questionKey" class="mb-4">
                              <div>
                                <span class="font-semibold">{{ questionKey }}: </span>
                                <span> {{ qObj.text }}</span>
                              </div>
                              <div v-if="qObj.files && qObj.files.length" class="mt-2 ml-2">
                                <div v-for="(fileLink, fileIndex) in qObj.files" :key="fileIndex" class="mb-1">
                                  <ImageLink :fileLink="fileLink" />
                                </div>
                              </div>
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Edit mode if isEditMode -->
                  <div v-else class="flex-1 overflow-y-auto max-h-full">
                    <div
                      v-for="(topicValue, topicName) in knowledgeBaseData.knowledge_base"
                      :key="topicName"
                      :id="`topic-${topicName}`"
                      class="mb-6"
                    >
                      <!-- Topic header with input and buttons -->
                      <div class="flex items-center mb-2 border-gray-400 dark:border-gray-600 pb-1">
                        <input
                          class="border p-1 flex-1 mr-2 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 rounded"
                          :placeholder="topicName.includes('New Topic') ? topicName : ''"
                          :value="topicName.includes('New Topic') ? '' : topicName"
                          @blur="renameTopic(topicName, $event.target.value)"
                          @keydown.enter.prevent="renameTopic(topicName, $event.target.value)"
                        />
                        <Button
                          icon="pi pi-arrow-up"
                          class="p-button-sm mr-1"
                          :disabled="isFirstTopic(topicName)"
                          @click="moveTopic(topicName, -1)"
                        />
                        <Button
                          icon="pi pi-arrow-down"
                          class="p-button-sm mr-2"
                          :disabled="isLastTopic(topicName)"
                          @click="moveTopic(topicName, 1)"
                        />
                        <Button icon="pi pi-minus" class="p-button-sm mr-2" @click="removeTopic(topicName)" />
                        <Button label="Add subtopic" icon="pi pi-plus" class="p-button-sm" @click="addSubtopic(topicName)" />
                      </div>
                      <!-- Subtopics and questions -->
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
                            :placeholder="subtopicName.includes('New Subtopic') ? subtopicName : ''"
                            :value="subtopicName.includes('New Subtopic') ? '' : subtopicName"
                            @blur="renameSubtopic(topicName, subtopicName, $event.target.value)"
                            @keydown.enter.prevent="renameSubtopic(topicName, subtopicName, $event.target.value)"
                          />
                          <Button
                            icon="pi pi-arrow-up"
                            class="p-button-sm mr-1"
                            :disabled="isFirstSub(topicName, subtopicName)"
                            @click="moveSub(topicName, subtopicName, -1)"
                          />
                          <Button
                            icon="pi pi-arrow-down"
                            class="p-button-sm mr-2"
                            :disabled="isLastSub(topicName, subtopicName)"
                            @click="moveSub(topicName, subtopicName, 1)"
                          />
                          <Button icon="pi pi-minus" class="p-button-sm mr-2" @click="removeSubtopic(topicName, subtopicName)" />
                          <Button
                            label="Add question"
                            icon="pi pi-plus"
                            class="p-button-sm"
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
                              <label class="font-semibold">Question:</label>
                              <div class="flex items-center gap-2">
                                <Button
                                  icon="pi pi-arrow-up"
                                  class="p-button-text p-button-rounded p-button-sm"
                                  :disabled="isFirstQ(topicName, subtopicName, questionKey)"
                                  @click="moveQ(topicName, subtopicName, questionKey, -1)"
                                />
                                <Button
                                  icon="pi pi-arrow-down"
                                  class="p-button-text p-button-rounded p-button-sm"
                                  :disabled="isLastQ(topicName, subtopicName, questionKey)"
                                  @click="moveQ(topicName, subtopicName, questionKey, 1)"
                                />
                                <Button
                                  icon="pi pi-trash"
                                  class="p-button-rounded p-button-text"
                                  @click="removeQuestion(topicName, subtopicName, questionKey)"
                                />
                              </div>
                            </div>

                            <!-- QUESTION (the key) -->
                            <Textarea
                              :placeholder="questionKey.includes('New Question') ? questionKey : ''"
                              :value="questionKey.includes('New Question') ? '' : questionKey"
                              class="block w-full mb-2 min-h-[50px] border rounded p-2 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700"
                              @blur="renameQuestion(topicName, subtopicName, questionKey, $event.target.value)"
                            />

                            <!-- ANSWER TEXT -->
                            <label class="font-semibold">Answer text:</label>
                            <Textarea
                              v-model="questionObj.text"
                              class="block w-full border rounded p-2 min-h-[100px] text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 mb-2"
                            />

                            <!-- LINKS / FILES -->
                            <label class="font-semibold">Links / Files:</label>
                            <ul class="mb-2">
                              <li v-for="(fileLink, fileIndex) in questionObj.files" :key="fileIndex" class="flex items-center gap-2 mb-1">
                                <input
                                  v-model="questionObj.files[fileIndex]"
                                  type="text"
                                  class="border p-1 flex-1 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 rounded"
                                />
                                <Button
                                  icon="pi pi-minus"
                                  class="p-button-sm"
                                  @click="removeQuestionFile(topicName, subtopicName, questionKey, fileIndex)"
                                />
                              </li>
                            </ul>
                            <div v-if="localFiles.length" class="mt-4">
                              <h3>Selected files:</h3>
                              <ul>
                                <li v-for="(file, idx) in localFiles" :key="idx">{{ file.name }} - {{ file.size }} bytes</li>
                              </ul>
                            </div>

                            <Button
                              label="Add link"
                              icon="pi pi-plus"
                              class="p-button-sm"
                              @click="addQuestionFile(topicName, subtopicName, questionKey)"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div
                  v-if="!Object.keys(knowledgeBaseData.knowledge_base).length && !isEditMode"
                  class="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-center p-10"
                >
                  <!-- иконка -->
                  <i class="pi pi-th-large text-gray-500 dark:text-gray-400 text-5xl mb-6" />
                  <!-- заголовок -->
                  <h3 class="text-2xl font-semibold text-gray-500 dark:text-gray-300 mb-2">Playground пуст</h3>
                  <!-- подпись -->
                  <p class="text-gray-500 dark:text-gray-400 mb-6 max-w-md">
                    Импортируйте контент из левой панели или&nbsp;создайте новый блок
                  </p>
                  <!-- кнопка -->
                  <Button
                    label="Создать блок"
                    icon="pi pi-plus"
                    class="px-10 py-3 text-lg font-semibold bg-gray-900 border-0"
                    @click="
                      () => {
                        toggleEditMode();
                        addTopic();
                      }
                    "
                  />
                </div>

                <!-- Save / Reject / Transfer -->
                <div v-if="isEditMode" class="flex flex-col gap-2 my-2">
                  <Button :disabled="isLoading" label="Save playground" icon="pi pi-save" class="p-button-sm" @click="savePlayground" />
                  <Button
                    :disabled="isLoading"
                    label="Reject playground"
                    icon="pi pi-times"
                    class="p-button-sm"
                    @click="rejectPlayground"
                  />
                </div>
                <div v-else class="flex flex-col gap-2 my-2">
                  <Button
                    :disabled="isLoading || !hasChanges"
                    label="Transfer to database"
                    icon="pi pi-save"
                    class="p-button-sm"
                    @click="saveChanges"
                  />
                  <Button
                    :disabled="isLoading"
                    label="Reject playground"
                    icon="pi pi-times"
                    class="p-button-sm"
                    @click="rejectPlayground"
                  />
                </div>
              </div>
            </section>
          </div>

          <!-- RIGHT COLUMN (Readonly Copy) -->
          <div class="flex-0 xl:flex-1 max-h-screen flex flex-col bg-white dark:bg-gray-800 rounded-xl shadow-thicc m-4 max-h-full">
            <section class="rounded-xl flex flex-col flex-1 overflow-hidden">
              <header
                class="flex items-center justify-between gap-2 px-4 py-3 border-b border-secondaryDark bg-secondaryLight dark:bg-secondaryDark max-h-[60px] h-[60px]"
              >
                <div class="flex items-center gap-2">
                  <i class="pi pi-folder-open text-2xl"></i>
                  <h2 class="font-semibold text-xl">Knowledge base (read-only)</h2>
                </div>
                <div class="flex justify-center items-center">
                  <i class="pi pi-info-circle text-xl cursor-pointer" @click="showInstructions = true"></i>
                </div>
              </header>
              <div class="flex-1 overflow-y-auto p-4">
                <div v-for="(topicValue, topicName) in readonlyData.knowledge_base" :key="topicName" class="mb-6">
                  <h3 class="font-semibold text-gray-900 dark:text-gray-200">{{ topicName }}</h3>
                  <div v-if="topicValue.subtopics">
                    <div v-for="(subtopicValue, subtopicName) in topicValue.subtopics" :key="subtopicName" class="ml-4 mb-4">
                      <h4 class="font-medium text-gray-800 dark:text-gray-300">{{ subtopicName }}</h4>
                      <ul v-if="subtopicValue.questions" class="ml-4 list-disc text-sm text-gray-700 dark:text-gray-400">
                        <li v-for="(qObj, questionKey) in subtopicValue.questions" :key="questionKey" class="mb-4">
                          <div>
                            <span class="font-semibold">{{ questionKey }}: </span>
                            <span> {{ qObj.text }}</span>
                          </div>
                          <div v-if="qObj.files && qObj.files.length" class="mt-2 ml-2">
                            <div v-for="(fileLink, fileIndex) in qObj.files" :key="fileIndex" class="mb-1">
                              <ImageLink :fileLink="fileLink" />
                            </div>
                          </div>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
              <div class="flex flex-col gap-2 p-4 my-2">
                <Button label="Export" icon="pi pi-file-export" class="p-button-sm" @click="showExportDialog = true" />

                   <AdminChat/>
                </div>
            </section>
          </div>
        </div>
      </div>
    </div>

    <!-- 💾 Export-format picker -->
    <Dialog v-model:visible="showExportDialog" header="Export Knowledge Base" :modal="true" :style="{ width: '25rem' }">
      <div class="flex flex-col gap-4 pt-2">
        <div class="flex items-center justify-center  gap-3">
          <RadioButton  v-model="exportFormat" inputId="exp-json" value="json" />
          <label for="exp-json" class="cursor-pointer flex-1">
            <p class="font-semibold">JSON</p>
            <p class="text-sm text-gray-500">Full structured data (recommended)</p>
          </label>
        </div>

        <div class="flex items-center justify-center gap-3">
          <RadioButton v-model="exportFormat" inputId="exp-csv" value="csv" />
          <label for="exp-csv" class="cursor-pointer flex-1">
            <p class="font-semibold">CSV</p>
            <p class="text-sm text-gray-500">Spreadsheet-compatible format</p>
          </label>
        </div>

        <div class="flex items-center justify-center  gap-3">
          <RadioButton v-model="exportFormat" inputId="exp-txt" value="txt" />
          <label for="exp-txt" class="cursor-pointer flex-1">
            <p class="font-semibold">Plain Text</p>
            <p class="text-sm text-gray-500">Simple human-readable format</p>
          </label>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" class="p-button-text" @click="showExportDialog = false" />
        <Button label="Export" icon="pi pi-download" @click="exportData(exportFormat)" />
      </template>
    </Dialog>
    <!-- INSTRUCTIONS DIALOG -->
    <Dialog v-model:visible="showInstructions" :header="'How to use this tool?'" :modal="true" :closable="true" :style="{ width: '50vw' }">
      <div class="wysiwyg">
        <p>Welcome to the knowledge base tool usage guide. Here are a few recommendations:</p>
        <ul>
          <li>
            <strong>Formulate your queries clearly:</strong> Use clear and specific wording so that the AI can better understand your
            intentions.
          </li>
          <li>
            <strong>Use keywords:</strong> Include keywords that best describe the topic or question to improve search and generation
            results.
          </li>
          <li><strong>Review the results:</strong> Always check and edit the AI-generated data to ensure its accuracy and relevance.</li>
          <li>
            <strong>Provide examples:</strong> If possible, provide examples or context to help the AI better adapt to your requirements.
          </li>
          <li><strong>Give feedback:</strong> Share feedback about the AI’s results to help improve its performance in the future.</li>
        </ul>
        <p>
          By following these recommendations, you will be able to use the AI capabilities for working with your knowledge base most
          effectively.
        </p>

        <h3 class="text-center">Prompt Templates</h3>
        <ul>
          <li>Fill in this data in Russian with keys and break it into MANY questions, topics, and subtopics.</li>
        </ul>

        <h3 class="text-center">Instructions</h3>
        <h1>Knowledge Base Usage Instructions</h1>

        <h2>General Information</h2>
        <p>The interface is divided into three parts:</p>
        <ul>
          <li><strong>Prompt Input</strong> – a field for uploading text data.</li>
          <li><strong>Playground (Intermediate Database)</strong> – the data editing area.</li>
          <li><strong>Actual Database</strong> – the real data storage.</li>
        </ul>

        <h2>Editing Data</h2>
        <p>Two editing modes are available:</p>
        <ul>
          <li><strong>Manual Mode</strong> – you can add topics, subtopics, questions, and answers manually.</li>
          <li><strong>Automatic Mode</strong> – enter a prompt to automatically fill the database structure.</li>
        </ul>

        <h2>Applying Changes</h2>
        <p>
          After editing in the <strong>Playground</strong>, you can transfer the changes to the real database by clicking
          <strong>"Transfer to database"</strong>.
        </p>

        <h2>Discarding Changes</h2>
        <p>To discard the changes and revert the Playground to its original state, click <strong>"Reject playground"</strong>.</p>

        <h2>Working with JSON</h2>
        <p>The following features are available:</p>
        <ul>
          <li><strong>Download JSON</strong> – save the current version of the database.</li>
          <li><strong>Upload JSON</strong> – restore the database from a previously saved file.</li>
        </ul>

        <h2>Additional Features</h2>
        <p>The interface design and functionality may be improved in the future for better user experience.</p>

        <div class="highlight">
          <p>
            <strong>Important:</strong> any changes made in the Playground do not affect the real database until the "Transfer to database"
            button is clicked.
          </p>
        </div>

        <h3 class="text-center">IMPORTANT!</h3>
        <ul>
          <li>Each query is independent and does not take previous queries into account.</li>
          <li>Do not use TOO large queries.</li>
        </ul>
      </div>
    </Dialog>

    <SaveChangesDialog
      v-model:visible="showSaveChangesDialog"
      :review-only="reviewOnly"
      :is-edit-mode="isEditMode"
      :has-changes="hasChanges"
      :changes="changes"
      :added-items="addedItems"
      :changed-items="changedItems"
      :deleted-items="getDeletedItems()"
      @save="handleConfirmChanges"
      @cancel="showSaveChangesDialog = false"
    />

     <!-- Transition for smooth show/hide -->
     <transition name="fade">
            <!-- The actual chat box (visible only if `showChat` is true) -->
            <div v-if="isChatOpen" class="chat-box" :class="{ 'chat-overlay-mobile': isMobile }">
                <iframe :src="chatUrl" class="flex-1" style="border: none; z-index: 9999"></iframe>
                <Button v-if="isMobile" @click="onClose" :label="$t('buttons.close')"></Button>
            </div>
        </transition>
  </div>
</template>

<script setup>
import { ref } from "vue";
// import Textarea from 'primevue/textarea';
// import Button from 'primevue/button';
import cloneDeep from "lodash/cloneDeep";
import ImageLink from "./ImageLink.vue";
import { useI18n } from "vue-i18n"; // Добавляем i18n
import SaveChangesDialog from "./SaveChangesDialog.vue";

const { t } = useI18n(); // Получаем функцию перевода
const toast = useToast();
const readonlyData = ref({});
const promptText = ref("");
const searchTerm = ref("");
const selectedFiles = ref([]);
const isEditMode = ref(false);
const showInstructions = ref(false);
const isLoading = ref(false);
// Local array to store *all* selected files
const localFiles = ref([]);
const selectedModel = ref("gpt-4o");

const aiModels = ref([
  { label: "gpt-4o", value: "gpt-4o" },
  { label: "gpt-4o-mini", value: "gpt-4o-mini" },
  { label: "gemini-2.0-flash", value: "gemini-2.0-flash" },
]);

import AdminChat from '~/components/AdminChat.vue';

const reviewOnly = ref(false);
/* ---------- контекст ---------- */
const contextList = ref([]); // список
const showContextDialog = ref(false); // диалог

const contextTypes = [
  { label: "Text", value: "text" },
  { label: "File / Photo", value: "file" },
  { label: "Link", value: "url" },
];

const contextPurposes = [
  { label: "None", value: "none" },
  { label: "Bot", value: "bot" },
  { label: "KB", value: "kb" },
  { label: "Both", value: "both" },
];

// данные формы добавления
const newCtx = reactive({
  type: "", // 'TEXT' | 'FILE' | 'URL'
  title: "",
  text: "",
  url: "",
  file: null,
});

/* ---------- смена purpose ---------- */
async function onPurposeChange(ctx, newPurpose) {
  const prev = ctx.purpose; // на случай отката
  ctx.purpose = newPurpose;

  try {
    const form = new FormData();
    form.append("new_purpose", newPurpose);
    await useNuxtApp().$api.patch(`/api/knowledge/context_entity/${ctx.id}/purpose`, form);
    showSuccess("Purpose updated");
  } catch (_) {
    ctx.purpose = prev; // откат при ошибке
    showError("Purpose not updated");
  }
}

onMounted(fetchContextUnits);

const changesTotal = computed(() => changes.value.added + changes.value.changed + changes.value.deleted);

function reviewChanges() {
  calculateChanges(); // always refresh counters
  reviewOnly.value = true; // read-only mode
  showSaveChangesDialog.value = true;
}

/* ---------- helpers ---------- */

function typeIcon(t) {
  return (
    {
      text: "pi pi-align-left",
      file: "pi pi-file",
      url: "pi pi-link",
    }[t] || "pi pi-question"
  );
}

/* ---------- API ----------- */
async function fetchContextUnits() {
  try {
    const { data } = await useNuxtApp().$api.get("/api/knowledge/context_entity");
    console.log("contextList= ", data);
    contextList.value = data;
  } catch (_) {
    showError("Cannot load context");
  }
}

function openContextDialog() {
  Object.assign(newCtx, { type: "", title: "", text: "", url: "", file: null });
  showContextDialog.value = true;
}

function onCtxFileSelect(e) {
  newCtx.file = e.files[0] || null;
}

const canSubmitContext = computed(() => {
  if (newCtx.type === "text") return newCtx.text.trim();
  if (newCtx.type === "url") return newCtx.url.trim();
  if (newCtx.type === "file") return newCtx.file;
  return false;
});

async function submitContext() {
  try {
    const form = new FormData();
    form.append("type", newCtx.type);
    form.append("purpose", "none");
    if (newCtx.title) form.append("title", newCtx.title);

    if (newCtx.type === "text") form.append("text", newCtx.text);
    if (newCtx.type === "url") form.append("url", newCtx.url);
    if (newCtx.type === "file" && newCtx.file) form.append("file", newCtx.file, newCtx.file.name);

    console.log("form= ", ...form);
    await useNuxtApp().$api.post("/api/knowledge/context_entity", form);
    showSuccess("Context added");
    showContextDialog.value = false;
    fetchContextUnits();
  } catch (_) {
    showError("Context not added");
  }
}

async function deleteContext(id) {
  if (!confirm("Delete context unit?")) return;
  try {
    await useNuxtApp().$api.delete(`/api/knowledge/context_entity/${id}`);
    contextList.value = contextList.value.filter((c) => c.id !== id);
    showSuccess("Context deleted");
  } catch (_) {
    showError("Context not deleted");
  }
}

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
const { currentFrontendUrl } = useURLState();
const chatUrl = isLocalhost ? `${currentFrontendUrl.value}/chats/telegram-chat` : `${currentFrontendUrl.value}/chats/telegram-chat`;

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

  const originalName = questionRenamingMap.value.get(oldQuestion) || oldQuestion;
  questionRenamingMap.value.delete(oldQuestion);
  questionRenamingMap.value.set(newQuestion, originalName);
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

      const inputElement = lastAddedElement.value.querySelector("input");
      if (inputElement) {
        inputElement.focus();
      }
    }
  });
  showSuccess("Topic added successfully");
}

// Удалить тему
function removeTopic(topicName) {
  if (confirm(t("knowledgeBase.removeTopic", { topicName }))) {
    countDeletedItemsFromTopic(topicName);

    delete knowledgeBaseData.value.knowledge_base[topicName];
    showSuccess("Topic removed successfully");
  } else {
    showError("Topic not removed");
  }
}

function countDeletedItemsFromTopic(topicName) {
  const originalTopic = readonlyData.value.knowledge_base?.[topicName];
  const currentTopic = knowledgeBaseData.value.knowledge_base[topicName];

  if (originalTopic) {
    deletedItemsCount.value++;

    for (const subtopic in originalTopic.subtopics || {}) {
      if (currentTopic?.subtopics?.[subtopic]) {
        deletedItemsCount.value++;
        const originalQuestions = originalTopic.subtopics[subtopic].questions || {};
        const currentQuestions = currentTopic.subtopics[subtopic].questions || {};

        for (const question in originalQuestions) {
          if (currentQuestions[question]) {
            deletedItemsCount.value++;
          }
        }
      }
    }
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

      const inputElement = lastAddedElement.value.querySelector("input");

      if (inputElement) {
        inputElement.focus();
      }
    }
  });
  showSuccess("Subtopic added successfully");
}

// Удалить подтему
function removeSubtopic(topicName, subtopicName) {
  if (confirm(t("knowledgeBase.removeSubtopic", { subtopicName, topicName }))) {
    const topic = knowledgeBaseData.value.knowledge_base[topicName];
    if (topic && topic.subtopics[subtopicName]) {
      countDeletedItemsFromSubtopic(topicName, subtopicName, topic);

      delete topic.subtopics[subtopicName];
      showSuccess("Subtopic removed successfully");
    } else {
      showError("Subtopic not removed");
    }
  }
}

function countDeletedItemsFromSubtopic(topicName, subtopicName, topic) {
  const originalSubtopic = readonlyData.value.knowledge_base?.[topicName]?.subtopics?.[subtopicName];
  const currentSubtopic = topic.subtopics[subtopicName];

  if (originalSubtopic) {
    deletedItemsCount.value++;
    const originalQuestions = originalSubtopic.questions || {};
    const currentQuestions = currentSubtopic.questions || {};
    for (const question in originalQuestions) {
      if (currentQuestions[question]) {
        deletedItemsCount.value++;
      }
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

      const textareaElement = lastAddedElement.value.querySelector("textarea");
      if (textareaElement) {
        textareaElement.focus();
      }
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

  nextTick(() => {
    const escapedTopicName = CSS.escape(topicName);
    const escapedSubtopicName = CSS.escape(subtopicName);
    const escapedQuestion = CSS.escape(question);

    const inputs = document.querySelectorAll(`#question-${escapedTopicName}-${escapedSubtopicName}-${escapedQuestion} input[type="text"]`);
    const lastInput = inputs[inputs.length - 1];
    if (lastInput) {
      lastInput.focus();
      lastInput.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });

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

    const existedInOriginal = readonlyData.value.knowledge_base?.[topicName]?.subtopics?.[subtopicName]?.questions?.[questionKey];
    delete subtopic.questions[questionKey];
    if (existedInOriginal) {
      deletedItemsCount.value++;
    }
    showSuccess("Question removed successfully");
  } else {
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
    calculateChanges();
    hasChanges.value = true;
    console.log("Успешное обновление базы знаний:", response.data);
    isEditMode.value = false;
    showSuccess("Playground updated successfully");
  } catch (error) {
    console.error("Ошибка при обновлении базы знаний:", error);
    showError("Playground not updated");
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

      clearVariables();

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
  if (confirm(`Clear playground?\n\nChanges in the playground will be discarded.\nThis action will NOT affect the knowledge base.`)) {
    countDeletedItems();
    knowledgeBaseData.value.knowledge_base = {};
    calculateChanges();

    showSuccess("Playground cleared successfully");
  }
}

function countDeletedItems() {
  const readonlyBase = readonlyData.value.knowledge_base;
  let totalDeleted = 0;

  for (const topic in readonlyBase) {
    totalDeleted++;
    const subtopics = readonlyBase[topic].subtopics || {};
    for (const subtopic in subtopics) {
      totalDeleted++;
      const questions = subtopics[subtopic].questions || {};
      totalDeleted += Object.keys(questions).length;
    }
  }

  deletedItemsCount.value = totalDeleted;
}

function savePlayground() {
  calculateChanges();
  showSaveChangesDialog.value = true;
}

function rejectPlayground() {
  const confirmation = confirm(
    `Reject playground?\n\nChanges in the playground will be discarded.\nThis action will NOT affect the knowledge base.`
  );
  if (!confirmation) return;

  isEditMode.value = false;

  clearVariables();

  knowledgeBaseData.value.knowledge_base = cloneDeep(readonlyData.value.knowledge_base);
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

function saveChanges() {
  calculateChanges();
  showSaveChangesDialog.value = true;
}
async function generatePatch() {
  // 1. Prepare FormData
  const formData = new FormData();

  // 2. Append any other fields if needed:
  formData.append("user_message", promptText.value);
  formData.append("ai_model", selectedModel.value);
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

  knowledgeBaseData.value.knowledge_base[newName] = {
    ...knowledgeBaseData.value.knowledge_base[oldName],
  };
  delete knowledgeBaseData.value.knowledge_base[oldName];

  const originalName = renamingMap.value.get(oldName) || oldName;
  renamingMap.value.delete(oldName);
  renamingMap.value.set(newName, originalName);
}

// Переименовать подтему
function renameSubtopic(topicName, oldSubtopicName, newSubtopicName) {
  if (!newSubtopicName || newSubtopicName === oldSubtopicName) return;
  const topic = knowledgeBaseData.value.knowledge_base[topicName];
  if (!topic || !topic.subtopics) return;

  topic.subtopics[newSubtopicName] = topic.subtopics[oldSubtopicName];
  delete topic.subtopics[oldSubtopicName];

  const originalName = subtopicRenamingMap.value.get(oldSubtopicName) || oldSubtopicName;
  subtopicRenamingMap.value.delete(oldSubtopicName);
  subtopicRenamingMap.value.set(newSubtopicName, originalName);
}

const showSaveChangesDialog = ref(false);
const changes = ref({ added: 0, changed: 0, deleted: 0 });
const deletedItemsCount = ref(0);
const addedItems = ref({});
const changedItems = ref({});
const renamingMap = ref(new Map());
const subtopicRenamingMap = ref(new Map());
const questionRenamingMap = ref(new Map());
const hasChanges = ref(false);

watch(showSaveChangesDialog, () => {
  if (!showSaveChangesDialog.value) {
    reviewOnly.value = false; // reset to edit mode
  }
});

function clearVariables() {
  changes.value = { added: 0, changed: 0, deleted: 0 };
  deletedItemsCount.value = 0;
  addedItems.value = {};
  changedItems.value = {};
  hasChanges.value = false;

  renamingMap.value.clear();
  subtopicRenamingMap.value.clear();
  questionRenamingMap.value.clear();
}

function calculateChanges() {
  const original = readonlyData.value.knowledge_base;
  const current = knowledgeBaseData.value.knowledge_base;
  const result = { added: 0, changed: 0, deleted: 0 };
  const added = {};
  const changed = {};

  for (const topic in current) {
    const currentSubtopics = current[topic]?.subtopics || {};

    //if key doesn't exist, it can be new or changed topic
    if (!original[topic]) {
      const currentTopic = renamingMap.value.get(topic);
      if (currentTopic && !currentTopic?.includes("New Topic")) {
        result.changed++;
        changed[topic] = {
          _changed: true,
          subtopics: {},
        };
      } else {
        result.added++;
        added[topic] = {
          subtopics: {},
          _new: true,
        };

        // Count and add all subtopics and questions inside new topic
        for (const subtopic in currentSubtopics) {
          result.added++;
          added[topic].subtopics[subtopic] = {
            questions: {},
            _new: true,
          };

          const questions = currentSubtopics[subtopic]?.questions || {};
          for (const question in questions) {
            result.added++;
            added[topic].subtopics[subtopic].questions[question] = {
              ...questions[question],
              _new: true,
            };
          }
        }
        continue;
      }
    }

    const originalTopicName = renamingMap.value.get(topic) || topic;
    const originalSubtopics = original[originalTopicName]?.subtopics || {};

    for (const subtopic in currentSubtopics) {
      const currentQuestions = currentSubtopics[subtopic]?.questions || {};

      if (!originalSubtopics[subtopic]) {
        const currentSubtopic = subtopicRenamingMap.value.get(subtopic);

        if (currentSubtopic && !currentSubtopic?.includes("New Subtopic")) {
          result.changed++;
          if (!changed[topic]) {
            changed[topic] = { subtopics: {} };
          }
          if (!changed[topic].subtopics[subtopic]) {
            changed[topic].subtopics[subtopic] = {
              _changed: true,
              questions: {},
            };
          }
        } else {
          result.added++;

          if (!added[topic]) {
            added[topic] = { subtopics: {} };
          }

          added[topic].subtopics[subtopic] = {
            questions: {},
            _new: true,
          };

          // Add and count all questions inside new subtopic
          const questions = currentSubtopics[subtopic]?.questions || {};
          for (const question in questions) {
            result.added++;
            added[topic].subtopics[subtopic].questions[question] = {
              ...questions[question],
              _new: true,
            };
          }
          continue;
        }
      }

      const originalSubtopicName = subtopicRenamingMap.value.get(subtopic) || subtopic;
      const originalQuestions = originalSubtopics[originalSubtopicName]?.questions || {};

      // For each question in existing subtopic
      for (const qstn in currentQuestions) {
        const question = questionRenamingMap.value.get(qstn) || qstn;

        if (!originalQuestions[question]) {
          const currentQuestion = questionRenamingMap.value.get(qstn);

          if (currentQuestion && !currentQuestion?.includes("New Question")) {
            result.changed++;

            const currentQuestion = currentQuestions[question];

            if (!changed[topic]) {
              changed[topic] = { subtopics: {} };
            }
            if (!changed[topic].subtopics[subtopic]) {
              changed[topic].subtopics[subtopic] = { questions: {} };
            }
            changed[topic].subtopics[subtopic].questions[qstn] = {
              ...currentQuestion,
              _changed: true,
            };
          } else {
            result.added++;

            if (!added[topic]) {
              added[topic] = { subtopics: {} };
            }
            if (!added[topic].subtopics[subtopic]) {
              added[topic].subtopics[subtopic] = { questions: {} };
            }
            added[topic].subtopics[subtopic].questions[qstn] = {
              ...currentQuestions[qstn],
              _new: true,
            };
          }
        } else if (JSON.stringify(currentQuestions[question]) !== JSON.stringify(originalQuestions[question])) {
          result.changed++;

          if (!changed[topic]) {
            changed[topic] = { subtopics: {} };
          }
          if (!changed[topic].subtopics[subtopic]) {
            changed[topic].subtopics[subtopic] = { questions: {} };
          }
          if (question === qstn) {
            const currentQuestion = currentQuestions[question];
            const originalQuestion = originalQuestions[question];

            changed[topic].subtopics[subtopic].questions[question] = {
              _previous: { ...originalQuestion },
              _current: { ...currentQuestion },
            };
          } else {
            const currentQuestion = currentQuestions[qstn];
            const originalQuestion = originalQuestions[question];

            changed[topic].subtopics[subtopic].questions[qstn] = {
              _previous: { ...originalQuestion },
              _current: { ...currentQuestion },
              _changed: question !== qstn,
            };

            if (currentQuestion.text !== originalQuestion.text || currentQuestion.files.join("") !== originalQuestion.files.join("")) {
              result.changed++;
            }
          }
        }
      }
    }
  }

  result.deleted = deletedItemsCount.value;

  changes.value = result;
  addedItems.value = added;
  changedItems.value = changed;

  hasChanges.value = result.added > 0 || result.changed > 0 || result.deleted > 0;
}

function getDeletedItems() {
  const original = readonlyData.value.knowledge_base;
  const current = knowledgeBaseData.value.knowledge_base;
  const deleted = {};

  for (const topic in original) {
    if (!current[topic]) {
      // Topic was completely deleted
      deleted[topic] = {
        ...original[topic],
        _deleted: true,
        subtopics: Object.entries(original[topic].subtopics || {}).reduce((acc, [subtopicName, subtopicData]) => {
          acc[subtopicName] = {
            ...subtopicData,
            _deleted: true,
            questions: Object.entries(subtopicData.questions || {}).reduce((qAcc, [questionKey, questionData]) => {
              qAcc[questionKey] = {
                ...questionData,
                _deleted: true,
              };
              return qAcc;
            }, {}),
          };
          return acc;
        }, {}),
      };
      continue;
    }

    const originalSubtopics = original[topic].subtopics || {};
    const currentSubtopics = current[topic].subtopics || {};
    const topicDeleted = { subtopics: {} };
    let hasDeletedItems = false;

    for (const subtopic in originalSubtopics) {
      if (!currentSubtopics[subtopic]) {
        // Subtopic was deleted
        topicDeleted.subtopics[subtopic] = {
          ...originalSubtopics[subtopic],
          _deleted: true,
          questions: Object.entries(originalSubtopics[subtopic].questions || {}).reduce((acc, [questionKey, questionData]) => {
            acc[questionKey] = {
              ...questionData,
              _deleted: true,
            };
            return acc;
          }, {}),
        };
        hasDeletedItems = true;
        continue;
      }

      const originalQuestions = originalSubtopics[subtopic].questions || {};
      const currentQuestions = currentSubtopics[subtopic].questions || {};
      const deletedQuestions = {};
      let hasDeletedQuestions = false;

      for (const question in originalQuestions) {
        if (!currentQuestions[question]) {
          deletedQuestions[question] = {
            ...originalQuestions[question],
            _deleted: true,
          };
          hasDeletedQuestions = true;
        }
      }

      if (hasDeletedQuestions) {
        topicDeleted.subtopics[subtopic] = {
          questions: deletedQuestions,
        };
        hasDeletedItems = true;
      }
    }

    if (hasDeletedItems) {
      deleted[topic] = topicDeleted;
    }
  }

  return deleted;
}

function handleConfirmChanges() {
  showSaveChangesDialog.value = false;
  if (isEditMode.value) {
    updatePlayground();
  } else {
    saveDatabase();
  }
}

/* ---------- generic reorder helper ---------- */
function moveKey(obj, key, delta) {
  const keys = Object.keys(obj);
  const i = keys.indexOf(key);
  const j = i + delta;
  if (i === -1 || j < 0 || j >= keys.length) return obj; // no-op
  keys.splice(i, 1); // remove old
  keys.splice(j, 0, key); // insert new
  return Object.fromEntries(keys.map((k) => [k, obj[k]]));
}

/* ---------- TOPICS ---------- */
function moveTopic(name, delta) {
  knowledgeBaseData.value.knowledge_base = moveKey(knowledgeBaseData.value.knowledge_base, name, delta);
}
function isFirstTopic(name) {
  return Object.keys(knowledgeBaseData.value.knowledge_base)[0] === name;
}
function isLastTopic(name) {
  const k = Object.keys(knowledgeBaseData.value.knowledge_base);
  return k[k.length - 1] === name;
}

/* ---------- SUBTOPICS ---------- */
function moveSub(topic, sub, delta) {
  const t = knowledgeBaseData.value.knowledge_base[topic];
  if (!t) return;
  t.subtopics = moveKey(t.subtopics, sub, delta);
}
function isFirstSub(topic, sub) {
  return Object.keys(knowledgeBaseData.value.knowledge_base[topic].subtopics)[0] === sub;
}
function isLastSub(topic, sub) {
  const k = Object.keys(knowledgeBaseData.value.knowledge_base[topic].subtopics);
  return k[k.length - 1] === sub;
}

/* ---------- QUESTIONS ---------- */
function moveQ(topic, sub, q, delta) {
  const qs = knowledgeBaseData.value.knowledge_base[topic]?.subtopics?.[sub]?.questions;
  if (!qs) return;
  knowledgeBaseData.value.knowledge_base[topic].subtopics[sub].questions = moveKey(qs, q, delta);
}
function isFirstQ(topic, sub, q) {
  return Object.keys(knowledgeBaseData.value.knowledge_base[topic].subtopics[sub].questions)[0] === q;
}
function isLastQ(topic, sub, q) {
  const k = Object.keys(knowledgeBaseData.value.knowledge_base[topic].subtopics[sub].questions);
  return k[k.length - 1] === q;
}




const showExportDialog = ref(false)
const exportFormat     = ref('json')  // 'json' | 'csv' | 'txt'

function exportData(format = 'json') {
  let blob
  let filename = `knowledge_base.${format}`

  if (format === 'json') {
    blob = new Blob(
      [JSON.stringify(knowledgeBaseData.value.knowledge_base, null, 2)],
      { type: 'application/json' }
    )
  } else if (format === 'csv') {
    const rows = []
    for (const [topic, tVal] of Object.entries(knowledgeBaseData.value.knowledge_base)) {
      for (const [sub, sVal] of Object.entries(tVal.subtopics || {})) {
        for (const [q, qObj] of Object.entries(sVal.questions || {})) {
          rows.push(
            [topic, sub, q, (qObj.text || '').replace(/\r?\n/g, ' ')].map(csvEscape).join(',')
          )
        }
      }
    }
    blob = new Blob([rows.join('\n')], { type: 'text/csv' })
  } else { // txt
    let txt = ''
    for (const [topic, tVal] of Object.entries(knowledgeBaseData.value.knowledge_base)) {
      txt += `# ${topic}\n`
      for (const [sub, sVal] of Object.entries(tVal.subtopics || {})) {
        txt += `## ${sub}\n`
        for (const [q, qObj] of Object.entries(sVal.questions || {})) {
          txt += `● ${q}\n${qObj.text || ''}\n\n`
        }
      }
      txt += '\n'
    }
    blob = new Blob([txt], { type: 'text/plain' })
  }

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
  showExportDialog.value = false
}

function csvEscape(val) {
  return /[",\n]/.test(val) ? `"${val.replace(/"/g, '""')}"` : val
}
</script>

<style scoped>
/* Tailwind (или ваши кастомные стили) */
</style>
