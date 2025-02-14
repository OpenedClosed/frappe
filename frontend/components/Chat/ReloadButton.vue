<template>
    <div class="py-4 flex justify-center">
      <Button :label="reloadLabel" class="p-button-outlined p-button-danger" @click="reloadPage" />
    </div>
  </template>
  
  <script setup>
  import Button from "primevue/button";
  
  const props = defineProps({
    reloadLabel: {
      type: String,
      default: ""
    },
    reloadPage: {
      type: Function,
      required: true
    }
  });
  </script>
  