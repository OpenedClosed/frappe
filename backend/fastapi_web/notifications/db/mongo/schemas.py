# db/mongo/apps/notifications/schemas.py
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field
from db.mongo.base.schemas import BaseValidatedModel, BaseValidatedIdModel
from .enums import Priority, NotificationChannel

class EntityRef(BaseValidatedModel):
    """Гибкая привязка к любой сущности домена."""
    entity_type: Optional[str] = None   # 'chat' | 'order' | 'task' | ...
    entity_id:   Optional[str] = None   # бизнес-ID (не обяз. ObjectId)
    route:       Optional[str] = None   # относительный путь в админке (/admin/..)
    extra: Dict[str, Any] = Field(default_factory=dict)

class ReadReceipt(BaseValidatedModel):
    user_id: str
    read_at: datetime = Field(default_factory=datetime.utcnow)

class Notification(BaseValidatedModel):
    """Админское уведомление."""
    # контент/тип
    kind: str                     # код типа для бизнес-логики
    message: str = Field(
        default="",
        json_schema_extra={"settings": {"type": "textarea"}}
    )                # текст (plain/HTML по месту показа)
    title: Optional[Dict[str, str]] = None
    priority: Priority = Priority.NORMAL

    # каналы доставки (куда показывали/планируем показывать)
    deliver_to: List[NotificationChannel] = Field(default_factory=list)

    # подсказки UI
    popup: bool = True
    sound: bool = True

    # адресация (None → общий фид админов)
    recipient_user_id: Optional[str] = None

    # универсальная ссылка/привязка
    entity: Optional[EntityRef] = None
    link_url: Optional[str] = None

    # тех. поля
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # прочтения несколькими пользователями
    read_receipts: List[ReadReceipt] = Field(default_factory=list)
