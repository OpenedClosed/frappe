<template>
   <div class="flex ">

    <Button label="Train AI bot"
                    icon="pi pi-user" class="p-button-sm w-full" @click="toggleChat" />
    <div v-if="currentPageName === 'admin' && currentGroup === 'knowledge-base'" class="chat-overlay-container">
        <!-- Chat toggle button (always visible) -->


        <!-- Transition for smooth show/hide -->
        <transition name="fade">
            <!-- The actual chat box (visible only if `showChat` is true) -->
            <div v-if="isChatOpen" class="chat-box " :class="{ 'chat-overlay-mobile': isMobile }">
                <iframe :src="chatUrl" class="flex-1" style="border: none; z-index: 9999"></iframe>
                <Button @click="onClose" icon="pi pi-times" label="Close chat"></Button>
            </div>
        </transition>
    </div>
   </div>
</template> 
<script setup>
import { useI18n } from "#imports";
import { ref, computed, onMounted, onUnmounted } from "vue";
const route = useRoute();
const currentGroup = computed(() => route.params.group); // :group
const { currentPageName } = usePageState()
// Reactive variable to store the current window width
const windowWidth = ref(window.innerWidth);

// Function to update the window width
const updateWidth = () => {
    windowWidth.value = window.innerWidth;
};

// Set up the event listener on mount
onMounted(() => {
    window.addEventListener("resize", updateWidth);
});

// Remove the event listener on unmount
onUnmounted(() => {
    window.removeEventListener("resize", updateWidth);
});

// Use windowWidth in a computed property to determine if it's mobile
const isMobile = computed(() => windowWidth.value < 768);

// Existing reactive states and computed properties
const isLocalhost = window.location.hostname === "localhost";
const { currentFrontendUrl } = useURLState();
const chatUrl = isLocalhost ? `${currentFrontendUrl.value}/chats/telegram-chat` : `${currentFrontendUrl.value}/chats/telegram-chat`;
const isChatOpen = ref(false);
const toggleChat = () => {
    isChatOpen.value = !isChatOpen.value;
};
function onClose() {
    isChatOpen.value = false;
}


const { t } = useI18n();

let openLabel = computed(() => (isMobile.value ? "" : 'Open test chat'));
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
    width: 400px;
    height: 82vh;
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
