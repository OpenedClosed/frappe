"""Формирование маршрутов приложения Персональный аккаунт."""
import random
import string
from datetime import datetime
from typing import Dict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi_jwt_auth import AuthJWT

from personal_account.client_interface.db.mongo.enums import AccountVerificationEnum, GenderEnum
from integrations.panamedica.utils.help_functions import format_crm_phone
from integrations.panamedica.client import CRMError, get_client
from crud_core.registry import BaseRegistry
from crud_core.routes_generator import generate_base_routes
from db.mongo.db_init import mongo_db
from users.db.mongo.enums import RoleEnum
from users.db.mongo.schemas import User
from utils.help_functions import normalize_numbers, send_sms

from .client_interface.db.mongo.schemas import (ConfirmationSchema, ContactInfoSchema,
                                                LoginSchema, MainInfoSchema,
                                                RegistrationSchema,
                                                TwoFASchema)

REG_CODES: Dict[str, str] = {}
TWO_FA_CODES: Dict[str, str] = {}

REG_CODES: Dict[str, str] = {}
TWO_FA_CODES: Dict[str, str] = {}


def generate_base_account_routes(registry) -> APIRouter:
    """Генерирует маршруты для регистрации и входа."""
    router = APIRouter()
    # ------------------------------------------------------------------
    # Регистрация (шаг 1): проверка вводимых данных и отправка SMS‑кода
    # ------------------------------------------------------------------
    @router.post("/register")
    async def register(data: RegistrationSchema):
        """
        Первый шаг регистрации: валидация и генерация кода.
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
            # Проверяем по контактной информации, а не основной
            if await mongo_db["patients_contact_info"].find_one({"phone": phone_key}):
                errors["phone"] = "User with this phone already exists."

        if errors:
            return JSONResponse(status_code=400, content={"errors": errors})

        code = "".join(random.choices("0123456789", k=6))
        REG_CODES[phone_key] = code

        # TODO: отправлять SMS, когда будет готов фронт
        # await send_sms(phone_key, f"Код подтверждения: {code}")

        return {"message": "Code sent to phone", "debug_code": code}  # временно возвращаем код


    # ------------------------------------------------------------------
    # Регистрация (шаг 2): CRM + сохранение + JWT
    # ------------------------------------------------------------------
    @router.post("/register_confirm")
    async def register_confirm(
        data: ConfirmationSchema,
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends(),
    ):
        """Шаг 2 регистрации: работа с CRM, запись в Mongo, выдача токенов."""
        phone_key = "48123456789"  # временно: заглушка на номер телефона для тестов

        ln, fn, *rest = data.full_name.split()
        main_schema = MainInfoSchema(
            last_name=ln,
            first_name=fn,
            patronymic=rest[0] if rest else None,
            phone=phone_key,
            metadata=dict(request.query_params),
            gender=GenderEnum.MALE,  # временно
            birth_date=datetime(1990, 1, 1),  # временно
        )
        contact_schema = ContactInfoSchema(
            phone=phone_key,
            email=data.email or "",
        )

        crm = get_client()
        try:
            crm_data, created_now = await crm.find_or_create_patient(
                local_data=main_schema.model_dump(),
                contact_data=contact_schema.model_dump(),
            )
        except CRMError as e:
            print(e)
            raise HTTPException(502, "CRM registration failed") from e

        if not created_now:
            duplicate = await mongo_db["patients_main_info"].find_one(
                {"patient_id": crm_data["externalId"]}
            )
            if duplicate:
                raise HTTPException(409, "User already registered")

        # ------------------------------------------------------------------
        # Создаём локального пользователя и две коллекции пациента
        # ------------------------------------------------------------------
        user = User(password=data.password, full_name=data.full_name, role=RoleEnum.CLIENT)
        user.set_password()
        user_doc = user.model_dump(mode="python") | {"created_at": datetime.utcnow()}
        user_id = (await mongo_db["users"].insert_one(user_doc)).inserted_id

        main_db_doc = main_schema.model_dump() | {
            "user_id": str(user_id),
            "patient_id": crm_data["externalId"],
            "crm_last_sync": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        contact_db_doc = contact_schema.model_dump() | {
            "user_id": str(user_id),
            "updated_at": datetime.utcnow(),
        }

        await mongo_db["patients_main_info"].insert_one(main_db_doc)
        await mongo_db["patients_contact_info"].insert_one(contact_db_doc)

        access_token = Authorize.create_access_token(subject=str(user_id))
        refresh_token = Authorize.create_refresh_token(subject=str(user_id))

        response.set_cookie("access_token", access_token, httponly=False, secure=True, samesite="None")
        response.set_cookie("refresh_token", refresh_token, httponly=False, secure=True, samesite="None")

        return {"message": "Registered", "user_id": str(user_id)}

    # ------------------------------------------------------------------
    # Логин (шаг 1): проверка пароля и отправка 2FA‑кода
    # ------------------------------------------------------------------
    @router.post("/login")
    async def login(data: LoginSchema):
        """
        Первый шаг входа: проверка пароля и генерация 2FA‑кода.
        """
        phone_key = "48123456789"  # временно: заглушка на номер телефона для тестов

        # Ищем по контактной информации
        contact = await mongo_db["patients_contact_info"].find_one({"phone": phone_key})
        if not contact or not contact.get("user_id"):
            raise HTTPException(404, detail={"phone": "User not found"})

        user_main = await mongo_db["patients_main_info"].find_one({"user_id": contact["user_id"]})
        if not user_main or not user_main.get("user_id"):
            raise HTTPException(404, detail={"user": "Main info not found"})

        user = await mongo_db["users"].find_one({"_id": ObjectId(user_main["user_id"])})
        if not user or not data.check_password(user.get("password", "")):
            raise HTTPException(401, detail={"password": "Wrong password"})

        code_2fa = "".join(random.choices("0123456789", k=6))
        TWO_FA_CODES[phone_key] = code_2fa

        # TODO: отправить SMS, когда будет готов фронт
        # await send_sms(phone_key, f"Ваш код входа: {code_2fa}")

        return {"message": "2FA code sent", "debug_code": code_2fa}  # временно


    # ------------------------------------------------------------------
    # Логин (шаг 2): проверка 2FA‑кода, синхронизация с CRM, JWT
    # ------------------------------------------------------------------
    @router.post("/login_confirm")
    async def login_confirm(
        data: TwoFASchema,
        response: Response,
        Authorize: AuthJWT = Depends(),
    ):
        """
        Второй шаг входа: проверка 2FA‑кода и выдача токенов.
        """
        phone_key = "48123456789"  # временно: заглушка

        # Получаем контактную информацию и user_id
        contact = await mongo_db["patients_contact_info"].find_one({"phone": phone_key})
        if not contact or not contact.get("user_id"):
            raise HTTPException(404, detail={"phone": "User not found"})

        user_main = await mongo_db["patients_main_info"].find_one({"user_id": contact["user_id"]})
        if not user_main or not user_main.get("user_id"):
            raise HTTPException(404, detail={"user": "Main info not found"})

        # Лёгкая синхронизация с CRM
        patient_id = user_main.get("patient_id")
        if patient_id:
            crm = get_client()
            try:
                crm_data = await crm.find_patient(patient_id=patient_id)
                if not crm_data:
                    # в CRM нет пациента — создаём заново с тем же UUID
                    local_schema = MainInfoSchema(**user_main)
                    contact_schema = ContactInfoSchema(**contact)
                    crm_data, _ = await crm.find_or_create_patient(
                        local_data=local_schema.model_dump(),
                        contact_data=contact_schema.model_dump(),
                    )

                # Определяем статус аккаунта
                profile = crm_data.get("profile")
                account_status = (
                    AccountVerificationEnum.VERIFIED
                    if profile == "normal"
                    else AccountVerificationEnum.UNVERIFIED
                )

                # Обновляем Mongo полями из CRM
                await mongo_db["patients_main_info"].update_one(
                    {"_id": user_main["_id"]},
                    {"$set": {
                        "first_name": crm_data.get("firstname"),
                        "last_name": crm_data.get("lastname"),
                        "birth_date": datetime.fromisoformat(crm_data.get("birthdate")),
                        "gender": crm_data.get("gender"),
                        "account_status": account_status.value,
                        "crm_last_sync": datetime.utcnow(),
                    }}
                )
                await mongo_db["patients_contact_info"].update_one(
                    {"user_id": user_main["user_id"]},
                    {"$set": {
                        "email": crm_data.get("email"),
                        "phone": normalize_numbers(crm_data.get("phone")),
                        "updated_at": datetime.utcnow(),
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

    # ------------------------------------------------------------------
    # CRUD‑маршруты, сгенерированные автоматически из registry
    # ------------------------------------------------------------------
    router.include_router(generate_base_routes(registry))
    return router

