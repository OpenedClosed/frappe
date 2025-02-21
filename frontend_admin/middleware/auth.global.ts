export default defineNuxtRouteMiddleware(async (to, from) => {
  const { isAuthorized } = useAuthState();
  const { currentUrl } = useURLState();
  const { currentLanguage } = useLanguageState();

  currentUrl.value =
    window.location.hostname === "localhost" ? "http://localhost:8000" : `${window.location.protocol}//${window.location.hostname}`;

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
    await useNuxtApp().$api.get(`api/admin/info`);
    isAuthorized.value = true;
    console.log("User is authorized.");
  } catch (err) {
    console.log("Authorization check failed:", err.message);
    if (err.request.status === 401 && refresh_token.value) {
      try {
        const response = await useNuxtApp().$api.post("api/admin/refresh/");
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

  if (isAuthorized.value && to.path === "/admin/login/") {
    return navigateTo("/admin");
  } else if (!isAuthorized.value && !to.path.startsWith("/admin/login")) {
    return navigateTo("/admin/login/");
  }
});
