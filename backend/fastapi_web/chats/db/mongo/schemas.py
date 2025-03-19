"""Схемы приложения Чаты для работы с БД MongoDB."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

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
    sender_role: SenderRole
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    choice_options: Optional[List] = None
    choice_strict: bool = False
    gpt_evaluation: Optional[GptEvaluation] = None
    reply_to: Optional[str] = None
    external_id: Optional[str] = None
    files: Optional[List[str]] = None


class Client(IdModel):
    """Клиент."""
    client_id: str
    source: ChatSource
    external_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


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

    def get_client_id(self) -> str:
        """Возвращает `client_id` или `external_id`, если он указан."""
        return self.client.external_id or self.client.client_id if self.client else ""

    def calculate_mode(self, brief_questions: List[BriefQuestion]) -> str:
        """Определяет текущий режим работы чата."""
        return "brief" if not self._is_brief_completed(brief_questions) else (
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
        return self._determine_final_status()

    def get_current_question(
            self, brief_questions: List[BriefQuestion]) -> Optional[BriefQuestion]:
        """Возвращает следующий вопрос брифа, на который ещё не был дан ответ."""
        answered_questions = {a.question for a in self.brief_answers}
        return next(
            (q for q in brief_questions if q.question not in answered_questions), None)

    def _is_brief_completed(
            self, brief_questions: List[BriefQuestion]) -> bool:
        """Проверяет, все ли вопросы брифа получили ответы."""
        return {a.question for a in self.brief_answers}.issuperset(
            q.question for q in brief_questions)

    def _determine_final_status(self) -> ChatStatus:
        """Возвращает финальный статус чата в зависимости от последнего сообщения."""
        return (
            ChatStatus.SUCCESSFULLY_CLOSED
            if self.messages[-1].sender_role == SenderRole.CONSULTANT
            else ChatStatus.CLOSED_WITHOUT_RESPONSE
        )
