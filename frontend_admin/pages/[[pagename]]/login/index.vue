<script setup>
import AdminLogin from '~/components/Auth/Admin/Login/MainLogin.vue'
import PersonalLogin from '~/components/Auth/Personal/Login/MainLogin.vue'

const { currentPageName } = usePageState()

</script>
<template>
    <div class="Main">
        <AdminLogin v-if="currentPageName === 'admin'"/>
        <PersonalLogin v-if="currentPageName === 'personal_account'"/>
    </div>
</template>