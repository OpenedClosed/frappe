# Техническое задание: Конструктор форм для платформы Dantist

## Обзор проекта

Данное ТЗ расширяет базовые требования с учетом существующей архитектуры проекта Dantist. Проект уже содержит развитую систему динамических форм с компонентом `DynamicForm` и `MainForm`, которые будут использованы как основа для конструктора.

## Анализ существующей архитектуры

### Текущие компоненты форм:
- **DynamicForm** - основной компонент рендеринга форм с поддержкой группировки полей
- **MainForm** - контроллер форм с CRUD операциями
- **InlineList** - компонент для встроенных списков
- Специализированные view-компоненты для разных типов данных

### Существующие типы полей:
- `string`, `email`, `phone`, `password`
- `select`, `multiselect`, `checkbox`, `checkbox_group`
- `textarea`, `json`, `wysiwyg`
- `calendar`, `calendar_time`, `datetime`
- `file`, `multifile`, `image`, `multiimage`
- `rating`, `range_value`, `tag_cloud`
- `autocomplete`, `location`
- `drag_and_drop`

### Текущая структура данных поля:
```typescript
interface FieldDefinition {
  name: string;
  type: string;
  title: Record<string, string>; // многоязычные заголовки
  help_text?: Record<string, string>;
  required?: boolean;
  read_only?: boolean;
  default?: any;
  choices?: Array<{value: any, label: string}>;
  settings?: Record<string, any>;
}

interface FieldGroup {
  title: Record<string, string>;
  help_text?: Record<string, string>;
  fields: string[]; // массив имен полей
}
```

## Цель

Создать интуитивный конструктор форм, интегрированный с существующей системой, позволяющий визуально создавать и редактировать формы через drag-and-drop интерфейс.

## Основные задачи

### 0. Подготовительный этап: Рефакторинг DynamicForm (ПРИОРИТЕТ 1)
Перед созданием конструктора форм необходимо провести рефакторинг существующего компонента `DynamicForm` для улучшения архитектуры и переиспользования.

#### 0.1 Создание отдельных компонентов для каждого типа поля
Разбить монолитный `DynamicForm` на отдельные компоненты для каждого типа поля:

```vue
<!-- Текущая структура в DynamicForm.vue -->
<Dropdown v-if="field.type === 'select'" ... />
<MultiSelect v-else-if="field.type === 'multiselect'" ... />
<InputText v-else-if="field.type === 'string'" ... />

<!-- Новая структура -->
<FieldRenderer :field="field" :value="internalValue[field.name]" @update="updateField" />
```

#### 0.2 Структура компонентов полей
```
components/Dashboard/Components/Form/Fields/
├── FieldRenderer.vue              # Главный рендерер полей
├── BaseField.vue                  # Базовый компонент с общей логикой
├── TextField/
│   ├── StringField.vue           # Текстовое поле
│   ├── EmailField.vue            # Email поле
│   ├── PhoneField.vue            # Телефон с маской
│   ├── PasswordField.vue         # Пароль
│   └── TextareaField.vue         # Многострочный текст
├── SelectField/
│   ├── DropdownField.vue         # Одиночный выбор
│   ├── MultiSelectField.vue      # Множественный выбор
│   ├── AutoCompleteField.vue     # Автодополнение
│   └── TagCloudField.vue         # Облако тегов
├── InputField/
│   ├── CheckboxField.vue         # Чекбокс
│   ├── CheckboxGroupField.vue    # Группа чекбоксов
│   ├── BooleanField.vue          # Булево поле
│   └── RatingField.vue           # Рейтинг
├── DateField/
│   ├── CalendarField.vue         # Дата
│   ├── CalendarTimeField.vue     # Дата и время
│   └── DateTimeField.vue         # Datetime
├── FileField/
│   ├── FileUploadField.vue       # Одиночный файл
│   ├── MultiFileField.vue        # Множественные файлы
│   ├── ImageField.vue            # Одиночное изображение
│   └── MultiImageField.vue       # Множественные изображения
├── SpecialField/
│   ├── JsonField.vue             # JSON редактор
│   ├── LocationField.vue         # Карта/локация
│   ├── RangeField.vue            # Слайдер диапазона
│   ├── DragDropField.vue         # Drag and drop
│   └── WysiwygField.vue          # WYSIWYG редактор
└── index.js                      # Экспорт всех компонентов
```

