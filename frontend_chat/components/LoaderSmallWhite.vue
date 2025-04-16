<template>
  <div>
    <div class="">
      <svg id="spinner" version="1.1" viewBox="0 0 64 64" width="1em" xmlns="http://www.w3.org/2000/svg">
        <circle class="path-gradient" cx="32" cy="32" r="28" fill="none" stroke="url(#sGD)" stroke-width="8" />
        <path
          class="path-solid"
          d="M 32,4 A 28 28,0,0,0,32,60"
          fill="none"
          stroke="#FF66C4"
          stroke-width="8"
          stroke-linecap="round"
        />

        <defs>
          <linearGradient id="sGD" gradientUnits="userSpaceOnUse" x1="32" y1="0" x2="32" y2="64">
            <stop offset="0.1" stop-opacity="0" class="stop1"></stop>
            <stop offset=".9" stop-opacity="1" class="stop2"></stop>
          </linearGradient>
        </defs>

        <animateTransform
          values="0,0,0;360,0,0"
          attributeName="transform"
          type="rotate"
          repeatCount="indefinite"
          dur="750ms"
        ></animateTransform>
      </svg>
    </div>
  </div>
</template>

<style scoped>
  #spinner {
    width: 25px;
  }

  #spinner .path-gradient {
    stroke: url(#sGD);
  }

  #spinner .path-solid {
    stroke: white;
  }

  .dark #spinner .path-solid {
    stroke: white;
  }

  #spinner #sGD stop {
    stop-color: white;
  }

  .dark #spinner #sGD stop {
    stop-color: white;
  }
</style>
