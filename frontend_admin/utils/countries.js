import { countries as countryData } from 'country-codes-flags-phone-codes';

const { currentLanguage } = useLanguageState();

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

// Генерация списка стран из country-codes-flags-phone-codes
export const countries = countryData
  .map(country => {
    const iso = country.code;
    const priority = priorityCountries[iso];
    
    // Используем готовый dialCode из новой библиотеки или исключения
    const callingCode = country.dialCode;
    const mask = '999 999 999';
    const placeholder = '___ ___ ___';

    return {
      name: country.name, // Уже локализовано в библиотеке
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