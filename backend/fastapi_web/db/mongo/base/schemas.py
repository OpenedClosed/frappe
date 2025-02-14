"""Базовые схемы для работы с БД MongoDB."""
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class IdModel(BaseModel):
    """Базовая модель с MongoDB `_id`."""
    id: Optional[str] = Field(
        default_factory=lambda: str(
            ObjectId()), alias="_id")

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
