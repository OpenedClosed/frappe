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
