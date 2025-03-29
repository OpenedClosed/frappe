import { useState } from "#app";

export const useAuthState = () => {
  const isAuthorized = useState("is-authorized", () => false);

  return { isAuthorized };
};
export const useURLState = () => {
  const currentUrl = useState("current-url", () => "");
  const currentFrontendUrl = useState("currentFrontendUrl", () => "");
  const showComponentImage = useState("showComponentImage", () => true);
  return { currentUrl, showComponentImage, currentFrontendUrl };
};
export const useSidebarState = () => {
  const isSidebarOpen = useState("isSidebarOpen", () => false);
  return { isSidebarOpen };
};
export const useLanguageState = () => {
  const currentLanguage = useState("currentLanguage", () => "en");
  return { currentLanguage };
};

export function useChatState() {
  const isAutoMode = useState("isAutoMode", () => true);

  return {
    isAutoMode,
  };
}
export function usePageState() {
  const currentPageName = useState("currentPageName", () => "admin");
  const currentPageInstances = useState("currentPageInstances", () => 0);

  return {
    currentPageName,
    currentPageInstances,
  };
}
