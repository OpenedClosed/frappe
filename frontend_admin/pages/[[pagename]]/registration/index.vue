<script setup>
import AdminRegistration from '~/components/Auth/Admin/Registration/MainRegistration.vue'
import PersonalRegistration from '~/components/Auth/Personal/Registration/MainRegistration.vue'
const { currentPageName } = usePageState()

</script>
<template>
    <div class="Main">
        <AdminRegistration v-if="currentPageName === 'admin'"/>
        <PersonalRegistration v-if="currentPageName === 'personal_account'"/>
    </div>
</template>