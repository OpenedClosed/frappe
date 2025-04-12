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

    user_doc = await mongo_db["users"].find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    user_doc["_id"] = str(user_doc["_id"])
    data["user_id"] = user_id
    user = UserWithData(**user_doc, data=data)
    return user


async def get_user_by_id(user_id: str, data: Optional[dict] = {}) -> UserWithData:
    """
    Получает пользователя по ID из MongoDB и возвращает в виде UserWithData.
    """
    user_doc = await mongo_db["users"].find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    user_doc["_id"] = str(user_doc["_id"])
    data["user_id"] = user_id
    return UserWithData(**user_doc, data=data)
