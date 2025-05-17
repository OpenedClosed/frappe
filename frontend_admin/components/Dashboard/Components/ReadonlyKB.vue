<!-- ReadonlyKB.vue -->
<template>
  <!-- one collapsible block per source -->
  <section v-for="(tree, sourceId) in sources" :key="sourceId" class="mb-4">
    <details class="mt-2 p-2 rounded border bg-gray-50 dark:bg-gray-800">
      <summary class="cursor-pointer font-medium gap-2 space-x-2 ">
        <i class="pi pi-database" />
        <span>{{ sourceId === "kb" ? "Knowledge base" : sourceId }}</span>
      </summary>

      <div class="mt-2 text-sm leading-5 space-y-2">
        <template v-for="(topic, topicName) in tree" :key="topicName">
          <div class="flex items-center gap-4">
            <p class="font-semibold">{{ topicName }}</p>
            <Button disabled class="cursor-not-allowed line-through" size="small" label="Go to source" />
          </div>

          <template v-for="(sub, subName) in topic.subtopics" :key="subName">
            <p class="ml-2 font-medium">{{ subName }}</p>

            <ul class="ml-6 list-disc">
              <li v-for="(qObj, qKey) in sub.questions" :key="qKey" class="flex flex-col gap-1 mb-1">
                <span class="font-semibold">{{ qKey }}</span>

                <template v-if="qObj.files?.length">
                  <ImageLink v-for="(link, i) in qObj.files" :key="i" :fileLink="link" />
                </template>
              </li>
            </ul>
          </template>
        </template>
      </div>
    </details>
  </section>
</template>

<script setup>
import { computed } from "vue";
import ImageLink from "./ImageLink.vue";

const props = defineProps({
  sources: { type: Object, required: true },
});
</script>
