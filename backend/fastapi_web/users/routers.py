"""Обработчики маршрутов приложения Пользователи."""
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi_jwt_auth import AuthJWT

from auth.utils.help_functions import jwt_required
from db.mongo.db_init import mongo_db

from .db.mongo.schemas import User

user_router = APIRouter()


@user_router.post("/me")
@jwt_required()
async def get_my_info(
    request: Request,
    response: Response,
    Authorize: AuthJWT = Depends()
):
    """
    Возвращает информацию о текущем пользователе по JWT.
    """
    current_user_id = Authorize.get_jwt_subject()
    if not current_user_id:
        raise HTTPException(status_code=401, detail="User not authenticated.")

    user_doc = await mongo_db["users"].find_one({"_id": ObjectId(current_user_id)})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found.")

    user = User(**user_doc)
    return user.dict(exclude={"password"})
