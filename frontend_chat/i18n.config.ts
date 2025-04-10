// filepath: /Users/sergeisander/Documents/HotelsAiHub/frontend_chat/i18n.config.ts
import en from './locales/en.json';
import ru from './locales/ru.json';
import uk from './locales/uk.json';
import pl from './locales/pl.json';

export default defineI18nConfig(() => {
  let userLang = "en";
  if (process.client) {
    const browserLang = navigator.language || navigator.userLanguage;
    const shortLang = browserLang.split("-")[0];
    if (["en", "ru", "uk", "pl"].includes(shortLang)) {
      userLang = shortLang;
    }
  }

  const messages = {
    en,
    ru,
    uk,
    pl,
  };
  console.log('messages', messages);

  return {
    legacy: false,
    locale: userLang,
    fallbackLocale: "en",
    messages,
  };
});