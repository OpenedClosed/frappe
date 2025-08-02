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
from fastapi import BackgroundTasks
from db.redis.db_init import redis_db
from users.utils.help_functions import cascade_delete_user
from personal_account.client_interface.db.mongo.enums import AccountVerificationEnum, GenderEnum
from integrations.panamedica.utils.help_functions import format_crm_phone
from integrations.panamedica.client import CRMError, get_client
from crud_core.registry import BaseRegistry
from crud_core.routes_generator import generate_base_routes
from db.mongo.db_init import mongo_db
from users.db.mongo.enums import RoleEnum
from users.db.mongo.schemas import User
from utils.help_functions import normalize_numbers, send_email, send_sms

from .client_interface.db.mongo.schemas import (ConfirmationSchema, ContactInfoSchema,
                                                LoginSchema, MainInfoSchema,
                                                RegistrationSchema,
                                                TwoFASchema)


REG_CODE_TTL  = 300   # 5 минут
REG_SEND_TTL  = 60    # анти-флуд, 1 минута
TWO_FA_CODE_TTL: int = 300   # 5 минут живёт код
TWO_FA_SEND_TTL: int = 60    # анти-флуд: 1 минута между отправками

# ──────────────────────────────────────────────────────────────────────
#  Маршруты регистрации
# ──────────────────────────────────────────────────────────────────────
def generate_base_account_routes(registry) -> APIRouter:  # noqa: C901
    """
    Генерирует маршруты:

    1.  /register          → выдача 6-значного кода (email / SMS)
    2.  /register_confirm  → CRM + Mongo + JWT  
    3.  /login             → пароль + 2-FA код  
    4.  /login_confirm     → 2-FA + CRM-синхрон + JWT  
    5.  CRUD для всех админ-моделей из `registry`
    """
    router = APIRouter()

    # ────────────────────────────────────────────────────────────────
    #  Шаг 1 Регистрации → код (email / телефон)
    # ────────────────────────────────────────────────────────────────
    @router.post("/register")
    async def register(data: RegistrationSchema, background_tasks: BackgroundTasks):
        """
        Проверяет ввод и отправляет 6-значный код подтверждения
        по каналу, указанному в поле `via` («email» | «phone»).
        """
        errors: dict[str, dict] = {}

        # ——— канал
        via: str = data.via if data.via in {"email", "phone"} else "email"

        # ——— приём условий
        if not data.accept_terms:
            errors["accept_terms"] = {
                "ru": "Необходимо принять условия.",
                "en": "Terms must be accepted.",
                "pl": "Warunki muszą zostać zaakceptowane.",
                "uk": "Потрібно прийняти умови.",
                "de": "Die Bedingungen müssen akzeptiert werden.",
                "be": "Неабходна прыняць умовы.",
            }

        # ——— совпадение паролей
        if not data.passwords_match():
            msg = {
                "ru": "Пароли не совпадают.",
                "en": "Passwords do not match.",
                "pl": "Hasła nie pasują do siebie.",
                "uk": "Паролі не співпадають.",
                "de": "Passwörter stimmen nicht überein.",
                "be": "Паролі не супадаюць.",
            }
            errors["password"] = errors["password_confirm"] = msg

        # ——— сила пароля
        pwd_error = data.password_strength_errors()
        if pwd_error:
            errors["password"] = pwd_error | {"be": pwd_error.get("ru", "")}

        # ——— телефон
        phone_key = normalize_numbers(data.phone)
        if not phone_key:
            errors["phone"] = {
                "ru": "Телефон обязателен.",
                "en": "Phone is required.",
                "pl": "Telefon jest wymagany.",
                "uk": "Телефон обов'язковий.",
                "de": "Telefonnummer ist erforderlich.",
                "be": "Тэлефон абавязковы.",
            }
        else:
            contact_doc = await mongo_db["patients_contact_info"].find_one({"phone": phone_key})
            if contact_doc:
                user_doc = await mongo_db["users"].find_one(
                    {"_id": ObjectId(contact_doc["user_id"])}
                )
                if user_doc:
                    errors["phone"] = {
                        "ru": "Пользователь с таким телефоном уже существует.",
                        "en": "User with this phone already exists.",
                        "pl": "Użytkownik z tym numerem już istnieje.",
                        "uk": "Користувач з таким телефоном вже існує.",
                        "de": "Ein Benutzer mit dieser Telefonnummer existiert bereits.",
                        "be": "Карыстальнік з такім тэлефонам ужо існуе.",
                    }
                else:
                    await cascade_delete_user(contact_doc["user_id"])

        # ——— email
        if not data.email:
            errors["email"] = {
                "ru": "Email обязателен.",
                "en": "Email is required.",
                "pl": "Email jest wymagany.",
                "uk": "Email обов'язковий.",
                "de": "E-Mail ist erforderlich.",
                "be": "Email абавязковы.",
            }

        # ——— возраст
        today = datetime.utcnow().date()
        if not data.birth_date:
            errors["birth_date"] = {
                "ru": "Дата рождения обязательна.",
                "en": "Birth date is required.",
                "pl": "Data urodzenia jest wymagana.",
                "uk": "Дата народження обов'язкова.",
                "de": "Geburtsdatum ist erforderlich.",
                "be": "Дата нараджэння абавязковая.",
            }
        else:
            birth = data.birth_date.date()
            if birth > today:
                errors["birth_date"] = {
                    "ru": "Дата рождения не может быть в будущем.",
                    "en": "Birth date cannot be in the future.",
                    "pl": "Data urodzenia nie może być z przyszłości.",
                    "uk": "Дата народження не може бути в майбутньому.",
                    "de": "Geburtsdatum kann nicht in der Zukunft liegen.",
                    "be": "Дата нараджэння не можа быць у будучыні.",
                }
            elif birth > today - timedelta(days=365 * 18):
                errors["birth_date"] = {
                    "ru": "Регистрация доступна только с 18 лет.",
                    "en": "Registration is only available from age 18.",
                    "pl": "Rejestracja dostępna od 18 roku życia.",
                    "uk": "Реєстрація доступна лише з 18 років.",
                    "de": "Registrierung ist erst ab 18 Jahren möglich.",
                    "be": "Рэгістрацыя даступная толькі з 18 год.",
                }

        # ——— пол
        if not data.gender:
            errors["gender"] = {
                "ru": "Пол обязателен.",
                "en": "Gender is required.",
                "pl": "Płeć jest wymagana.",
                "uk": "Стать обов'язкова.",
                "de": "Geschlecht ist erforderlich.",
                "be": "Пол абавязковы.",
            }

        # ——— реферальный код (проверка не менялась)
        referral_id: Optional[str] = None
        if data.referral_code:
            m = re.fullmatch(r"([A-Za-z0-9]{2,10})_([A-Za-z0-9\-]{3,36})", data.referral_code)
            if not m:
                errors["referral_code"] = {
                    "ru": "Некорректный формат реферального кода.",
                    "en": "Invalid referral-code format.",
                    "pl": "Nieprawidłowy format kodu polecającego.",
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
                        }
                    else:
                        referral_id = ref_patient["externalId"]
                except CRMError:
                    errors["referral_code"] = {
                        "ru": "Ошибка CRM при проверке кода.",
                        "en": "CRM error while validating code.",
                        "pl": "Błąd CRM podczas weryfikacji kodu.",
                    }

        # ——— анти-флуд
        identifier = data.email.lower() if via == "email" else phone_key
        sent_key = f"reg:sent:{via}:{identifier}"
        if await redis_db.exists(sent_key):
            return JSONResponse(
                status_code=429,
                content={
                    "errors": {
                        "__all__": {
                            "ru": "Код уже был отправлен, попробуйте через минуту.",
                            "en": "Code already sent, please wait a minute.",
                            "pl": "Kod został już wysłany, spróbuj ponownie za minutę.",
                        }
                    }
                },
            )

        if errors:
            return JSONResponse(status_code=400, content={"errors": errors})

        # ——— генерируем 6-значный код
        code: str = "".join(random.choices("0123456789", k=6))

        # ——— сохраняем в Redis
        await redis_db.set(
            f"reg:code:{identifier}",
            json.dumps({"code": code, "referral_id": referral_id}),
            ex=REG_CODE_TTL,
        )
        await redis_db.set(sent_key, "1", ex=REG_SEND_TTL)

        # ——— отправка
        if via == "email":
            html_body = f"""
            <div style="font-family: sans-serif; padding: 24px; background: #f2f2f2;">
                <div style="max-width: 500px; margin: auto; background: white; padding: 32px;
                            border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <h2 style="color: #333;">Kod weryfikacyjny</h2>
                    <p style="font-size: 16px;">Twój kod:</p>
                    <p style="font-size: 28px; font-weight: bold; color: #007bff;
                            letter-spacing: 6px;">{code}</p>
                    <p style="font-size: 14px; color: #777;">Kod jest ważny przez 5 minut</p>
                </div>
            </div>
            """
            try:
                background_tasks.add_task(
                    send_email,
                    to_email=identifier,
                    subject="Kod weryfikacyjny",
                    body=f"Twój kod weryfikacyjny: {code}",
                    html_body=html_body,
                )

            except HTTPException:
                return JSONResponse(
                    status_code=400,
                    content={
                        "errors": {
                            "email": {
                                "ru": "Ошибка при отправке письма. Проверьте email.",
                                "en": "Failed to send email. Please check the address.",
                                "pl": "Nie udało się wysłać wiadomości email. Sprawdź adres.",
                            }
                        }
                    },
                )
        else:
            try:
                await send_sms(identifier, f"Twój kod potwierdzający to: {code}")
            except HTTPException:
                return JSONResponse(
                    status_code=400,
                    content={
                        "errors": {
                            "phone": {
                                "ru": "Ошибка при отправке SMS. Проверьте номер телефона.",
                                "en": "Failed to send SMS. Please check your phone number.",
                                "pl": "Nie udało się wysłać SMS-a. Sprawdź numer telefonu.",
                            }
                        }
                    },
                )

        return {
            "message": {
                "ru": "Код отправлен." if via == "phone" else "Код отправлен на email.",
                "en": "Code sent." if via == "phone" else "Code sent to e-mail.",
                "pl": "Kod wysłany." if via == "phone" else "Kod wysłany na e-mail.",
            }
        }


    # ────────────────────────────────────────────────────────────────
    #  Шаг 2 Регистрации → CRM + Mongo + JWT
    # ────────────────────────────────────────────────────────────────
    @router.post("/register_confirm")
    async def register_confirm(
        data: ConfirmationSchema,
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends(),
    ):
        """
        Валидирует код (по каналу `via`), создаёт/обновляет профиль,
        синхронизирует с CRM и выдаёт JWT.
        """
        import json

        via: str = data.via if data.via in {"email", "phone"} else "email"
        identifier = data.email.lower() if via == "email" else normalize_numbers(data.phone)

        stored_raw = await redis_db.get(f"reg:code:{identifier}")
        stored: dict = json.loads(stored_raw) if stored_raw else {}
        if stored.get("code") != data.code:
            raise HTTPException(
                400,
                detail={
                    "code": {
                        "ru": "Неверный код.",
                        "en": "Invalid code.",
                        "pl": "Nieprawidłowy kod.",
                    }
                },
            )

        referral_id = stored.get("referral_id")
        phone_key   = normalize_numbers(data.phone)
        email_key   = data.email.lower()

        # ——— сбор схем
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
            email=email_key,
        )

        # ——— если пользователь уже авторизован
        current_user_id: Optional[str] = None
        try:
            current_user_id = Authorize.get_jwt_subject()
        except Exception:
            pass
        current_user_doc = (
            await mongo_db["users"].find_one({"_id": ObjectId(current_user_id)})
            if current_user_id
            else None
        )

        # ——— CRM
        crm = get_client()
        try:
            crm_data, _created_now = await crm.find_or_create_patient(
                local_data=main_schema.model_dump(),
                contact_data=contact_schema.model_dump(),
            )
        except CRMError as e:
            raise HTTPException(
                e.status_code,
                detail={
                    "__all__": {
                        "ru": "Ошибка CRM при регистрации.",
                        "en": "CRM error during registration.",
                        "pl": "Błąd CRM podczas rejestracji.",
                    }
                },
            ) from e

        patient_id = crm_data["externalId"]

        # ——— если был залогинен → достраиваем профиль
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
                        "last_name":  crm_data.get("lastname"),
                        "birth_date": datetime.fromisoformat(crm_data["birthdate"]),
                        "gender":     crm_data.get("gender"),
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
                }
            }

        # ——— создаём нового пользователя
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
        access_token  = Authorize.create_access_token(subject=str(user_id))
        refresh_token = Authorize.create_refresh_token(subject=str(user_id))

        response.set_cookie("access_token", access_token,  httponly=False, secure=True, samesite="None")
        response.set_cookie("refresh_token", refresh_token, httponly=False, secure=True, samesite="None")

        return {
            "message": {
                "ru": "Регистрация завершена.",
                "en": "Registration completed.",
                "pl": "Rejestracja zakończona.",
            },
            "access_token": access_token,
        }

    # ────────────────────────────────────────────────────────────────
    #  Шаг 1 Логина → 2-FA код
    # ────────────────────────────────────────────────────────────────
    @router.post("/login")
    async def login(data: LoginSchema, background_tasks: BackgroundTasks):
        """
        Проверяет пароль и отправляет 6-значный 2-FA код на e-mail или по SMS
        в зависимости от поля `via`.
        """
        via: str = data.via if data.via in {"email", "phone"} else "email"
        identifier: str

        # ------------------------------------------------------------------
        # Поиск контакта
        # ------------------------------------------------------------------
        if via == "email":
            if not data.email:
                raise HTTPException(400, detail={"email": {"ru": "Email обязателен."}})
            identifier = data.email.lower()
            contact = await mongo_db["patients_contact_info"].find_one({"email": identifier})
        else:
            if not data.phone:
                raise HTTPException(400, detail={"phone": {"ru": "Телефон обязателен."}})
            identifier = normalize_numbers(data.phone)
            contact = await mongo_db["patients_contact_info"].find_one({"phone": identifier})

        # ------------------------------------------------------------------
        # Зачистка «висящего» пользователя
        # ------------------------------------------------------------------
        if contact and await mongo_db["users"].find_one({"_id": ObjectId(contact["user_id"])}) is None:
            await cascade_delete_user(contact["user_id"])
            contact = None

        # ------------------------------------------------------------------
        # Если пользователь не найден
        # ------------------------------------------------------------------
        if contact is None:
            field = "email" if via == "email" else "phone"
            raise HTTPException(
                404,
                detail={field: {
                    "ru": "Пользователь не найден.",
                    "en": "User not found.",
                    "pl": "Użytkownik nie znaleziony.",
                }},
            )

        # ------------------------------------------------------------------
        # Документ пользователя
        # ------------------------------------------------------------------
        user_doc = await mongo_db["users"].find_one({"_id": ObjectId(contact["user_id"])})

        # ------------------------------------------------------------------
        # Проверка блокировки
        # ------------------------------------------------------------------
        if user_doc and user_doc.get("is_active", True) is False:
            raise HTTPException(
                403,
                detail={"__all__": {
                    "ru": "Пользователь заблокирован.",
                    "en": "User is blocked.",
                    "pl": "Użytkownik jest zablokowany.",
                }},
            )

        # ------------------------------------------------------------------
        # Проверка пароля
        # ------------------------------------------------------------------
        if user_doc is None or data.check_password(user_doc.get("password", "")) is False:
            raise HTTPException(
                401,
                detail={"password": {
                    "ru": "Неверный пароль.",
                    "en": "Wrong password.",
                    "pl": "Błędne hasło.",
                }},
            )

        # ------------------------------------------------------------------
        # Анти-флуд
        # ------------------------------------------------------------------
        send_key = f"login:sent:{via}:{identifier}"
        if await redis_db.exists(send_key):
            raise HTTPException(
                429,
                detail={"__all__": {
                    "ru": "Код уже был отправлен, попробуйте через минуту.",
                    "en": "Code already sent, please wait a minute.",
                    "pl": "Kod został już wysłany, spróbuj ponownie za minutę.",
                }},
            )

        # ------------------------------------------------------------------
        # Генерация и сохранение 2-FA кода
        # ------------------------------------------------------------------
        code_2fa: str = "".join(random.choices("0123456789", k=6))
        await redis_db.set(f"login:code:{identifier}", code_2fa, ex=TWO_FA_CODE_TTL)
        await redis_db.set(send_key, "1", ex=TWO_FA_SEND_TTL)

        # ------------------------------------------------------------------
        # Отправка
        # ------------------------------------------------------------------
        if via == "email":
            html_body = f"""
            <div style="font-family: sans-serif; padding: 24px; background: #f2f2f2;">
                <div style="max-width: 500px; margin: auto; background: white; padding: 32px;
                            border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <h2 style="color: #333;">Kod 2FA</h2>
                    <p style="font-size: 16px;">Twój kod:</p>
                    <p style="font-size: 28px; font-weight: bold; color: #007bff;
                            letter-spacing: 6px;">{code_2fa}</p>
                    <p style="font-size: 14px; color: #777;">Kod jest ważny przez 5&nbsp;minut</p>
                </div>
            </div>
            """
            background_tasks.add_task(
                send_email,
                to_email=identifier,
                subject="Kod 2FA",
                body=f"Twój kod 2FA: {code_2fa}",
                html_body=html_body,
            )

        else:
            await send_sms(identifier, f"Twój kod 2FA to: {code_2fa}")

        return {
            "message": {
                "ru": "Код отправлен." if via == "phone" else "Код отправлен на e-mail.",
                "en": "Code sent." if via == "phone" else "Code sent to e-mail.",
                "pl": "Kod wysłany." if via == "phone" else "Kod wysłany na e-mail.",
            }
        }



    # ────────────────────────────────────────────────────────────────
    #  Шаг 2 Логина → JWT
    # ────────────────────────────────────────────────────────────────
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
        via: str = data.via if data.via in {"email", "phone"} else "email"
        identifier: str = (
            data.email.lower() if via == "email" else normalize_numbers(data.phone)
        )

        # ------------------------------------------------------------------
        # Проверка 2-FA кода
        # ------------------------------------------------------------------
        stored_code = await redis_db.get(f"login:code:{identifier}")
        if stored_code is None or stored_code.decode() != data.code:
            raise HTTPException(
                400,
                detail={"code": {
                    "ru": "Неверный код.",
                    "en": "Invalid code.",
                    "pl": "Nieprawidłowy kod.",
                }},
            )

        # ------------------------------------------------------------------
        # Поиск контакта
        # ------------------------------------------------------------------
        field = "email" if via == "email" else "phone"
        contact = await mongo_db["patients_contact_info"].find_one({field: identifier})
        if contact is None:
            raise HTTPException(
                404,
                detail={field: {
                    "ru": "Пользователь не найден.",
                    "en": "User not found.",
                    "pl": "Użytkownik nie znaleziony.",
                }},
            )

        # ------------------------------------------------------------------
        # Проверка активности
        # ------------------------------------------------------------------
        user_doc = await mongo_db["users"].find_one({"_id": ObjectId(contact["user_id"])})
        if user_doc and user_doc.get("is_active", True) is False:
            raise HTTPException(
                403,
                detail={"__all__": {
                    "ru": "Пользователь заблокирован.",
                    "en": "User is blocked.",
                    "pl": "Użytkownik jest zablokowany.",
                }},
            )

        # ------------------------------------------------------------------
        # Основная информация пациента
        # ------------------------------------------------------------------
        main_doc = await mongo_db["patients_main_info"].find_one({"user_id": contact["user_id"]})
        user_id: str = str(main_doc["user_id"])
        patient_id: Optional[str] = main_doc.get("patient_id")

        # ------------------------------------------------------------------
        # Мягкая CRM-синхронизация
        # ------------------------------------------------------------------
        if patient_id:
            try:
                crm_data = await get_client().get_patient(patient_id)
                await mongo_db["patients_main_info"].update_one(
                    {"_id": main_doc["_id"]},
                    {"$set": {
                        "first_name": crm_data.get("firstname"),
                        "last_name":  crm_data.get("lastname"),
                        "crm_last_sync": datetime.utcnow(),
                    }},
                )
            except CRMError:
                pass

        # ------------------------------------------------------------------
        # Генерация JWT
        # ------------------------------------------------------------------
        access_token: str = Authorize.create_access_token(subject=user_id)
        refresh_token: str = Authorize.create_refresh_token(subject=user_id)

        response.set_cookie("access_token", access_token, httponly=False, secure=True, samesite="None")
        response.set_cookie("refresh_token", refresh_token, httponly=False, secure=True, samesite="None")

        return {
            "message": {
                "ru": "Вход выполнен.",
                "en": "Logged in.",
                "pl": "Zalogowano.",
            },
            "access_token": access_token,
        }

    # ------------------------------------------------------------------
    # CRUD-маршруты всех моделей
    # ------------------------------------------------------------------
    router.include_router(generate_base_routes(registry))

    return router