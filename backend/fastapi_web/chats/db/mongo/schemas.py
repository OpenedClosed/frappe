"""Схемы приложения Чаты для работы с БД MongoDB."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from db.mongo.base.schemas import (BaseValidatedIdModel, BaseValidatedModel,
                                   IdModel)

from .enums import ChatSource, ChatStatus, SenderRole


class GptEvaluation(BaseModel):
    """Результаты анализа GPT."""
    topics: Optional[List[Any]] = Field(default_factory=list)
    confidence: float = 0.0
    out_of_scope: bool = False
    consultant_call: bool = False


class BriefQuestion(IdModel):
    """Вопрос брифа."""
    question: str
    question_translations: Optional[Dict[str, str]] = None
    expected_answers: Optional[List[str]] = None
    expected_answers_translations: Optional[Dict[str, List[str]]] = None
    question_type: str = "text"


class BriefAnswer(IdModel):
    """Ответ на вопрос брифа."""
    question: str
    expected_answers: Optional[List[str]] = None
    user_answer: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(BaseValidatedIdModel):
    """Сообщение в чате."""
    message: str
    message_before_postprocessing: Optional[str] = None
    sender_role: SenderRole
    sender_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    choice_options: Optional[List] = None
    choice_strict: bool = False
    gpt_evaluation: Optional[GptEvaluation] = None
    snippets_by_source: Optional[Dict[str, Any]] = Field(default_factory=dict)
    reply_to: Optional[str] = None
    external_id: Optional[str] = None
    synced_to_constructor: bool = False
    files: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] | None = {}

    @field_validator("message")
    @classmethod
    def validate_length(cls, v: str, info: ValidationInfo) -> str:
        MAX_MESSAGE_LENGTH = 10000
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"Сообщение превышает допустимую длину {MAX_MESSAGE_LENGTH} символов.")
        return v


class MasterClient(BaseValidatedIdModel):
    """Информация о клиенте."""
    client_id: str
    source: ChatSource
    external_id: Optional[str] = None
    name: str | None = None
    avatar_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    created_at: datetime


class Client(IdModel):
    """Клиент."""
    client_id: str
    source: ChatSource


class ChatReadInfo(BaseValidatedModel):
    """Отметка о том, до какого сообщения дочитал конкретный участник."""
    client_id: str
    user_id: Optional[str] = None
    last_read_msg: str
    last_read_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(BaseValidatedModel):
    """Чат-сессия."""

    chat_id: str
    client: Optional[Client] = None
    bot_id: Optional[str] = None
    company_name: Optional[str] = None
    external_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    manual_mode: bool = False
    messages: Optional[List[ChatMessage]] = []
    brief_answers: List[BriefAnswer] = []
    closed_by_request: Optional[bool] = False
    admin_marker: bool = False
    constructor_chat_id: Optional[str] = None
    read_state: Optional[List[ChatReadInfo]] = Field(default_factory=list)

    @property
    def updated_at(self) -> datetime:
        """Дата последнего сообщения в чате (или last_activity/created_at)."""
        if self.messages:
            return self.messages[-1].timestamp
        if self.last_activity:
            return self.last_activity
        return self.created_at


    def get_client_id(self) -> str:
        """Возвращает client_id клиента (external_id больше не хранится здесь)."""
        return self.client.client_id if self.client else ""

    def calculate_mode(self, brief_questions: List[BriefQuestion]) -> str:
        """Определяет текущий режим работы чата."""
        return "brief" if not self.is_brief_completed(brief_questions) else (
            "manual" if self.manual_mode else "automatic"
        )

    def compute_status(self, ttl_value: int) -> ChatStatus:
        """Определяет статус чата на основе его активности и закрытия."""
        if self.closed_by_request:
            return ChatStatus.FORCED_CLOSED
        if ttl_value > 0:
            return ChatStatus.IN_PROGRESS
        if not self.messages:
            return ChatStatus.CLOSED_WITHOUT_RESPONSE
        return self.determine_final_status()

    def get_current_question(
            self, brief_questions: List[BriefQuestion]) -> Optional[BriefQuestion]:
        """Возвращает следующий вопрос брифа, на который ещё не был дан ответ."""
        answered_questions = {a.question for a in self.brief_answers}
        return next(
            (q for q in brief_questions if q.question not in answered_questions), None)

    def is_brief_completed(
            self, brief_questions: List[BriefQuestion]) -> bool:
        """Проверяет, все ли вопросы брифа получили ответы."""
        return {a.question for a in self.brief_answers}.issuperset(
            q.question for q in brief_questions)

    def determine_final_status(self) -> ChatStatus:
        """Возвращает финальный статус чата в зависимости от последнего сообщения."""
        return (
            ChatStatus.SUCCESSFULLY_CLOSED
            if self.messages[-1].sender_role == SenderRole.CONSULTANT
            else ChatStatus.CLOSED_WITHOUT_RESPONSE
        )

    def is_read_by_any_staff(self, staff_ids: set[str]) -> bool:
        """Проверяет, прочитан ли чат хотя бы одним из указанных staff-пользователей."""
        if not self.messages or not self.read_state:
            return False

        last_msg_id = self.messages[-1].id

        return any(
            ri.user_id in staff_ids and ri.last_read_msg == last_msg_id
            for ri in self.read_state if ri.user_id
        )
