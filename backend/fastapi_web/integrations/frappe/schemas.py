from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class SessionRequest(BaseModel):
    """Запрос на выпуск access-токена по HMAC."""
    user_id: str
    ts: int
    nonce: str
    sig: str
    aud: str | None = None


class SessionResponse(BaseModel):
    """Ответ с access-токеном."""
    token: str
    exp: int


class EnsureMongoAdminUserRequest(BaseModel):
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None  # RoleEnum.value
    frappe_roles: Optional[List[str]] = None


class BotSettingsSyncRequest(BaseModel):
    project_name: str
    employee_name: str
    mention_name: bool = False
    avatar_url: Optional[str] = None
    bot_color: str
    communication_tone: str
    personality_traits: str
    additional_instructions: Optional[str] = None
    role: Optional[str] = None
    target_action: List[str] = Field(default_factory=list)
    core_principles: Optional[str] = None
    special_instructions: List[str] = Field(default_factory=list)
    forbidden_topics: List[str] = Field(default_factory=list)

    greeting: Dict[str, str] = Field(default_factory=dict)
    error_message: Dict[str, str] = Field(default_factory=dict)
    farewell_message: Dict[str, str] = Field(default_factory=dict)
    fallback_ai_error_message: Dict[str, str] = Field(default_factory=dict)

    app_name: Optional[str] = None
    ai_model: str
    created_at: Optional[str] = None

    frappe_doctype: Optional[str] = None
    frappe_name: Optional[str] = None
    frappe_modified: Optional[str] = None

    is_active: bool = False