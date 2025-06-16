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

export const useProjectState = () => {
  /**
   * 🔑 The project slug you’re running right now.
   * Stored in Nuxt’s global reactive state so every component can read/update it.
   */
  const projectKey = useState('project-key', () => {
    // 1) Prefer an explicit env var set per deployment
    const { public: pub } = useRuntimeConfig()
    if (pub?.projectKey) return pub.projectKey        // e.g. 'dantist'

    // 2) Fallback: derive from the current host
    // Works both during SSR and on the client
    const host =
      process.server
        ? useRequestHeaders()[':host']                // SSR
        : window.location.hostname                    // Client

    if (!host) return 'unknown'

    if (host.includes('panamed-aihubworks.com')) return 'dantist'
    if (host.includes('nika.aihubworks.com'))    return 'hotel'
    if (host.includes('chat.aihubworks.com'))    return 'aihub'
    if (host.includes('denisdrive-aihub.com'))   return 'denisdrive'
    if (host.includes('aihubworks.com'))         return 'test'
    if (host.includes('localhost'))         return 'localhost'

    return 'unknown'
  })

  return { projectKey }
}
