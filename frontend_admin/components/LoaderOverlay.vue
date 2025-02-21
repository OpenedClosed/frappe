<script setup>
import { ref } from 'vue';

// A reactive variable to control whether the loader is visible or not

const props = defineProps({
  isLoading: {
    type: Boolean,
    default: true,
  },
  finshText: {
    type: String,
    default: "Loading completed!",
  },
});
</script>

<style>
#spinner {
    width: 30px;
}

#spinner #sGD stop {
    stop-color: var(--main-red);
}

#spinner .path-solid {
    stroke: var(--main-red);
}
</style>

<template>
    <div>
        <div
            class="loading-overlay rounded-xl fixed inset-0 bg-black opacity-80 z-50 flex items-center justify-center ">
            <div class="w-full flex items-center justify-center h-10 my-4 opacity-100">
                <!-- Conditional rendering: If isLoading is true, show the spinner; otherwise, show the text -->
                <div v-if="isLoading">
                    <svg version="1.1" viewBox="0 0 64 64" width="1em" xmlns="http://www.w3.org/2000/svg" id="spinner">
                        <circle class="path-gradient" cx="32" cy="32" r="28" fill="none" stroke="url(#sGD)"
                            stroke-width="8" />
                        <path class="path-solid" d="M 32,4 A 28 28,0,0,0,32,60" fill="none" stroke="#000"
                            stroke-width="8" stroke-linecap="round" />

                        <defs>
                            <linearGradient id="sGD" gradientUnits="userSpaceOnUse" x1="32" y1="0" x2="32" y2="64">
                                <stop stop-color="#000" offset="0.1" stop-opacity="0" class="stop1"></stop>
                                <stop stop-color="#000" offset=".9" stop-opacity="1" class="stop2"></stop>
                            </linearGradient>
                        </defs>

                        <animateTransform values="0,0,0;360,0,0" attributeName="transform" type="rotate"
                            repeatCount="indefinite" dur="750ms">
                        </animateTransform>
                    </svg>
                </div>
                <div v-else class="text-white">
                    {{ finshText }}
                </div>
            </div>
        </div>
    </div>
</template>
