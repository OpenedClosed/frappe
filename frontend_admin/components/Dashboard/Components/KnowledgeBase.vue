<template>
  <!-- Full screen container with no overflow -->
  <div class="flex flex-1 flex-col min-h-0 xl:max-h-[90vh] h-full">
    <Toast />
    <!-- Main container -->
    <div class="flex flex-col flex-1 overflow-hidden">
      <!-- Main block: 3 columns -->
      <div class="flex flex-1 flex-row rounded-md overflow-hidden">
        <div class="flex flex-col xl:flex-row flex-1 justify-between overflow-hidden">
          <!-- LEFT COLUMN -->
          <div
            class="flex-0 xl:flex-1 min-w-[60px] max-h-screen flex flex-col bg-white dark:bg-gray-800 rounded-xl overflow-hidden shadow-thicc m-4"
          >
            <section>
              <header
                class="flex items-center justify-between gap-2 px-4 py-3 border-b border-secondaryDark bg-secondaryLight max-h-[60px] h-[60px]"
              >
                <div class="flex items-center gap-2">
                  <i class="pi pi-database text-[14px] 2xl:text-2xl"></i>
                  <h2 class="font-semibold text-[10px] 2xl:text-xl">{{ t("KnowledgeBase.contextSources") }}</h2>
                </div>
                <div class="flex justify-center items-center">
                  <i class="pi pi-info-circle text-base cursor-pointer text-xl" v-tooltip.right="t('KnowledgeBase.contextInfoTip')" />
                </div>
              </header>
              <header class="flex items-center justify-between gap-2 px-4 py-3 border-b border-secondaryDark">
                <!-- поиск -->
                <div class="p-input-icon-left flex-1">
                  <IconField>
                    <InputIcon class="pi pi-search" />
                    <InputText
                      v-model="searchTerm"
                      icon="pi pi-search"
                      :placeholder="t('KnowledgeBase.searchPlaceholder')"
                      class="w-full"
                      v-tooltip.bottom="t('KnowledgeBase.searchTip')"
                    />
                  </IconField>
                </div>

                <!-- добавить -->
                <Button
                  :label="t('KnowledgeBase.addContext')"
                  icon="pi pi-plus"
                  class=""
                  @click="openContextDialog"
                  v-tooltip.bottom="t('KnowledgeBase.addContextTip')"
                />
              </header>

              <div class="flex flex-col gap-4 p-4 h-full max-h-[20vh] overflow-y-auto">
                <div>
                  <!-- compact + regular in one markup — relies only on Tailwind breakpoints -->
                  <ul class="flex flex-col divide-y divide-slate-200">
                    <li
                      v-for="(ctx, idx) in filteredContextList"
                      :key="ctx.id"
                      class="flex items-center justify-between gap-4 py-2 /* a bit tighter vertically */ xl:py-3 /* regular on ≥ 1024 px */"
                    >
                      <!-- Icon -->
                      <div class="flex-shrink-0">
                        <div
                          :class="[
                            'h-8 w-8 rounded-lg 2xl:h-12 2xl:w-12 2xl:rounded-xl flex items-center justify-center',
                            colourFor(ctx.purpose).bg /* bg‑tint */,
                            colourFor(ctx.purpose).text /* icon colour */,
                          ]"
                        >
                          <i :class="[typeIcon(ctx.type), 'text-lg 2xl:text-xl']" />
                        </div>
                      </div>

                      <!-- Title + meta -->
                      <div class="flex-1 flex flex-col justify-between">
                        <p class="font-medium truncate text-[14px] 2xl:text-[17px] leading-5 max-w-[60px] 2xl:max-w-[190px]">
                          {{ ctx.title }}
                        </p>
                        <!-- hide date on really tight widths to keep one‑line height -->
                        <p class="text-[10px] text-slate-500 2xl:text-sm /* ≥640 px */ max-[375px]:hidden /* iPhone‑sized screens only */">
                          {{ formatDate(ctx.created_at) }} · {{ ctx.type.toUpperCase() }}
                        </p>
                      </div>

                      <!-- Actions -->
                      <div class="flex items-center gap-1 2xl:gap-2">
                        <div class="flex flex-col 2xl:flex-row items-center gap-1 2xl:gap-2">
                          <Button
                            v-if="ctx.type === 'file'"
                            icon="pi pi-download text-xs 2xl:text-base"
                            class="p-button-rounded p-button-text p-button-xs 2xl:p-button-sm"
                            @click="downloadContext(ctx)"
                          />
                          <Button
                            icon="pi pi-trash text-xs 2xl:text-base"
                            class="p-button-rounded p-button-text p-button-xs 2xl:p-button-sm"
                            @click="deleteContext(ctx.id)"
                          />
                        </div>
                        <Dropdown
                          v-model="ctx.purpose"
                          :options="contextPurposes"
                          optionLabel="label"
                          optionValue="value"
                          @change="onPurposeChange(ctx, $event.value)"
                          :class="['w-28 2xl:w-60 text-xs 2xl:text-base', colourFor(ctx.purpose).bg, colourFor(ctx.purpose).text]"
                          :pt="{
                            /* internal label inherits the text colour so it stays readable */
                            label: () => ({ class: colourFor(ctx.purpose).text }),
                          }"
                        >
                          <!-- ­­­­OPTION LIST → keep default panel colour, just tint each row -->
                          <template #option="slotProps">
                            <div
                              class="flex justify-between items-center gap-2 px-2 py-1 rounded"
                              :class="[
                                colourFor(slotProps.option.value).bg,
                                colourFor(slotProps.option.value).text,
                                slotProps.selected && 'ring-2 ring-offset-1 ring-current',
                              ]"
                            >
                              <span class="flex items-center gap-2">{{ slotProps.option.label }}</span>
                              <i
                                class="pi pi-info-circle"
                                :class="colourFor(slotProps.option.value).text"
                                v-tooltip.right="slotProps.option.desc"
                              />
                            </div>
                          </template>
                        </Dropdown>
                      </div>
                    </li>
                  </ul>

                  <!-- ================= Dialog ================= -->
                  <Dialog
                    v-model:visible="showContextDialog"
                    :header="t('KnowledgeBase.addContextHeader')"
                    :modal="true"
                    :closable="true"
                    :style="{ width: '40vw' }"
                  >
                    <div class="flex flex-col gap-4">
                      <!-- ░░ TYPE SELECTOR ░░ -->
                      <div class="flex rounded-md overflow-hidden border border-gray-300 dark:border-gray-600">
                        <button
                          v-for="tab in ctxTabs"
                          :key="tab.value"
                          @click="newCtx.type = tab.value"
                          class="flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium transition-colors"
                          :class="[
                            newCtx.type === tab.value
                              ? 'bg-gray-900 text-white dark:bg-gray-200 dark:text-gray-900'
                              : 'bg-white text-gray-700 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700',
                          ]"
                        >
                          <i :class="tab.icon"></i>
                          <span>{{ tab.label }}</span>
                        </button>
                      </div>
                      <!-- OPTIONAL TITLE (always shown) -->
                      <InputText v-model="newCtx.title" class="w-full" :placeholder="t('KnowledgeBase.titlePlaceholder')" />
                      <!-- ░░ DYNAMIC FIELDS ░░ -->
                      <!-- TEXT -->
                      <Textarea
                        v-if="newCtx.type === 'text'"
                        v-model="newCtx.text"
                        rows="6"
                        class="w-full max-h-[40vh]"
                        :placeholder="t('KnowledgeBase.pasteTextPlaceholder')"
                      />

                      <!-- SITE / URL -->
                      <InputText v-else-if="newCtx.type === 'url'" v-model="newCtx.url" class="w-full" placeholder="https://example.com" />

                      <!-- FILE -->
                      <!-- FILE -->
                      <div v-else-if="newCtx.type === 'file'">
                        <FileUpload
                          ref="fileUpload"
                          name="file"
                          mode="advanced"
                          dragDrop
                          :customUpload="true"
                          :auto="false"
                          :showUploadButton="false"
                          :showChooseButton="false"
                          :showCancelButton="false"
                          :accept="acceptedTypes"
                          @select="onCtxFileSelect"
                        >
                          <!-- custom empty state -->
                          <template #header>
                            <span></span>
                          </template>
                          <template #empty>
                            <div
                              class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition"
                              @click="fileUpload.choose"
                            >
                              <i class="pi pi-cloud-upload text-5xl text-gray-400 mb-4"></i>
                              <h3 class="text-lg font-medium mb-1">{{ t("KnowledgeBase.uploadHeader") }}</h3>
                              <p class="text-sm text-gray-500 mb-2">{{ t("KnowledgeBase.uploadSub") }}</p>
                              <p class="text-xs text-gray-400">{{ t("KnowledgeBase.uploadTypes") }}</p>
                            </div>
                          </template>
                        </FileUpload>
                        <p v-if="newCtx.file" class="text-sm mt-2 italic">
                          {{ newCtx.file.name }} – {{ newCtx.file.size.toLocaleString() }} bytes
                        </p>
                      </div>

                      <!-- ░░ ACTIONS ░░ -->
                      <div class="flex justify-between items-center gap-2 mt-4">
                        <span>{{ t("KnowledgeBase.totalSources") }} {{ totalSources }}/{{ MAX_SOURCES }}</span>
                        <div class="flex items-center gap-2">
                          <Button :label="t('KnowledgeBase.dialogCancel')" class="p-button-text" @click="showContextDialog = false" />
                          <Button
                            :label="t('KnowledgeBase.dialogCancel')"
                            icon="pi pi-check"
                            class="p-button-success"
                            :disabled="!canSubmitContext"
                            @click="submitContext"
                          />
                        </div>
                      </div>
                    </div>
                  </Dialog>
                </div>
              </div>
            </section>
            <!-- Context source count display -->
            <header
              class="flex items-center justify-between px-4 py-2 text-[15px] font-medium bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border-t border-secondaryDark"
            >
              <span>{{ t("KnowledgeBase.totalSources") }} {{ totalSources }}/{{ MAX_SOURCES }}</span>
              <span> {{ t("KnowledgeBase.selectedSources") }} {{ selectedSources }}</span>
            </header>

            <section class="flex flex-col flex-1 overflow-y-auto">
              <header
                class="flex items-center justify-between gap-2 px-4 py-3 border-y border-secondaryDark bg-secondaryLight dark:bg-secondaryDark max-h-[60px] h-[60px] 2xl:h-[60px]"
              >
                <div class="flex items-center gap-2">
                  <i class="pi pi-pencil text-sm 2xl:text-2xl"></i>
                  <h2 class="font-semibold text-sm 2xl:text-xl">{{ t("KnowledgeBase.queryField") }}</h2>
                </div>
                <div class="flex justify-center items-center gap-2">
                  <Dropdown
                    v-model="selectedModel"
                    :options="aiModels"
                    optionLabel="label"
                    optionValue="value"
                    class="w-full text-sm 2xl:text-xl"
                    :placeholder="t('KnowledgeBase.aiModelPlaceholder')"
                  />
                  <i class="pi pi-info-circle text-base cursor-pointer text-xl" v-tooltip.right="t('KnowledgeBase.queryFieldTip')" />
                </div>
              </header>
              <div class="flex flex-col p-4 h-full gap-2">
                <!-- FORM with generatePatch submit handler -->
                <!-- Request History section styled like the design -->
                <section class="bg-white dark:bg-gray-900 rounded-xl shadow-md border border-gray-200 dark:border-gray-700 p-2">
                  <header class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2">
                      <h2 class="text-base font-semibold text-gray-800 dark:text-gray-100">{{ t("KnowledgeBase.requestHistory") }}</h2>
                    </div>
                    <button type="button" class="self-start text-red-600 text-sm underline" @click="clearRequestHistory">
                      {{ t("KnowledgeBase.clearHistory") }}
                    </button>
                  </header>

                  <div v-if="requestHistory.length" class="flex flex-col gap-2 max-h-[12vh] overflow-y-auto">
                    <button
                      v-for="(item, index) in requestHistory"
                      :key="index"
                      type="button"
                      class="text-sm text-left px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition"
                      @click="reuseRequest(item)"
                      v-tooltip.bottom="t('KnowledgeBase.reuseTip')"
                    >
                      {{ item.length > 40 ? item.slice(0, 40) + "…" : item }}
                    </button>
                  </div>
                  <div v-else class="text-sm text-gray-500 dark:text-gray-400">{{ t("KnowledgeBase.noHistory") }}</div>
                </section>

                <form @submit.prevent="generatePatch" class="flex flex-col flex-grow min-h-0 gap-2">
                  <!-- GENERATE SMART CHANGE BUTTON -->

                  <!-- TEXTAREA -->
                  <div class="flex flex-row gap-1 justify-center items-center">
                    <Textarea
                      autoResize
                      id="promptTextArea"
                      class="w-full"
                      :placeholder="t('KnowledgeBase.typeHere')"
                      required
                      v-model="promptText"
                      size="small"
                      v-tooltip.bottom="t('KnowledgeBase.typeHereTip')"
                    />
                    <Button
                      type="submit"
                      :disabled="isLoading"
                      icon="pi pi-send"
                      class="w-full flex justify-center items-center min-h-[37px] max-h-[37px] max-w-[37px] p-button-sm"
                    >
                      <LoaderSmall v-if="isLoading" />
                    </Button>
                  </div>
                </form>
              </div>
            </section>
          </div>

          <!-- CENTER COLUMN -->
          <div
            class="flex-0 xl:flex-1 min-w-[60px] max-h-screen flex flex-col bg-white dark:bg-gray-800 rounded-xl shadow-thicc m-4 max-h-full"
          >
            <section class="rounded-xl flex flex-col flex-1 overflow-hidden">
              <header
                class="flex items-center justify-between gap-2 px-4 py-3 border-b border-secondaryDark bg-secondaryLight max-h-[60px] h-[60px]"
              >
                <div class="flex items-center gap-2">
                  <i class="pi pi-sliders-h text-[14px] 2xl:text-2xl"></i>
                  <h2 class="font-semibold text-[8px] 2xl:text-xl">{{ t("KnowledgeBase.playgroundHeader") }}</h2>
                </div>

                <div class="flex justify-center items-center gap-4">
                  <div class="flex flex-row gap-2">
                    <!-- Review-changes button -->
                    <Button class="p-button-sm flex items-center justify-center gap-2 max-h-[37px]" @click="reviewChanges">
                      <div v-if="!isLoading" class="flex items-center">
                        <i class="pi pi-eye"></i>

                        <Badge :value="changesTotal" severity="info" class="ml-2" />
                      </div>
                      <LoaderSmall v-else />
                    </Button>

                    <Button v-if="!isEditMode" icon="pi pi-pencil" class="p-button-sm" @click="toggleEditMode" />
                    <Button :disabled="isLoading" icon="pi pi-trash" class="p-button-sm" @click="clearPlayground" />
                    <Button
                      v-if="isEditMode"
                      :label="t('KnowledgeBase.addTopic')"
                      icon="pi pi-plus"
                      class="p-button-sm"
                      @click="addTopic"
                    />
                  </div>
                  <i class="pi pi-info-circle text-base cursor-pointer text-xl" v-tooltip.right="t('KnowledgeBase.addTopicDesc')" />
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
                          v-tooltip.right="t('KnowledgeBase.topicTooltip')"
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
                        <Button
                          :label="t('KnowledgeBase.addSubtopic')"
                          icon="pi pi-plus"
                          class="p-button-sm"
                          @click="addSubtopic(topicName)"
                        />
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
                            v-tooltip.right="t('KnowledgeBase.subtopicTooltip')"
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
                            :label="t('KnowledgeBase.addQuestion')"
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
                              <label class="font-semibold"> {{ t("KnowledgeBase.questionLabel") }}</label>
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

                            <Textarea
                              :modelValue="questionKey"
                              :placeholder="questionKey"
                              class="block w-full mb-2 min-h-[50px] border rounded p-2 text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700"
                              @blur="renameQuestion(topicName, subtopicName, questionKey, $event.target.value)"
                              v-tooltip.right="t('KnowledgeBase.questionTooltip')"
                            />

                            <!-- ANSWER TEXT -->
                            <label class="font-semibold">{{ t("KnowledgeBase.answerTextLabel") }}</label>
                            <Textarea
                              v-model="questionObj.text"
                              class="block w-full border rounded p-2 min-h-[100px] text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 mb-2"
                              v-tooltip.right="t('KnowledgeBase.answerTooltip')"
                            />

                            <!-- LINKS / FILES -->
                            <label class="font-semibold">{{ t("KnowledgeBase.linksFilesLabel") }}</label>
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
                              <h3>{{ t("KnowledgeBase.selectedFilesLabel") }}</h3>
                              <ul>
                                <li v-for="(file, idx) in localFiles" :key="idx">{{ file.name }} - {{ file.size }} bytes</li>
                              </ul>
                            </div>

                            <Button
                              :label="t('KnowledgeBase.addLink')"
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
                  <h3 class="text-2xl font-semibold text-gray-500 dark:text-gray-300 mb-2">{{ t("KnowledgeBase.playgroundEmpty") }}</h3>
                  <!-- подпись -->
                  <p class="text-gray-500 dark:text-gray-400 mb-6 max-w-md">
                    {{ t("KnowledgeBase.playgroundEmptyBody") }}
                  </p>
                  <!-- кнопка -->
                  <Button
                    :label="t('KnowledgeBase.createBlock')"
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
                <div class="flex flex-row justify-between gap-2 my-2">
                  <Button
                    :disabled="isLoading"
                    :label="t('KnowledgeBase.reject')"
                    icon="pi pi-times"
                    class="p-button-sm flex-1 bg-gray-100 text-black hover:bg-gray-300"
                    @click="rejectPlayground"
                  />
                  <Button
                    :disabled="isLoading || !isEditMode"
                    :label="t('KnowledgeBase.save')"
                    icon="pi pi-save"
                    class="p-button-sm flex-1"
                    @click="savePlayground"
                    v-tooltip.bottom="t('KnowledgeBase.saveDesc')"
                  />

                  <Button
                    :disabled="(isLoading || !hasChanges) && isEditMode"
                    :label="t('KnowledgeBase.publish')"
                    icon="pi pi-save"
                    class="p-button-sm flex-1"
                    @click="saveChanges"
                    v-tooltip.bottom="t('KnowledgeBase.publishDesc')"
                  />
                </div>
              </div>
            </section>
          </div>

          <!-- RIGHT COLUMN (Readonly Copy) -->
          <div
            class="flex-0 xl:flex-1 min-w-[60px] max-h-screen flex flex-col bg-white dark:bg-gray-800 rounded-xl shadow-thicc m-4 max-h-full"
          >
            <section class="rounded-xl flex flex-col flex-1 overflow-hidden">
              <header
                class="flex items-center justify-between gap-2 px-4 py-3 border-b border-secondaryDark bg-secondaryLight max-h-[60px] h-[60px]"
              >
                <div class="flex items-center gap-2">
                  <i class="pi pi-book text-[14px] 2xl:text-2xl"></i>
                  <h2 class="font-semibold text-[10px] 2xl:text-xl">{{ t("KnowledgeBase.knowledgeBase") }}</h2>
                </div>
                <div class="flex justify-center items-center gap-4">
                  <!-- 🔍 search toggle -->
                  <!-- 🔍 search toggle -->
                  <Button icon="pi pi-search text-xl" class="p-button-text p-button-rounded p-button-sm" @click="toggleReadonlySearch" />
                  <i class="pi pi-info-circle text-base cursor-pointer text-xl" v-tooltip="t('KnowledgeBase.knowledgeBaseDesc')" />
                </div>
              </header>
              <div v-if="showReadonlySearch" class="px-4 py-3 bg-secondaryLight border-b border-secondaryDark flex items-center gap-2">
                <InputText
                  ref="readonlySearchInput"
                  v-model="readonlySearchTerm"
                  :placeholder="t('KnowledgeBase.searchKbPlaceholder')"
                  class="flex-1 w-full"
                >
                </InputText>
                <Button icon="pi pi-times" class="p-button-text p-button-rounded p-button-sm" @click="resetReadonlySearch" />
              </div>
              <div class="flex-1 overflow-y-auto p-4">
                <div v-for="(topicValue, topicName) in filteredReadonlyData" :key="topicName" class="mb-6">
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
              <div class="flex flex-row justify-between gap-2 p-4 my-2">
                <Button
                  :label="t('KnowledgeBase.export')"
                  icon="pi pi-file-export"
                  class="p-button-sm flex-1 bg-gray-100 text-black hover:bg-gray-300"
                  @click="showExportDialog = true"
                />

                <AdminChat class="flex-1" />
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>

    <!-- 💾 Export-format picker -->
    <Dialog v-model:visible="showExportDialog" :header="t('KnowledgeBase.exportDialogTitle')" :modal="true" :style="{ width: '25rem' }">
      <div class="flex flex-col gap-4 pt-2">
        <div class="flex items-center justify-center gap-3">
          <RadioButton v-model="exportFormat" inputId="exp-json" value="json" />
          <label for="exp-json" class="cursor-pointer flex-1">
            <p class="font-semibold">{{ t("KnowledgeBase.exportJson") }}</p>
            <p class="text-sm text-gray-500">{{ t("KnowledgeBase.exportJsonDesc") }}</p>
          </label>
        </div>

        <div class="flex items-center justify-center gap-3">
          <RadioButton v-model="exportFormat" inputId="exp-csv" value="csv" />
          <label for="exp-csv" class="cursor-pointer flex-1">
            <p class="font-semibold">{{ t("KnowledgeBase.exportCsv") }}</p>
            <p class="text-sm text-gray-500">{{ t("KnowledgeBase.exportCsvDesc") }}</p>
          </label>
        </div>

        <div class="flex items-center justify-center gap-3">
          <RadioButton v-model="exportFormat" inputId="exp-txt" value="txt" />
          <label for="exp-txt" class="cursor-pointer flex-1">
            <p class="font-semibold">{{ t("KnowledgeBase.exportTxt") }}</p>
            <p class="text-sm text-gray-500">{{ t("KnowledgeBase.exportTxtDesc") }}</p>
          </label>
        </div>
      </div>

      <template #footer>
        <Button :label="t('KnowledgeBase.exportCancel')" class="p-button-text" @click="showExportDialog = false" />
        <Button label="Export" icon="pi pi-download" @click="exportData(exportFormat)" />
      </template>
    </Dialog>
    <!-- INSTRUCTIONS DIALOG -->
    <!-- <Dialog v-model:visible="showInstructions" :header="'How to use this tool?'" :modal="true" :closable="true" :style="{ width: '50vw' }">
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
    </Dialog> -->

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
  </div>
