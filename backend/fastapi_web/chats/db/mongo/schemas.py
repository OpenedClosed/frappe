"""Схемы приложения Чаты для работы с БД MongoDB."""
from datetime import datetime, timedelta
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from db.mongo.base.schemas import (
    BaseValidatedIdModel,
    BaseValidatedModel,
    IdModel,
)
from .enums import ChatSource, ChatStatus, SenderRole

# ==============================
# Модели брифа и оценок
# ==============================


class GptEvaluation(BaseModel):
    """Результаты анализа GPT."""
    topics: Optional[List[Any]] = Field(default_factory=list)
    confidence: float = 0.0
    out_of_scope: bool = False
    consultant_call: Optional[bool] = None


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

# ==============================
# Сообщения и клиенты
# ==============================


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
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def validate_length(cls, v: str, info: ValidationInfo) -> str:
        max_len = 10000
        if len(v) > max_len:
            raise ValueError(
                f"Сообщение превышает допустимую длину {max_len} символов."
            )
        return v


class MasterClient(BaseValidatedIdModel):
    """Информация о клиенте."""
    client_id: str
    source: ChatSource
    external_id: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    created_at: datetime


class Client(IdModel):
    """Клиент."""
    client_id: str
    source: ChatSource


class ChatReadInfo(BaseValidatedModel):
    """Отметка о том, до какого сообщения дочитал участник."""
    client_id: str
    user_id: Optional[str] = None
    last_read_msg: str
    last_read_at: datetime = Field(default_factory=datetime.utcnow)

