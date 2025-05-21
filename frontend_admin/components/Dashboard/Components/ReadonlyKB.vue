<!-- ReadonlyKB.vue -->
<template>
  <!-- one collapsible block per source -->
  <section
    v-for="(tree, sourceId) in sources"
    :key="sourceId"
    class="mb-4"
  >
    <!-- PrimeVue v4 toggleable panel -->
    <Panel
      :toggleable="true"
      :collapsed="true"
      class="mt-2 p-2 rounded border bg-gray-50 dark:bg-gray-800"
    >
      <!-- ── Custom header (re-creates the old <summary>) -->
      <template #header>
        <!-- — Knowledge-base pseudo-source -->
        <div
          v-if="sourceId === 'kb'"
          class="flex items-center gap-2 cursor-pointer font-medium p-1"
        >
          <i class="pi pi-database" />
          <span>{{ t('ReadonlyKB.summary.knowledgeBase') }}</span>
        </div>

        <!-- — Context-unit source (Mongo-like ObjectId) -->
        <div
          v-else-if="isObjectId(sourceId)"
          class="flex items-center gap-2 cursor-pointer font-medium"
        >
          <template v-if="contextMap[sourceId]">
            <!-- icon badge -->
            <div class="flex-shrink-0">
              <div
                :class="[
                  'h-8 w-8 2xl:h-12 2xl:w-12 rounded-lg 2xl:rounded-xl flex items-center justify-center',
                  colourFor(contextMap[sourceId].purpose).bg,
                  colourFor(contextMap[sourceId].purpose).text,
                ]"
              >
                <i
                  :class="[typeIcon(contextMap[sourceId].type), 'text-lg 2xl:text-xl']"
                />
              </div>
            </div>

            <!-- title + meta -->
            <div class="flex-1 flex flex-col justify-between">
              <p
                class="font-medium truncate text-[14px] 2xl:text-[17px] leading-5 max-w-[190px]"
              >
                {{ contextMap[sourceId].title }}
              </p>
              <p
                class="text-[10px] text-slate-500 2xl:text-sm max-[375px]:hidden"
              >
                {{ formatDate(contextMap[sourceId].created_at) }} ·
                {{ contextMap[sourceId].type.toUpperCase() }}
              </p>
            </div>
          </template>

          <!-- fallback (shouldn’t normally hit) -->
          <template v-else>
            <span>{{ sourceId }}</span>
          </template>
        </div>

        <!-- — Anything else (plain label) -->
        <div
          v-else
          class="flex items-center gap-2 cursor-pointer font-medium"
        >
          <span>{{ sourceId }}</span>
        </div>
      </template>

      <!-- ── Topics & Q-A tree (panel content) -->
      <div class="mt-2 text-sm leading-5 space-y-2">
        <template v-for="(topic, topicName) in tree" :key="topicName">
          <div class="flex items-center gap-4">
            <p class="font-semibold">{{ topicName }}</p>
            <Button
              disabled
              class="cursor-not-allowed line-through"
              size="small"
              :label="t('ReadonlyKB.buttons.goToSource')"
            />
          </div>

          <template
            v-for="(sub, subName) in topic.subtopics"
            :key="subName"
          >
            <p class="ml-2 font-medium">{{ subName }}</p>

            <ul class="ml-6 list-disc">
              <li
                v-for="(qObj, qKey) in sub.questions"
                :key="qKey"
                class="flex flex-col gap-1 mb-1"
              >
                <!-- question -->
                <span class="font-semibold">{{ qKey }}</span>

                <!-- answer -->
                <p class="ml-4 whitespace-pre-line">{{ qObj.text }}</p>

                <!-- attached files (if any) -->
                <template v-if="qObj.files?.length">
                  <ImageLink
                    v-for="(link, i) in qObj.files"
                    :key="i"
                    :fileLink="link"
                  />
                </template>
              </li>
            </ul>
          </template>
        </template>
      </div>
    </Panel>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import ImageLink from './ImageLink.vue'
import Panel from 'primevue/panel'

const { t } = useI18n()

/* ------------------------------------------------------------------ */
/* props & remote context units                                       */
/* ------------------------------------------------------------------ */
const props = defineProps({
  sources: { type: Object, required: true },
})

const contextList = ref([])

async function fetchContextUnits() {
  try {
    const { data } = await useNuxtApp().$api.get(
      '/api/knowledge/context_entity',
    )
    contextList.value = data
  } catch (err) {
    showError(t('KnowledgeBase.ctxLoadErr'))
  }
}

onMounted(fetchContextUnits)

/* quick lookup by id */
const contextMap = computed(() =>
  Object.fromEntries(contextList.value.map((c) => [c.id, c])),
)

/* ------------------------------------------------------------------ */
/* helpers                                                            */
/* ------------------------------------------------------------------ */
const isObjectId = (str) => /^[0-9a-fA-F]{24}$/.test(str)

const typeIcon = (t) => {
  switch (t) {
    case 'text':
      return 'pi pi-pencil'
    case 'file':
      return 'pi pi-file'
    case 'qa':
      return 'pi pi-question'
    case 'url':
      return 'pi pi-globe'
    default:
      return 'pi pi-file'
  }
}

const purposeColours = {
  bot: {
    bg: 'bg-green-100 dark:bg-green-900/40',
    text: 'text-green-600 dark:text-green-300',
  },
  kb: {
    bg: 'bg-blue-100 dark:bg-blue-900/40',
    text: 'text-blue-600 dark:text-blue-300',
  },
  both: {
    bg: 'bg-purple-100 dark:bg-purple-900/40',
    text: 'text-purple-600 dark:text-purple-300',
  },
  none: {
    bg: 'bg-gray-50 dark:bg-gray-700',
    text: 'text-gray-500 dark:text-gray-300',
  },
}

const colourFor = (purpose) => purposeColours[purpose] ?? purposeColours.none

const formatDate = (d) =>
  new Intl.DateTimeFormat('ru-RU').format(new Date(d))
</script>

<style scoped>
/* keeps PrimeVue panel outline consistent with the old <details> */
.p-panel {
  @apply border rounded;
}
</style>
