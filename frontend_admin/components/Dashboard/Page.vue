<template>
 <div>
    <div v-if="currentPageName === 'admin'" class="flex flex-col min-h-screen bg-surface-0 dark:bg-surface-950">
        <Sidebar />
        <MainContent  />
    </div>
    <div v-if="currentPageName === 'personal_account'" class="flex flex-col min-h-screen bg-surface-0 dark:bg-surface-950">
        <Sidebar />
        <MainContent  />
    </div>

 </div>
</template>

<script setup>

import MainContent from "~/components/Dashboard/Components/MainContent.vue";
import Sidebar from "~/components/Dashboard/Components/Topbar.vue";
const colorMode = useColorMode();
const { currentPageName } = usePageState()
function updateTheme() {
  // const systemTheme =
  //   colorMode.preference != "dark" ? "aura-light-cyan" : "aura-dark-cyan";
  // //console.log("systemTheme", systemTheme)
  // const themeLink = document.getElementById("theme-link");
  // //console.log(themeLink)
  // themeLink.setAttribute("href", `/${systemTheme}/theme.css`);
  // //console.log(themeLink)
}
if(currentPageName.value === 'personal_account') {
    colorMode.preference = "light";
    updateTheme();
}


</script>

<style>
/* Add any additional styling if needed */
</style>
