import { defineNuxtConfig } from "nuxt/config";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  // spaLoadingTemplate: "spa-loading-template.html",
  // app: {
  //   head: {
  //     // title: "",
  //     meta: [
  //       { charset: "UTF-8" },
  //       // {
  //       //   name: "",
  //       //   content:
  //       //     "description",
  //       // },
  //       { "http-equiv": "Content-Security-Policy", content: "upgrade-insecure-requests" },
  //       { "http-equiv": "X-UA-Compatible", content: "IE=edge" },
  //       // { property: "og:image", content: "/banner-main.png" },
  //     ],
  //     script: [
  //       { src: "https://telegram.org/js/telegram-web-app.js" },
  //     ],
  //     link: [
  //       {
  //         rel: "preconnect",
  //         href: "https://fonts.gstatic.com",
  //         crossorigin: "anonymous",
  //       },
  //       {
  //         href: "https://fonts.googleapis.com/css2?family=Play:wght@400;700&display=swap",
  //         rel: "stylesheet",
  //       },
  //       {
  //         href: "https://cdn.jsdelivr.net/gh/lipis/flag-icons@7.0.0/css/flag-icons.min.css",
  //         rel: "stylesheet",
  //         crossorigin: "anonymous",
  //       },
  //       {
  //         id: "theme-link",
  //         rel: "stylesheet",
  //         href: "/aura-light-cyan/theme.css",
  //       },
  //     ],
  //   },
  // },

  spaLoadingTemplate: "spa-loading-template.html",

  app: {
    buildAssetsDir: "/admin/_nuxt/",
    head: {
      meta: [
        { charset: "UTF-8" },
        { "http-equiv": "Content-Security-Policy", content: "upgrade-insecure-requests" },
        { "http-equiv": "X-UA-Compatible", content: "IE=edge" },
      ],
      script: [
        { src: "https://telegram.org/js/telegram-web-app.js" },
      ],
      link: [
        {
          rel: "preconnect",
          href: "https://fonts.gstatic.com",
          crossorigin: "anonymous",
        },
        {
          href: "https://fonts.googleapis.com/css2?family=Play:wght@400;700&display=swap",
          rel: "stylesheet",
        },
        {
          href: "https://cdn.jsdelivr.net/gh/lipis/flag-icons@7.0.0/css/flag-icons.min.css",
          rel: "stylesheet",
          crossorigin: "anonymous",
        },
        {
          id: "theme-link",
          rel: "stylesheet",
          href: "/aura-light-cyan/theme.css",
      },
    ],
  },
},

  ssr: false,

  // alias: {
  //   "@": resolve(__dirname, "/"),
  // },
  css: [
    // "~/assets/themes/theme.css",
    "~/assets/css/tailwind.css",
    "~/node_modules/primeicons/primeicons.css",
  ],

  modules: [
    "@nuxtjs/tailwindcss",
    "nuxt-primevue",
    "@nuxtjs/i18n",
    "@nuxtjs/color-mode",
    'nuxt-jsoneditor',
    "nuxt-maplibre",
  ],

  jsoneditor: {
    componentName: 'JsonEditor',
    includeCss: true,
    options: {
        /**
        *
        * SET GLOBAL OPTIONS
        * 
        * */
    }
  },
  colorMode: {
    classSuffix: "",
    preference: "light",
  },

  i18n: {
    vueI18n: "./i18n.config.ts", // if you are using custom path, default
  },

  pinia: {
    storesDirs: ["./stores/**", "./custom-folder/stores/**"],
  },

  postcss: {
    plugins: {
      tailwindcss: {
        plugins: [require("@tailwindcss/typography")],
      },
      autoprefixer: {},
    },
  },

  // extends: ['nuxt-umami'],
  vue: {
    compilerOptions: {
      isCustomElement: (tag) => ["vue-advanced-chat","draggable"].includes(tag),
    },
  },

  primevue: {
    cssLayerOrder: "tailwind-base, primevue, tailwind-utilities",   
  },
 

  nitro: {
    routeRules: {
      '/chat': { headers: { 'X-Frame-Options': 'ALLOWALL' } },
    },
  },

  routeRules: {
    '/scripts/**': { headers: { 'Cache-Control': 'no-store, max-age=0' } }
  },

  devtools: { enabled: true },
  compatibilityDate: "2025-02-27",
});