#### 0.3 Базовый интерфейс FieldComponent
```typescript
// types/field-components.ts
export interface FieldComponentProps {
  field: FieldDefinition;
  modelValue: any;
  disabled?: boolean;
  readonly?: boolean;
  errors?: string | Record<string, string>;
  currentLanguage?: string;
}

export interface FieldComponentEmits {
  'update:modelValue': [value: any];
  'focus': [event: FocusEvent];
  'blur': [event: FocusEvent];
  'change': [value: any];
}

export interface BaseFieldComponent {
  props: FieldComponentProps;
  emits: FieldComponentEmits;
  validate?: () => boolean;
  reset?: () => void;
  focus?: () => void;
}
```

#### 0.4 BaseField.vue - общий родительский компонент
```vue
<template>
  <div class="field-wrapper" :class="fieldWrapperClasses">
    <!-- Лейбл поля -->
    <label 
      v-if="showLabel" 
      :for="fieldId" 
      class="field-label"
      :class="labelClasses"
    >
      {{ getLocalizedTitle() }}
      
      <!-- Иконка помощи -->
      <span
        v-if="field.help_text"
        class="help-icon"
        v-tooltip="getLocalizedHelpText()"
      >
        <i class="pi pi-question-circle"></i>
      </span>
      
      <!-- Обязательное поле -->
      <span v-if="field.required" class="required-indicator">*</span>
    </label>

    <!-- Содержимое поля (слот) -->
    <div class="field-content" :class="contentClasses">
      <slot 
        :fieldId="fieldId"
        :isInvalid="isInvalid"
        :getLocalizedTitle="getLocalizedTitle"
        :emitUpdate="emitUpdate"
      />
      
      <!-- Кнопка сброса для некоторых полей -->
      <Button
        v-if="showResetButton"
        @click="resetField"
        icon="pi pi-times"
        class="field-reset-button"
        size="small"
        text
      />
    </div>

    <!-- Ошибки валидации -->
    <div 
      v-if="errorMessage" 
      :id="`${fieldId}-error`"
      class="field-error"
    >
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue';
import type { FieldComponentProps, FieldComponentEmits } from '@/types/field-components';

const props = withDefaults(defineProps<FieldComponentProps>(), {
  disabled: false,
  readonly: false,
  currentLanguage: 'en'
});

const emit = defineEmits<FieldComponentEmits>();

const fieldId = useId();

// Вычисляемые свойства
const isInvalid = computed(() => Boolean(props.errors));
const errorMessage = computed(() => {
  if (!props.errors) return '';
  if (typeof props.errors === 'string') return props.errors;
  return props.errors[props.currentLanguage] || props.errors.en || '';
});

// Методы
const getLocalizedTitle = () => {
  return props.field.title[props.currentLanguage] || props.field.title.en || '';
};

const getLocalizedHelpText = () => {
  if (!props.field.help_text) return '';
  return props.field.help_text[props.currentLanguage] || props.field.help_text.en || '';
};

const emitUpdate = (value: any) => {
  emit('update:modelValue', value);
  emit('change', value);
};

const resetField = () => {
  emit('update:modelValue', props.field.default || null);
};

// CSS классы
const fieldWrapperClasses = computed(() => ({
  'field-wrapper--invalid': isInvalid.value,
  'field-wrapper--disabled': props.disabled,
  'field-wrapper--readonly': props.readonly,
  [`field-wrapper--${props.field.type}`]: true
}));

const labelClasses = computed(() => ({
  'field-label--required': props.field.required
}));

const contentClasses = computed(() => ({
  'field-content--invalid': isInvalid.value
}));

const showLabel = computed(() => props.field.type !== 'boolean');
const showResetButton = computed(() => 
  !props.disabled && 
  !props.readonly && 
  ['select', 'string', 'email'].includes(props.field.type) &&
  props.modelValue
);
</script>
```

