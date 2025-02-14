<template>
    <div class="flex flex-col min-h-screen bg-surface-0 dark:bg-surface-950">
        <Sidebar />
        <MainContent  />
    </div>
</template>

<script setup>

import MainContent from "~/components/Dashboard/Components/MainContent.vue";
import Sidebar from "~/components/Dashboard/Components/Topbar.vue";

</script>

<style>
/* Add any additional styling if needed */
</style>
