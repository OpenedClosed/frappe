"""Формирование маршрутов приложения Персональный аккаунт."""
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi_jwt_auth import AuthJWT                     # JWT-обёртка
from fastapi_jwt_auth import exceptions as jwt_exc
from fastapi.encoders import jsonable_encoder
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


def generate_base_account_routes(registry) -> APIRouter:  # noqa: C901
    """
    Генерирует:
    1.  /register → выдача 6-значного кода по SMS  
    2.  /register_confirm → создание / достройка локального профиля + CRM + JWT  
    3.  /login → проверка пароля, выдача 2-FA кода  
    4.  /login_confirm → проверка 2-FA, мягкая синхронизация с CRM + JWT  
    5.  CRUD-маршруты всех админ-моделей из `registry`

    *Все сообщения и ошибки возвращаются как словари вида
    `{"ru": "...", "en": "...", "pl": "..."}`.*
    """
    router = APIRouter()

    # ------------------------------------------------------------------
    # Шаг 1 Регистрации  ➔  отправка SMS-кода
    # ------------------------------------------------------------------
    @router.post("/register")
    async def register(data: RegistrationSchema):
        """
        Проверяет ввод и отправляет 6-значный код подтверждения на SMS.
        """
        errors: dict[str, dict] = {}

        if not data.accept_terms:
            errors["accept_terms"] = {
                "ru": "Необходимо принять условия.",
                "en": "Terms must be accepted.",
                "pl": "Warunki muszą zostać zaakceptowane."
            }

        if not data.passwords_match():
            msg = {
                "ru": "Пароли не совпадают.",
                "en": "Passwords do not match.",
                "pl": "Hasła nie pasują do siebie."
            }
            errors["password"] = errors["password_confirm"] = msg

        phone_key = normalize_numbers(data.phone)
        if not phone_key:
            errors["phone"] = {
                "ru": "Телефон обязателен.",
                "en": "Phone is required.",
                "pl": "Telefon jest wymagany."
            }
        else:
            exists = await mongo_db["patients_contact_info"].find_one({"phone": phone_key})
            if exists:
                errors["phone"] = {
                    "ru": "Пользователь с таким телефоном уже существует.",
                    "en": "User with this phone already exists.",
                    "pl": "Użytkownik z tym numerem już istnieje."
                }

        today = datetime.utcnow().date()

        if not data.birth_date:
            errors["birth_date"] = {
                "ru": "Дата рождения обязательна.",
                "en": "Birth date is required.",
                "pl": "Data urodzenia jest wymagana."
            }
        else:
            birth = data.birth_date.date()  # приведение к date
            if birth > today:
                errors["birth_date"] = {
                    "ru": "Дата рождения не может быть в будущем.",
                    "en": "Birth date cannot be in the future.",
                    "pl": "Data urodzenia nie może być z przyszłości."
                }
            elif birth > today - timedelta(days=365 * 10):
                errors["birth_date"] = {
                    "ru": "Регистрация доступна только с 10 лет.",
                    "en": "Registration is only available from age 10.",
                    "pl": "Rejestracja dostępna od 10 roku życia."
                }


        if not data.gender:
            errors["gender"] = {
                "ru": "Пол обязателен.",
                "en": "Gender is required.",
                "pl": "Płeć jest wymagana."
            }

        if errors:
            return JSONResponse(status_code=400, content={"errors": errors})

        code = "".join(random.choices("0123456789", k=6))
        REG_CODES[phone_key] = code

        # --- Пока ничего не шлём, оставляем заглушку ---
        # await send_sms(phone_key, f"Код подтверждения: {code}")

        return {
            "message": {
                "ru": "Код отправлен на телефон.",
                "en": "Code sent to phone.",
                "pl": "Kod został wysłany na telefon."
            },
            "debug_code": code  # Убрать в бою
        }
    # ------------------------------------------------------------------
    # Шаг 2 Регистрации  ➔  CRM + Mongo + (опц.) JWT
    # ------------------------------------------------------------------
    @router.post("/register_confirm")
    async def register_confirm(
        data: ConfirmationSchema,
        request: Request,
        response: Response,
        Authorize: Optional[AuthJWT] = Depends(lambda: None),   # token опционален
    ):
        """
        • Валидирует 6-значный код  
        • Создаёт (или достраивает) локальные документы  
        • Создаёт/находит пациента в CRM  
        • Выдаёт JWT, **если** пользователь не был залогинен
        """
        # data.gender = GenderEnum.MALE
        # data.birth_date = datetime.now()
        phone_key = normalize_numbers(data.phone)
        # if REG_CODES.get(phone_key) != data.code:
        #     raise HTTPException(400, detail={
        #         "code": {
        #             "ru": "Неверный код.",
        #             "en": "Invalid code.",
        #             "pl": "Nieprawidłowy kod."
        #         }
        #     })

        # ---------------- Принимаем данные из схемы ----------------
        main_schema = MainInfoSchema(
            last_name=data.full_name.split()[0],
            first_name=" ".join(data.full_name.split()[1:]) or "-",
            birth_date=data.birth_date,
            gender=data.gender,
            phone=phone_key,
            metadata=dict(request.query_params),
        )

        
        contact_schema = ContactInfoSchema(
            phone=phone_key,
            email=data.email or ""
        )

        # ---------------- Определяем текущего пользователя ----------------
        current_user_id: Optional[str] = None
        current_user_doc = None
        if Authorize is not None:
            try:
                current_user_id = Authorize.get_jwt_subject()
            except jwt_exc.MissingTokenError:
                current_user_id = None
        # заглушка
        # current_user_id = "67e489affa4507fba7de630e"
        if current_user_id:
            current_user_doc = await mongo_db["users"].find_one({"_id": ObjectId(current_user_id)})
        # raise HTTPException(502)

        # ---------------- Работа с CRM ----------------
        crm = get_client()
        try:
            crm_data, created_now = await crm.find_or_create_patient(
                local_data=main_schema.model_dump(),
                contact_data=contact_schema.model_dump(),
            )
        except CRMError as e:
            raise HTTPException(e.status_code, detail={
                "__all__": {
                    "ru": "Ошибка CRM при регистрации.",
                    "en": "CRM error during registration.",
                    "pl": "Błąd CRM podczas rejestracji."
                }
            }) from e

        # ---------------- Mongo: создаём/обновляем ----------------
        patient_id = crm_data["externalId"]

        # (а) Пользователь существует ➔ обновляем / создаём patient-доки
        if current_user_doc:
            user_id = str(current_user_doc["_id"])

            main_doc = await mongo_db["patients_main_info"].find_one({"user_id": user_id})
            contact_doc = await mongo_db["patients_contact_info"].find_one({"user_id": user_id})

            # обновляем или создаём MainInfo
            if main_doc:
                await mongo_db["patients_main_info"].update_one(
                    {"_id": main_doc["_id"]},
                    {"$set": {
                        "patient_id": patient_id,
                        "first_name": crm_data.get("firstname"),
                        "last_name": crm_data.get("lastname"),
                        "birth_date": datetime.fromisoformat(crm_data["birthdate"]),
                        "gender": crm_data.get("gender"),
                        "crm_last_sync": datetime.utcnow(),
                    }},
                )
            else:
                await mongo_db["patients_main_info"].insert_one(
                    main_schema.model_dump() | {
                        "user_id": user_id,
                        "patient_id": patient_id,
                        "crm_last_sync": datetime.utcnow(),
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                )

            # обновляем / создаём ContactInfo
            if contact_doc:
                await mongo_db["patients_contact_info"].update_one(
                    {"_id": contact_doc["_id"]},
                    {"$set": {
                        "email": crm_data.get("email"),
                        "phone": normalize_numbers(crm_data.get("phone")),
                        "updated_at": datetime.utcnow(),
                    }},
                )
            else:
                await mongo_db["patients_contact_info"].insert_one(
                    contact_schema.model_dump() | {
                        "user_id": user_id,
                        "updated_at": datetime.utcnow(),
                    }
                )

            return {
                "message": {
                    "ru": "Профиль успешно обновлён.",
                    "en": "Profile updated successfully.",
                    "pl": "Profil został pomyślnie zaktualizowany."
                }
            }

        # (б) Нет JWT ➔ создаём нового пользователя
        user = User(
            full_name=data.full_name,
            role=RoleEnum.CLIENT,
            password=data.password,
        )
        user.set_password()
        user_doc = user.model_dump(mode="python") | {"created_at": datetime.utcnow()}
        user_id = (await mongo_db["users"].insert_one(user_doc)).inserted_id

        await mongo_db["patients_main_info"].insert_one(
            main_schema.model_dump() | {
                "user_id": str(user_id),
                "patient_id": patient_id,
                "crm_last_sync": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        await mongo_db["patients_contact_info"].insert_one(
            contact_schema.model_dump() | {
                "user_id": str(user_id),
                "updated_at": datetime.utcnow(),
            }
        )

        # --- JWT ---
        Authorize = AuthJWT()  # локальный экземпляр
        access_token = Authorize.create_access_token(subject=str(user_id))
        refresh_token = Authorize.create_refresh_token(subject=str(user_id))

        response.set_cookie(
            "access_token", access_token,
            httponly=False, secure=True, samesite="None",
        )
        response.set_cookie(
            "refresh_token", refresh_token,
            httponly=False, secure=True, samesite="None",
        )

        return {
            "message": {
                "ru": "Регистрация завершена.",
                "en": "Registration completed.",
                "pl": "Rejestracja zakończona."
            },
            "access_token": access_token
        }

    # ------------------------------------------------------------------
    # Шаг 1 Логина  ➔  2-FA код
    # ------------------------------------------------------------------
    @router.post("/login")
    async def login(data: LoginSchema):
        """
        Проверяет пароль и отправляет 6-значный 2-FA код на SMS.
        """
        phone_key = normalize_numbers(data.phone)
        contact = await mongo_db["patients_contact_info"].find_one({"phone": phone_key})
        if not contact:
            raise HTTPException(404, detail={
                "phone": {
                    "ru": "Пользователь не найден.",
                    "en": "User not found.",
                    "pl": "Użytkownik nie znaleziony."
                }
            })

        user_doc = await mongo_db["users"].find_one({"_id": ObjectId(contact["user_id"])})
        if not user_doc or not data.check_password(user_doc.get("password", "")):
            raise HTTPException(401, detail={
                "password": {
                    "ru": "Неверный пароль.",
                    "en": "Wrong password.",
                    "pl": "Błędne hasło."
                }
            })

        code_2fa = "".join(random.choices("0123456789", k=6))
        TWO_FA_CODES[phone_key] = code_2fa

        # Заглушка — SMS пока не отправляем
        # await send_sms(phone_key, f"Ваш код входа: {code_2fa}")

        return {
            "message": {
                "ru": "Код отправлен.",
                "en": "Code sent.",
                "pl": "Kod wysłany."
            },
            "debug_code": code_2fa
        }

    # ------------------------------------------------------------------
    # Шаг 2 Логина  ➔  CRM-синхронизация + JWT
    # ------------------------------------------------------------------
    @router.post("/login_confirm")
    async def login_confirm(
        data: TwoFASchema,
        response: Response,
        Authorize: AuthJWT = Depends(),
    ):
        """
        Проверяет 2-FA код и выдаёт JWT.  
        Одновременно подтягивает свежие данные из CRM.
        """
        phone_key = normalize_numbers(data.phone)
        if TWO_FA_CODES.get(phone_key) != data.code:
            raise HTTPException(400, detail={
                "code": {
                    "ru": "Неверный код.",
                    "en": "Invalid code.",
                    "pl": "Nieprawidłowy kod."
                }
            })

        contact = await mongo_db["patients_contact_info"].find_one({"phone": phone_key})
        if not contact:
            raise HTTPException(404, detail={
                "phone": {
                    "ru": "Пользователь не найден.",
                    "en": "User not found.",
                    "pl": "Użytkownik nie znaleziony."
                }
            })

        main_doc = await mongo_db["patients_main_info"].find_one({"user_id": contact["user_id"]})
        user_id = str(main_doc["user_id"])
        patient_id = main_doc.get("patient_id")

        # лёгкая синхронизация
        if patient_id:
            try:
                crm_data = await get_client().get_patient(patient_id)
                await mongo_db["patients_main_info"].update_one(
                    {"_id": main_doc["_id"]},
                    {"$set": {
                        "first_name": crm_data.get("firstname"),
                        "last_name": crm_data.get("lastname"),
                        "crm_last_sync": datetime.utcnow(),
                    }}
                )
            except CRMError:
                pass  # игнорируем сбой CRM на логине

        access_token = Authorize.create_access_token(subject=user_id)
        refresh_token = Authorize.create_refresh_token(subject=user_id)

        response.set_cookie("access_token", access_token, httponly=False, secure=True, samesite="None")
        response.set_cookie("refresh_token", refresh_token, httponly=False, secure=True, samesite="None")

        return {
            "message": {
                "ru": "Вход выполнен.",
                "en": "Logged in.",
                "pl": "Zalogowano."
            },
            "access_token": access_token
        }

    # ------------------------------------------------------------------
    # CRUD-маршруты всех моделей
    # ------------------------------------------------------------------
    router.include_router(generate_base_routes(registry))
    return router

