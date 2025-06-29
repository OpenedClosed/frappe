"""Формирование маршрутов приложения Персональный аккаунт."""
import random
import re
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


REG_CODES: Dict[str, dict] = {}
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
    `{"ru": "...", "en": "...", "pl": "...", "uk": "...", "de": "..."}`.*
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
                "pl": "Warunki muszą zostać zaakceptowane.",
                "uk": "Потрібно прийняти умови.",
                "de": "Die Bedingungen müssen akzeptiert werden."
            }

        if not data.passwords_match():
            msg = {
                "ru": "Пароли не совпадают.",
                "en": "Passwords do not match.",
                "pl": "Hasła nie pasują do siebie.",
                "uk": "Паролі не співпадають.",
                "de": "Passwörter stimmen nicht überein."
            }
            errors["password"] = errors["password_confirm"] = msg

        pwd_error = data.password_strength_errors()
        if pwd_error:
            errors["password"] = pwd_error

        phone_key = normalize_numbers(data.phone)
        if not phone_key:
            errors["phone"] = {
                "ru": "Телефон обязателен.",
                "en": "Phone is required.",
                "pl": "Telefon jest wymagany.",
                "uk": "Телефон обов'язковий.",
                "de": "Telefonnummer ist erforderlich."
            }
        else:
            exists = await mongo_db["patients_contact_info"].find_one({"phone": phone_key})
            if exists:
                errors["phone"] = {
                    "ru": "Пользователь с таким телефоном уже существует.",
                    "en": "User with this phone already exists.",
                    "pl": "Użytkownik z tym numerem już istnieje.",
                    "uk": "Користувач з таким телефоном вже існує.",
                    "de": "Ein Benutzer mit dieser Telefonnummer existiert bereits."
                }

        today = datetime.utcnow().date()

        if not data.birth_date:
            errors["birth_date"] = {
                "ru": "Дата рождения обязательна.",
                "en": "Birth date is required.",
                "pl": "Data urodzenia jest wymagana.",
                "uk": "Дата народження обов'язкова.",
                "de": "Geburtsdatum ist erforderlich."
            }
        else:
            birth = data.birth_date.date()
            if birth > today:
                errors["birth_date"] = {
                    "ru": "Дата рождения не может быть в будущем.",
                    "en": "Birth date cannot be in the future.",
                    "pl": "Data urodzenia nie może być z przyszłości.",
                    "uk": "Дата народження не може бути в майбутньому.",
                    "de": "Geburtsdatum kann nicht in der Zukunft liegen."
                }
            elif birth > today - timedelta(days=365 * 18):
                errors["birth_date"] = {
                    "ru": "Регистрация доступна только с 18 лет.",
                    "en": "Registration is only available from age 18.",
                    "pl": "Rejestracja dostępna od 18 roku życia.",
                    "uk": "Реєстрація доступна лише з 18 років.",
                    "de": "Registrierung ist erst ab 18 Jahren möglich."
                }

        if not data.gender:
            errors["gender"] = {
                "ru": "Пол обязателен.",
                "en": "Gender is required.",
                "pl": "Płeć jest wymagana.",
                "uk": "Стать обов'язкова.",
                "de": "Geschlecht ist erforderlich."
            }

        # ----- ПРОВЕРКА REFERRAL CODE ------------------------------------
        referral_id: Optional[str] = None
        if data.referral_code:
            m = re.fullmatch(r"([A-Za-z0-9]{2,10})_([A-Za-z0-9\-]{3,36})", data.referral_code)
            if not m:
                errors["referral_code"] = {
                    "ru": "Некорректный формат реферального кода.",
                    "en": "Invalid referral-code format.",
                    "pl": "Nieprawidłowy format kodu polecającego.",
                    "uk": "Некоректний формат реферального коду.",
                    "de": "Ungültiges Format des Empfehlungscodes."
                }
            else:
                patient_key = m.group(2)
                try:
                    ref_patient = await get_client().find_patient(patient_id=patient_key)
                    if not ref_patient:
                        errors["referral_code"] = {
                            "ru": "Такой реферальный код не найден.",
                            "en": "Referral code not found.",
                            "pl": "Nie znaleziono takiego kodu polecającego.",
                            "uk": "Такий реферальний код не знайдено.",
                            "de": "Empfehlungscode nicht gefunden."
                        }
                    else:
                        referral_id = ref_patient["externalId"]
                except CRMError:
                    errors["referral_code"] = {
                        "ru": "Ошибка CRM при проверке кода.",
                        "en": "CRM error while validating code.",
                        "pl": "Błąd CRM podczas weryfikacji kodu.",
                        "uk": "Помилка CRM під час перевірки коду.",
                        "de": "CRM-Fehler bei der Codeüberprüfung."
                    }

        if errors:
            return JSONResponse(status_code=400, content={"errors": errors})

        code = "".join(random.choices("0123456789", k=6))
        REG_CODES[phone_key] = {"code": code, "referral_id": referral_id}

        await send_sms(phone_key, f"Код подтверждения: {code}")

        return {
            "message": {
                "ru": "Код отправлен на телефон.",
                "en": "Code sent to phone.",
                "pl": "Kod został wysłany na telefon.",
                "uk": "Код надіслано на телефон.",
                "de": "Code wurde an das Telefon gesendet."
            },
            "debug_code": code
        }

    # ------------------------------------------------------------------
    # Шаг 2 Регистрации  ➔  CRM + Mongo + (опц.) JWT
    # ------------------------------------------------------------------
    @router.post("/register_confirm")
    async def register_confirm(
        data: ConfirmationSchema,
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        • Валидирует 6-значный код  
        • Создаёт (или достраивает) локальные документы  
        • Создаёт/находит пациента в CRM  
        • Выдаёт JWT, если пользователь не был залогинен
        """
        phone_key = normalize_numbers(data.phone)
        stored = REG_CODES.get(phone_key) or {}
        if stored.get("code") != data.code:
            raise HTTPException(400, detail={
                "code": {
                    "ru": "Неверный код.",
                    "en": "Invalid code.",
                    "pl": "Nieprawidłowy kod.",
                    "uk": "Невірний код.",
                    "de": "Ungültiger Code."
                }
            })

        referral_id = stored.get("referral_id")

        main_schema = MainInfoSchema(
            last_name=data.last_name.strip(),
            first_name=data.first_name.strip(),
            birth_date=data.birth_date,
            gender=data.gender,
            phone=phone_key,
            referral_id=referral_id,
            metadata=dict(request.query_params),
        )

        contact_schema = ContactInfoSchema(
            phone=phone_key,
            email=data.email or ""
        )

        current_user_id: Optional[str] = None
        current_user_doc = None
        try:
            current_user_id = Authorize.get_jwt_subject()
        except Exception:
            current_user_id = None
        if current_user_id:
            current_user_doc = await mongo_db["users"].find_one({"_id": ObjectId(current_user_id)})

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
                    "pl": "Błąd CRM podczas rejestracji.",
                    "uk": "Помилка CRM під час реєстрації.",
                    "de": "CRM-Fehler während der Registrierung."
                }
            }) from e

        patient_id = crm_data["externalId"]

        if current_user_doc:
            user_id = str(current_user_doc["_id"])

            main_doc = await mongo_db["patients_main_info"].find_one({"user_id": user_id})
            contact_doc = await mongo_db["patients_contact_info"].find_one({"user_id": user_id})

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
                    "pl": "Profil został pomyślnie zaktualizowany.",
                    "uk": "Профіль успішно оновлено.",
                    "de": "Profil erfolgreich aktualisiert."
                }
            }

        user = User(
            full_name=f"{data.first_name.strip()} {data.last_name.strip()}",
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

        Authorize = AuthJWT()
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
                "pl": "Rejestracja zakończona.",
                "uk": "Реєстрацію завершено.",
                "de": "Registrierung abgeschlossen."
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
                    "pl": "Użytkownik nie znaleziony.",
                    "uk": "Користувача не знайдено.",
                    "de": "Benutzer nicht gefunden."
                }
            })

        user_doc = await mongo_db["users"].find_one({"_id": ObjectId(contact["user_id"])})
        if not user_doc or not data.check_password(user_doc.get("password", "")):
            raise HTTPException(401, detail={
                "password": {
                    "ru": "Неверный пароль.",
                    "en": "Wrong password.",
                    "pl": "Błędne hasło.",
                    "uk": "Невірний пароль.",
                    "de": "Falsches Passwort."
                }
            })

        code_2fa = "".join(random.choices("0123456789", k=6))
        TWO_FA_CODES[phone_key] = code_2fa

        await send_sms(phone_key, f"Ваш код входа: {code_2fa}")

        return {
            "message": {
                "ru": "Код отправлен.",
                "en": "Code sent.",
                "pl": "Kod wysłany.",
                "uk": "Код відправлено.",
                "de": "Code gesendet."
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
                    "pl": "Nieprawidłowy kod.",
                    "uk": "Невірний код.",
                    "de": "Ungültiger Code."
                }
            })

        contact = await mongo_db["patients_contact_info"].find_one({"phone": phone_key})
        if not contact:
            raise HTTPException(404, detail={
                "phone": {
                    "ru": "Пользователь не найден.",
                    "en": "User not found.",
                    "pl": "Użytkownik nie znaleziony.",
                    "uk": "Користувача не знайдено.",
                    "de": "Benutzer nicht gefunden."
                }
            })

        main_doc = await mongo_db["patients_main_info"].find_one({"user_id": contact["user_id"]})
        user_id = str(main_doc["user_id"])
        patient_id = main_doc.get("patient_id")

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
                pass

        access_token = Authorize.create_access_token(subject=user_id)
        refresh_token = Authorize.create_refresh_token(subject=user_id)

        response.set_cookie("access_token", access_token, httponly=False, secure=True, samesite="None")
        response.set_cookie("refresh_token", refresh_token, httponly=False, secure=True, samesite="None")

        return {
            "message": {
                "ru": "Вход выполнен.",
                "en": "Logged in.",
                "pl": "Zalogowano.",
                "uk": "Вхід виконано.",
                "de": "Eingeloggt."
            },
            "access_token": access_token
        }

    # ------------------------------------------------------------------
    # CRUD-маршруты всех моделей
    # ------------------------------------------------------------------
    router.include_router(generate_base_routes(registry))
    return router
