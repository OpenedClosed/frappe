import axios from "axios";
import { defineNuxtPlugin, useCookie } from "nuxt/app";
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

  const token = useCookie("access_token");
  const csrfTokenCookie = useCookie("csrftoken");
  // console.log("token.value", token.value);
  // Reset Authorization header function
  const resetAuthorizationHeader = () => {
    delete api.defaults.headers.common["Authorization"];
  };

  // Initial setup of Authorization and CSRF headers
  const setupHeaders = () => {
    const myString = token.value;
    if (myString) {
      api.defaults.headers.common["Authorization"] = `Bearer ${myString}`;
    }

    const csrfToken = csrfTokenCookie.value;
    if (csrfToken) {
      api.defaults.headers.common["X-CSRFToken"] = csrfToken;
    }
  };

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
          const response = await api.post("api/admin/refresh").catch((err) => {
            reloadNuxtApp({ path: "/admin/login/", ttl: 1000 });
          });
          const myString = response.data.access_token;

          if (myString) {
            api.defaults.headers.common["Authorization"] = `Bearer ${myString}`;
            // Update the Authorization header for the retried request
            originalRequest.headers["Authorization"] = `Bearer ${myString}`;

            // Retry the original request
            return api(originalRequest);
          }
        } catch (err) {
          console.log(err.response ? err.response.data : err.message);
          reloadNuxtApp({ path: "/admin/login/", ttl: 1000 });
          resetAuthorizationHeader();
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
