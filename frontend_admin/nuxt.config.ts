import { defineNuxtConfig } from "nuxt/config";
import Aura from "@primeuix/themes/aura";
import { definePreset } from "@primeuix/themes";

const MyPreset = definePreset(Aura, {
  semantic: {
    colorScheme: {
      light: {
        primary: {
          color: "var(--tw-color-primary)",
          inverseColor: "var(--tw-color-white)",
          hoverColor: "var(--tw-color-primary-light)",
          activeColor: "var(--tw-color-primary-dark)",
          // Optional extra mapping:
          header: "var(--tw-color-primary-header)",
        },
        highlight: {
          background: "var(--tw-color-secondary)",
          focusBackground: "var(--tw-color-secondary-dark)",
          color: "var(--tw-color-white)",
          focusColor: "var(--tw-color-white)",
        },
        // Additional mappings based on your Tailwind theme:
        accent: {
          color: "var(--tw-color-accent)",
          dark: "var(--tw-color-accent-dark)",
        },
        neutral: {
          color: "var(--tw-color-neutral)",
          dark: "var(--tw-color-neutral-dark)",
          light: "var(--tw-color-neutral-light)",
        },
      },
      dark: {
        primary: {
          color: "var(--tw-color-primary)",
          inverseColor: "var(--tw-color-white)",
          hoverColor: "var(--tw-color-primary-light)",
          activeColor: "var(--tw-color-primary-dark)",
          header: "var(--tw-color-primary-header)",
        },
        highlight: {
          background: "var(--tw-color-secondary)",
          focusBackground: "var(--tw-color-secondary-dark)",
          color: "var(--tw-color-white)",
          focusColor: "var(--tw-color-white)",
        },
        accent: {
          color: "var(--tw-color-accent)",
          dark: "var(--tw-color-accent-dark)",
        },
        neutral: {
          color: "var(--tw-color-neutral)",
          dark: "var(--tw-color-neutral-dark)",
          light: "var(--tw-color-neutral-light)",
        },
      },
    },
  },
});
// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  spaLoadingTemplate: "spa-loading-template.html",

  app: {
    buildAssetsDir: "/admin/_nuxt/",
    head: {
      meta: [
        { charset: "UTF-8" },
        { "http-equiv": "Content-Security-Policy", content: "upgrade-insecure-requests" },
        { "http-equiv": "X-UA-Compatible", content: "IE=edge" },
      ],
      script: [{ src: "https://telegram.org/js/telegram-web-app.js" }],
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
        // {
        //   id: "theme-link",
        //   rel: "stylesheet",
        //   href: "/aura-light-cyan/theme.css",
        // },
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

  modules: ["@nuxtjs/tailwindcss", "@primevue/nuxt-module", "@nuxtjs/i18n", "@nuxtjs/color-mode", "nuxt-jsoneditor", "nuxt-maplibre"],

  jsoneditor: {
    componentName: "JsonEditor",
    includeCss: true,
    options: {
      /**
       *
       * SET GLOBAL OPTIONS
       *
       * */
    },
  },
  colorMode: {
    classSuffix: "",
    preference: "light",
  },

  i18n: {
    strategy: "no_prefix",
    defaultLocale: "en",
    locales: [
      { code: "en", name: "English", file: "en.json" }, // English
      { code: "de", name: "Deutsch", file: "de.json" },
      { code: "pl", name: "Polski", file: "pl.json" }, // Polish
      { code: "ru", name: "Русский", file: "ru.json" }, // Russian
      { code: "be", name: "Беларуская", file: "be.json" }, // Belarusian
      { code: "uk", name: "Українська", file: "uk.json" }, // Ukrainian
      { code: "ka", name: "ქართული", file: "ka.json" }, // Georgian
    ],

    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: "i18n_redirected",
      alwaysRedirect: false,
      fallbackLocale: "en",
    },
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
      isCustomElement: (tag) => ["vue-advanced-chat", "draggable"].includes(tag),
    },
  },

  //   primevue: {
  //     options: {
  //       theme: {
  //         options: {
  //           darkModeSelector: "light",
  //         }
  //       },
  //       ripple: true
  //     },
  //     cssLayerOrder: "reset, primevue, tailwind-base, tailwind-utilities",
  //     components: {
  //       exclude: ["Tag", "Terminal", "Form", "FormField", "LazyTag", "LazyTerminal", "LazyForm", "LazyFormField"],
  //     },
  // },

  primevue: {
    options: {
      theme: {
        preset: MyPreset,
        options: {
          darkModeSelector: ".dark",
        },
      },
    },
    //  cssLayerOrder: "reset, primevue, tailwind-base, tailwind-utilities",
    components: {
      exclude: ["Tag", "Terminal", "Form", "FormField", "LazyTag", "LazyTerminal", "LazyForm", "LazyFormField"],
    },
  },
  nitro: {
    routeRules: {
      "/chat": { headers: { "X-Frame-Options": "ALLOWALL" } },
    },
  },

  routeRules: {
    "/scripts/**": { headers: { "Cache-Control": "no-store, max-age=0" } },
  },

  devtools: { enabled: true },
  compatibilityDate: "2025-02-27",
});
