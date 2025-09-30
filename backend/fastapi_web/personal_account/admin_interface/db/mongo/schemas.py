"""Схемы приложения Административная зона для работы с БД MongoDB."""
from datetime import datetime
from typing import Optional

from pydantic import Field

from db.mongo.base.schemas import BaseValidatedModel


class CalendarIntegration(BaseValidatedModel):
    """
    Интеграция с внешним календарём пользователя.
    """
    provider: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: datetime
    last_sync: datetime = Field(default_factory=datetime.utcnow)
