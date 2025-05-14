<template>
    <!-- Обёртка -->
    <div class="p-4 rounded border  shadow-sm bg-white dark:bg-secondaryDark">
        <!-- Заголовок всей секции -->
        <h2 class="text-2xl font-bold mb-4">Основная информация</h2>

        <!-- Контейнер для всех блоков в ряд -->
        <div class="flex gap-10">
            <!-- Первый блок: "Личные данные" -->
            <div class="flex-1 flex flex-col">
                <h3 class="text-lg font-bold mb-2 ">Личные данные</h3>
                <div class="flex flex-col space-y-1">
                    <div class="flex items-center justify-between">
                        <span class="text-sm ">Фамилия:</span>
                        <span class="ml-1 font-semibold">{{ itemData.last_name }}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-sm ">Имя:</span>
                        <span class="ml-1 font-semibold">{{ itemData.first_name }}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-sm ">Отчество:</span>
                        <span class="ml-1 font-semibold">{{ itemData.patronymic }}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-sm ">Дата рождения:</span>
                        <span class="ml-1 font-semibold">{{ formatDate(itemData.birth_date) }}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-sm ">Пол:</span>
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
                    <h3 class="text-lg font-bold mb-2 ">Информация о компании</h3>
                    <div class="flex flex-col space-y-1">
                        <div class="flex items-center justify-between">
                            <span class="text-sm ">Название компании:</span>
                            <span class="ml-1 font-semibold">{{ itemData.company_name }}</span>
                        </div>
                    </div>
                </div>

                <!-- Третий блок: "Системная информация" -->
                <div class="flex-1 flex flex-col">
                    <h3 class="text-lg font-bold mb-2 ">Системная информация</h3>
                    <div class="flex flex-col space-y-1">
                        <div class="flex items-center justify-between">
                            <span class="text-sm ">ID пациента:</span>
                            <span class="ml-1 font-semibold">{{ itemData.patient_id }}</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm ">Дата создания:</span>
                            <span class="ml-1 font-semibold">{{ formatDate(itemData.created_at) }}</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm ">Последнее обновление:</span>
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

// Props
const props = defineProps({
    itemData: {
        type: Object,
        default: () => ({})
    }
})

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
        return 'Invalid date'
    } catch (error) {
        console.error('Invalid date:', date)
        return 'Invalid date'
    }
}
</script>
  
<style scoped>
/* Дополнительные стили при необходимости */
</style>
