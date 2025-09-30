<template>
  <Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    :modal="true"
    :dismissableMask="true"
    :header="
      reviewOnly
        ? t('SaveChangesDialog.header.preview')
        : isEditMode
        ? t('SaveChangesDialog.header.savePlayground')
        : t('SaveChangesDialog.header.saveKnowledgeBase')
    "
    class="w-1/2 max-w-4xl min-w-96"
  >
    <!-- ──────────── info text ────────────-->
    <p class="mb-4 text-sm text-gray-600">
      {{
        reviewOnly
          ? ''
          : !isEditMode && !hasChanges
          ? t('SaveChangesDialog.info.noChanges')
          : isEditMode
          ? t('SaveChangesDialog.info.editModeNote')
          : t('SaveChangesDialog.info.applyKb')
      }}
    </p>

    <!-- ──────────── counters & diff ────────────-->
    <div class="p-4">
      <div class="flex flex-row justify-between items-center mb-4">
        <div class="flex items-center gap-4">
          <div><span class="font-bold text-green-600">{{ t('SaveChangesDialog.labels.added') }}</span> {{ changes.added }}</div>
          <div><span class="font-bold text-blue-600">{{t('SaveChangesDialog.labels.changed')}}</span> {{ changes.changed }}</div>
          <div><span class="font-bold text-red-600">{{t('SaveChangesDialog.labels.deleted')}}</span> {{ changes.deleted }}</div>
        </div>
      </div>

      <div v-if="changes.added > 0" class="mb-6">
        <h3 class="font-semibold text-green-900 dark:text-gray-200">
          {{t('SaveChangesDialog.labels.addedItems')}}
        </h3>

        <div
          v-for="(topicValue, topicName) in addedItems"
          :key="topicName"
          class="mb-6"
        >
          <h3
            class="font-semibold text-gray-900 dark:text-gray-200"
            :class="{ 'text-green-600': topicValue._new }"
          >
            {{ topicName }}
          </h3>
          <div v-if="topicValue.subtopics">
            <div
              v-for="(subtopicValue, subtopicName) in topicValue.subtopics"
              :key="subtopicName"
              class="ml-4 mb-4"
            >
              <h4
                class="font-medium text-gray-800 dark:text-gray-300"
                :class="{ 'text-green-600': subtopicValue._new }"
              >
                {{ subtopicName }}
              </h4>
              <ul
                v-if="subtopicValue.questions"
                class="ml-4 list-disc text-sm text-gray-700 dark:text-gray-400"
              >
                <li
                  v-for="(qObj, questionKey) in subtopicValue.questions"
                  :key="questionKey"
                  class="mb-4"
                >
                  <div :class="{ 'text-green-600': qObj._new }">
                    <span class="font-semibold">{{ questionKey }}: </span>
                    <span>{{ qObj.text }}</span>
                  </div>
                  <div v-if="qObj.files && qObj.files.length" class="mt-2 ml-2">
                    <div
                      v-for="(fileLink, fileIndex) in qObj.files"
                      :key="fileIndex"
                      class="mb-1"
                    >
                      <ImageLink :fileLink="fileLink" />
                    </div>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div v-if="changes.changed > 0" class="mb-6">
        <h3 class="font-semibold text-gray-900 dark:text-gray-200">
          {{t('SaveChangesDialog.labels.changedItems')}}
        </h3>
        <div
          v-for="(topicValue, topicName) in changedItems"
          :key="topicName"
          class="mb-6"
        >
          <h3
            class="font-semibold text-gray-900 dark:text-gray-200"
            :class="{ '!text-blue-600': topicValue._changed }"
          >
            {{ topicName }}
          </h3>
          <div v-if="topicValue.subtopics">
            <div
              v-for="(subtopicValue, subtopicName) in topicValue.subtopics"
              :key="subtopicName"
              class="ml-4 mb-4"
            >
              <h4
                class="font-medium text-gray-800 dark:text-gray-300"
                :class="{ '!text-blue-600': subtopicValue._changed }"
              >
                {{ subtopicName }}
              </h4>
              <ul
                v-if="subtopicValue.questions"
                class="ml-4 list-disc text-sm text-gray-700 dark:text-gray-400"
              >
                <li
                  v-for="(qObj, questionKey) in subtopicValue.questions"
                  :key="questionKey"
                  class="mb-4"
                >
                  <div>
                    <span
                      class="font-semibold"
                      :class="{ '!text-blue-600': qObj._changed }"
                      >{{ questionKey }}</span
                    >
                    <template
                      v-if="
                        qObj._previous &&
                        qObj._previous.text !== qObj._current.text
                      "
                    >
                      <div class="line-through text-red-600">
                        {{ qObj._previous.text }}
                      </div>
                      <div class="text-green-600">
                        {{ qObj._current.text }}
                      </div>
                    </template>
                    <template v-else>
                      <div class="text-gray-900 dark:text-gray-200">
                        {{ qObj.text }}
                      </div>
                    </template>
                    <template
                      v-if="
                        qObj._previous &&
                        qObj._previous.files?.join(', ') !==
                          qObj._current.files?.join(', ')
                      "
                    >
                      <div
                        v-if="qObj._previous.files?.length"
                        class="line-through text-red-600 break-all"
                      >
                        {{ qObj._previous.files.join(", ") }}
                      </div>
                      <div
                        v-if="qObj._current.files?.length"
                        class="text-green-600 break-all"
                      >
                        {{ qObj._current.files.join(", ") }}
                      </div>
                    </template>
                    <template v-else>
                      <div
                        v-if="qObj.files?.length"
                        class="text-gray-900 dark:text-gray-200 break-all"
                      >
                        {{ qObj.files.join(", ") }}
                      </div>
                    </template>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div v-if="changes.deleted > 0" class="mb-6">
        <h3 class="font-semibold text-gray-900 dark:text-gray-200">
        {{t('SaveChangesDialog.labels.deletedItems')}}
        </h3>

        <div
          v-for="(topicValue, topicName) in deletedItems"
          :key="topicName"
          class="mb-6"
        >
          <h3
            class="font-semibold text-gray-900 dark:text-gray-200"
            :class="{ 'text-red-600': topicValue._deleted }"
          >
            {{ topicName }}
          </h3>
          <div v-if="topicValue.subtopics">
            <div
              v-for="(subtopicValue, subtopicName) in topicValue.subtopics"
              :key="subtopicName"
              class="ml-4 mb-4"
            >
              <h4
                class="font-medium text-gray-800 dark:text-gray-300"
                :class="{ 'text-red-600': subtopicValue._deleted }"
              >
                {{ subtopicName }}
              </h4>
              <ul
                v-if="subtopicValue.questions"
                class="ml-4 list-disc text-sm text-gray-700 dark:text-gray-400"
              >
                <li
                  v-for="(qObj, questionKey) in subtopicValue.questions"
                  :key="questionKey"
                  class="mb-4"
                >
                  <div :class="{ 'text-red-600': qObj._deleted }">
                    <span class="font-semibold">{{ questionKey }}: </span>
                    <span>{{ qObj.text }}</span>
                  </div>
                  <div v-if="qObj.files && qObj.files.length" class="mt-2 ml-2">
                    <div
                      v-for="(fileLink, fileIndex) in qObj.files"
                      :key="fileIndex"
                      class="mb-1"
                    >
                      <ImageLink :fileLink="fileLink" />
                    </div>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ──────────── footer ────────────-->
    <template #footer>
      <div class="flex justify-end gap-2">
        <Button
          :label="reviewOnly ? t('SaveChangesDialog.buttons.close') : t('SaveChangesDialog.buttons.cancel')"
          class="p-button-secondary p-button-sm"
          @click="$emit('cancel')"
        />
        <Button
          v-if="!reviewOnly"
          :label="t('SaveChangesDialog.buttons.confirm')"
          class="p-button-success p-button-sm"
          :disabled="!isEditMode && !hasChanges"
          @click="$emit('save')"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';
import ImageLink from './ImageLink.vue';
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
const props = defineProps({
  visible: { type: Boolean, required: true },
  isEditMode: { type: Boolean, default: false },
  hasChanges: { type: Boolean, default: false },
  reviewOnly: { type: Boolean, default: false }, // ★ NEW PROP ★
  changes: { type: Object, default: () => ({ added: 0, changed: 0, deleted: 0 }) },
  addedItems: { type: Object, default: () => ({}) },
  changedItems: { type: Object, default: () => ({}) },
  deletedItems: { type: Object, default: () => ({}) },
});

defineEmits(['update:visible', 'save', 'cancel']);
</script>

<!-- Add or adjust scoped styles if necessary -->
