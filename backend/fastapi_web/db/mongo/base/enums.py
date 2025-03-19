"""Базовые Enum классы."""
import json
from typing import Any


class BaseJsonEnumMixin:
    """
    Базовый Enum-класс для Pydantic, который позволяет:
    - Игнорировать регистр при сопоставлении значений.
    - Автоматически парсить JSON-значения внутри Enum.
    - Возвращать исходное значение, если оно не соответствует известным членам Enum (fallback).
    """

    UNKNOWN = json.dumps({"en": "unknown", "ru": "неизвестно"})

    @classmethod
    def __get_validators__(cls):
        yield cls._validate

    @classmethod
    def _validate(cls, value: Any, field=None, config=None) -> Any:
        """Проверяет значение и пытается привести его к Enum, игнорируя регистр и обрабатывая JSON."""
        if isinstance(value, str):
            lower_value = value.lower()

            for member in cls:
                if lower_value == member.name.lower():
                    return member

            for member in cls:
                try:
                    parsed_value = json.loads(member.value)
                    if lower_value in map(
                            str.lower, cls._extract_string_values(parsed_value)):
                        return member
                except json.JSONDecodeError:
                    continue

        return value

    @classmethod
    def _extract_string_values(cls, data: Any) -> list:
        """Рекурсивно извлекает все строковые значения из JSON-объекта."""
        if isinstance(data, dict):
            return [v for val in data.values()
                    for v in cls._extract_string_values(val)]
        if isinstance(data, list):
            return [
                v for item in data for v in cls._extract_string_values(item)]
        return [data] if isinstance(data, str) else []

    @classmethod
    def __get_pydantic_json_schema__(
            cls, core_schema: Any, handler: Any) -> Any:
        """Генерирует JSON-схему с учетом Enum-значений."""
        schema = handler(core_schema)
        schema.update({
            "type": "string",
            "enum": [member.name for member in cls],
            "examples": [json.loads(member.value) for member in cls if isinstance(member.value, str)]
        })
        return schema