# ==============================
# Чат-сессия
# ==============================


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
    consultant_requested: bool = False
    messages: List[ChatMessage] = Field(default_factory=list)
    brief_answers: List[BriefAnswer] = Field(default_factory=list)
    closed_by_request: Optional[bool] = False
    admin_marker: bool = False
    constructor_chat_id: Optional[str] = None
    read_state: List[ChatReadInfo] = Field(default_factory=list)

    @property
    def updated_at(self) -> datetime:
        """Дата последнего сообщения или активности."""
        if self.messages:
            return self.messages[-1].timestamp
        if self.last_activity:
            return self.last_activity
        return self.created_at

    def get_client_id(self) -> str:
        """Возвращает client_id клиента."""
        return self.client.client_id if self.client else ""

    def calculate_mode(self, brief_questions: List[BriefQuestion]) -> str:
        """Определяет текущий режим работы чата."""
        return (
            "brief"
            if not self.is_brief_completed(brief_questions)
            else ("manual" if self.manual_mode else "automatic")
        )


    def compute_status(
        self,
        ttl_value: int,
        staff_ids: Optional[set[str]] = None,
        brief_questions: Optional[List[BriefQuestion]] = None,
    ) -> ChatStatus:
        """Возвращает текущий статус чата с подробными логами.

        Правила смены статуса:
        1) Закрыто:
            • CLOSED_BY_OPERATOR — если self.closed_by_request.
            • CLOSED_NO_MESSAGES — если TTL <= 0 и сообщений нет.
            • CLOSED_BY_TIMEOUT — если TTL <= 0 и сообщения есть.
        2) Старт/бриф:
            • NEW_SESSION — если сообщений ещё нет (и нет эскалации).
            • MANUAL_WAITING_CONSULTANT — если сообщений нет, но consultant_requested=True.
            • BRIEF_IN_PROGRESS — если бриф не завершён.
        3) Ручной режим (manual_mode=True):
            • MANUAL_WAITING_CLIENT — клиент ещё не писал.
            • MANUAL_WAITING_CONSULTANT — последнее клиентское НЕ прочитано staff.
            • MANUAL_WAITING_CLIENT — консультант уже ответил ПОСЛЕ последнего клиентского.
            • MANUAL_READ_BY_CONSULTANT — последнее клиентское прочитано, ответа ещё нет.
        4) Авто + эскалация (consultant_requested=True, manual_mode=False):
            • AUTO_WAITING_AI — если последним писал клиент (идёт/будет ответ ИИ).
            • MANUAL_READ_BY_CONSULTANT — если клиентское прочитано staff.
            • MANUAL_WAITING_CONSULTANT — если клиентское ещё НЕ прочитано staff.
        5) Чистый авто-режим (без эскалации):
            • AUTO_WAITING_AI — если последним писал клиент.
            • AUTO_WAITING_CLIENT — если последним писал не клиент (ИИ/консультант).
        """

        # --- 1) Закрыто ---
        if self.closed_by_request:
            return ChatStatus.CLOSED_BY_OPERATOR

        if ttl_value <= 0:
            if not self.messages:
                return ChatStatus.CLOSED_NO_MESSAGES
            return ChatStatus.CLOSED_BY_TIMEOUT

        # --- 2) Нет сообщений / бриф ---
        if not self.messages:
            if self.consultant_requested:
                return ChatStatus.MANUAL_WAITING_CONSULTANT
            return ChatStatus.NEW_SESSION

        if self.calculate_mode(brief_questions or []) == "brief":
            return ChatStatus.BRIEF_IN_PROGRESS

        # --- 3) Индексы/роли ---
        def _role_en(msg_role) -> str:
            try:
                return json.loads(msg_role)["en"] if isinstance(msg_role, str) else msg_role.en_value
            except Exception:
                return "Unknown"

        last_msg = self.messages[-1]
        last_role = _role_en(last_msg.sender_role)

        last_client_idx = -1
        last_client_id = None
        for i in range(len(self.messages) - 1, -1, -1):
            if _role_en(self.messages[i].sender_role) == SenderRole.CLIENT.en_value:
                last_client_idx = i
                last_client_id = self.messages[i].id
                break

        last_consultant_idx = -1
        for i in range(len(self.messages) - 1, -1, -1):
            if _role_en(self.messages[i].sender_role) == SenderRole.CONSULTANT.en_value:
                last_consultant_idx = i
                break

        # --- 3.1) Свежее ли последнее клиентское сообщение для AUTO_WAITING_AI ---
        AI_WAITING_MAX_AGE = timedelta(hours=1)
        has_recent_client_msg = False
        if last_client_idx != -1:
            try:
                client_ts = self.messages[last_client_idx].timestamp
                has_recent_client_msg = (datetime.utcnow() - client_ts) <= AI_WAITING_MAX_AGE
            except Exception:
                has_recent_client_msg = False

        # --- 3.2) Если консультант уже ответил после клиента — диалог закрыт, ждём клиента ---
        # (Это «короткое замыкание» исключает любые «ожидания консультанта» дальше.)
        if last_client_idx != -1 and last_consultant_idx > last_client_idx:
            return ChatStatus.MANUAL_WAITING_CLIENT

        # --- 4) Прочтение staff ---
        read_by_staff = self.is_read_by_any_staff(staff_ids or set())

        # --- 5) Ручной режим ---
        if self.manual_mode:
            if last_client_idx == -1:
                return ChatStatus.MANUAL_WAITING_CLIENT

            # до сюда уже известно, что консультант НЕ отвечал после клиента
            if not read_by_staff:
                return ChatStatus.MANUAL_WAITING_CONSULTANT

            # консультант не ответил, но клиентское прочитано
            return ChatStatus.MANUAL_READ_BY_CONSULTANT

        # --- 6) Авто + эскалация ---
        if self.consultant_requested:
            if last_role == SenderRole.CLIENT.en_value:
                # AI ждём только если клиент писал недавно
                return ChatStatus.AUTO_WAITING_AI if has_recent_client_msg else ChatStatus.MANUAL_WAITING_CONSULTANT

            # последний не клиент → смотрим read_state
            return ChatStatus.MANUAL_READ_BY_CONSULTANT if read_by_staff else ChatStatus.MANUAL_WAITING_CONSULTANT

        # --- 7) Чистый авто-режим ---
        if last_role == SenderRole.CLIENT.en_value:
            return ChatStatus.AUTO_WAITING_AI if has_recent_client_msg else ChatStatus.AUTO_WAITING_CLIENT

        return ChatStatus.AUTO_WAITING_CLIENT

    def get_current_question(
        self, brief_questions: List[BriefQuestion]
    ) -> Optional[BriefQuestion]:
        """Возвращает следующий вопрос брифа без ответа."""
        answered = {a.question for a in self.brief_answers}
        return next((q for q in brief_questions if q.question not in answered), None)

    def is_brief_completed(self, brief_questions: List[BriefQuestion]) -> bool:
        """Проверяет, все ли вопросы брифа получили ответы."""
        return {a.question for a in self.brief_answers}.issuperset(
            q.question for q in brief_questions
        )

    def is_read_by_any_staff(self, staff_ids: set[str]) -> bool:
        """Проверяет, прочитан ли чат хотя бы одним из указанных staff-пользователей."""
        if not self.messages or not self.read_state:
            return False
        last_msg_id = self.messages[-1].id
        return any(
            ri.user_id in staff_ids and ri.last_read_msg == last_msg_id
            for ri in self.read_state
            if ri.user_id
        )
