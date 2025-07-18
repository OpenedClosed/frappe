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
  const messagesLoaded = useState("messagesLoaded", () => false);
  const currentChatId = useState("currentChatId", () => "");
  const chatMessages = useState("chatMessages", () => []);

  return {
    isAutoMode,
    currentChatId,
    chatMessages,
    messagesLoaded,
  };
}

export const useHeaderState = () => {
  const botHeaderData = useState("botHeaderData", () => {});
  const rooms = useState("rooms", () => []);
  return { botHeaderData, rooms };
};

export function usePageState() {
  const initialIsAccountUnverified = typeof window !== "undefined" ? localStorage.getItem("initialIsAccountUnverified") || "" : "";
  const initialBannerText = typeof window !== "undefined" ? localStorage.getItem("crmBannerText") || "" : "";
  
  const currentPageName = useState("currentPageName", () => "admin");
  const currentPageInstances = useState("currentPageInstances", () => 0);
  const crmBannerText = useState("crmBannerText", () => initialBannerText);
  const isAccountUnverified = useState("isAccountUnverified", () => initialIsAccountUnverified);

  // Watch for changes and save to localStorage
  if (typeof window !== "undefined") {
    watch(crmBannerText, (val) => {
      localStorage.setItem("crmBannerText", val || "");
    });
    watch(isAccountUnverified, (val) => {
      localStorage.setItem("initialIsAccountUnverified", val || false);
    });
  }

  return {
    currentPageName,
    currentPageInstances,
    crmBannerText,
    isAccountUnverified,
  };
}
