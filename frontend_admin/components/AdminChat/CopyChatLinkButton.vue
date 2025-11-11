<template>
  <Button 
    :icon="icon"
    :severity="severity"
    :size="size"
    :text="text"
    :class="buttonClass"
    @click="handleCopyLink"
    v-tooltip.bottom="tooltipText"
  />
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from '#imports';
import { useChatLink } from '~/composables/useChatLink';

const { t } = useI18n();
const { copyChatLink } = useChatLink();

const props = defineProps({
  chatId: {
    type: String,
    default: null
  },
  icon: {
    type: String,
    default: 'pi pi-link'
  },
  severity: {
    type: String,
    default: 'secondary'
  },
  size: {
    type: String,
    default: 'small'
  },
  text: {
    type: Boolean,
    default: false
  },
  buttonClass: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['link-copied']);

const tooltipText = computed(() => t('EmbeddedChat.copyChatLink'));

async function handleCopyLink() {
  try {
    const link = await copyChatLink(props.chatId);
    emit('link-copied', link);
  } catch (error) {
    console.error('Failed to copy link:', error);
  }
}
</script>
