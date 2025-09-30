export default defineNuxtRouteMiddleware(async (to, from) => {
  const { isAuthorized } = useAuthState();
  const { currentUrl } = useURLState();
  const { currentLanguage } = useLanguageState();

  currentUrl.value =
    window.location.hostname === "localhost"
      ? "http://localhost:8000"
      : `${window.location.protocol}//${window.location.hostname}`;

  const refresh_token = useCookie("refresh_token");
  const token = useCookie("access_token");

  if (process.client) {
    const browserLang = navigator.language || navigator.userLanguage;
    const shortLang = browserLang.split("-")[0];
    if (["en", "ru", "uk", "pl"].includes(shortLang)) {
      currentLanguage.value = shortLang;
    }
  }
});
