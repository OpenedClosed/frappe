import { createApp } from 'vue';
import EmbeddedChat from './components/Chat/EmbeddedChat.vue'; // Adjust the path to your component

export default function mountEmbeddedChat(containerId) {
  const container = document.getElementById(containerId);

  if (!container) {
    console.error(`Container with id "${containerId}" not found`);
    return;
  }

  const app = createApp({
    components: { EmbeddedChat },
    template: '<EmbeddedChat />',
  });

  app.mount(container);
}
