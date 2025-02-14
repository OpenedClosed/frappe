"""Схемы приложения Чаты для работы с БД MongoDB."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from db.mongo.base.schemas import IdModel

from .enums import ChatSource, ChatStatus, SenderRole


class GptEvaluation(BaseModel):
    """Модель для хранения результатов анализа GPT."""
    topic: str = ""
    subtopic: str = ""
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


class ChatMessage(IdModel):
    """Модель сообщения в чате."""
    message: str
    sender_role: SenderRole
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    choice_options: Optional[List[str]] = None
    choice_strict: bool = False
    gpt_evaluation: Optional[GptEvaluation] = None
    reply_to: Optional[str] = None
    external_id: Optional[str] = None
    command_name: Optional[str] = None



class Client(IdModel):
    """Модель клиента."""
    client_id: str
    source: ChatSource
    external_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ChatSession(BaseModel):
    """Модель чата."""
    chat_id: str
    client: Client
    bot_id: Optional[str] = None
    company_name: Optional[str] = None
    external_id: Optional[str] = None  # ID Instagram-бота
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime
    manual_mode: bool = False
    messages: List[ChatMessage] = []
    brief_answers: List[BriefAnswer] = []
    closed_by_request: Optional[bool] = False
    admin_marker: bool = False

    def get_client_id(self) -> str:
        """Быстрый доступ к `client_id` клиента."""
        return self.client.external_id if self.client.external_id else self.client.client_id

    def calculate_mode(self, brief_questions: List[BriefQuestion]) -> str:
        """Определение режима брифа."""
        answered = {a.question for a in self.brief_answers}
        all_q = {q.question for q in brief_questions}
        if not answered.issuperset(all_q):
            return "brief"
        return "manual" if self.manual_mode else "automatic"

    def compute_status(self, ttl_value: int) -> ChatStatus:
        """Вычисление статуса чата."""
        if self.closed_by_request:
            return ChatStatus.FORCED_CLOSED

        if ttl_value > 0:
            return ChatStatus.IN_PROGRESS

        if not self.messages:
            return ChatStatus.CLOSED_WITHOUT_RESPONSE

        return (
            ChatStatus.SUCCESSFULLY_CLOSED
            if self.messages[-1].sender_role == SenderRole.CONSULTANT
            else ChatStatus.CLOSED_WITHOUT_RESPONSE
        )

    def get_current_question(
            self, brief_questions: List[BriefQuestion]) -> Optional[BriefQuestion]:
        """Определение текущего вопроса брифа."""
        answered_questions = {a.question for a in self.brief_answers}
        return next(
            (q for q in brief_questions if q.question not in answered_questions), None)
