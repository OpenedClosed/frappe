<template>
    <div>
        <Button v-if="smallButton" @click="visible_support = true" text class="export-button h-full flex justify-center items-center">
            <i class="pi pi-comments text-[18px] text-black dark:text-white"></i>
          </Button>
        <Button v-else   icon="pi pi-comment" :label="t('supportForm.support')" class="w-full neon-button flex justify-between  items-center text-white" @click="visible_support = true" >
        </Button>

        <Dialog v-model:visible="visible_support" modal :header="t('supportForm.supportForm')" :style="{ width: '25rem' }">

            <!-- <span class="text-surface-500 dark:text-surface-400 block mb-8">Create Project.</span> -->
            <LoaderOverlay v-if="is_loading" :isLoading="!loading_text_displayed" :finshText="t('supportForm.messageSent')" />
            <form @submit.prevent="sendSupport" class="flex flex-col  gap-4">

                <label for="audience" class="font-semibold w-full">{{ t('supportForm.message') }}</label>
                <Textarea :minlength="50" :maxlength="1500" v-model="creationForm.message" required id="audience"
                    class="w-full h-64" autocomplete="off" />
                <label for="audience" class="font-semibold w-full">{{ t('supportForm.email') }}</label>
                <InputText type="email" v-model="creationForm.email" required id="audience" class="w-full"
                    autocomplete="off" />
                <div class="flex flex-row mt-2 justify-between px-2 gap-2">
                    <Button class="neon-button"  type="button" :label="t('supportForm.cancel')" severity="secondary"
                        @click="visible_support = false"></Button>
                    <Button class="neon-button"  type="submit"  :label="t('supportForm.sendMessage')"></Button>
                </div>
            </form>

        </Dialog>
    </div>
</template>

<script setup>
import LoaderOverlay from '~/components/LoaderOverlay.vue';
const visible_support = ref(false);
const is_loading = ref(false);
const loading_text_displayed = ref(false);
const creationForm = ref({
    message: "",
    email: '',
});
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

let props = defineProps({
    smallButton: { type: Boolean, default: false },

});

function sendSupport() {
    is_loading.value = true
    loading_text_displayed.value = false;
    useNuxtApp().$api
        .post(`api/users/support_requests`, creationForm.value)
        .then((response) => {
            let responseData = response.data;
            console.log("Profile responseData= ", responseData);
            loading_text_displayed.value = true;
            setTimeout(() => {
                is_loading.value = false;
                visible_support.value = false
            }, 2000);

        })
        .catch((err) => {
            if (err.response) {
                //console.log(err.response.data)
            }
        });
}

</script>