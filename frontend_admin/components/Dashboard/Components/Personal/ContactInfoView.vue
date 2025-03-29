<template>
    <div class="p-4 rounded border bg-white shadow-sm">
      <!-- Заголовок страницы -->
      <h1 class="text-xl font-bold mb-6">Контактная информация</h1>
  
      <!-- Контейнер, разбивающий на 2 колонки -->
      <div class="flex flex-row gap-8">
        <!-- Левая колонка -->
        <div class="flex-1 flex flex-col space-y-4">
          <!-- Email -->
          <div>
            <label class="block text-[13px] font-normal text-[#6B6B7B]">
              Email
            </label>
            <span class="text-[15px] font-normal text-[#1F1F29]">
              {{ itemData.email }}
            </span>
          </div>
  
          <!-- Phone -->
          <div>
            <label class="block text-[13px] font-normal text-[#6B6B7B]">
              Телефон
            </label>
            <span class="text-[15px] font-bold text-[#1F1F29]">
              {{ itemData.phone }}
            </span>
          </div>
  
          <!-- Address -->
          <div>
            <label class="block text-[13px] font-normal text-[#6B6B7B]">
              Адрес
            </label>
            <span class="text-[15px] font-normal text-[#1F1F29]">
              {{ itemData.address }}
            </span>
          </div>
  
          <!-- PESEL -->
          <div>
            <label class="block text-[13px] font-normal text-[#6B6B7B]">
              PESEL / Идентификатор
            </label>
            <span class="text-[15px] font-normal text-[#1F1F29]">
              {{ itemData.pesel }}
            </span>
          </div>
        </div>
  
        <!-- Правая колонка -->
        <div class="flex-1 flex flex-col space-y-4">
          <!-- Emergency Contact -->
          <div>
            <label class="block text-[13px] font-normal text-[#6B6B7B]">
              Экстренный контакт
            </label>
            <span class="text-[15px] font-bold text-[#1F1F29]">
              {{ itemData.emergency_contact }}
            </span>
          </div>
  
          <!-- Document ID -->
          <div>
            <label class="block text-[13px] font-normal text-[#6B6B7B]">
              ID документа
            </label>
            <span class="text-[15px] font-normal text-[#1F1F29]">
              {{ itemData.doc_id }}
            </span>
          </div>
  
          <!-- Last Update -->
          <div>
            <label class="block text-[12px] font-normal text-[#8B8B99]">
              Последнее обновление
            </label>
            <span class="text-[14px] font-normal text-[#4F4F59]">
              {{ itemData.updated_at }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  /**
   * Предполагаем, что в родительском компоненте
   * передаётся объект itemData с данными из API.
   */
  const props = defineProps({
    itemData: {
      type: Object,
      default: () => ({})
    }
  })
  </script>
  
  <style scoped>
  /* При необходимости можно добавить дополнительные стили */
  </style>
  