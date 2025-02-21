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
  const systemTheme = colorMode.preference != 'dark' ? 'aura-light-cyan' : 'aura-dark-cyan';
  const themeLink = document.getElementById('theme-link');
  themeLink.setAttribute('href', `/${systemTheme}/theme.css`);
}

// Initialize theme on mount
updateTheme();

const isHydrating = ref(true);

onMounted(() => {
  isHydrating.value = false;
});


</script>