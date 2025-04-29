"""Схемы приложения Знания для работы с БД MongoDB."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, HttpUrl

from db.mongo.base.schemas import BaseValidatedModel, IdModel, Photo

from .enums import (AIModelEnum, BotColorEnum, CommunicationStyleEnum,
                    ContextPurpose, ContextType, ForbiddenTopicsEnum,
                    FunctionalityEnum, PersonalityTraitsEnum, TargetActionEnum)

# ==============================
# БЛОК: Контекст
# ==============================

class ContextEntry(IdModel):
    """Универсальная единица контекста."""

    type: ContextType
    purpose: ContextPurpose = ContextPurpose.NONE
    title: str

    text: Optional[str] = None
    file_path: Optional[str] = None
    url: Optional[str] = None
    snapshot_text: Optional[str] = None
    kb_structure: Optional[dict] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==============================
# БЛОК: База знаний
# ==============================

class Answer(BaseModel):
    """Ответ на вопрос с текстом и файлами."""

    text: str
    files: Optional[List[str]] = []


class Subtopic(BaseModel):
    """Подтема с вопросами и ответами."""

    questions: Dict[str, Answer]


class Topic(BaseModel):
    """Тема с подтемами."""

    subtopics: Dict[str, Subtopic]


class KnowledgeBase(BaseModel):
    """База знаний с темами, вопросами и датой обновления."""

    app_name: Optional[str] = None
    knowledge_base: Dict[str, Topic] = Field(default_factory=dict)
    brief_questions: Dict[str, str] = Field(default_factory=dict)
    context: Optional[List[ContextEntry]] = Field(default_factory=list)
    update_date: datetime = Field(default_factory=datetime.now)


class UpdateResponse(BaseModel):
    """Ответ на обновление базы знаний."""

    knowledge: KnowledgeBase
    diff: Dict[str, Any]


class PatchKnowledgeRequest(BaseModel):
    """Запрос на частичное обновление базы знаний."""

    patch_data: dict
    base_data: Optional[dict] = None


class DetermineChangesRequest(BaseModel):
    """Запрос на определение изменений по сообщению пользователя."""

    user_message: str
    user_info: Optional[str] = ""
    base_data: Optional[dict] = None


# ==============================
# БЛОК: Настройки бота
# ==============================

class BotSettings(BaseValidatedModel):
    """Настройки ИИ-бота."""

    # Основные параметры
    project_name: str
    employee_name: str
    mention_name: bool = False
    avatar: Optional[Photo] = None
    bot_color: BotColorEnum

    # Характер и поведение
    communication_tone: CommunicationStyleEnum
    personality_traits: PersonalityTraitsEnum
    additional_instructions: Optional[str] = Field(
        default="",
        json_schema_extra={"settings": {"type": "textarea"}}
    )
    role: str
    target_action: List[TargetActionEnum] = Field(default_factory=list)

    # Темы и ограничения
    core_principles: Optional[str] = Field(
        default="",
        json_schema_extra={"settings": {"type": "textarea"}}
    )
    special_instructions: List[FunctionalityEnum] = Field(default_factory=list)
    forbidden_topics: List[ForbiddenTopicsEnum] = Field(default_factory=list)

    greeting: Dict[str, str] = Field(
        default_factory=lambda: {
            "en": "Hello! How can I assist you today?",
            "ru": "Здравствуйте! Чем могу помочь?"
        }
    )
    error_message: Dict[str, str] = Field(
        default_factory=lambda: {
            "en": "Your question requires further review. A specialist will join the conversation shortly.",
            "ru": "Ваш вопрос требует дополнительного рассмотрения. Специалист скоро подключится к беседе."
        }
    )
    farewell_message: Dict[str, str] = Field(
        default_factory=lambda: {
            "en": "Goodbye! If you need anything else, feel free to ask.",
            "ru": "До свидания! Если вам что-то понадобится, обращайтесь."
        }
    )
    fallback_ai_error_message: Dict[str, str] = Field(
        default_factory=lambda: {
            "en": "Unfortunately, I'm having trouble generating a response right now. Please try again later.",
            "ru": "К сожалению, я не могу сейчас сгенерировать ответ. Пожалуйста, попробуйте позже."
        }
    )

    ai_model: AIModelEnum
    created_at: datetime = Field(default_factory=datetime.utcnow)
