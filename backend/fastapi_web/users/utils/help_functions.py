"""Вспомогательные функции приложения Пользователи."""
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi_jwt_auth import AuthJWT
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from db.mongo.db_init import mongo_db
from users.db.mongo.schemas import User, UserWithData


async def get_current_user(
    Authorize: AuthJWT = Depends(),
    data: Optional[dict] = {},
) -> dict:
    """
    Извлекает user_id из JWT, ищет пользователя в Mongo и возвращает его в виде словаря.
    """
    user_id = Authorize.get_jwt_subject()
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Ищем пользователя по _id в коллекции "users" (название подставь своё)
    user_doc = await mongo_db["users"].find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    # Приводим _id -> str, чтобы удобно было использовать дальше
    user_doc["_id"] = str(user_doc["_id"])

    # Пример: user_doc может содержать "role", "username", "is_superuser" и т.д.
    # user_doc = User(**user_doc)
    data["user_id"] = user_id
    user_doc = UserWithData(**user_doc, data=data)
    return user_doc