</template>

<script setup>
import { ref, Text } from "vue";
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

import AdminChat from "~/components/AdminChat.vue";

const reviewOnly = ref(false);
/* ---------- контекст ---------- */
const contextList = ref([]); // список
const showContextDialog = ref(false); // диалог

const ctxMenu = ref(null); // ссылка на меню
const selectedCtx = ref(null); // «активный» ctx

const searchTerm = ref("");

/* 🔎 filtered list */
const filteredContextList = computed(() =>
  contextList.value.filter((c) => {
    if (!searchTerm.value.trim()) return true;
    const s = searchTerm.value.toLowerCase();
    return (c.title && c.title.toLowerCase().includes(s)) || (c.type && c.type.toLowerCase().includes(s));
  })
);

/* открыть меню */
function openCtxMenu(ctx, event) {
  selectedCtx.value = ctx; // запоминаем, над кем кликнули
  ctxMenu.value.toggle(event); // показываем TieredMenu
}
async function renameContext(ctx) {
  if (!ctx) return;
  const newTitle = prompt(t("KnowledgeBase.ctxRenamePrompt"), ctx.title);
  if (!newTitle || newTitle === ctx.title) return;
  try {
    const form = new FormData();
    form.append("title", newTitle);
    await useNuxtApp().$api.patch(`/api/knowledge/context_entity/${ctx.id}/rename`, form);
    ctx.title = newTitle;
    showSuccess(t("KnowledgeBase.ctxRenamed"));
  } catch (e) {
    showError(t("KnowledgeBase.ctxNotRenamed"));
  }
}