#### 0.5 Пример StringField.vue
```vue
<template>
  <BaseField 
    :field="field" 
    :model-value="modelValue"
    :disabled="disabled"
    :readonly="readonly"
    :errors="errors"
    :current-language="currentLanguage"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #default="{ fieldId, isInvalid, emitUpdate }">
      <InputText
        :id="fieldId"
        :model-value="localizedValue"
        :disabled="disabled || readonly"
        :class="{ 'p-invalid': isInvalid }"
        :placeholder="getPlaceholder()"
        class="w-full"
        @update:model-value="updateLocalizedValue"
      />
    </template>
  </BaseField>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import BaseField from '../BaseField.vue';
import InputText from 'primevue/inputtext';
import type { FieldComponentProps, FieldComponentEmits } from '@/types/field-components';

const props = defineProps<FieldComponentProps>();
const emit = defineEmits<FieldComponentEmits>();

// Локализация значений
const localizedValue = computed(() => {
  if (!props.modelValue) return '';
  if (typeof props.modelValue === 'object') {
    return props.modelValue[props.currentLanguage] || props.modelValue.en || '';
  }
  return props.modelValue;
});

const updateLocalizedValue = (newValue: string) => {
  if (typeof props.modelValue === 'object') {
    const updated = { ...props.modelValue };
    updated[props.currentLanguage] = newValue;
    emit('update:modelValue', updated);
  } else {
    emit('update:modelValue', newValue);
  }
};

const getPlaceholder = () => {
  if (!props.field.placeholder) return '';
  if (typeof props.field.placeholder === 'object') {
    return props.field.placeholder[props.currentLanguage] || props.field.placeholder.en || '';
  }
  return props.field.placeholder;
};
</script>
```

#### 0.6 FieldRenderer.vue - универсальный рендерер
```vue
<template>
  <component 
    :is="fieldComponent" 
    :field="field"
    :model-value="modelValue"
    :disabled="disabled"
    :readonly="readonly"
    :errors="errors"
    :current-language="currentLanguage"
    v-bind="$attrs"
    @update:model-value="$emit('update:modelValue', $event)"
    @focus="$emit('focus', $event)"
    @blur="$emit('blur', $event)"
    @change="$emit('change', $event)"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { FieldComponentProps, FieldComponentEmits } from '@/types/field-components';

// Импорт всех компонентов полей
import StringField from './TextField/StringField.vue';
import EmailField from './TextField/EmailField.vue';
import DropdownField from './SelectField/DropdownField.vue';
import CheckboxField from './InputField/CheckboxField.vue';
// ... остальные импорты

const props = defineProps<FieldComponentProps>();
defineEmits<FieldComponentEmits>();

// Маппинг типов полей на компоненты
const FIELD_COMPONENTS = {
  string: StringField,
  email: EmailField,
  select: DropdownField,
  boolean: CheckboxField,
  // ... остальные маппинги
} as const;

const fieldComponent = computed(() => {
  return FIELD_COMPONENTS[props.field.type as keyof typeof FIELD_COMPONENTS] || StringField;
});
</script>
```

#### 0.7 Документация компонентов
Каждый компонент поля должен содержать:

```vue
<script setup lang="ts">
/**
 * StringField - Компонент для ввода текстовых данных
 * 
 * @description Поддерживает многоязычные значения, валидацию и локализацию плейсхолдеров
 * 
 * @props
 * - field: FieldDefinition - конфигурация поля
 * - modelValue: string | Record<string, string> - значение поля
 * - disabled: boolean - заблокировано ли поле
 * - readonly: boolean - только для чтения
 * - errors: string | Record<string, string> - ошибки валидации
 * - currentLanguage: string - текущий язык интерфейса
 * 
 * @emits
 * - update:modelValue - изменение значения
 * - focus - получение фокуса
 * - blur - потеря фокуса
 * - change - изменение значения (для совместимости)
 * 
 * @example
 * <StringField 
 *   :field="{ name: 'title', type: 'string', title: { en: 'Title', ru: 'Заголовок' } }"
 *   :model-value="formData.title"
 *   @update:model-value="formData.title = $event"
 * />
 */
</script>
```

#### 0.8 Миграция DynamicForm.vue
После создания компонентов полей, `DynamicForm.vue` будет упрощен:

