"""Формирование маршрутов приложения Персональный аккаунт."""
import random
import string
from datetime import datetime
from typing import Dict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT

from crud_core.registry import BaseRegistry
from crud_core.routes_generator import generate_base_routes
from db.mongo.db_init import mongo_db
from users.db.mongo.enums import RoleEnum
from users.db.mongo.schemas import User
from utils.help_functions import normalize_numbers, send_sms

from .client_interface.db.mongo.schemas import (ConfirmationSchema,
                                                LoginSchema,
                                                RegistrationSchema,
                                                TwoFASchema)

REG_CODES: Dict[str, str] = {}
TWO_FA_CODES: Dict[str, str] = {}


def generate_base_account_routes(registry) -> APIRouter:
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
        - Генерируем код и (опционально) отправляем SMS.
        """
        errors: dict[str, str] = {}

        if not data.accept_terms:
            errors["accept_terms"] = "Must accept terms."
        if not data.passwords_match():
            errors["password"] = errors["password_confirm"] = "Passwords do not match."

        phone_key = normalize_numbers(data.phone)
        if not phone_key:
            errors["phone"] = "Phone is required."
        else:
            if await mongo_db["patients_main_info"].find_one({"phone": phone_key}):
                errors["phone"] = "User with this phone already exists."

        if errors:
            return JSONResponse(status_code=400, content={"errors": errors})

        code = "".join(random.choices("0123456789", k=6))
        REG_CODES[phone_key] = code

        # await send_sms(phone_key, f"Код подтверждения: {code}")

        return {"message": "Code sent to phone", "debug_code": code}

    @router.post("/register_confirm")
    async def register_confirm(
        data: ConfirmationSchema,
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Шаг 2 регистрации:
        - Проверяем код из REG_CODES.
        - Создаём пользователя, две коллекции пациента.
        - Сохраняем query-параметры запроса в `metadata`.
        - (пока закомментировано) создаём запись в CRM.
        - Выдаём JWT-токены.
        """
        phone_key = normalize_numbers(data.phone)
        if REG_CODES.pop(phone_key, None) != data.code:
            raise HTTPException(400, "Invalid code.")
        if not data.passwords_match():
            raise HTTPException(400, "Passwords do not match.")

        user = User(password=data.password, role=RoleEnum.CLIENT)
        user.set_password()
        user_doc = user.model_dump(mode="python") | {
            "created_at": datetime.utcnow()}
        user_id = (await mongo_db["users"].insert_one(user_doc)).inserted_id

        ln, fn, *rest = data.full_name.split()
        main_doc = {
            "last_name": ln,
            "first_name": fn,
            "patronymic": rest[0] if rest else "",
            "phone": phone_key,
            "user_id": str(user_id),
            # сохраняем query-параметры
            "metadata": dict(request.query_params),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await mongo_db["patients_main_info"].insert_one(main_doc)

        contact_doc = {
            "phone": phone_key,
            "email": data.email or "",
            "user_id": str(user_id),
            "updated_at": datetime.utcnow()
        }
        await mongo_db["patients_contact_info"].insert_one(contact_doc)

        # ---------- CRM (пока отключено) ----------
        # crm_client = get_client()
        # pid = await crm_client.find_or_create_patient(local_data=main_doc, contact_data=contact_doc)
        # await mongo_db["patients_main_info"].update_one(
        #     {"user_id": str(user_id)}, {"$set": {"patient_id": pid}}
        # )

        access_token = Authorize.create_access_token(subject=str(user_id))
        refresh_token = Authorize.create_refresh_token(subject=str(user_id))

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

        return {"message": "Registered", "user_id": str(user_id)}

    @router.post("/login")
    async def login(data: LoginSchema):
        """
        Шаг 1 входа:
        - Проверяем телефон и пароль.
        - Если у пользователя нет patient_id, но он есть в CRM — обновляем.
        - Генерируем одноразовый код 2FA и (опц.) отправляем SMS.
        """
        phone_key = normalize_numbers(data.phone)
        user_main = await mongo_db["patients_main_info"].find_one({"phone": phone_key})
        if not user_main or not user_main.get("user_id"):
            raise HTTPException(404, detail={"phone": "User not found"})

        user = await mongo_db["users"].find_one({"_id": ObjectId(user_main["user_id"])})
        if not user or not data.check_password(user.get("password", "")):
            raise HTTPException(401, detail={"password": "Wrong password"})

        # Попытка найти пациента в CRM и обновить, если patient_id отсутствует
        if not user_main.get("patient_id"):
            # from utils.crm import get_client
            # crm = get_client()
            # patient_id = await crm.find_patient(
            #     phone=phone_key,
            #     pesel=None,  # можно заменить на user_main.get("pesel")
            #     gender=user_main.get("gender", "other"),
            #     birth_date=user_main.get("birth_date", datetime.utcnow()).strftime("%Y-%m-%d")
            # )
            # if patient_id:
            #     await mongo_db["patients_main_info"].update_one(
            #         {"_id": user_main["_id"]},
            #         {"$set": {"patient_id": patient_id}}
            #     )
            pass  # CRM-интеграция временно отключена

        code_2fa = "".join(random.choices("0123456789", k=6))
        TWO_FA_CODES[phone_key] = code_2fa
        # await send_sms(phone_key, f"Ваш код входа: {code_2fa}")

        return {"message": "2FA code sent", "debug_code": code_2fa}

    @router.post("/login_confirm")
    async def login_confirm(
        data: TwoFASchema,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Шаг 2 входа:
        - Проверяем одноразовый код.
        - Выдаём JWT-токены.
        """
        phone_key = normalize_numbers(data.phone)
        if TWO_FA_CODES.pop(phone_key, None) != data.code:
            raise HTTPException(400, detail={"code": "Invalid 2FA code"})

        user_main = await mongo_db["patients_main_info"].find_one({"phone": phone_key})
        if not user_main or not user_main.get("user_id"):
            raise HTTPException(404, detail={"phone": "User not found"})

        user_id = str(user_main["user_id"])
        access_token = Authorize.create_access_token(subject=user_id)
        refresh_token = Authorize.create_refresh_token(subject=user_id)

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

        return {"message": "Logged in", "access_token": access_token}

    router.include_router(generate_base_routes(registry))
    return router
