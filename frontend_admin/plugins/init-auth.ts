export default defineNuxtPlugin(async (nuxtApp) => {
  const { isAuthorized } = useAuthState();
  const { currentUrl, currentFrontendUrl } = useURLState();
  const { currentPageName } = usePageState();
  const route = useRoute();

  // Set initial currentPageName
  const pagename = route.params.pagename || "admin";
  currentPageName.value = pagename;

  currentUrl.value =
    window.location.hostname === "localhost" ? "http://localhost:8000" : `${window.location.protocol}//${window.location.hostname}`;

  // Auth check logic
  const token = useCookie("access_token");
  const refresh_token = useCookie("refresh_token");

  try {
    await nuxtApp.$api.get(`api/users/me`);
    isAuthorized.value = true;
  } catch (err) {
    if (err?.request?.status === 401 && refresh_token.value) {
      try {
        const response = await nuxtApp.$api.post(`api/${currentPageName.value}/refresh/`);
        const newAccessToken = response.data.access_token;
        if (newAccessToken) {
          nuxtApp.$api.defaults.headers.common["Authorization"] = `Bearer ${newAccessToken}`;
          isAuthorized.value = true;
        }
      } catch {
        isAuthorized.value = false;
      }
    } else {
      isAuthorized.value = false;
    }
  }
});
