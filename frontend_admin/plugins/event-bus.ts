import mitt from 'mitt'
import { defineNuxtPlugin } from 'nuxt/app'

export default defineNuxtPlugin(() => {
  const emitter = mitt()
  return {
    provide: {
      event: emitter.emit,
      listen: emitter.on
    }
  }
})
