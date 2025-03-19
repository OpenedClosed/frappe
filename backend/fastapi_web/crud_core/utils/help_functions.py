"""Вспомогательные функции приложения ядро CRUD создания."""
import json
from enum import Enum
from typing import List, Union, get_args, get_origin

# -----------------------------------------
# 1) Работа с Optional[T] и List[T]
# -----------------------------------------


def unwrap_optional(py_type):
    """Если py_type - это Optional[T], возвращает T, иначе возвращает сам py_type."""
    origin = get_origin(py_type)
    if origin is Union:
        args = get_args(py_type)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return py_type


def extract_list_inner_type(py_type):
    """Если py_type - это (Optional) List[T], возвращает T, иначе сам py_type."""
    py_type = unwrap_optional(py_type)
    origin = get_origin(py_type)
    args = get_args(py_type)

    if origin in (list, List) and args:
        return unwrap_optional(args[0])

    return py_type


# -----------------------------------------
# 2) Проверки специальных типов (File, Photo и пр.)
# -----------------------------------------

def is_type(py_type, type_name: str) -> bool:
    """Проверяет, является ли py_type заданным типом по имени."""
    py_type = unwrap_optional(py_type)
    return getattr(py_type, "__name__", "") == type_name if py_type else False


def is_list_of_type(py_type, type_name: str) -> bool:
    """Проверяет, является ли py_type списком объектов заданного типа."""
    py_type = unwrap_optional(py_type)
    return get_origin(py_type) in (list, List) and is_type(
        extract_list_inner_type(py_type), type_name)


def is_file_type(py_type): return is_type(py_type, "File")
def is_list_of_file(py_type): return is_list_of_type(py_type, "File")
def is_photo_type(py_type): return is_type(py_type, "Photo")
def is_list_of_photo(py_type): return is_list_of_type(py_type, "Photo")
def is_location_type(py_type): return is_type(py_type, "Location")
def is_rating_type(py_type): return is_type(py_type, "Rating")
def is_range_value_type(py_type): return is_type(py_type, "RangeValue")
def is_table_row_type(py_type): return is_type(py_type, "TableRow")
def is_email_type(py_type): return is_type(py_type, "EmailStr")


# -----------------------------------------
# 3) Работа с Enum-значениями (choices)
# -----------------------------------------

def is_enum_type(py_type) -> bool:
    """Проверяет, является ли py_type классом Enum."""
    py_type = unwrap_optional(py_type)
    try:
        return issubclass(py_type, Enum)
    except TypeError:
        return False


def is_list_of_enum(py_type) -> bool:
    """Проверяет, является ли py_type списком объектов Enum."""
    return get_origin(unwrap_optional(py_type)) in (
        list, List) and is_enum_type(extract_list_inner_type(py_type))


def parse_enum_label(value: str) -> Union[str, dict]:
    """Парсит JSON-строки в словари (для переводов), иначе возвращает строку."""
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


def get_enum_choices(enum_type):
    """Формирует список choices для Enum-класса (значения и переводы)."""
    enum_type = unwrap_optional(enum_type)
    return [
        {"value": parse_enum_label(member.value),
         "label": parse_enum_label(member.value)}
        for member in enum_type
    ] if is_enum_type(enum_type) else []


# -----------------------------------------
# 4) Проверка типа словаря (dict)
# -----------------------------------------

def is_dict_type(py_type) -> bool:
    """Проверяет, является ли py_type словарём (dict или Dict[...])."""
    py_type = unwrap_optional(py_type)
    return py_type == dict or get_origin(py_type) is dict
