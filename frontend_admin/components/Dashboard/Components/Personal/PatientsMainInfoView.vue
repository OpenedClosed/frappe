<template>
    <!-- Обёртка -->
    <div class="p-4 rounded border  shadow-sm bg-white dark:bg-secondaryDark">
        <!-- Заголовок всей секции -->
        <h2 class="text-2xl font-bold mb-4">{{ t('PatientsMainInfoView.sectionTitle') }}</h2>

        <!-- Контейнер для всех блоков в ряд -->
        <div class="flex gap-10">
            <!-- Первый блок: "Личные данные" -->
            <div class="flex-1 flex flex-col">
                <h3 class="text-lg font-bold mb-2 ">{{ t('PatientsMainInfoView.blockPersonal') }}</h3>
                <div class="flex flex-col space-y-1">
                    <div class="flex items-center justify-between">
                        <span class="text-sm ">	{{ t('PatientsMainInfoView.lastName') }}</span>
                        <span class="ml-1 font-semibold">{{ itemData.last_name }}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-sm ">	{{ t('PatientsMainInfoView.firstName') }}</span>
                        <span class="ml-1 font-semibold">{{ itemData.first_name }}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-sm ">	{{ t('PatientsMainInfoView.patronymic') }}</span>
                        <span class="ml-1 font-semibold">{{ itemData.patronymic }}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-sm ">{{ t('PatientsMainInfoView.birthDate') }}</span>
                        <span class="ml-1 font-semibold">{{ formatDate(itemData.birth_date) }}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-sm ">{{ t('PatientsMainInfoView.birthDate') }}</span>
                        <span class="ml-1 font-semibold">
                            {{ itemData.gender?.ru || itemData.gender?.en || itemData.gender }}
                        </span>
                    </div>
                </div>
            </div>

            <!-- Второй блок: "Контактные данные" -->
            <div class="flex-1 flex flex-col gap-1">
                <!-- Второй блок: "Информация о компании" -->
                <div class="flex-1 flex flex-col">
                    <h3 class="text-lg font-bold mb-2 ">{{ t('PatientsMainInfoView.blockCompany') }}</h3>
                    <div class="flex flex-col space-y-1">
                        <div class="flex items-center justify-between">
                            <span class="text-sm ">{{ t('PatientsMainInfoView.companyName') }}</span>
                            <span class="ml-1 font-semibold">{{ itemData.company_name }}</span>
                        </div>
                    </div>
                </div>

                <!-- Третий блок: "Системная информация" -->
                <div class="flex-1 flex flex-col">
                    <h3 class="text-lg font-bold mb-2 ">{{ t('PatientsMainInfoView.blockSystem') }}</h3>
                    <div class="flex flex-col space-y-1">
                        <div class="flex items-center justify-between">
                            <span class="text-sm ">{{ t('PatientsMainInfoView.patientId') }}</span>
                            <span class="ml-1 font-semibold">{{ itemData.patient_id }}</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm ">{{ t('PatientsMainInfoView.createdAt') }}</span>
                            <span class="ml-1 font-semibold">{{ formatDate(itemData.created_at) }}</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm ">{{ t('PatientsMainInfoView.updatedAt') }}</span>
                            <span class="ml-1 font-semibold">{{ formatDate(itemData.updated_at) }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
  
<script setup>
import _ from 'lodash'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

// Props
const props = defineProps({
    itemData: {
        type: Object,
        default: () => ({})
    }
})

watch(
    () => props,  
    (newValue) => {
        if (newValue) {
            console.log('itemData changed:', newValue)
        }
    },
    { immediate: true }
)

// Helper function to format dates with time
function formatDate(date) {
    if (!date) return '—'
    try {
        const parsedDate = new Date(date)
        if (_.isDate(parsedDate) && !isNaN(parsedDate)) {
            return `${_.padStart(parsedDate.getDate(), 2, '0')}.${_.padStart(
                parsedDate.getMonth() + 1,
                2,
                '0'
            )}.${parsedDate.getFullYear()} ${_.padStart(parsedDate.getHours(), 2, '0')}:${_.padStart(
                parsedDate.getMinutes(),
                2,
                '0'
            )}`
        }
        
        return 	t('PatientsMainInfoView.invalidDate')
    } catch (error) {
        console.error('Invalid date:', date)
        return 	t('PatientsMainInfoView.invalidDate')
    }
}
</script>
  
<style scoped>
/* Дополнительные стили при необходимости */
</style>
