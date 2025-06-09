<template>
    <div class="p-4 rounded border bg-white dark:bg-secondaryDark shadow-sm">
      <!-- Заголовок страницы -->
      <h1 class="text-xl font-bold mb-6">{{ t('ContactInfoView.title') }}</h1>
  
      <!-- Контейнер, разбивающий на 2 колонки -->
      <div class="flex flex-row gap-8">
        <!-- Левая колонка -->
        <div class="flex-1 flex flex-col space-y-4">
          <!-- Email -->
          <div>
            <label class="block text-[13px] font-normal ">
              {{ t('ContactInfoView.email') }}
            </label>
            <span class="text-[15px] font-normal">
              {{ itemData.email }}
            </span>
          </div>
  
          <!-- Phone -->
          <div>
            <label class="block text-[13px] font-normal ">
              {{ t('ContactInfoView.phone') }}
            </label>
            <span class="text-[15px] font-bold">
              {{ itemData.phone }}
            </span>
          </div>
  
          <!-- Address -->
          <div>
            <label class="block text-[13px] font-normal ">
              {{ t('ContactInfoView.address') }}
            </label>
            <span class="text-[15px] font-normal">
              {{ itemData.address }}
            </span>
          </div>
  
          <!-- PESEL -->
          <div>
            <label class="block text-[13px] font-normal ">
              {{ t('ContactInfoView.pesel') }}
            </label>
            <span class="text-[15px] font-normal">
              {{ itemData.pesel }}
            </span>
          </div>
        </div>
  
        <!-- Правая колонка -->
        <div class="flex-1 flex flex-col space-y-4">
          <!-- Emergency Contact -->
          <div>
            <label class="block text-[13px] font-normal ">
              {{ t('ContactInfoView.emergency') }}
            </label>
            <span class="text-[15px] font-bold">
              {{ itemData.emergency_contact }}
            </span>
          </div>
  
          
  
          <!-- Last Update -->
          <div>
            <label class="block text-[12px] font-normal ">
             	{{ t('ContactInfoView.lastUpdate') }}
            </label>
            <span class="text-[14px] font-normal text-[#4F4F59]">
              {{ formatDate(itemData.updated_at) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import _ from 'lodash'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
  /**
   * Props for receiving data from the parent component
   */
  const props = defineProps({
    itemData: {
      type: Object,
      default: () => ({})
    }
  })

  /**
   * Helper function to format dates with time
   */
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
  /* Add additional styles if necessary */
  </style>
