"""Формирование маршрутов приложения Персональный аккаунт."""
import random
import string
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi_jwt_auth import AuthJWT
from crud_core.registry import BaseRegistry
from crud_core.routes_generator import generate_base_routes
from db.mongo.db_init import mongo_db

from .client_interface.db.mongo.schemas import ConfirmSchema, RegisterSchema

REG_CODES: Dict[str, str] = {}


def generate_base_account_routes(registry: BaseRegistry) -> APIRouter:
    """Генерирует маршруты для управления аккаунтами."""
    router = generate_base_routes(registry)

    @router.post("/login")
    async def login_no_password(
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """Логин без пароля: пользователь передаёт email/phone + code."""
        data = await request.json()
        key = data.get("email", "").lower() or data.get("phone", "")
        code = data.get("code")

        if not key or not code:
            raise HTTPException(400, "Email/phone and code required")

        if REG_CODES.pop(key, None) != code:
            raise HTTPException(400, "Invalid code")

        user_profile = await mongo_db["user_profiles"].find_one({"email": key} if "@" in key else {"phone": key})
        if not user_profile:
            raise HTTPException(
                404, "User profile not found. Please register first.")

        access_token = Authorize.create_access_token(
            subject=str(user_profile["_id"]))
        refresh_token = Authorize.create_refresh_token(
            subject=str(user_profile["_id"]))

        response.set_cookie(
            "access_token",
            access_token,
            httponly=False,
            secure=True,
            samesite="None")
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=False,
            secure=True,
            samesite="None")

        return {"message": "Logged in successfully",
                "access_token": access_token}

    @router.post("/register")
    async def register(data: RegisterSchema):
        """Генерирует код подтверждения при регистрации."""
        key = data.email.lower() if data.email else data.phone
        if not key:
            raise HTTPException(400, "Email or phone required")

        if await mongo_db["user_profiles"].find_one({"email": key} if "@" in key else {"phone": key}):
            raise HTTPException(400, "User profile already exists")

        REG_CODES[key] = "".join(random.choices(string.digits, k=6))
        return {"message": "Verification code generated.",
                "code_for_test": REG_CODES[key]}

    @router.post("/register_confirm")
    async def register_validation(
        data: ConfirmSchema,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """Создаёт профиль пользователя после подтверждения кода."""
        key = data.email.lower() if data.email else data.phone
        if not key or REG_CODES.pop(key, None) != data.code:
            raise HTTPException(400, "Invalid code")

        user_profile = {
            "email": data.email.lower() if data.email else "",
            "phone_number": data.phone or "",
            "first_name": data.first_name,
            "last_name": data.last_name,
            "birth_date": data.birth_date,
            "gender": data.gender,
            "is_2fa_enabled": False,
            "subscription_status": None,
            "medical_forms": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        user_id = await mongo_db["user_profiles"].insert_one(user_profile)
        access_token = Authorize.create_access_token(
            subject=str(user_id.inserted_id))
        refresh_token = Authorize.create_refresh_token(
            subject=str(user_id.inserted_id))

        response.set_cookie(
            "access_token",
            access_token,
            httponly=False,
            secure=True,
            samesite="None")
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=False,
            secure=True,
            samesite="None")

        return {"message": "User registered successfully"}

    return router
