/** @type {import('tailwindcss').Config} */
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
        primary: "var(--tw-color-primary)",
        primaryLight: "var(--tw-color-primary-light)",
        primaryDark: "var(--tw-color-primary-dark)",
        primaryHeader: "var(--tw-color-primary-header)",

        secondary: "var(--tw-color-secondary)",
        secondaryLight: "var(--tw-color-secondary-light)",
        secondaryExtraLight: "var(--tw-color-secondary-extra-light)",
        secondaryDark: "var(--tw-color-secondary-dark)",

        accent: "var(--tw-color-accent)",
        accentDark: "var(--tw-color-accent-dark)",

        neutral: "var(--tw-color-neutral)",
        neutralDark: "var(--tw-color-neutral-dark)",
        neutralLight: "var(--tw-color-neutral-light)",

        white: "var(--tw-color-white)",
        black: "var(--tw-color-black)",
      },
      fontFamily: {
        play: ['Play', 'sans-serif'],
      },
      boxShadow: {
        thicc: '0 8px 12px rgba(0, 0, 0, 0.6)',
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography"),
  ],
};
