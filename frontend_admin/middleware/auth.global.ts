export default defineNuxtRouteMiddleware((to) => {
  const { isAuthorized } = useAuthState();
  const { currentPageName } = usePageState();

  console.log("isAuthorized", isAuthorized.value);
});
