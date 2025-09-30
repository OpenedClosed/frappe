// plugins/mark.client.ts
import { defineNuxtPlugin } from '#app'
import Mark from 'mark.js'

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.directive('mark', {
    mounted(el, binding) {
      // store the instance on the element for later reuse
      const instance = new Mark(el)
      el.__markInstance = instance
      if (binding.value) highlight(instance, binding.value)
    },
    updated(el, binding) {
      // re-run every time the bound value changes
      const instance = el.__markInstance
      instance.unmark({
        done: () => binding.value && highlight(instance, binding.value)
      })
    }
  })
})

function highlight(instance: Mark, query: string) {
  instance.mark(query, {
    separateWordSearch : true,           // "foo bar" → highlights both
    diacritics         : true,           // ā / a, é / e, …
    className          : 'kb-hit'        // your own Tailwind class
  })
}