```vue
<template>
  <div>
    <!-- Iterate over field groups -->
    <div v-for="group in groupedFields" :key="group.title.en">
      <div class="field-group">
        <!-- Group header -->
        <h2 class="field-group__title">
          {{ group.title?.[currentLanguage] || group.title?.en || "" }}
        </h2>

        <p v-if="group.help_text" class="field-group__description">
          {{ group.help_text[currentLanguage] || group.help_text.en || "" }}
        </p>

        <!-- Render fields for this group -->
        <div class="field-group__fields">
          <div v-for="field in group.fields" :key="field.name" class="field-container">
            <FieldRenderer
              :field="field"
              :model-value="internalValue[field.name]"
              :disabled="isDisabled(field)"
              :readonly="readOnly || field.read_only"
              :errors="parsedFieldErrors[field.name]"
              :current-language="currentLanguage"
              @update:model-value="updateField(field.name, $event)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import FieldRenderer from './Fields/FieldRenderer.vue';
// Остальная логика остается той же, но значительно упрощается
</script>
```

### 1. Архитектурная интеграция
- **Использовать Nuxt 3** как основу приложения (уже реализовано)
- **Использовать PrimeVue** компоненты (уже интегрировано)
- **Интегрироваться с существующими composables**: `usePageState()`, `useLanguageState()`, `useURLState()`
- **Использовать существующую систему локализации** (i18n с поддержкой EN/RU/UK/PL)

### 2. Компоненты конструктора

#### 2.1 FormBuilder (главный компонент)
```vue
<template>
  <div class="form-builder">
    <div class="builder-toolbar">
      <!-- Панель инструментов -->
    </div>
    <div class="builder-workspace">
      <FieldPalette />
      <FormCanvas />
      <PropertyPanel />
    </div>
    <div class="builder-actions">
      <!-- Кнопки сохранения, предпросмотра и т.д. -->
    </div>
  </div>
</template>
```

#### 2.2 FieldPalette (палитра полей)
- Категоризированный список всех доступных типов полей
- Поддержка поиска и фильтрации
- Drag-источник для новых полей

#### 2.3 FormCanvas (холст формы)
- Основная область для построения формы
- Drop-зона для полей из палитры
- Поддержка группировки полей (используя существующий механизм `fieldGroups`)
- Визуальные индикаторы для drag-and-drop

#### 2.4 PropertyPanel (панель свойств)
- Редактирование свойств выбранного поля
- Многоязычное редактирование заголовков и описаний
- Настройка валидации и ограничений

#### 2.5 FormPreview (предпросмотр)
- Реальный рендеринг формы с использованием существующего `DynamicForm`
- Переключение между языками
- Тестирование валидации

### 3. Drag-and-Drop функциональность

#### 3.1 Библиотека
- Использовать `vuedraggable` (уже присутствует в проекте)
- Интеграция с Vue 3 Composition API

#### 3.2 Возможности
- Перетаскивание полей из палитры на холст
- Изменение порядка полей
- Группировка полей (drag поля в группы)
- Копирование полей

### 4. Типизация TypeScript

#### 4.1 Основные интерфейсы
```typescript
// types/form-builder.ts
export interface FormBuilderField extends FieldDefinition {
  id: string; // уникальный ID для конструктора
  position: number;
  groupId?: string;
  validation?: ValidationRule[];
}

export interface FormBuilderGroup extends FieldGroup {
  id: string;
  position: number;
  collapsed?: boolean;
}

export interface FormBuilderSchema {
  id: string;
  name: Record<string, string>;
  description?: Record<string, string>;
  version: string;
  created_at: string;
  updated_at: string;
  fields: FormBuilderField[];
  groups: FormBuilderGroup[];
  settings: FormSettings;
}

export interface ValidationRule {
  type: 'required' | 'email' | 'min' | 'max' | 'pattern' | 'custom';
  value?: any;
  message: Record<string, string>;
}

export interface FormSettings {
  layout: 'single-column' | 'two-column' | 'grid';
  theme?: string;
  showProgress?: boolean;
  allowDraft?: boolean;
}
```

