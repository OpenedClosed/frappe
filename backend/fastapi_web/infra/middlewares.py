"""Функциональные прослойки проекта."""
import base64

from fastapi import HTTPException, Request, status
from fastapi_jwt_auth import AuthJWT
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from auth.utils.help_functions import (add_token_to_blacklist,
                                       is_token_blacklisted)


class RefreshTokenMiddleware(BaseHTTPMiddleware):
    """Мидлваре проверки и обновления refresh токена."""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        Authorize = AuthJWT()
        try:
            refresh_token = request.cookies.get("refresh_token")
            if not refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token is missing."
                )
            Authorize._token = refresh_token
            Authorize.jwt_refresh_token_required()
            raw_jwt = Authorize.get_raw_jwt()
            jti = raw_jwt["jti"]
            current_user = Authorize.get_jwt_subject()

            if await is_token_blacklisted(current_user, "refresh", jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token is invalid."
                )

            new_refresh_token = Authorize.create_refresh_token(
                subject=current_user)

            response = await call_next(request)

            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=False,
                secure=True,
                samesite="None"
            )
            await add_token_to_blacklist(current_user, "refresh", jti)
        except Exception:
            response = await call_next(request)
        return response


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Проверка аутентификации для доступа к документации."""

    def __init__(self, app, username: str, password: str):
        super().__init__(app)
        self.username = username
        self.password = password

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/docs", "/openapi.json"]:
            auth_header = request.headers.get("Authorization")
            if auth_header is None:
                return Response(
                    headers={"WWW-Authenticate": "Basic"},
                    status_code=status.HTTP_401_UNAUTHORIZED
                )

            try:
                scheme, credentials = auth_header.split()
                if scheme.lower() != "basic":
                    raise ValueError("Invalid auth schema.")

                decoded_credentials = base64.b64decode(
                    credentials).decode("utf-8")
                username, password = decoded_credentials.split(":")

                if username != self.username or password != self.password:
                    raise ValueError("Data error.")
            except Exception as e:
                return Response(
                    headers={"WWW-Authenticate": "Basic"},
                    status_code=status.HTTP_401_UNAUTHORIZED
                )

        response = await call_next(request)
        return response
