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


export function useChatState() {
  const currentUserId = useState("currentUserId", () => "1234");
  const activeRoomId = useState("activeRoomId", () => "1");
  const rooms = useState("rooms", () => []);
  const messages = useState("messages", () => []);
  const messagesLoaded = useState("messagesLoaded", () => false);
  const websocket = useState<any>("websocket", () => null);
  const currenChatId = useState("currenChatId", () => "");
  
  // Логика выбора (choiceOptions, strict)
  const choiceOptions = useState("choiceOptions", () => []);
  const isChoiceStrict = useState("isChoiceStrict", () => false);
  
  // Таймер
  const timerExpired = useState("timerExpired", () => false);
  const countdown = useState("countdown", () => 0);

  return {
    currentUserId,
    activeRoomId,
    rooms,
    messages,
    messagesLoaded,
    websocket,
    currenChatId,
    choiceOptions,
    isChoiceStrict,
    timerExpired,
    countdown,
  };
}

