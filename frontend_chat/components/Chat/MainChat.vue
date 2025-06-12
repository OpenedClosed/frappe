<template>
  <div>
    <!-- Floating toggle -->
    <Button text v-if="projectKey === 'aihub' || projectKey === 'localhost' " size="large"
      class="chat-toggle-button flex flex-row gap-2" @click="toggleChat">
      <div ref="logoRef" class="relative w-[100px] pointer-events-none">

        <img src="/images/logo_gregg.png" alt="Chat Icon" class="w-full h-full" />
        <!-- <div v-for="(eye, index) in eyes" :key="index"
          class="absolute w-[12px] h-[12px] bg-white rounded-full border border-black"
          :style="{ top: eye.top, left: eye.left }">
          <div class="w-[6px] h-[6px] bg-black rounded-full"
            :style="{ transform: `translate(${eye.pupilX}px, ${eye.pupilY}px)` }" />
        </div> -->
      </div>
    </Button>
    <Button v-else icon="pi pi-comments" label="Open Chat" size="large" class="chat-toggle-button text-white"
      @click="toggleChat" />
 
    <!-- Chat box -->
    <transition name="fade">
      <div v-if="showChat" class="chat-box" :class="{ 'chat-box--mobile': isMobile }">
        <ChatComponent :is-telegram="false" @close-chat="toggleChat" />
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import ChatComponent from "./ChatComponent.vue";
import Button from "primevue/button";
const { projectKey } = useProjectState()
const showChat = ref(false); // Controls whether the chat is visible
const isMobile = ref(false); // Tracks if we're on a mobile screen
function postSizeToParent() {
  console.log("postSizeToParent");
  if (!window.parent) return;
  console.log("postSizeToParent", window.parent);

  const collapsedSize = (projectKey === 'aihub' || projectKey === 'localhost') ? { width: 162, height: 62 } : { width: 162, height: 162 };
  console.log("collapsedSize", collapsedSize);

  const expandedSize = { width: 420, height: 700, };

  const size = showChat.value ? expandedSize : collapsedSize;
  console.log("postSizeToParent", size);

  window.parent.postMessage({ ...size, type: 'bgSize', showChat: showChat.value }, "*"); // or use specific origin for security
}

function toggleChat() {
  showChat.value = !showChat.value;
  // Post new size to parent window
  postSizeToParent();
}


function checkScreenSize() {
  // Customize breakpoint if needed
  isMobile.value = window.innerWidth < 768;
}


const eyes = ref([
  { top: '15px', left: '29px', pupilX: 0, pupilY: 0 },  // left eye
  { top: '15px', left: '47px', pupilX: 0, pupilY: 0 }  // right eye
])

const logoRef = ref(null)

function handleMouseMove(event) {
  const logoEl = logoRef.value
  if (!logoEl) return

  const rect = logoEl.getBoundingClientRect()

  eyes.value.forEach((eye) => {
    const eyeCenterX = rect.left + parseInt(eye.left) 
    const eyeCenterY = rect.top + parseInt(eye.top) 
    const dx = event.clientX - eyeCenterX
    const dy = event.clientY - eyeCenterY
    const angle = Math.atan2(dy, dx)
    const distance = 2
    eye.pupilX = Math.cos(angle) * distance
    eye.pupilY = Math.sin(angle) * distance
  })
}


onMounted(() => {
  checkScreenSize();
  window.addEventListener("resize", checkScreenSize);
  window.addEventListener('mousemove', handleMouseMove)
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", checkScreenSize);
  window.removeEventListener('mousemove', handleMouseMove)
});





</script>
<!-- http://localhost:4000/chats/chat/index.html -->
<style>
html,
body {
  background: transparent !important;
}

#app,
/* Vue root on that page */
.vac-container,
/* vue-advanced-chat */
.p-panel {
  background: transparent !important;
  border: none;
}
</style>


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
/* In the embedded page's CSS */
body {
  background-color: transparent;
}

.chat-overlay-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  /* Allows clicks to pass through to the page */
  z-index: 9999;
  /* Make sure this is on top of everything */
}

/* 
  2. The chat button 
     ---------------------------------------------
     - Re-enable pointer events so it is clickable.
     - Position it in the bottom-right corner by default.
*/
.chat-toggle-button {
  pointer-events: auto;
  /* Now it's clickable again */
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 9999;
  /* Keep it above other elements if needed */
}

/*
  3. Chat box with transition 
     ---------------------------------------------
     - Also re-enable pointer events (so user can type, click, etc.).
     - Position it in the bottom-right (desktop).
     - On mobile, we’ll override with `chat-overlay-mobile`.
*/
.chat-box {
  pointer-events: auto;
  /* Make the chat box interactive */
  position: absolute;
  bottom: 80px;
  right: 20px;

  width: 420px;
  height: 600px;
  border: 1px solid #ccc;
  background-color: transparent;
  /* Set to transparent if needed */
  display: flex;
  flex-direction: column;
  z-index: 10000;
}

/* 
  4. Mobile full-screen 
     ---------------------------------------------
*/
.chat-box--mobile {
  position: fixed !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  border: 0 !important;
  border-radius: 0 !important;
  bottom: 0 !important;
  right: 0 !important;
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
