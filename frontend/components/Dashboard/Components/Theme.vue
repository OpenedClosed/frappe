<template>
  <div>
    <Button text :icon="colorMode.preference === 'dark' ? 'pi pi-sun' : 'pi pi-moon'" @click="toggleTheme"
      class="w-full h-10 outline hover:bg-secondaryDark outline-primary">
      <i v-if="!colorMode.preference === 'dark'" :class="colorMode.preference === 'dark' ? 'pi pi-sun' : 'pi pi-moon'"
        class="text-white"></i>
      <i v-else :class="colorMode.preference === 'dark' ? 'pi pi-sun' : 'pi pi-moon'" class="text-white"></i>
    </Button>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
const colorMode = useColorMode();

const colorModeClass = ref("");

function toggleTheme() {
  colorMode.preference = colorMode.preference === "dark" ? "light" : "dark";
  updateTheme();
}

function updateTheme() {
  const systemTheme =
    colorMode.preference != "dark" ? "aura-light-cyan" : "aura-dark-cyan";
  //console.log("systemTheme", systemTheme)
  const themeLink = document.getElementById("theme-link");
  //console.log(themeLink)
  themeLink.setAttribute("href", `/${systemTheme}/theme.css`);
  //console.log(themeLink)
}

// Initialize theme on mount
updateTheme();
</script>
