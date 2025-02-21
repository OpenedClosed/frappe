import { defineNuxtPlugin } from '#app';
import DOMPurify from 'dompurify';

export default defineNuxtPlugin(nuxtApp => {
  nuxtApp.provide('dompurify', DOMPurify);
});