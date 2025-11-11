/**
 * Composable for managing chat links and URL synchronization
 * Handles copying chat links and updating URL with chat ID
 */
import { useRoute, useRouter } from '#app';
import { useToast } from 'primevue/usetoast';
import { useI18n } from '#imports';

export function useChatLink() {
  const route = useRoute();
  const router = useRouter();
  const toast = useToast();
  const { t } = useI18n();

  /**
   * Copy the current chat link to clipboard
   * @param {string} chatId - The ID of the chat to copy link for
   */
  async function copyChatLink(chatId) {
    if (!chatId) {
      toast.add({
        severity: 'warn',
        summary: t('EmbeddedChat.warning'),
        detail: t('EmbeddedChat.noChatSelected'),
        life: 3000
      });
      return;
    }
    
    try {
      // Build the full URL with current chat ID
      const baseUrl = window.location.origin;
      const currentPath = route.path;
      const chatUrl = `${baseUrl}${currentPath}?chatId=${encodeURIComponent(chatId)}`;
      
      // Copy to clipboard
      await navigator.clipboard.writeText(chatUrl);
      
      toast.add({
        severity: 'success',
        summary: t('EmbeddedChat.success'),
        detail: t('EmbeddedChat.chatLinkCopied'),
        life: 3000
      });
      
      return chatUrl;
    } catch (error) {
      console.error('Failed to copy chat link:', error);
      toast.add({
        severity: 'error',
        summary: t('EmbeddedChat.errorTitle'),
        detail: t('EmbeddedChat.failedToCopyLink'),
        life: 5000
      });
      throw error;
    }
  }

  /**
   * Update the URL query parameter with current chat ID
   * @param {string} chatId - The ID of the chat to add to URL
   */
  function updateUrlWithChatId(chatId) {
    if (!chatId) return;
    
    try {
      // Update URL without triggering navigation
      const newQuery = { ...route.query, chatId };
      router.replace({ query: newQuery });
    } catch (error) {
      console.error('Failed to update URL with chat ID:', error);
    }
  }

  return {
    copyChatLink,
    updateUrlWithChatId
  };
}
