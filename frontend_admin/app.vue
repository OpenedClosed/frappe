<template>
  <div >
    {{ colorMode }}
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
  
</template>
<script setup>
import { ref, onMounted, watch } from 'vue'
import { useI18n, useColorMode } from '#imports'


/* ------------------------------------------------------------------ */
/*  Composables                                                        */
/* ------------------------------------------------------------------ */
const { setLocale, locale } = useI18n()
const colorMode             = useColorMode()
const { currentPageName }   = usePageState()

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
const isLocal = ref(window.location.hostname === 'localhost')

const cabinetPalette = {
  light: {
    '--color-primary':         '#000000',
    '--color-primary-light':   '#666666',
    '--color-primary-dark':    '#000000',
    '--color-secondary':       '#000000',
    '--color-secondary-light': '#666666',
    '--color-secondary-dark':  '#1a1a1a',
    '--color-accent':          '#000000',
    '--color-accent-dark':     '#333333',
    '--color-neutral':         '#ffffff',
    '--color-neutral-dark':    '#e5e5e5',
    '--color-neutral-light':   '#f9f9f9',
  },
  dark: {
    '--color-primary':         '#cbd5e1',
    '--color-primary-light':   '#94a3b8',
    '--color-primary-dark':    '#ffffff',
    '--color-secondary':       '#334155',
    '--color-secondary-light': '#1e293b',
    '--color-secondary-dark':  '#475569',
    '--color-accent':          '#facc15',
    '--color-accent-dark':     '#fde047',
    '--color-neutral':         '#1e293b',
    '--color-neutral-dark':    '#0f172a',
    '--color-neutral-light':   '#334155',
  },
}

function applyCabinetPalette (mode) {
  if (currentPageName.value != 'personal_account') return
  const root = document.documentElement
  for (const k in cabinetPalette[mode]) {
    root.style.setProperty(k, cabinetPalette[mode][k])
  }
}

function updateTheme () {
  const systemTheme =
    colorMode.preference !== 'dark' ? 'aura-light-cyan' : 'aura-dark-cyan'
  document
    .getElementById('theme-link')
    ?.setAttribute('href', `/${systemTheme}/theme.css`)

  applyCabinetPalette(colorMode.preference === 'dark' ? 'dark' : 'light')
}

/* ------------------------------------------------------------------ */
/*  Toggle & watchers                                                  */
/* ------------------------------------------------------------------ */
function toggleTheme () {
  colorMode.preference = colorMode.preference === 'dark' ? 'light' : 'dark'
}

onMounted(() => {
  // Set the initial theme based on the user's preference
  updateTheme()
})

watch(() => colorMode.preference, updateTheme)
</script>
