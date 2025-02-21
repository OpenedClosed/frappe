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
        // Primary green
        primary: '#458457',
        // A lighter tint of the primary green
        light: '#63a475',
        // A slightly darker green
        secondary: '#306345',
        // Even darker green
        secondaryDark: '#1e412c',
        // An orange accent (complementary to green)
        accent: '#FA7642',
        // Darker version of the accent
        accentDark: '#9E2D00',
        // Keep white as is
        white: '#FFFFFF',
      },
      fontFamily: {
        play: ['Play', 'sans-serif'],
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography"),
  ],
};
