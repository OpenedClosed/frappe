"""Базовые схемы для работы с БД MongoDB."""
import functools
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union, get_args, get_origin

from bson import ObjectId
from pydantic import BaseModel, Field, create_model, validator

from crud_core.utils.help_functions import (extract_list_inner_type,
                                            is_enum_type, is_list_of_enum,
                                            unwrap_optional)

logger = logging.getLogger(__name__)


class IdModel(BaseModel):
    """Базовая модель с MongoDB `_id`."""
    id: Optional[str] = Field(
        default_factory=lambda: str(
            ObjectId()))

    class Config:
        """Настройки модели."""
        allow_population_by_field_name = True


class TimeBasedModel(IdModel):
    """Модель, зависимая от времени."""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc))
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc))


class TimeBasedModelNoneId(BaseModel):
    """Модель, зависимая от времени."""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc))
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc))


class BaseValidatedModel(BaseModel):
    """Базовая модель с универсальной валидацией Enum-полей."""

    @classmethod
    def _validate_enum(cls, enum_type: Type[Enum], value: Any) -> Enum:
        """Валидирует одно значение типа Enum, обрабатывая Optional[T] и поддерживая JSON."""
        enum_type = unwrap_optional(enum_type)
        if not issubclass(enum_type, Enum):
            raise ValueError(f"Invalid Enum type: {enum_type}")

        if isinstance(value, enum_type):
            return value

        if isinstance(value, str):
            for em in enum_type:
                if value in [em.value, em.name]:
                    return em
            try:
                loaded = json.loads(value)
                return cls._validate_enum(enum_type, loaded)
            except json.JSONDecodeError:
                pass

        if isinstance(value, dict):
            dict_json = json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(
                    ',',
                    ':'))
            for em in enum_type:
                try:
                    em_dict = json.loads(em.value)
                    em_json = json.dumps(
                        em_dict,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(
                            ',',
                            ':'))
                    if dict_json == em_json:
                        return em
                except (json.JSONDecodeError, TypeError):
                    pass

        if hasattr(enum_type, "UNKNOWN"):
            return enum_type.UNKNOWN

        allowed_values = []
        for em in enum_type:
            try:
                allowed_values.append(json.loads(em.value))
            except (json.JSONDecodeError, TypeError):
                allowed_values.append(em.value)

        raise ValueError(
            f"Invalid value '{value}' for {enum_type.__name__}. Allowed: {allowed_values}"
        )

    @classmethod
    def _validate_list_of_enum(
            cls, enum_type: Type[Enum], values: Any) -> List[Enum]:
        """Валидирует список значений типа Enum."""
        if values is None:
            return []
        if not isinstance(values, list):
            raise ValueError(
                f"Expected a list of {enum_type.__name__}, got {type(values).__name__}")
        return [cls._validate_enum(enum_type, v) for v in values]

    @classmethod
    def _validate_field_type(cls, field_name: str,
                             field_type: Any, value: Any) -> Any:
        """Определяет правильный обработчик поля в зависимости от его типа."""
        if value is None:
            return None

        origin = get_origin(field_type)
        args = get_args(field_type)

        if origin is Union:
            for a in args:
                if a is not type(None):
                    return cls._validate_field_type(field_name, a, value)
            return None

        if isinstance(field_type, type) and issubclass(field_type, Enum):
            return cls._validate_enum(field_type, value)

        if origin is list:
            inner_type = args[0]
            if isinstance(inner_type, type) and issubclass(inner_type, Enum):
                return cls._validate_list_of_enum(inner_type, value)
            TempModel = create_model(
                "TempModel", **{field_name: (field_type, ...)})
            validated_obj = TempModel(**{field_name: value})
            return getattr(validated_obj, field_name)

        try:
            TempModel = create_model(
                "TempModel", **{field_name: (field_type, ...)})
            validated_obj = TempModel(**{field_name: value})
            return getattr(validated_obj, field_name)
        except Exception as e:
            raise HTTPException(
                400, f"Ошибка валидации поля {field_name}: {e}")

    @staticmethod
    def _is_json(val: str) -> bool:
        """Проверяет, является ли строка валидным JSON."""
        try:
            json.loads(val)
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    @classmethod
    def get_validators(cls) -> Dict[str, Any]:
        """Формирует набор валидаторов для Enum и списка Enum."""
        validators = {}

        def validate_enum_fn(v, field_type, field_name):
            return cls._validate_enum(field_type, v)

        def validate_list_fn(v, field_type, field_name):
            return cls._validate_list_of_enum(field_type, v)

        for field_name, field_type in cls.__annotations__.items():
            if field_name == "created_at":
                continue

            if is_enum_type(field_type):
                vfunc = validator(field_name, pre=True, allow_reuse=True)(
                    functools.partial(
                        validate_enum_fn,
                        field_type=field_type,
                        field_name=field_name)
                )
                validators[field_name] = vfunc
            elif is_list_of_enum(field_type):
                inner_type = extract_list_inner_type(field_type)
                vfunc = validator(field_name, pre=True, allow_reuse=True)(
                    functools.partial(
                        validate_list_fn,
                        field_type=inner_type,
                        field_name=field_name)
                )
                validators[field_name] = vfunc

        return validators

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Подмешивает валидаторы в дочерние классы при наследовании."""
        super().__init_subclass__(**kwargs)
        for field_name, vfunc in cls.get_validators().items():
            setattr(cls, f"_validate_{field_name}", vfunc)


class BaseValidatedIdModel(IdModel, BaseValidatedModel):
    """Базовая модель с универсальной валидацией Enum-полей и полем ID."""
    pass


class File(BaseModel):
    """Файл любого типа."""
    url: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class Photo(BaseModel):
    """Изображение."""
    url: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class ColorChoice(BaseModel):
    """Выбор цвета."""
    color_code: str = Field(..., description="HEX-код цвета")


class Location(BaseModel):
    """Поле для карты (широта и долгота)."""
    latitude: float
    longitude: float


class Rating(BaseModel):
    """Оценка (звезды, смайлы, шкала)."""
    value: int = Field(..., ge=1, le=10, description="Оценка от 1 до 10")
    type: str = Field(
        default="stars",
        description="Тип оценки: stars, emojis, numbers")


class TableRow(BaseModel):
    """Одна строка таблицы (например, измерение давления, веса)."""
    column_1: str
    column_2: str
    column_3: Optional[str] = None


class RangeValue(BaseModel):
    """Диапазон значений (например, для фильтров, настроек)."""
    min_value: int
    max_value: int
