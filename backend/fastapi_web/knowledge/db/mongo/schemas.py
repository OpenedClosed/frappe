"""Схемы приложения База знаний для работы с БД MongoDB."""
from datetime import datetime
from typing import Any, Dict, Optional

from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator

from infra import settings

Questions = Dict[str, str]

class Subtopic(BaseModel):
    """Модель подтемы, содержащая словарь вопросов."""
    questions: Questions

class Topic(BaseModel):
    """Модель темы, содержащая словарь подтем."""
    subtopics: Dict[str, Subtopic]

class KnowledgeBase(BaseModel):
    """Модель базы знаний, содержащая темы, краткие вопросы и дату обновления."""
    app_name: Optional[str] = None
    knowledge_base: Dict[str, Topic]
    brief_questions: Optional[Dict[str, str]] = Field(default_factory=dict)
    update_date: Optional[datetime] = Field(default_factory=datetime.now)


class UpdateResponse(BaseModel):
    """Модель ответа обновления, содержащая новую базу знаний и объект различий."""
    knowledge: KnowledgeBase
    diff: Dict[str, Any]

class PatchKnowledgeRequest(BaseModel):
    """Модель запроса патча для базы знаний с обязательным patch_data и опциональным base_data."""
    patch_data: dict
    base_data: Optional[dict] = None

class DetermineChangesRequest(BaseModel):
    """Модель запроса для определения изменений в базе знаний по тексту пользователя с опциональными исходными данными."""
    user_message: str
    user_info: Optional[str] = ""
    base_data: Optional[dict] = None