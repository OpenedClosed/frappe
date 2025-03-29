export default defineNuxtRouteMiddleware((to) => {
  const { isAuthorized } = useAuthState();
  const { currentPageName } = usePageState();

  console.log("isAuthorized", isAuthorized.value);

  // if ((isAuthorized.value && (to.path.includes("/login")) || to.path.includes("/registration"))) {
  //   return navigateTo(`/${currentPageName.value}`);
  // }
  // console.log("to.path", to.path);
  // if (!isAuthorized.value && !["/login", "/registration"].some((path) => to.path.includes(path))) {
  //   // return navigateTo(`/${currentPageName.value}/login`);
  // }
});
