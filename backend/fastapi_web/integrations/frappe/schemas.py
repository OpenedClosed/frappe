from typing import List, Optional
from pydantic import BaseModel

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
