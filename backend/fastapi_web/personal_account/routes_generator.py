"""Формирование маршрутов приложения Персональный аккаунт."""
import random
import string
from datetime import datetime
from typing import Dict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT

from crud_core.registry import BaseRegistry
from crud_core.routes_generator import generate_base_routes
from db.mongo.db_init import mongo_db
from users.db.mongo.enums import RoleEnum
from users.db.mongo.schemas import User

from .client_interface.db.mongo.schemas import (ConfirmationSchema,
                                                LoginSchema,
                                                RegistrationSchema,
                                                TwoFASchema)

REG_CODES: Dict[str, str] = {}
TWO_FA_CODES: Dict[str, str] = {}


def generate_base_account_routes(registry: BaseRegistry) -> APIRouter:
    """
    Генерирует маршруты для регистрации и авторизации.
    """
    router = APIRouter()

    @router.post("/register")
    async def register(data: RegistrationSchema):
        """
        Шаг 1 регистрации:
        - Проверяем согласие (accept_terms).
        - Проверяем совпадение паролей.
        - Проверяем, что телефон не занят.
        - Генерируем код, отправляем (заглушка).
        """

        errors = {}

        if not data.accept_terms:
            errors["accept_terms"] = "Must accept terms."

        if not data.passwords_match():
            errors["password"] = "Passwords do not match."
            errors["password_confirm"] = "Passwords do not match."

        phone_key = data.phone.strip()
        if not phone_key:
            errors["phone"] = "Phone is required."
        else:
            existing_main = await mongo_db["patients_main_info"].find_one({"phone": phone_key})
            if existing_main:
                errors["phone"] = "User with this phone already exists."

        if errors:
            return JSONResponse(status_code=400, content={"errors": errors})

        code = "".join(random.choices(string.digits, k=6))
        REG_CODES[phone_key] = code

        return {"message": "Code sent to phone", "debug_code": code}

    @router.post("/register_confirm")
    async def register_confirm(
        data: ConfirmationSchema,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Шаг 2 регистрации:
        - Проверяем код из REG_CODES.
        - Если ок, создаём:
            1) Запись в `users` (роль CLIENT), телефон = username, пароль хэшируем
            2) Документ в `patients_main_info` (phone, ФИО, ...)
            3) Документ в `patients_contact_info` (phone, email, user_id, ...)
        - Выдаём токены.
        """
        phone_key = data.phone.strip()
        real_code = REG_CODES.pop(phone_key, None)
        if not real_code or real_code != data.code:
            raise HTTPException(400, "Invalid code.")

        if not data.passwords_match():
            raise HTTPException(400, "Passwords do not match.")

        new_user = User(
            password=data.password,
            role=RoleEnum.CLIENT,
        )
        new_user.set_password()
        user_doc = new_user.model_dump(mode="python")
        user_doc["created_at"] = datetime.utcnow()

        user_result = await mongo_db["users"].insert_one(user_doc)
        user_id = user_result.inserted_id

        splitted = data.full_name.split()
        last_name = splitted[0] if len(splitted) > 0 else ""
        first_name = splitted[1] if len(splitted) > 1 else ""
        patronymic = splitted[2] if len(splitted) > 2 else ""

        main_doc = {
            "last_name": last_name,
            "first_name": first_name,
            "patronymic": patronymic,
            "phone": phone_key,
            "user_id": str(user_id),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        main_info_result = await mongo_db["patients_main_info"].insert_one(main_doc)

        contact_doc = {
            "phone": phone_key,
            "email": data.email or "",
            "user_id": str(user_id),
            "updated_at": datetime.utcnow()
        }
        await mongo_db["patients_contact_info"].insert_one(contact_doc)

        access_token = Authorize.create_access_token(subject=str(user_id))
        refresh_token = Authorize.create_refresh_token(subject=str(user_id))

        response.set_cookie(
            "access_token", access_token,
            httponly=False, secure=True, samesite="None"
        )
        response.set_cookie(
            "refresh_token", refresh_token,
            httponly=False, secure=True, samesite="None"
        )

        return {
            "message": "Registered",
            "user_id": str(user_id)
        }

    @router.post("/login")
    async def login(data: LoginSchema):
        """
        Шаг 1 входа:
        - Ищем пользователя по телефону.
        - Проверяем пароль (data.check_password(stored_hash)).
        - Генерируем одноразовый код 2FA.
        """
        phone_key = data.phone.strip()

        user_main = await mongo_db["patients_main_info"].find_one({"phone": phone_key})
        if not user_main or not user_main.get("user_id"):
            raise HTTPException(
                status_code=404,
                detail={"phone": "User not found"}
            )

        user_id = user_main["user_id"]
        user = await mongo_db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"phone": "User not found"}
            )

        stored_hash = user.get("password", "")
        if not data.check_password(stored_hash):
            raise HTTPException(
                status_code=401,
                detail={"password": "Wrong password"}
            )

        code_2fa = "".join(random.choices(string.digits, k=6))
        TWO_FA_CODES[phone_key] = code_2fa

        return {
            "message": "2FA code sent",
            "debug_code": code_2fa
        }

    @router.post("/login_confirm")
    async def login_confirm(
        data: TwoFASchema,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Шаг 2 входа:
        - Проверяем код из TWO_FA_CODES.
        - Возвращаем JWT токены.
        """
        phone_key = data.phone.strip()

        real_code = TWO_FA_CODES.pop(phone_key, None)
        if not real_code or real_code != data.code:
            raise HTTPException(
                status_code=400,
                detail={"code": "Invalid 2FA code"}
            )

        user_main = await mongo_db["patients_main_info"].find_one({"phone": phone_key})
        if not user_main or not user_main.get("user_id"):
            raise HTTPException(
                status_code=404,
                detail={"phone": "User not found"}
            )

        user_id = str(user_main["user_id"])

        access_token = Authorize.create_access_token(subject=user_id)
        refresh_token = Authorize.create_refresh_token(subject=user_id)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=False,
            secure=True,
            samesite="None"
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=False,
            secure=True,
            samesite="None"
        )

        return {
            "message": "Logged in",
            "access_token": access_token
        }

    base_router = generate_base_routes(registry)
    router.include_router(base_router)
    return router
