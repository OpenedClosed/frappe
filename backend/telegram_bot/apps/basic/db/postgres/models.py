"""Базовые модели (Tortoise ORM)."""
from tortoise import fields
from tortoise.models import Model


class IdModel(Model):
    """Базовая модель с ID."""
    id = fields.IntField(pk=True)

    class Meta:
        abstract = True