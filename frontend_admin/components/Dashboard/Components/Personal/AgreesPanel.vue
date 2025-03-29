<template>
    <div class="p-6 border rounded-lg shadow-sm bg-white">
      <!-- Заголовок и описание -->
      <h2 class="text-xl font-semibold mb-1">Согласия пользователя</h2>
      <p class="text-gray-600 mb-4">Информация о согласиях пользователя</p>
  
      <!-- Список согласий -->
      <ul>
        <li
          v-for="(consent, index) in consents"
          :key="index"
          class="flex items-center mb-2"
        >
          <!-- Цветной кружок -->
          <span
            :class="consent.status ? 'bg-green-500' : 'bg-red-500'"
            class="inline-block w-3 h-3 rounded-full mr-2"
          />
          <!-- Текст согласия -->
          <span>{{ consent.title }}</span>
        </li>
      </ul>
  
      <!-- Дата последнего обновления -->
      <p class="text-sm text-gray-500 mt-4">
        Дата последнего обновления согласия:
        <span class="font-medium">
          {{ formatDate(props.itemData.lastUpdated) }}
        </span>
      </p>
    </div>
  </template>
  
  <script setup>
  import { defineProps, watch, computed } from 'vue'
  
  const props = defineProps({
    itemData: {
      type: Object,
      required: true,
    }
  })
  
  // Отслеживаем изменение данных для отладки (необязательно)
  watch(
    () => props.itemData,
    (newVal) => {
      if (newVal) {
        console.log('Updated itemData:', newVal)
      }
    },
    { immediate: true }
  )
  
  // Функция для форматирования даты
  function formatDate(dateStr) {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
  
  // Список согласий (настраивайте названия полей под вашу структуру)
  const consents = computed(() => [
    {
      title: 'Согласие на обработку персональных данных (GDPR)',
      status: props.itemData.gdpr
    },
    {
      title: 'Согласие с политикой конфиденциальности',
      status: props.itemData.privacyPolicy
    },
    {
      title: 'Согласие с условиями использования',
      status: props.itemData.termsOfUse
    },
    {
      title: 'Согласие на использование cookies',
      status: props.itemData.cookies
    },
    {
      title: 'Согласие на email-маркетинг',
      status: props.itemData.emailMarketing
    },
    {
      title: 'Согласие на SMS-маркетинг',
      status: props.itemData.smsMarketing
    },
    {
      title: 'Согласие на персонализацию',
      status: props.itemData.personalization
    }
  ])
  </script>
  