#### 4.2 Composables типизации
```typescript
// composables/useFormBuilder.ts
export interface UseFormBuilderReturn {
  schema: Ref<FormBuilderSchema>;
  selectedField: Ref<FormBuilderField | null>;
  selectedGroup: Ref<FormBuilderGroup | null>;
  addField: (fieldType: string, position?: number) => void;
  removeField: (fieldId: string) => void;
  updateField: (fieldId: string, updates: Partial<FormBuilderField>) => void;
  addGroup: (position?: number) => void;
  removeGroup: (groupId: string) => void;
  moveField: (fieldId: string, newPosition: number, newGroupId?: string) => void;
  exportSchema: () => FormBuilderSchema;
  importSchema: (schema: FormBuilderSchema) => void;
  validateSchema: () => ValidationResult;
}
```

### 5. Компоненты конфигурации полей

#### 5.1 FieldConfigurator
- Универсальный компонент для настройки любого типа поля
- Динамическое отображение настроек в зависимости от типа поля
- Интеграция с существующей системой валидации

#### 5.2 ValidationConfigurator
- Настройка правил валидации для каждого поля
- Поддержка кастомных валидаторов
- Многоязычные сообщения об ошибках

### 6. Предпросмотр и тестирование

#### 6.1 FormPreview компонент
```vue
<FormPreview 
  :schema="formSchema" 
  :language="currentLanguage"
  :test-mode="true"
  @form-submit="handleTestSubmit"
/>
```

#### 6.2 Функциональность тестирования
- Симуляция отправки формы
- Проверка валидации
- Тестирование всех типов полей
- Переключение между языками

### 7. Экспорт и импорт

#### 7.1 Форматы экспорта
- **JSON Schema** - основной формат для API
- **Vue Template** - экспорт как готовый Vue компонент
- **HTML/CSS** - статичная версия формы

#### 7.2 API интеграция
```typescript
// Эндпоинты для работы с формами
POST /api/forms/                    // создание формы
GET /api/forms/{id}                 // получение формы
PUT /api/forms/{id}                 // обновление формы
DELETE /api/forms/{id}              // удаление формы
POST /api/forms/{id}/duplicate      // дублирование формы
GET /api/forms/{id}/preview         // предпросмотр формы
```

### 8. Локализация

#### 8.1 Многоязычность
- Поддержка существующих языков: EN, RU, UK, PL
- Локализация интерфейса конструктора
- Многоязычные поля в создаваемых формах

#### 8.2 Структура переводов
```typescript
// Добавить в i18n.config.ts
formBuilder: {
  title: "Form Builder",
  fieldPalette: "Field Palette",
  properties: "Properties",
  preview: "Preview",
  fieldTypes: {
    string: "Text Field",
    email: "Email Field",
    // ... остальные типы
  },
  actions: {
    addField: "Add Field",
    removeField: "Remove Field",
    duplicateField: "Duplicate Field",
    // ... остальные действия
  }
}
```

### 9. Интеграция стилей

#### 9.1 Использование существующих стилей
- Интеграция с Tailwind CSS (уже настроено)
- Использование существующих CSS классов проекта
- Поддержка темной темы

#### 9.2 Кастомизация
- Настройка цветовой схемы форм
- Выбор шрифтов и размеров
- Настройка отступов и расположения

### 10. Дополнительные функции

#### 10.1 Шаблоны форм
- Предустановленные шаблоны (регистрация, контакты, опросы)
- Возможность создания кастомных шаблонов
- Библиотека шаблонов сообщества

#### 10.2 Условная логика
- Показ/скрытие полей на основе значений других полей
- Динамическое изменение свойств полей
- Каскадные выпадающие списки

#### 10.3 Интеграция с данными
- Подключение к внешним источникам данных для select/multiselect
- Предзаполнение полей из API
- Валидация на основе внешних данных

## Структура файлов

