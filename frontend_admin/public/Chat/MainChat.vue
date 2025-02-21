<template>
  <!-- 
    This div is our full-page overlay. It's positioned fixed at top-left,
    covering 100% viewport. It has pointer-events: none, so it doesn't
    block clicks on the underlying page unless we specifically re-enable 
    them for elements inside (the chat button & chat panel).
  -->
  <div class="chat-overlay-container">
    <!-- Chat toggle button (always visible) -->
    <Button
      icon="pi pi-comments"
      label="Open Chat"
      class="chat-toggle-button"
      @click="toggleChat"
    />

    <!-- Transition for smooth show/hide -->
    <transition name="fade">
      <!-- The actual chat box (visible only if `showChat` is true) -->
      <div
        v-if="showChat"
        class="chat-box"
        :class="{ 'chat-overlay-mobile': isMobile }"
      >
        <!-- 
          Optional header: close button, title, etc.
          <div class="chat-header">
            <h3>Live Chat</h3>
            <Button 
              icon="pi pi-times"
              class="p-button-rounded p-button-text"
              @click="toggleChat"
            />
          </div>
        -->

        <!-- Your chat component -->
        <ChatComponent @close-chat="toggleChat" />
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import ChatComponent from "./ChatComponent.vue";
import Button from 'primevue/button';
const showChat = ref(false); // Controls whether the chat is visible
const isMobile = ref(false); // Tracks if we're on a mobile screen

function toggleChat() {
  showChat.value = !showChat.value;
}

function checkScreenSize() {
  // Customize breakpoint if needed
  isMobile.value = window.innerWidth < 768;
}

onMounted(() => {
  checkScreenSize();
  window.addEventListener("resize", checkScreenSize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", checkScreenSize);
});
</script>

<style scoped>
/* 
  1. Full-screen overlay container 
     ---------------------------------------------
     - Covers the entire viewport.
     - pointer-events: none so it does NOT block 
       clicks on the underlying page.
     - We apply pointer-events: auto to child 
       elements that should be interactive.
*/
.chat-overlay-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* Allows clicks to pass through to the page */
  z-index: 9999;        /* Make sure this is on top of everything */
}

/* 
  2. The chat button 
     ---------------------------------------------
     - Re-enable pointer events so it is clickable.
     - Position it in the bottom-right corner by default.
*/
.chat-toggle-button {
  pointer-events: auto; /* Now it's clickable again */
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 9999; /* Keep it above other elements if needed */
}

/*
  3. Chat box with transition 
     ---------------------------------------------
     - Also re-enable pointer events (so user can type, click, etc.).
     - Position it in the bottom-right (desktop).
     - On mobile, we’ll override with `chat-overlay-mobile`.
*/
.chat-box {
  pointer-events: auto; /* Make the chat box interactive */
  position: absolute;
  bottom: 80px;
  right: 20px;
  width: 400px;
  height: 600px;
  border: 1px solid #ccc;
  background-color: #fff;
  display: flex;
  flex-direction: column;
  z-index: 10000;
}

/* 
  4. Mobile full-screen 
     ---------------------------------------------
*/
.chat-overlay-mobile {
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  width: 100% !important;
  height: 100% !important;
  border: none;
}

/* 
  5. Fade transition 
     ---------------------------------------------
*/
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter,
.fade-leave-to {
  opacity: 0;
}

/* 
  6. Optional chat header styles, etc.
*/
.chat-header {
  background-color: #f8f9fa;
  border-bottom: 1px solid #ccc;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
}
</style>