const formatDate = (d) => new Intl.DateTimeFormat("ru-RU").format(new Date(d));

const formatSize = (bytes) => (bytes / (1024 * 1024)).toFixed(1) + " MB";

const purposeLabel = (v) => (contextPurposes.find((o) => o.value === v) || {}).label || v;

const typeIcon = (t) => {
  switch (t) {
    case "text":
      return "pi pi-pencil";
    case "file":
      return "pi pi-file";
    case "qa":
      return "pi pi-question";
    case "url":
      return "pi pi-globe";
    default:
      return "pi pi-file";
  }
};

const contextPurposes = [
  {
    label: t("KnowledgeBase.purposeNone"),
    value: "none",
    desc: t("KnowledgeBase.purposeNoneDesc"),
  },
  {
    label: t("KnowledgeBase.purposeBot"),
    value: "bot",
    desc: t("KnowledgeBase.purposeBotDesc"),
  },
  {
    label: t("KnowledgeBase.purposeKb"),
    value: "kb",
    desc: t("KnowledgeBase.purposeKbDesc"),
  },
  {
    label: t("KnowledgeBase.purposeBoth"),
    value: "both",
    desc: t("KnowledgeBase.purposeBothDesc"),
  },
];
/* light + dark palette for the “source purpose” dropdown */
const purposeColours = {
  bot: { bg: "bg-green-100  dark:bg-green-900/40", text: "text-green-600  dark:text-green-300" },
  kb: { bg: "bg-blue-100   dark:bg-blue-900/40", text: "text-blue-600   dark:text-blue-300" },
  both: { bg: "bg-purple-100 dark:bg-purple-900/40", text: "text-purple-600 dark:text-purple-300" },
  none: { bg: "bg-gray-50    dark:bg-gray-700", text: "text-gray-500   dark:text-gray-300" },
};

