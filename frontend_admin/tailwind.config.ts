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
        primary: "var(--color-primary)",
        primaryLight: "var(--color-primary-light)",
        primaryDark: "var(--color-primary-dark)",

        secondary: "var(--color-secondary)",
        secondaryLight: "var(--color-secondary-light)",
        secondaryExtraLight: "var(--color-secondary-extra-light)",
        secondaryDark: "var(--color-secondary-dark)",

        accent: "var(--color-accent)",
        accentDark: "var(--color-accent-dark)",

        neutral: "var(--color-neutral)",
        neutralDark: "var(--color-neutral-dark)",
        neutralLight: "var(--color-neutral-light)",

        white: "var(--color-white)",
        black: "var(--color-black)",
      },
      fontFamily: {
        play: ['Play', 'sans-serif'],
      },
      boxShadow: {
        thicc: '0 8px 12px rgba(0, 0, 0, 0.6)', // darker, tighter shadow
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography"),
  ],
};
