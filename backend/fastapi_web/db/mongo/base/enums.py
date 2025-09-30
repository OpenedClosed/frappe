"""Базовые Enum классы."""
import json
from typing import Any

from pydantic.json_schema import JsonSchemaValue


class BaseJsonEnumMixin:
    """
    Базовый Enum-класс для Pydantic, поддерживающий:
    - Игнорирование регистра.
    - Сопоставление JSON-значений.
    - Fallback на оригинальное значение.
    """

    UNKNOWN = json.dumps({"en": "unknown", "ru": "неизвестно"})

    @classmethod
    def __get_validators__(cls):
        yield cls._validate

    @classmethod
    def _validate(cls, value: Any, field=None, config=None) -> Any:
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
        if isinstance(data, dict):
            return [v for val in data.values()
                    for v in cls._extract_string_values(val)]
        if isinstance(data, list):
            return [
                v for item in data for v in cls._extract_string_values(item)]
        return [data] if isinstance(data, str) else []

    @classmethod
    def __get_pydantic_json_schema__(
            cls, core_schema: Any, handler: Any) -> JsonSchemaValue:
        """Возвращает JSON-схему Enum без использования handler(), чтобы избежать ошибки."""
        return {
            "type": "string",
            "enum": [member.name for member in cls],
            "examples": [
                json.loads(member.value)
                for member in cls
                if isinstance(member.value, str)
            ],
            "title": cls.__name__,
            "description": f"Enum with relaxed matching for {cls.__name__}"
        }
    
    @property
    def en_value(self) -> str:
        """Возвращает значение поля 'en' из JSON-строки."""
        try:
            parsed = json.loads(self.value)
            return parsed.get("en", self.name)
        except Exception:
            return self.name

