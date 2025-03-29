<template>
 <div>
    <div v-if="currentPageName === 'admin'" class="flex flex-col min-h-screen bg-surface-0 dark:bg-surface-950">
        <Sidebar />
        <MainContent  />
    </div>
    <div v-if="currentPageName === 'personal_account'" class="flex flex-col min-h-screen bg-surface-0 dark:bg-surface-950">
        <MainContent  />
    </div>

 </div>
</template>

<script setup>

import MainContent from "~/components/Dashboard/Components/MainContent.vue";
import Sidebar from "~/components/Dashboard/Components/Topbar.vue";

const { currentPageName } = usePageState()



</script>

<style>
/* Add any additional styling if needed */
</style>
