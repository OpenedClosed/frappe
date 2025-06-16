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
    source_ref: Optional[str] = None


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

    postprocessing_instruction: Optional[str] = Field(
        default="Do not invent facts. Do not generate placeholder links. Do not provide addresses, phones, or prices unless clearly present in the snippets or chat history.",
        json_schema_extra={"settings": {"type": "textarea"}}
    )

    language_instruction: Optional[str] = Field(
        default="Always respond in the language of the user's latest messages. If it is unclear, use the language of the recent chat context or interface.",
        json_schema_extra={"settings": {"type": "textarea"}}
    )

    greeting: Dict[str, str] = Field(
        default_factory=lambda: {
            "en": "Hello! How can I assist you today?",
            "pl": "Cześć! W czym mogę pomóc?",
            "uk": "Вітаю! Чим я можу допомогти?",
            "ru": "Здравствуйте! Чем могу помочь?",
            "ka": "გამარჯობა! რით შემიძლია დაგეხმარო?"
        }
    )
    error_message: Dict[str, str] = Field(
        default_factory=lambda: {
            "en": "Your question requires further review. A specialist will join the conversation shortly.",
            "pl": "Twoje pytanie wymaga dalszej analizy. Konsultant wkrótce dołączy do rozmowy.",
            "uk": "Ваше питання потребує додаткового розгляду. Спеціаліст незабаром приєднається до розмови.",
            "ru": "Ваш вопрос требует дополнительного рассмотрения. Специалист скоро подключится к беседе.",
            "ka": "თქვენი კითხვა საჭიროებს დამატებით განხილვას. სპეციალისტი მალე შემოუერთდება საუბარს."
        }
    )
    farewell_message: Dict[str, str] = Field(
        default_factory=lambda: {
            "en": "Goodbye! If you need anything else, feel free to ask.",
            "pl": "Do widzenia! Jeśli będziesz czegoś potrzebować, śmiało pytaj.",
            "uk": "До побачення! Якщо потрібно буде щось ще — звертайтесь.",
            "ru": "До свидания! Если вам что-то понадобится, обращайтесь.",
            "ka": "ნახვამდის! თუ კიდევ დაგჭირდებათ რაიმე — დაწერეთ."
        }
    )
    fallback_ai_error_message: Dict[str, str] = Field(
        default_factory=lambda: {
            "en": "Unfortunately, I'm having trouble generating a response right now. Please try again later.",
            "pl": "Niestety, mam problem z wygenerowaniem odpowiedzi. Spróbuj ponownie później.",
            "uk": "На жаль, не можу згенерувати відповідь. Спробуйте пізніше.",
            "ru": "К сожалению, я не могу сейчас сгенерировать ответ. Пожалуйста, попробуйте позже.",
            "ka": "სამწუხაროდ, ამჟამად ვერ ვქმნი პასუხს. გთხოვთ, სცადეთ მოგვიანებით."
        }
    )

    app_name: Optional[str] = None

    ai_model: AIModelEnum
    created_at: datetime = Field(default_factory=datetime.utcnow)
