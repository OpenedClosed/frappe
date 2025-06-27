"""Вспомогательные функции приложения Пользователи."""
import json
from typing import Optional

from bson import ObjectId
from fastapi import Depends, HTTPException
from fastapi_jwt_auth import AuthJWT
from utils.encoders import DateTimeEncoder
from db.mongo.db_init import mongo_db
from users.db.mongo.schemas import UserWithData
from db.redis.db_init import redis_db


async def get_current_user(
    Authorize: AuthJWT = Depends(),
    data: Optional[dict] = {},
) -> dict:
    """
    Извлекает user_id из JWT, ищет пользователя в Mongo и возвращает его в виде словаря.
    """
    try:
        user_id = Authorize.get_jwt_subject()
    except Exception:
        user_id = None
    if not user_id:
        return None
        # raise HTTPException(status_code=401, detail="Not authenticated")

    user_doc = await mongo_db["users"].find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        # raise HTTPException(status_code=401, detail="User not found")
        return None

    user_doc["_id"] = str(user_doc["_id"])
    data["user_id"] = user_id
    user = UserWithData(**user_doc, data=data)
    return user


# async def get_user_by_id(
#         user_id: str, data: Optional[dict] = {}) -> UserWithData:
#     """
#     Получает пользователя по ID из MongoDB и возвращает в виде UserWithData.
#     """
#     user_doc = await mongo_db["users"].find_one({"_id": ObjectId(user_id)})
#     if not user_doc:
#         raise HTTPException(status_code=401, detail="User not found")

#     user_doc["_id"] = str(user_doc["_id"])
#     data["user_id"] = user_id
#     return UserWithData(**user_doc, data=data)

async def get_user_by_id(user_id: str, data: Optional[dict] = {}) -> UserWithData:
    """
    Получает пользователя по ID из кеша Redis или MongoDB.
    Если в Redis нет — загружает из базы и сохраняет в Redis на 60 секунд.
    """
    cache_key = f"user:data:{user_id}"

    # 1. Пробуем достать из кеша
    cached = await redis_db.get(cache_key)
    if cached:
        user_doc = json.loads(cached)
    else:
        # 2. Загружаем из MongoDB
        user_doc = await mongo_db["users"].find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            raise HTTPException(status_code=401, detail="User not found")

        # Преобразуем _id в строку для сериализации
        user_doc["_id"] = str(user_doc["_id"])

        # 3. Кладём в Redis на 60 секунд
        await redis_db.set(cache_key, json.dumps(user_doc, cls=DateTimeEncoder), ex=60)

    # Добавляем дополнительное поле
    data["user_id"] = user_id
    return UserWithData(**user_doc, data=data)