```
frontend_admin/
├── components/
│   └── Dashboard/
│       └── Components/
│           └── Form/
│               ├── DynamicForm.vue             # Рефакторенный главный компонент
│               ├── MainForm.vue               # Контроллер форм (без изменений)
│               └── Fields/                    # НОВАЯ структура компонентов полей
│                   ├── FieldRenderer.vue     # Универсальный рендерер
│                   ├── BaseField.vue         # Базовый компонент
│                   ├── TextField/
│                   │   ├── StringField.vue
│                   │   ├── EmailField.vue
│                   │   ├── PhoneField.vue
│                   │   ├── PasswordField.vue
│                   │   └── TextareaField.vue
│                   ├── SelectField/
│                   │   ├── DropdownField.vue
│                   │   ├── MultiSelectField.vue
│                   │   ├── AutoCompleteField.vue
│                   │   └── TagCloudField.vue
│                   ├── InputField/
│                   │   ├── CheckboxField.vue
│                   │   ├── CheckboxGroupField.vue
│                   │   ├── BooleanField.vue
│                   │   └── RatingField.vue
│                   ├── DateField/
│                   │   ├── CalendarField.vue
│                   │   ├── CalendarTimeField.vue
│                   │   └── DateTimeField.vue
│                   ├── FileField/
│                   │   ├── FileUploadField.vue
│                   │   ├── MultiFileField.vue
│                   │   ├── ImageField.vue
│                   │   └── MultiImageField.vue
│                   ├── SpecialField/
│                   │   ├── JsonField.vue
│                   │   ├── LocationField.vue
│                   │   ├── RangeField.vue
│                   │   ├── DragDropField.vue
│                   │   └── WysiwygField.vue
│                   └── index.ts              # Экспорт компонентов
│   └── FormBuilder/                          # БУДУЩИЕ компоненты конструктора
│       ├── FormBuilder.vue                   # Главный компонент конструктора
│       ├── FieldPalette.vue                 # Палитра полей
│       ├── FormCanvas.vue                   # Холст формы
│       ├── PropertyPanel.vue                # Панель свойств
│       ├── FormPreview.vue                  # Предпросмотр
│       ├── FieldConfigurator.vue            # Конфигуратор полей
│       ├── ValidationConfigurator.vue       # Конфигуратор валидации
│       ├── TemplateSelector.vue             # Выбор шаблонов
│       └── Utils/
│           ├── DraggableField.vue           # Перетаскиваемое поле
│           ├── DropZone.vue                 # Зона сброса
│           └── FieldIcon.vue                # Иконки полей
├── composables/
│   ├── useFormBuilder.ts                    # Основная логика конструктора
│   ├── useFieldValidation.ts                # Валидация полей
│   ├── useFormTemplate.ts                   # Работа с шаблонами
│   └── useFormExport.ts                     # Экспорт форм
├── types/
│   ├── form-builder.ts                      # Типы конструктора
│   ├── field-types.ts                       # Типы полей
│   ├── field-components.ts                  # НОВЫЕ типы для компонентов полей
│   └── validation.ts                        # Типы валидации
├── pages/
│   └── [[pagename]]/
│       └── form-builder/
│           ├── index.vue                    # Список форм
│           ├── create.vue                   # Создание формы
│           └── [id]/
│               ├── edit.vue                 # Редактирование
│               └── preview.vue              # Предпросмотр
├── docs/                                    # НОВАЯ документация
│   ├── field-components/                    # Документация компонентов полей
│   │   ├── README.md                       # Общий обзор
│   │   ├── base-field.md                   # BaseField документация
│   │   ├── text-fields.md                  # Текстовые поля
│   │   ├── select-fields.md                # Поля выбора
│   │   ├── input-fields.md                 # Поля ввода
│   │   ├── date-fields.md                  # Поля дат
│   │   ├── file-fields.md                  # Файловые поля
│   │   └── special-fields.md               # Специальные поля
│   └── form-builder/                       # Документация конструктора
└── assets/
    ├── icons/
    │   └── field-types/                     # Иконки типов полей
    └── templates/
        └── form-templates.json              # Предустановленные шаблоны
```

## Этапы реализации

### Этап 0: Рефакторинг DynamicForm (1-2 недели) - КРИТИЧЕСКИЙ ПРИОРИТЕТ
1. **Анализ существующего кода DynamicForm**
   - Инвентаризация всех типов полей и их логики
   - Выявление общих паттернов и повторяющегося кода
   - Документирование текущего API и поведения

2. **Создание базовой архитектуры компонентов**
   - Разработка BaseField.vue с общей логикой
   - Создание TypeScript интерфейсов для компонентов полей
   - Настройка структуры папок для компонентов полей

