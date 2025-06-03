"""Формирование маршрутов приложения Персональный аккаунт."""
import random
import string
from datetime import datetime
from typing import Dict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT

from integrations.panamedica.utils.help_functions import format_crm_phone
from integrations.panamedica.client import CRMError, get_client
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
    Генерирует маршруты для регистрации и входа.
    """
    router = APIRouter()

    @router.post("/register")
    async def register(data: RegistrationSchema):
        """
        Первый шаг регистрации: проверка данных и генерация кода.
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

        # TODO: отправлять SMS, когда будет готов фронт
        # await send_sms(phone_key, f"Код подтверждения: {code}")

        return {"message": "Code sent to phone", "debug_code": code}  # временно возвращаем код

    @router.post("/register_confirm")
    async def register_confirm(
        data: ConfirmationSchema,
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Второй шаг регистрации: CRM проверка → сохранение в Mongo → выдача токенов.
        """
        phone_key = "48123456789"  # временно: заглушка на номер телефона для тестов

        # TODO: вернуть проверки, когда фронт готов
        # if REG_CODES.pop(phone_key, None) != data.code:
        #     raise HTTPException(400, "Invalid code.")
        # if not data.passwords_match():
        #     raise HTTPException(400, "Passwords do not match.")

        ln, fn, *rest = data.full_name.split()
        main_doc = {
            "last_name": ln,
            "first_name": fn,
            "patronymic": rest[0] if rest else "",
            "phone": phone_key,
            "metadata": dict(request.query_params),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "gender": "male",  # временно
            "birth_date": datetime(1990, 1, 1),  # временно
        }
        contact_doc = {
            "phone": phone_key,
            "email": data.email or "",
            "updated_at": datetime.utcnow()
        }

        crm = get_client()
        try:
            crm_data = await crm.find_or_create_patient(local_data=main_doc, contact_data=contact_doc)
        except CRMError as e:
            print(e)
            raise HTTPException(502, "CRM registration failed")

        user = User(password=data.password, full_name=data.full_name, role=RoleEnum.CLIENT)
        user.set_password()
        user_doc = user.model_dump(mode="python") | {"created_at": datetime.utcnow()}
        user_id = (await mongo_db["users"].insert_one(user_doc)).inserted_id

        main_doc["user_id"] = str(user_id)
        main_doc["patient_id"] = crm_data["id"]
        main_doc["crm_last_sync"] = datetime.utcnow()
        contact_doc["user_id"] = str(user_id)

        await mongo_db["patients_main_info"].insert_one(main_doc)
        await mongo_db["patients_contact_info"].insert_one(contact_doc)

        access_token = Authorize.create_access_token(subject=str(user_id))
        refresh_token = Authorize.create_refresh_token(subject=str(user_id))

        response.set_cookie("access_token", access_token, httponly=False, secure=True, samesite="None")
        response.set_cookie("refresh_token", refresh_token, httponly=False, secure=True, samesite="None")

        return {"message": "Registered", "user_id": str(user_id)}

    @router.post("/login")
    async def login(data: LoginSchema):
        """
        Первый шаг входа: проверка данных и генерация 2FA.
        """
        phone_key = "48123456789"  # временно: заглушка на номер телефона для тестов

        user_main = await mongo_db["patients_main_info"].find_one({"phone": phone_key})
        if not user_main or not user_main.get("user_id"):
            raise HTTPException(404, detail={"phone": "User not found"})

        user = await mongo_db["users"].find_one({"_id": ObjectId(user_main["user_id"])})
        if not user or not data.check_password(user.get("password", "")):
            raise HTTPException(401, detail={"password": "Wrong password"})

        code_2fa = "".join(random.choices("0123456789", k=6))
        TWO_FA_CODES[phone_key] = code_2fa

        # TODO: отправить SMS, когда будет готов фронт
        # await send_sms(phone_key, f"Ваш код входа: {code_2fa}")

        return {"message": "2FA code sent", "debug_code": code_2fa}  # временно

    @router.post("/login_confirm")
    async def login_confirm(
        data: TwoFASchema,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Второй шаг входа: проверка кода и выдача токенов.
        """
        phone_key = "48123456789"  # временно: заглушка на номер телефона для тестов

        # TODO: вернуть проверки, когда фронт готов
        # if TWO_FA_CODES.pop(phone_key, None) != data.code:
        #     raise HTTPException(400, detail={"code": "Invalid 2FA code"})

        user_main = await mongo_db["patients_main_info"].find_one({"phone": phone_key})
        if not user_main or not user_main.get("user_id"):
            raise HTTPException(404, detail={"phone": "User not found"})

        if user_main.get("patient_id"):
            crm = get_client()
            try:
                crm_data = await crm.find_patient(patient_id=user_main["patient_id"])
                await mongo_db["patients_main_info"].update_one(
                    {"_id": user_main["_id"]},
                    {"$set": {
                        "first_name": crm_data.get("firstname"),
                        "last_name": crm_data.get("lastname"),
                        "birth_date": datetime.fromisoformat(crm_data.get("birthdate")),
                        "gender": crm_data.get("gender"),
                        "crm_last_sync": datetime.utcnow()
                    }}
                )
                await mongo_db["patients_contact_info"].update_one(
                    {"user_id": user_main["user_id"]},
                    {"$set": {
                        "email": crm_data.get("email"),
                        "phone": normalize_numbers(crm_data.get("phone")),
                        "updated_at": datetime.utcnow()
                    }}
                )
            except CRMError as e:
                print(e)

        user_id = str(user_main["user_id"])
        access_token = Authorize.create_access_token(subject=user_id)
        refresh_token = Authorize.create_refresh_token(subject=user_id)

        response.set_cookie("access_token", access_token, httponly=False, secure=True, samesite="None")
        response.set_cookie("refresh_token", refresh_token, httponly=False, secure=True, samesite="None")

        return {"message": "Logged in", "access_token": access_token}

    router.include_router(generate_base_routes(registry))
    return router

