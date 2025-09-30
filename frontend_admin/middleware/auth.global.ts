export default defineNuxtRouteMiddleware((to) => {
  const { isAuthorized } = useAuthState();
  const { currentPageName } = usePageState();

  // Use 'to.params' instead of useRoute()
  currentPageName.value = to.params.pagename || "admin";

  console.log("isAuthorized", isAuthorized.value);
});