/* unchanged helper */
const colourFor = (value) => purposeColours[value] || purposeColours.none;

// данные формы добавления
const newCtx = ref({
  type: "file", // 👈 default = Files
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
    showSuccess(t("KnowledgeBase.ctxPurposeUpdated"));
  } catch (_) {
    ctx.purpose = prev; // откат при ошибке
    showError(t("KnowledgeBase.ctxPurposeNotUpdated"));
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

/* ---------- API ----------- */
async function fetchContextUnits() {
  try {
    const { data } = await useNuxtApp().$api.get("/api/knowledge/context_entity");
    console.log("contextList= ", data);
    contextList.value = data;
  } catch (_) {
    showError(t("KnowledgeBase.ctxLoadErr"));
  }
}

const MAX_SOURCES = 50;

const totalSources = computed(() => contextList.value.length);
const selectedSources = computed(() => contextList.value.filter((c) => c.purpose !== "none").length);

const ctxTabs = [
  { label: "Files", value: "file", icon: "pi pi-upload" },
  { label: "Site", value: "url", icon: "pi pi-link" },
  { label: "Text", value: "text", icon: "pi pi-file" },
];

// Prevent opening dialog if limit is reached
function openContextDialog() {
  if (totalSources.value >= MAX_SOURCES) {
    showError(t("KnowledgeBase.ctxAddMax", { max: MAX_SOURCES }));
    return;
  }
  Object.assign(newCtx, { type: "", title: "", text: "", url: "", file: null });
  showContextDialog.value = true;
}

const fileUpload = ref(null);

const acceptedTypes = [
  "application/pdf",
  "text/plain",
  "text/markdown",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "image/*",
].join(",");

function onCtxFileSelect(event) {
  // event.files is an Array of File objects
  newCtx.value.file = event.files[0] || null;
}
const canSubmitContext = computed(() => {
  if (newCtx.value.type === "text") return newCtx.value.text.trim();
  if (newCtx.value.type === "url") return newCtx.value.url.trim();
  if (newCtx.value.type === "file") return newCtx.value.file;
  return false;
});

async function submitContext() {
  try {
    const form = new FormData();
    form.append("type", newCtx.value.type);
    form.append("purpose", "none");
    if (newCtx.value.title) form.append("title", newCtx.value.title);

    if (newCtx.value.type === "text") form.append("text", newCtx.value.text);
    if (newCtx.value.type === "url") form.append("url", newCtx.value.url);
    if (newCtx.value.type === "file" && newCtx.value.file) form.append("file", newCtx.value.file, newCtx.value.file.name);

    console.log("form= ", ...form);
    await useNuxtApp().$api.post("/api/knowledge/context_entity", form);
    showSuccess(t("KnowledgeBase.ctxAdded"));
    /* ──── 🔽  CLEAR THE FORM ──── */
    Object.assign(newCtx.value, {
      type: "file", // default tab
      title: "",
      text: "",
      url: "",
      file: null,
    });
    fileUpload.value?.clear(); // wipe PrimeVue FileUpload preview
    /* ─────────────────────────── */

    showContextDialog.value = false;
    fetchContextUnits();
  } catch (_) {
    showError(t("KnowledgeBase.ctxNotAdded"));
  }
}

async function deleteContext(id) {
  if (!confirm(t("KnowledgeBase.menuDelete") + "?")) return;
  try {
    await useNuxtApp().$api.delete(`/api/knowledge/context_entity/${id}`);
    contextList.value = contextList.value.filter((c) => c.id !== id);
    showSuccess(t("KnowledgeBase.ctxDeleted"));
  } catch (_) {
    showError(t("KnowledgeBase.ctxNotDeleted"));
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
const { currentFrontendUrl, currentUrl } = useURLState();

function downloadContext(ctx) {
  if (!ctx || ctx.type !== "file" || !ctx.file_path) return;

  // Extract relative path after "/files/context/"
  const match = ctx.file_path.match(/\/files\/context\/.+$/);
  if (!match) return;

  const fileRelativePath = match[0]; // "/files/context/..."
  const fileName = ctx.file_path.split("/").pop();

  const downloadUrl = `${currentUrl.value}${fileRelativePath}`;

  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = fileName;
  a.target = "_blank";
  a.click();
}

/* ▼ NEW state */
const readonlySearchTerm = ref("");
const showReadonlySearch = ref(false);
const readonlySearchInput = ref(null);

/* ▼ Toggle + autofocus helper */
function toggleReadonlySearch() {
  showReadonlySearch.value = !showReadonlySearch.value;
  if (showReadonlySearch.value) {
    nextTick(() => readonlySearchInput.value?.focus());
  } else {
    readonlySearchTerm.value = ""; // clear when closing
  }
}

/* ▼ Filtered readonly copy */
const filteredReadonlyData = computed(() => {
  const src = readonlyData.value.knowledge_base;
  const q = readonlySearchTerm.value.trim().toLowerCase();
  if (!q) return src;

  const out = {};
  for (const [topic, tVal] of Object.entries(src)) {
    let topicMatch = topic.toLowerCase().includes(q);
    const subOut = {};

    for (const [sub, sVal] of Object.entries(tVal.subtopics || {})) {
      let subMatch = sub.toLowerCase().includes(q);
      const qsOut = {};

      for (const [qKey, qObj] of Object.entries(sVal.questions || {})) {
        const text = `${qKey} ${qObj.text || ""}`.toLowerCase();
        if (text.includes(q)) qsOut[qKey] = qObj;
      }

      if (subMatch || Object.keys(qsOut).length) {
        subOut[sub] = { ...sVal, questions: Object.keys(qsOut).length ? qsOut : sVal.questions };
      }
    }

    if (topicMatch || Object.keys(subOut).length) {
      out[topic] = { ...tVal, subtopics: Object.keys(subOut).length ? subOut : tVal.subtopics };
    }
  }
  return out;
});

function resetReadonlySearch() {
  readonlySearchTerm.value = "";
  nextTick(() => readonlySearchInput.value?.focus());
}
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

  // Clone and update the questions object
  const updatedQuestions = { ...subtopic.questions };
  updatedQuestions[newQuestion] = updatedQuestions[oldQuestion];
  delete updatedQuestions[oldQuestion];

  // Assign the updated object to trigger reactivity
  console.log("updatedQuestions= ", updatedQuestions);
  knowledgeBaseData.value.knowledge_base[topicName].subtopics[subtopicName].questions = updatedQuestions;
  console.log("knowledgeBaseData= ", knowledgeBaseData.value.knowledge_base[topicName].subtopics[subtopicName].questions);
  // Update the renaming map
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
  topicAdded;
  showSuccess(t("knowledgeBase.topicAdded"));
}

// Удалить тему
function removeTopic(topicName) {
  if (confirm(t("knowledgeBase.removeTopic", { topicName }))) {
    countDeletedItemsFromTopic(topicName);

    delete knowledgeBaseData.value.knowledge_base[topicName];
    showSuccess(t("knowledgeBase.subtopicRemoved"));
  } else {
    showError(t("knowledgeBase.subtopicNotRemoved"));
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
  showSuccess(t("knowledgeBase.subtopicAdded"));
}

// Удалить подтему
function removeSubtopic(topicName, subtopicName) {
  if (confirm(t("knowledgeBase.removeSubtopic", { subtopicName, topicName }))) {
    const topic = knowledgeBaseData.value.knowledge_base[topicName];
    if (topic && topic.subtopics[subtopicName]) {
      countDeletedItemsFromSubtopic(topicName, subtopicName, topic);

      delete topic.subtopics[subtopicName];
      showSuccess(t("knowledgeBase.subtopicRemoved"));
    } else {
      showError(t("knowledgeBase.subtopicNotRemoved"));
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
  showSuccess(t("knowledgeBase.questionAdded"));
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

  showSuccess(t("knowledgeBase.fileAdded"));
}

function removeQuestionFile(topicName, subtopicName, question, fileIndex) {
  const questionObj = knowledgeBaseData.value.knowledge_base[topicName].subtopics[subtopicName].questions[question];
  if (questionObj?.files) {
    questionObj.files.splice(fileIndex, 1);
  }
  showSuccess(t("knowledgeBase.fileRemoved"));
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
  showSuccess(t("knowledgeBase.questionUpdated"));
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
    showSuccess(t("knowledgeBase.questionRemoved"));
  } else {
    showError(t("knowledgeBase.questionNotRemoved"));
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
    console.log(t("knowledgeBase.noChanges"));
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
    showSuccess(t("KnowledgeBase.msgPlaygroundUpdated"));
  } catch (error) {
    console.error(t("KnowledgeBase.msgPlaygroundUpdateErr"), error);
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
      showSuccess(t("KnowledgeBase.msgDbSaved"));
    }
  } catch (error) {
    console.error("Ошибка при обновлении базы знаний:", error);
    showError(t("KnowledgeBase.msgDbSaveErr"));
  }
}

function clearPlayground() {
  if (confirm(t("KnowledgeBase.confirmClear"))) {
    countDeletedItems();
    knowledgeBaseData.value.knowledge_base = {};
    calculateChanges();

    showSuccess(t("KnowledgeBase.msgPlaygroundCleared"));
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
  const confirmation = confirm(t("KnowledgeBase.confirmReject"));
  if (!confirmation) return;

  isEditMode.value = false;

  clearVariables();

  knowledgeBaseData.value.knowledge_base = cloneDeep(readonlyData.value.knowledge_base);
  showSuccess(t("KnowledgeBase.msgPlaygroundRejected"));
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
    rememberRequest(promptText.value);

    // handle success
    updatePlayground(response.data);
    showSuccess(t("KnowledgeBase.msgPatchGenerated"));
  } catch (error) {
    // handle error
    showError(t("KnowledgeBase.msgPatchErr"));
  } finally {
    isLoading.value = false;
  }
}

// Request history: LocalStorage-based
const REQUEST_HISTORY_KEY = "kb_request_history";
const requestHistory = ref(JSON.parse(localStorage.getItem(REQUEST_HISTORY_KEY) || "[]"));

// Save to localStorage whenever it changes
watch(
  requestHistory,
  (h) => {
    localStorage.setItem(REQUEST_HISTORY_KEY, JSON.stringify(h));
  },
  { deep: true }
);

// Remember a new request
function rememberRequest(text) {
  const v = text.trim();
  if (!v) return;
  requestHistory.value = [v, ...requestHistory.value.filter((i) => i !== v)].slice(0, 20);
}

// Reuse a request into the textarea
function reuseRequest(text) {
  promptText.value = text;
  nextTick(() => {
    document.getElementById("promptTextArea")?.focus();
  });
}

// Clear all history
function clearRequestHistory() {
  requestHistory.value = [];
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

const showExportDialog = ref(false);
const exportFormat = ref("json"); // 'json' | 'csv' | 'txt'

function exportData(format = "json") {
  let blob;
  let filename = `knowledge_base.${format}`;

  if (format === "json") {
    blob = new Blob([JSON.stringify(knowledgeBaseData.value.knowledge_base, null, 2)], { type: "application/json" });
  } else if (format === "csv") {
    const rows = [];
    for (const [topic, tVal] of Object.entries(knowledgeBaseData.value.knowledge_base)) {
      for (const [sub, sVal] of Object.entries(tVal.subtopics || {})) {
        for (const [q, qObj] of Object.entries(sVal.questions || {})) {
          rows.push([topic, sub, q, (qObj.text || "").replace(/\r?\n/g, " ")].map(csvEscape).join(","));
        }
      }
    }
    blob = new Blob([rows.join("\n")], { type: "text/csv" });
  } else {
    // txt
    let txt = "";
    for (const [topic, tVal] of Object.entries(knowledgeBaseData.value.knowledge_base)) {
      txt += `# ${topic}\n`;
      for (const [sub, sVal] of Object.entries(tVal.subtopics || {})) {
        txt += `## ${sub}\n`;
        for (const [q, qObj] of Object.entries(sVal.questions || {})) {
          txt += `● ${q}\n${qObj.text || ""}\n\n`;
        }
      }
      txt += "\n";
    }
    blob = new Blob([txt], { type: "text/plain" });
  }

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
  showExportDialog.value = false;
}

function csvEscape(val) {
  return /[",\n]/.test(val) ? `"${val.replace(/"/g, '""')}"` : val;
}
</script>

<style >
.p-fileupload .p-badge {
  display: none !important;
}
.p-fileupload-file .p-fileupload-file-thumbnail {
  display: none !important;
}
</style>
