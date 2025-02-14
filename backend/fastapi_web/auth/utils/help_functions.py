"""Вспомогательные функции приложения Аутентификации."""
from functools import wraps

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import JWTDecodeError, MissingTokenError

from db.mongo.db_init import mongo_db
from users.db.mongo.schemas import Settings


@AuthJWT.load_config
def get_config():
    """Конфиг для работы с jwt."""
    return Settings()


async def add_token_to_blacklist(user_id: str, token_type: str, jti: str):
    """Добавить токен в черный список."""
    await mongo_db.blacklist.update_one(
        {"user_id": user_id},
        {"$addToSet": {f"{token_type}_blacklist": jti}},
        upsert=True
    )


async def is_token_blacklisted(
        user_id: str, token_type: str, jti: str) -> bool:
    """Проверка нахождения токена в черном списке."""
    user_blacklist = await mongo_db.blacklist.find_one({"user_id": user_id})
    return user_blacklist and jti in user_blacklist.get(
        f"{token_type}_blacklist", [])


def jwt_required():
    """
    Декоратор, требующий наличие и валидность JWT-токена.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(
            request: Request,
            response: Response,
            *args,
            Authorize: AuthJWT = Depends(),
            **kwargs
        ):
            try:
                Authorize.jwt_required()
                raw_jwt = Authorize.get_raw_jwt()
                jti = raw_jwt["jti"]
                current_user = Authorize.get_jwt_subject()

                if await is_token_blacklisted(current_user, "access", jti):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token (blacklisted)."
                    )
                return await func(request, response, *args, Authorize=Authorize, **kwargs)

            except JWTDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized. Token decode error."
                )
            except MissingTokenError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized. Token not found."
                )
            except HTTPException as e:
                raise e
            except Exception as e:
                raise e

        return wrapper
    return decorator
