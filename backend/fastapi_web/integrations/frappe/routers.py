# dantist/integration/frappe/router.py
from datetime import datetime, timedelta
from users.db.mongo.enums import RoleEnum
from fastapi import APIRouter, Depends, Response, HTTPException, Request
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import MissingTokenError, JWTDecodeError

from .schemas import SessionRequest, SessionResponse
from .utils.help_functions import verify_hmac_request
from db.mongo.db_init import mongo_db
from fastapi import APIRouter, Depends, Response, HTTPException, Request, Query

from .schemas import EnsureMongoAdminUserRequest

frappe_router = APIRouter()

@frappe_router.post("/session_request")
async def frappe_session_request(
    data: SessionRequest,
    response: Response,
    request: Request,
    Authorize: AuthJWT = Depends(),
):
    """
    Выдаёт короткий access-токен по HMAC-подписи.
    КЛАДЁТ куку access_token (same-site) и возвращает только ok/exp.
    """
    user_id = str(data.user_id).strip()
    await verify_hmac_request(user_id, data.ts, data.nonce, data.sig, data.aud)

    token = Authorize.create_access_token(subject=user_id, expires_time=timedelta(minutes=15))
    # локалка по http -> secure=False; в проде https -> secure=True
    is_https = (request.url.scheme == "https")

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=False,            # как у тебя в админке
        secure=is_https,           # dev: False, prod: True
        samesite="Lax",            # один хост — Lax достаточно
        path="/",
    )
    return {"ok": True, "exp": 15 * 60}

@frappe_router.get("/link_check")
async def frappe_link_check(
    request: Request,
    Authorize: AuthJWT = Depends(),
):
    """
    Проверяет валидность токена: из Authorization: Bearer ... ИЛИ из cookie access_token.
    """
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    token = None
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # FastAPI-JWT-Auth забирает токен из Authorize._token
    Authorize._token = token
    try:
        Authorize.jwt_required()
        subject = Authorize.get_jwt_subject()
    except (MissingTokenError, JWTDecodeError):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {"ok": True, "user_id": subject}


@frappe_router.get("/users/lookup")
async def frappe_users_lookup(email: str = Query(...)):
    u = await mongo_db.users.find_one({"email": email})
    if not u:
        return {"ok": False}
    return {"ok": True, "user_id": str(u["_id"])}

@frappe_router.post("/users/ensure_mongoadmin")
async def frappe_users_ensure_mongoadmin(data: EnsureMongoAdminUserRequest):
    col = mongo_db.users
    u = await col.find_one({"email": data.email})
    if not u:
        doc = {
            "email": data.email,
            "username": data.username or data.email.split("@")[0],
            "password": "",
            "role": (data.role or RoleEnum.CLIENT.value),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "full_name": data.full_name,
            "avatar": None,
        }
        res = await col.insert_one(doc)
        return {"ok": True, "created": True, "user_id": str(res.inserted_id)}

    updates = {}
    if not u.get("full_name") and data.full_name:
        updates["full_name"] = data.full_name
    if not u.get("username") and data.username:
        updates["username"] = data.username
    if data.role and data.role != u.get("role"):
        updates["role"] = data.role
    if updates:
        await col.update_one({"_id": u["_id"]}, {"$set": updates})
    return {"ok": True, "created": False, "user_id": str(u["_id"])}