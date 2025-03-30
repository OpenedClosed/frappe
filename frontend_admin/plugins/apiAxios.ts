import axios from "axios";
import { defineNuxtPlugin, navigateTo, useCookie } from "nuxt/app";
import { ref } from "vue";

export default defineNuxtPlugin((nuxtApp) => {
  let defaultUrl;
  let first_time = ref(true);
  if (window.location.hostname === "localhost") {
    defaultUrl = "http://localhost:8000/";
  } else {
    defaultUrl = window.location.protocol + "//" + window.location.hostname + "/";
  }

  const api = axios.create({
    baseURL: defaultUrl,
    withCredentials: true,
    headers: {
      common: {},
    },
  });

  const csrfTokenCookie = useCookie("csrftoken");
  // console.log("token.value", token.value);
  // Reset Authorization header function
  const resetAuthorizationHeader = () => {
    delete api.defaults.headers.common["Authorization"];
  };

  // Initial setup of Authorization and CSRF headers
  const setupHeaders = () => {
    const token = useCookie("access_token");
    const myString = token.value;
    if (myString) {
      api.defaults.headers.common["Authorization"] = `Bearer ${myString}`;
    }

    const csrfToken = csrfTokenCookie.value;
    if (csrfToken) {
      api.defaults.headers.common["X-CSRFToken"] = csrfToken;
    }
  };
  function redirectToLoginIfNeeded() {
    const currentRoute = window.location.pathname;
    if (!currentRoute.includes("login") && !currentRoute.includes("registration")) {
      reloadNuxtApp({ path: `/${currentPageName.value}/login/`, ttl: 1000 });
    }
  }

  setupHeaders();

  // ----- Request Interceptor -----
  api.interceptors.request.use(
    async (config) => {
      // If the request is going to api/auth/login, remove the Authorization header
      if (config.url && config.url.includes("api/auth/login")) {
        delete config.headers.Authorization;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );
  api.interceptors.request.use(
    async (config) => {
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );
  const { currentPageName } = usePageState();
  // ----- Request Interceptor #2 (for refresh) -----
  // This will remove Authorization ONLY when requesting api/auth/refresh.
  api.interceptors.request.use(
    (config) => {
      if (config.url && config.url.includes(`api/${currentPageName.value}/refresh`)) {
        console.log("Removing Authorization header for refresh request.");
        delete config.headers.Authorization;
      }
      return config;
    },
    (error) => {
      console.error("Request Interceptor #2 Error:", error);
      return Promise.reject(error);
    }
  );

  api.interceptors.response.use(
    (response) => {
      return response;
    },
    async (error) => {
      const originalRequest = error.config;

      if (error.response && error.response.status === 401 && first_time.value && !originalRequest._retry) {
        originalRequest._retry = true;
        first_time.value = false;

        resetAuthorizationHeader();

        try {
          const token = useCookie("access_token");

          if (token.value) {
            const response = await api.post(`api/${currentPageName.value}/refresh`).catch((err) => {
              console.log("Axioserror 1");
              redirectToLoginIfNeeded();
            });
            const myString = token.value;

            if (myString) {
              api.defaults.headers.common["Authorization"] = `Bearer ${myString}`;
              originalRequest.headers["Authorization"] = `Bearer ${myString}`;
              return api(originalRequest); // Retry the original request
            }
          }
        } catch (err) {
          console.log(err.response ? err.response.data : err.message);
          console.log("Axioserror 2");
          redirectToLoginIfNeeded();
          resetAuthorizationHeader();
        }
      } else {
        console.log("error.response", error.response);
        if(error.response && (error.response.status === 403 || error.response.status === 401)) {
        redirectToLoginIfNeeded();
        }
      }
      return Promise.reject(error);
    }
  );

  return {
    provide: {
      api: api,
      resetAuthorizationHeader,
    },
  };
});
