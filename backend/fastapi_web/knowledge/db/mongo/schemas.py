"""Схемы приложения Знания для работы с БД MongoDB."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, HttpUrl

from db.mongo.base.schemas import BaseValidatedModel, IdModel, Photo
# from knowledge.utils.help_functions import (cache_url_snapshot,
#                                             generate_kb_structure_via_gpt,
#                                             parse_file)

from .enums import (AIModelEnum, BotColorEnum, CommunicationStyleEnum,
                    ContextPurpose, ContextType, ForbiddenTopicsEnum,
                    FunctionalityEnum, PersonalityTraitsEnum, TargetActionEnum)

# ==============================
# БЛОК: Контекст
# ==============================


class ContextEntry(IdModel):
    """
    Универсальная единица контекста.

    • `purpose` — куда потом пойдёт эта информация  
    • `get_content()` — возвращает актуальный текст  
      – ссылки кэшируются в Redis, файлы парсятся каждый раз (без кэша)
    • `to_kb_structure()` — превращает сырой текст в структуру,
      совместимую с `KnowledgeBase` (топик‑>подтема‑>Q/A)
    """
    type: ContextType
    purpose: ContextPurpose = ContextPurpose.NONE
    title: str

    text: Optional[str]      = None     # для TEXT
    file_path: Optional[str] = None     # для FILE
    url: Optional[str]   = None     # для URL
    snapshot_text: Optional[str] = None # кэш только для URL
    kb_structure: Optional[dict] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==============================
# БЛОК: База знаний
# ==============================

class Answer(BaseModel):
    """Ответ на вопрос, содержащий текст и файлы."""
    text: str
    files: Optional[List[str]] = []


class Subtopic(BaseModel):
    """Подтема, содержащая вопросы и их ответы."""
    questions: Dict[str, Answer]


class Topic(BaseModel):
    """Тема, содержащая подтемы."""
    subtopics: Dict[str, Subtopic]


class KnowledgeBase(BaseModel):
    """База знаний с темами, краткими вопросами и датой обновления."""
    app_name: Optional[str] = None
    knowledge_base: Dict[str, Topic] = Field(default_factory=dict)
    brief_questions: Dict[str, str] = Field(default_factory=dict)
    context: Optional[List[ContextEntry]] = Field(default_factory=list)
    update_date: datetime = Field(default_factory=datetime.now)


class UpdateResponse(BaseModel):
    """Ответ обновления базы знаний, содержащий обновленные данные и различия."""
    knowledge: KnowledgeBase
    diff: Dict[str, Any]


class PatchKnowledgeRequest(BaseModel):
    """Запрос на частичное обновление базы знаний."""
    patch_data: dict
    base_data: Optional[dict] = None


class DetermineChangesRequest(BaseModel):
    """Запрос на определение изменений в базе знаний по тексту пользователя."""
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
    # bot_color: BotColorEnum = {
    #     "settings": {"type": "color_multiselect"}
    # }
    bot_color: BotColorEnum

    # Характер и поведение
    communication_tone: CommunicationStyleEnum
    personality_traits: PersonalityTraitsEnum
    additional_instructions: str = ""
    role: str
    target_action: List[TargetActionEnum] = Field(default_factory=list)

    # Темы и ограничения
    core_principles: Optional[str] = None
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
