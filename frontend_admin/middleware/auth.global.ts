import { useRoute } from "vue-router";

export default defineNuxtRouteMiddleware(async (to, from) => {
  const { isAuthorized } = useAuthState();
  const { currentUrl,currentFrontendUrl } = useURLState();
  const { currentLanguage } = useLanguageState();

  const { currentPageName } = usePageState();
  const route = useRoute();

  //TODO: РЕШИТЬ ПРОБЛЕМУ С currentPageName становится undefined
  if (route.params.pagename === undefined) {
    console.log("Current page name:", route.params.pagename);
    currentPageName.value = "admin";
  } else if (route.params.pagename) {
    currentPageName.value = route.params.pagename || "admin";
  }

  if (process.client) {
    if (currentPageName.value === "personal_account") {
      // Set the main green color and its variations
      document.documentElement.style.setProperty("--color-primary", "#255F38"); // Main color
      document.documentElement.style.setProperty("--color-primary-light", "#4C8F6D"); // Lighter shade
      document.documentElement.style.setProperty("--color-primary-dark", "#1D4328"); // Darker shade

      // Secondary colors: complementary shades in the green family
      document.documentElement.style.setProperty("--color-secondary", "#2E7D32");
      document.documentElement.style.setProperty("--color-secondary-light", "#60AD5E");
      document.documentElement.style.setProperty("--color-secondary-dark", "#1B5E20");

      // Accent colors: additional green accents
      document.documentElement.style.setProperty("--color-accent", "#6FBF73");
      document.documentElement.style.setProperty("--color-accent-dark", "#3D7B43");

      // Optional: Update neutral colors to a subtle greenish tint
      document.documentElement.style.setProperty("--color-neutral", "#E8F5E9");
      document.documentElement.style.setProperty("--color-neutral-dark", "#C8E6C9");
      document.documentElement.style.setProperty("--color-neutral-light", "#F1F8E9");
    }
  }

  currentUrl.value =
    window.location.hostname === "localhost" ? "http://localhost:8000" : `${window.location.protocol}//${window.location.hostname}`;
  currentFrontendUrl.value = window.location.hostname === "localhost" ? "http://localhost:4000" : `${window.location.protocol}//${window.location.hostname}`;

  const refresh_token = useCookie("refresh_token");
  const token = useCookie("access_token");

  if (process.client) {
    const browserLang = navigator.language || navigator.userLanguage;
    const shortLang = browserLang.split("-")[0];
    if (["en", "ru", "uk", "pl"].includes(shortLang)) {
      currentLanguage.value = shortLang;
    }
  }

  console.log("Current URL:", currentUrl.value);
  console.log("Access Token:", token.value);
  console.log("Refresh Token:", refresh_token.value);

  try {
    await useNuxtApp().$api.get(`api/${currentPageName.value}/info`);
    isAuthorized.value = true;
    console.log("User is authorized.");
  } catch (err) {
    console.log("Authorization check failed:", err.message);
    if (err.request.status === 401 && refresh_token.value) {
      try {
        const response = await useNuxtApp().$api.post(`api/${currentPageName.value}/refresh/`);
        const newAccessToken = response.data.access_token;
        if (newAccessToken) {
          useNuxtApp().$api.defaults.headers.common["Authorization"] = `Bearer ${newAccessToken}`;
          isAuthorized.value = true;
          console.log("Token refreshed successfully.");
        }
      } catch (refreshErr) {
        console.log("Token refresh failed:", refreshErr.message);
        isAuthorized.value = false;
      }
    } else {
      isAuthorized.value = false;
    }
  }
  console.log(
    "isAuthorized.value && (to.path === `/login` || to.path === `/register`)",
    isAuthorized.value && (to.path === `/login` || to.path === `/register`)
  );
  console.log(
    "!isAuthorized.value && (!to.path.includes(`/login`) && !to.path.includes(`/register`))",
    !isAuthorized.value && !to.path.includes(`/login`) && !to.path.includes(`/register`)
  );
  if (isAuthorized.value && (to.path === `/login` || to.path === `/register`)) {
    return navigateTo(`/${currentPageName.value}`);
  } else if (!isAuthorized.value && !to.path.includes(`/login`) && !to.path.includes(`/register`)) {
    if (to.path.includes("login")) {
      return navigateTo(`/login`);
    } else if (to.path.includes("register")) {
      return navigateTo(`/register`);
    }
  }
});
