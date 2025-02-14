/** @type {import('tailwindcss').Config} */
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  content: [
    "./components/**/*.{js,vue,ts}",
    "./layouts/**/*.vue",
    "./pages/**/*.vue",
    "./plugins/**/*.{js,ts}",
    "./app.vue",
    "./error.vue",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1089EA',      
        secondary: '#076497',    
        secondaryDark: '#033A55',
        accent: '#FA7642',       
        accentDark: '#9E2D00',   
        white: '#FFFFFF',
      },
      fontFamily: {
        play: ['Play', 'sans-serif'],
      },
    },
  },
  
  // corePlugins: {
  //   preflight: false,
  // },
  plugins: [
    require("@tailwindcss/typography"),
  ],
 
}
