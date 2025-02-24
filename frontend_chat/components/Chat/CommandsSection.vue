<template>
    <div>
      <!-- Кнопка, при нажатии на которую идёт запрос на сервер -->
      <!-- <Button label="Получить команды" class="p-button-outlined" @click="toggleCommands" /> -->
  
      <!-- Блок с кнопками команд (ChoiceButtons) -->
      <ChoiceButtons
        v-if="showCommands"
        :choiceOptions="commands.map((cmd) => [cmd.command, cmd.command])"
        :handleChoiceClick="onCommandClick"
      />
    </div>
  </template>
  
  <script setup>
  import { ref } from "vue";
  import { useNuxtApp } from "#app";
  import ChoiceButtons from "./ChoiceButtons.vue"; // <-- Скорректируйте путь к файлу
  import { useChatLogic } from "~/composables/useChatLogic";
  const showCommands = ref(false);
  const commands = ref([]);
  
  // Получаем доступ к вашему кастомному API через Nuxt
  const { $api } = useNuxtApp();
  const { $event, $listen } = useNuxtApp();
  
  $listen("show-commands", async () => {
    toggleCommands();
  });
  
  /**
   * Тоггл: если команды не загружены и блок скрыт — грузим и показываем,
   * иначе прячем.
   */
  function toggleCommands() {
    if (!showCommands.value) {
      // Загружаем команды с бэкенда
      $api
        .get("api/chats/commands")
        .then((response) => {
          console.log("Profile responseData= ", response.data);
          // Предполагается, что response.data.commands — массив
          commands.value = response.data.commands;
          showCommands.value = true;
        })
        .catch((err) => {
          if (err.response) {
            console.error(err.response.data);
          }
        });
    } else {
      // Если уже показываем — просто скрываем
      showCommands.value = false;
    }
  }
  
  /**
   * Обработка клика по кнопке команды
   * @param {string} command
   */
  const { handleChoiceClick } = useChatLogic({});
  function onCommandClick(command) {
    if (!command) return;
    $event("command-clicked", command);
    showCommands.value = false;
  }
  </script>
  
  <style scoped>
  /* При необходимости стили для этого компонента */
  </style>