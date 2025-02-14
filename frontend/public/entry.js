import { createApp } from 'vue'
import MainChat from './components/Chat/MainChat.vue'

// PrimeVue or any other plugins:
import PrimeVue from 'primevue/config'
import 'primevue/resources/themes/saga-blue/theme.css'
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'

// Export a function to mount the chat
export function initMainChat() {
  const container = document.createElement('div')
  document.body.appendChild(container)

  const app = createApp(MainChat)
  app.use(PrimeVue)
  app.mount(container)
}
