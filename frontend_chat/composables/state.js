import { useState } from "#app";

export const useAuthState = () => {
  const isAuthorized = useState("is-authorized", () => false);

  return { isAuthorized };
};
export const useURLState = () => {
  const currentUrl = useState("current-url", () => "");
  const showComponentImage = useState("showComponentImage", () => true);
  return { currentUrl, showComponentImage };
};
export const useSidebarState = () => {
  const isSidebarOpen = useState("isSidebarOpen", () => false);
  return { isSidebarOpen };
};
export const useLanguageState = () => {
  const currentLanguage = useState("currentLanguage", () => "en");
  return { currentLanguage };
};
export const useHeaderState = () => {
  const botHeaderData = useState("botHeaderData", () => {});
  const rooms = useState("rooms", () => []);
  return { botHeaderData, rooms };
};

export function useChatState() {
  const isAutoMode = useState("isAutoMode", () => true);
  const messagesLoaded = useState("messagesLoaded", () => false);
  const currentChatId = useState("currentChatId", () => '');
  const chatMessages = useState("chatMessages", () => []);

  return {
    isAutoMode,
    currentChatId,
    chatMessages,
    messagesLoaded,
  };
}

