"""Схемы и Енам приложения Тест для работы с БД MongoDB."""
import json
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr

from db.mongo.base.schemas import (BaseValidatedModel, File, Location, Photo,
                                   RangeValue, Rating, TableRow)


class SingleInlineModel(BaseModel):
    """Модель для демонстрации одиночной инлайн-связи."""
    data: str = "Single inline content"


class MultipleInlineModel(BaseModel):
    """Модель для демонстрации множественной инлайн-связи."""
    info: str = "Some info"


class SelectionEnum(str, Enum):
    """Обычный выбор (Dropdown)"""
    OPTION_1 = json.dumps({"en": "Option 1", "ru": "Вариант 1"})
    OPTION_2 = json.dumps({"en": "Option 2", "ru": "Вариант 2"})
    OPTION_3 = json.dumps({"en": "Option 3", "ru": "Вариант 3"})


class MultiSelectionEnum(str, Enum):
    """Множественный выбор (Multi-Select)"""
    CHOICE_A = json.dumps({"en": "Choice A", "ru": "Выбор A"})
    CHOICE_B = json.dumps({"en": "Choice B", "ru": "Выбор B"})
    CHOICE_C = json.dumps({"en": "Choice C", "ru": "Выбор C"})


class ButtonSelectionEnum(str, Enum):
    """Выбор через кнопки"""
    BUTTON_1 = json.dumps({"en": "Button 1", "ru": "Кнопка 1"})
    BUTTON_2 = json.dumps({"en": "Button 2", "ru": "Кнопка 2"})
    BUTTON_3 = json.dumps({"en": "Button 3", "ru": "Кнопка 3"})


class RadioSelectionEnum(str, Enum):
    """Выбор через радио-кнопки"""
    RADIO_1 = json.dumps({"en": "Radio 1", "ru": "Радио 1"})
    RADIO_2 = json.dumps({"en": "Radio 2", "ru": "Радио 2"})
    RADIO_3 = json.dumps({"en": "Radio 3", "ru": "Радио 3"})


class DragAndDropEnum(str, Enum):
    """Drag & Drop элементы"""
    ITEM_1 = json.dumps({"en": "Draggable 1", "ru": "Перетаскиваемый 1"})
    ITEM_2 = json.dumps({"en": "Draggable 2", "ru": "Перетаскиваемый 2"})
    ITEM_3 = json.dumps({"en": "Draggable 3", "ru": "Перетаскиваемый 3"})


class ColorPickerEnum(str, Enum):
    """Выбор цвета"""
    RED = json.dumps({"en": "Soft Red",
                      "ru": "Мягкий красный",
                      "settings": {"color": "#E57373"}})
    ORANGE = json.dumps({"en": "Warm Orange",
                         "ru": "Теплый оранжевый",
                         "settings": {"color": "#FFB74D"}})
    YELLOW = json.dumps({"en": "Sunny Yellow",
                         "ru": "Солнечный желтый",
                         "settings": {"color": "#FFF176"}})
    GREEN = json.dumps({"en": "Fresh Green",
                        "ru": "Свежий зеленый",
                        "settings": {"color": "#81C784"}})
    TEAL = json.dumps({"en": "Teal Blue", "ru": "Бирюзовый",
                      "settings": {"color": "#4DB6AC"}})
    BLUE = json.dumps({"en": "Sky Blue",
                       "ru": "Небесный синий",
                       "settings": {"color": "#64B5F6"}})
    PURPLE = json.dumps({"en": "Lavender Purple",
                         "ru": "Лавандовый фиолетовый",
                         "settings": {"color": "#9575CD"}})
    PINK = json.dumps({"en": "Rose Pink", "ru": "Розовый",
                      "settings": {"color": "#F48FB1"}})


class TestSchema(BaseValidatedModel):
    """Тестовая модель для отображения всех возможных типов полей."""

    # Текстовые поля
    str_field: str = "Example string"
    text_field: str = {"settings": {"type": "textarea"}}
    wysiwyg_field: str = {
        "settings": {
            "type": "wysiwyg"}}
    email: EmailStr = "test@example.com"
    # phone_number: str = {"settings": {"type": "phone"}}
    # phone_number: Optional[str] = {"settings": {"type": "phone"}}
    phone_number: str = {"default": "+7xxxxxxx", "settings": {"type": "phone"}}
    password_field: str = {
        "settings": {
            "type": "password"}}

    # Файлы и медиа
    image_upload: Optional[Photo] = ""
    multi_images: List[Photo] = []
    file_upload: Optional[File] = None
    multi_files: List[File] = []

    # Выборы (Dropdown, Multi-Select, Tag Cloud, Autocomplete, Buttons, Radio)
    dropdown_selection: SelectionEnum = {
        "settings": {"type": "select"}
    }
    multi_dropdown_selection: List[MultiSelectionEnum] = {
        "settings": {"type": "multiselect"}
    }
    tag_cloud: List[str] = {"settings": {"type": "tag_cloud"}}
    autocomplete_field: str = {
        "settings": {"type": "autocomplete", "source": "countries"}
    }
    button_selection: ButtonSelectionEnum = {
        "settings": {"type": "button_select"}
    }
    radio_selection: RadioSelectionEnum = {
        "settings": {"type": "radio_select"}
    }

    # Поля даты и времени
    date_field: datetime = {"settings": {"type": "calendar"}}
    datetime_field: datetime = {"settings": {"type": "calendar"}}

    # Карта и координаты
    map_field: Optional[Location] = None  # Теперь объект Location

    # Оценки и рейтинги
    rating_field: Rating = Rating(value=5, type="stars")  # Оценка от 1 до 10

    # Диапазоны значений (range slider)
    range_slider: RangeValue = RangeValue(min_value=10, max_value=100)

    # Чекбоксы и переключатели
    boolean_toggle: bool = False  # Обычный чекбокс
    checkbox_group: List[str] = {
        "settings": {"type": "checkbox_group"}
    }

    # Drag and Drop
    drag_and_drop_list: List[DragAndDropEnum] = {
        "settings": {"type": "drag_and_drop"}
    }

    # Поле выбора цвета
    # color_picker: ColorPickerEnum = {
    #     "settings": {"type": "color_multiselect"}
    # }

    # Таблица (список строк)
    table_data: List[TableRow] = [
        TableRow(column_1="Value 1", column_2="Value 2"),
        TableRow(column_1="Value 3", column_2="Value 4"),
    ]

    # Поле ввода кода (JSON, YAML, SQL)
    dict_editor: dict
    code_editor: str = {
        "settings": {"type": "code_editor", "language": "json"}
    }

    # Инлайны (один объект + список объектов)
    single_relation: Optional[SingleInlineModel] = None
    multiple_relations: List[MultipleInlineModel] = []

    # Дата создания и обновления
    created_at: datetime = {"settings": {"type": "datetime"}}
    updated_at: datetime = {"settings": {"type": "datetime"}}
