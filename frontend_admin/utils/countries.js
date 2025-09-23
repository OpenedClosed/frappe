import worldCountries from 'world-countries';

const { currentLanguage } = useLanguageState();

// Функция для сопоставления языковых кодов с ключами переводов в world-countries
function getTranslationKey(languageCode) {
  const langMap = {
    'en': 'eng',
    'de': 'deu',
    'pl': 'pol', 
    'ru': 'rus',
    'be': 'bel',
    'uk': 'ukr',
    'ua': 'ukr',
    'ka': 'kat'
  };
  return langMap[languageCode] || 'eng';
}

// Приоритетные страны с кастомными настройками
const priorityCountries = {
  'PL': 1,
  'RU': 2,
  'UA': 3,
  'BY': 4,
  'DE': 5,
  'GE': 6,
  'KA': 7,
};

const exceptionCode = {
  'RU': '+7',
};

console.log('warldCountries', worldCountries);
// Генерация списка стран из world-countries
export const countries = worldCountries
  .filter(country => country.idd && country.idd.root && country.idd.suffixes && country.idd.suffixes.length > 0)
  .map(country => {
    const iso = country.cca2;
    const priority = priorityCountries[iso];
    
    // Формируем код страны из idd
    const callingCode = exceptionCode[iso] || country.idd.root + country.idd.suffixes[0];
    const mask = '999 999 999';
    const placeholder = '___ ___ ___';

    return {
      name: country.translations?.[getTranslationKey(currentLanguage.value)] || country.name.common,
      code: callingCode,
      iso: iso,
      mask: mask,
      placeholder: placeholder,
      flag: country.flag,
      priority: priority || 999,  // Не приоритетные страны в конце
    };
  })
  .sort((a, b) => {
    // Сначала по приоритету (меньше = выше)
    if (a.priority !== b.priority) {
      return a.priority - b.priority;
    }
  });