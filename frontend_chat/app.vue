<template>
  <div >
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
  
</template>

<script setup>
const { setLocale, locale } = useI18n();
const colorMode = useColorMode();


let isLocal = ref(window.location.hostname === 'localhost') 

function updateTheme() {
  colorMode.preference = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  const systemTheme = colorMode.preference != 'dark' ? 'aura-light-cyan' : 'aura-dark-cyan';
  const themeLink = document.getElementById('theme-link');
  themeLink.setAttribute('href', `/${systemTheme}/theme.css`);
}
const isDarkMode = ref(window.matchMedia('(prefers-color-scheme)'));

watch(isDarkMode, (newVal) => {
  console.log('Dark mode is active', newVal);
  updateTheme();
});
// Initialize theme on mount
updateTheme();

onMounted(() => {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

  // Update the state on change
  const handleChange = (event) => {
    isDarkMode.value = event.matches;
    updateTheme();
  };

  // Listen for changes
  mediaQuery.addEventListener('change', handleChange);

  // Cleanup on unmount
  onUnmounted(() => {
    mediaQuery.removeEventListener('change', handleChange);
  });
});

</script>