3. **Поэтапная миграция полей**
   - Неделя 1: TextField группа (string, email, phone, password, textarea)
   - Неделя 2: SelectField группа (select, multiselect, autocomplete, tag_cloud)
   - Продолжение с остальными группами

4. **Создание FieldRenderer и интеграция**
   - Разработка универсального рендерера полей
   - Замена монолитного кода в DynamicForm на FieldRenderer
   - Тестирование совместимости с существующими формами

5. **Документация и тестирование**
   - Документирование каждого компонента поля
   - Создание примеров использования
   - Unit тесты для компонентов полей

### Этап 1: Базовая структура конструктора (1-2 недели)
1. Создание основных компонентов (FormBuilder, FieldPalette, FormCanvas)
2. Интеграция drag-and-drop функциональности
3. Базовый рендеринг полей на холсте

### Этап 2: Конфигурация и свойства (1-2 недели)
1. Создание PropertyPanel
2. Реализация FieldConfigurator
3. Интеграция с существующими типами полей

### Этап 3: Предпросмотр и валидация (1 неделя)
1. Создание FormPreview с использованием DynamicForm
2. Интеграция системы валидации
3. Тестирование форм

### Этап 4: Экспорт и API (1 неделя)
1. Реализация экспорта в JSON
2. Интеграция с backend API
3. Сохранение и загрузка форм

### Этап 5: Дополнительные функции (1-2 недели)
1. Шаблоны форм
2. Условная логика
3. Расширенная кастомизация

## Критерии приемки

### Функциональные требования
- ✅ **ПРИОРИТЕТ 0**: Рефакторинг DynamicForm на модульные компоненты полей
- ✅ **ПРИОРИТЕТ 0**: Полная документация всех компонентов полей
- ✅ **ПРИОРИТЕТ 0**: TypeScript типизация для всех компонентов полей
- ✅ Drag-and-drop создание форм из всех существующих типов полей
- ✅ Группировка полей с поддержкой существующего механизма `fieldGroups`
- ✅ Многоязычная поддержка (EN/RU/UK/PL)
- ✅ Предпросмотр форм с использованием рефакторенного DynamicForm
- ✅ Валидация полей и форм
- ✅ Экспорт в JSON совместимый с существующей системой
- ✅ Интеграция с существующими composables

### Технические требования
- ✅ TypeScript типизация
- ✅ Vue 3 Composition API
- ✅ PrimeVue компоненты
- ✅ Responsive дизайн
- ✅ Производительность (виртуализация для больших форм)
- ✅ Accessibility (WCAG 2.1)

### Интеграционные требования
- ✅ **ПРИОРИТЕТ 0**: Обратная совместимость рефакторенного DynamicForm
- ✅ **ПРИОРИТЕТ 0**: Безболезненная миграция существующих форм
- ✅ Совместимость с существующим DynamicForm
- ✅ Использование текущей системы авторизации
- ✅ Интеграция с существующими API эндпоинтами
- ✅ Поддержка существующих стилей и тем

## Дополнительные рекомендации

### Производительность
- Использовать виртуализацию для больших форм
- Ленивая загрузка компонентов
- Оптимизация перерендеринга при drag-and-drop

### UX/UI
- Следовать существующему дизайну приложения
- Четкие визуальные индикаторы для drag-and-drop
- Контекстные меню для быстрых действий
- Горячие клавиши для часто используемых действий

### Тестирование
- **ПРИОРИТЕТ 0**: Регрессионное тестирование после рефакторинга DynamicForm
- **ПРИОРИТЕТ 0**: Unit тесты для каждого компонента поля
- **ПРИОРИТЕТ 0**: Integration тесты для FieldRenderer
- Unit тесты для composables
- Component тесты для UI компонентов конструктора
- E2E тесты для основных сценариев
- Тестирование на разных устройствах и браузерах
- Тестирование обратной совместимости существующих форм

Этот конструктор форм станет мощным инструментом для создания динамических форм в платформе Dantist, полностью интегрированным с существующей архитектурой и расширяющим её возможности. Начало с рефакторинга DynamicForm обеспечит прочную основу для всех будущих разработок.
