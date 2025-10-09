// Composable для валидации имен и фамилий
import { debounce } from 'lodash';

export const useNameValidation = () => {
  // Регулярное выражение для валидации имен (латинские + европейские диакритические символы)
  const nameValidationRegex = /^[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻáàâäãåéèêëíìîïóòôöõúùûüýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÝŸçćčşşğÇĆČŞĞñÑđĐðÐ]+$/;
  
  const { t } = useI18n();
  
  /**
   * Валидация имени/фамилии
   * @param {string} name - Имя для валидации
   * @param {string} fieldName - Название поля (firstName или lastName)
   * @returns {string|null} - Ключ ошибки или null если ошибок нет
   */
  function validateName(name, fieldName) {
    const trimmedName = name.trim();
    
    if (trimmedName.length < 2) {
      return `PersonalMainRegistration.${fieldName}TooShort`;
    }
    
    if (trimmedName.length > 50) {
      return `PersonalMainRegistration.${fieldName}TooLong`;
    }
    
    if (!nameValidationRegex.test(trimmedName)) {
      return `PersonalMainRegistration.${fieldName}Invalid`;
    }
    
    return null; // нет ошибки
  }
  
  /**
   * Форматирование имени (первая буква заглавная, остальные строчные)
   * @param {string} name - Имя для форматирования
   * @returns {string} - Отформатированное имя
   */
  function formatName(name) {
    const trimmed = name.trim();
    if (trimmed.length === 0) return trimmed;
    return trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase();
  }
  
  /**
   * Создает debounced функцию валидации
   * @param {function} validationFn - Функция валидации
   * @param {number} delay - Задержка в мс (по умолчанию 300)
   * @returns {function} - Debounced функция валидации
   */
  function createDebouncedValidator(validationFn, delay = 300) {
    return debounce(validationFn, delay);
  }
  
  /**
   * Проверка, является ли символ допустимым для имени
   * @param {string} char - Символ для проверки
   * @returns {boolean} - true если символ допустим
   */
  function isValidNameChar(char) {
    return nameValidationRegex.test(char);
  }
  
  return {
    validateName,
    formatName,
    createDebouncedValidator,
    isValidNameChar,
    nameValidationRegex
  };
};