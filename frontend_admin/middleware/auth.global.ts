export default defineNuxtRouteMiddleware((to) => {
  const { isAuthorized } = useAuthState();
  const { currentPageName } = usePageState();
  const route = useRoute();
  currentPageName.value = route.params.pagename || "admin";

  console.log("isAuthorized", isAuthorized.value);
});
