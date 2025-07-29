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


REG_CODES: Dict[str, dict] = {}
TWO_FA_CODES: Dict[str, str] = {}


def generate_base_account_routes(registry) -> APIRouter:  # noqa: C901
    """
    Генерирует маршруты:

    1.  /register           → выдача 6-значного кода по SMS  
    2.  /register_confirm   → CRM + Mongo + JWT (опц.)  
    3.  /login              → пароль + 2-FA код  
    4.  /login_confirm      → 2-FA + CRM-синхрон + JWT  
    5.  CRUD для всех админ-моделей из `registry`

    Все сообщения и ошибки возвращаются как словари вида  
    `{"ru": "...", "en": "...", "pl": "...", "uk": "...", "de": "...", "be": "..."}`.
    """
    router = APIRouter()

    # ------------------------------------------------------------------
    # Шаг 1 Регистрации → SMS-код
    # ------------------------------------------------------------------
    @router.post("/register")
    async def register(data: RegistrationSchema, background_tasks: BackgroundTasks):
        """
        Проверяет ввод и отправляет 6-значный код подтверждения на email.
        """
        errors: dict[str, dict] = {}

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
            errors["password"] = pwd_error | {
                "be": pwd_error.get("ru", "")
            }

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

        # ——— реферальный код
        referral_id: Optional[str] = None
        if data.referral_code:
            m = re.fullmatch(r"([A-Za-z0-9]{2,10})_([A-Za-z0-9\-]{3,36})", data.referral_code)
            if not m:
                errors["referral_code"] = {
                    "ru": "Некорректный формат реферального кода.",
                    "en": "Invalid referral-code format.",
                    "pl": "Nieprawidłowy format kodu polecającego.",
                    "uk": "Некоректний формат реферального коду.",
                    "de": "Ungültiges Format des Empfehlungscodes.",
                    "be": "Некарэктны фармат рэферальнага кода.",
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
                            "de": "Empfehlungscode nicht gefunden.",
                            "be": "Такі рэферальны код не знойдзены.",
                        }
                    else:
                        referral_id = ref_patient["externalId"]
                except CRMError:
                    errors["referral_code"] = {
                        "ru": "Ошибка CRM при проверке кода.",
                        "en": "CRM error while validating code.",
                        "pl": "Błąd CRM podczas weryfikacji kodu.",
                        "uk": "Помилка CRM під час перевірки коду.",
                        "de": "CRM-Fehler bei der Codeüberprüfung.",
                        "be": "Памылка CRM пры праверцы кода.",
                    }

        if errors:
            return JSONResponse(status_code=400, content={"errors": errors})

        # ——— генерируем 6-значный код
        code = "".join(random.choices("0123456789", k=6))

        # ——— сохраняем по email
        email_key = data.email.lower()
        REG_CODES[email_key] = {"code": code, "referral_id": referral_id}

        # ——— HTML-шаблон
        html_body = f"""
        <div style="font-family: sans-serif; padding: 24px; background: #f2f2f2;">
            <div style="max-width: 500px; margin: auto; background: white; padding: 32px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <h2 style="color: #333;">Код подтверждения</h2>
                <p style="font-size: 16px;">Ваш код:</p>
                <p style="font-size: 28px; font-weight: bold; color: #007bff; letter-spacing: 6px;">{code}</p>
                <p style="font-size: 14px; color: #777;">Он действителен в течение 5 минут</p>
            </div>
        </div>
        """

        # ——— отправка по email
        try:
            background_tasks.add_task(
                send_email,
                to_email=email_key,
                subject="Код подтверждения",
                body=f"Ваш код подтверждения: {code}",
                html_body=html_body,
            )
        except HTTPException:
            errors["email"] = {
                "ru": "Ошибка при отправке письма. Проверьте email.",
                "en": "Failed to send email. Please check the address.",
                "pl": "Nie udało się wysłać wiadomości email. Sprawdź adres.",
                "uk": "Не вдалося надіслати email. Перевірте адресу.",
                "de": "E-Mail konnte nicht gesendet werden. Bitte überprüfen Sie die Adresse.",
                "be": "Не атрымалася адправіць email. Праверце адрас.",
            }
            return JSONResponse(status_code=400, content={"errors": errors})

        # ——— отправка по SMS (временно отключена)
        # try:
        #     await send_sms(phone_key, f"Twój kod potwierdzający to: {code}")
        # except HTTPException:
        #     errors["phone"] = {
        #         "ru": "Ошибка при отправке SMS. Проверьте номер телефона.",
        #         "en": "Failed to send SMS. Please check your phone number.",
        #         "pl": "Nie udało się wysłać SMS-a. Sprawdź numer telefonu.",
        #         "uk": "Не вдалося надіслати SMS. Перевірте номер телефону.",
        #         "de": "SMS konnte nicht gesendet werden. Bitte überprüfen Sie die Telefonnummer.",
        #         "be": "Не атрымалася адправіць SMS. Праверце нумар тэлефона.",
        #     }
        #     return JSONResponse(status_code=400, content={"errors": errors})

        return {
            "message": {
                "ru": "Код отправлен на email.",
                "en": "Code sent to email.",
                "pl": "Kod został wysłany na adres email.",
                "uk": "Код надіслано на email.",
                "de": "Code wurde an die E-Mail gesendet.",
                "be": "Код адпраўлены на email.",
            }
        }


    # ------------------------------------------------------------------
    # Шаг 2 Регистрации → CRM + Mongo + JWT
    # ------------------------------------------------------------------
    @router.post("/register_confirm")
    async def register_confirm(
        data: ConfirmationSchema,
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends(),
    ):
        """
        Валидирует код, создаёт / обновляет профиль, синхронизирует с CRM,
        выдаёт JWT (если пользователь не был залогинен).
        """
        await send_email(
            to_email="opendoor200179@gmail.com",
            subject="Код подтверждения",
            body=f"Ваш код подтверждения: 1234",
            # html_body=html_body,
        )
        phone_key = normalize_numbers(data.phone)
        email_key = data.email.lower()
        stored = REG_CODES.get(email_key) or {}
        if stored.get("code") != data.code:
            raise HTTPException(400, detail={
                "code": {
                    "ru": "Неверный код.",
                    "en": "Invalid code.",
                    "pl": "Nieprawidłowy kod.",
                    "uk": "Невірний код.",
                    "de": "Ungültiger Code.",
                    "be": "Несапраўдны код.",
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
                    "de": "CRM-Fehler während der Registrierung.",
                    "be": "Памылка CRM падчас рэгістрацыі.",
                }
            }) from e

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
                        "phone": None,
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
                    "de": "Profil erfolgreich aktualisiert.",
                    "be": "Профіль паспяхова абноўлены.",
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
                "uk": "Реєстрацію завершено.",
                "de": "Registrierung abgeschlossen.",
                "be": "Рэгістрацыя завершана.",
            },
            "access_token": access_token,
        }

    # ------------------------------------------------------------------
    # Шаг 1 Логина → 2‑FA код
    # ------------------------------------------------------------------
    @router.post("/login")
    async def login(data: LoginSchema, background_tasks: BackgroundTasks):
        """
        Проверяет пароль и отправляет 6‑значный 2‑FA код на e‑mail.
        """

        email_key: str = data.email.lower()

        # ------------------------------------------------------------------
        # Поиск контакта по e‑mail
        # ------------------------------------------------------------------
        contact = await mongo_db["patients_contact_info"].find_one({"email": email_key})

        # ------------------------------------------------------------------
        # Поиск по телефону (оставлено закомментированным)
        # ------------------------------------------------------------------
        # phone_key: str = normalize_numbers(data.phone)
        # contact = await mongo_db["patients_contact_info"].find_one({"phone": phone_key})

        # ------------------------------------------------------------------
        # Зачистка «висящего» пользователя
        # ------------------------------------------------------------------
        if (
            contact is not None
            and await mongo_db["users"].find_one({"_id": ObjectId(contact["user_id"])}) is None
        ):
            await cascade_delete_user(contact["user_id"])
            contact = None

        # ------------------------------------------------------------------
        # Если пользователь не найден
        # ------------------------------------------------------------------
        if contact is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "email": {
                        "ru": "Пользователь не найден.",
                        "en": "User not found.",
                        "pl": "Użytkownik nie znaleziony.",
                        "uk": "Користувача не знайдено.",
                        "de": "Benutzer nicht gefunden.",
                        "be": "Карыстальнік не знойдзены.",
                    },
                    # "phone": {
                    #     "ru": "Пользователь не найден.",
                    #     "en": "User not found.",
                    #     "pl": "Użytkownik nie znaleziony.",
                    #     "uk": "Користувача не знайдено.",
                    #     "de": "Benutzer nicht gefunden.",
                    #     "be": "Карыстальнік не знойдзены.",
                    # },
                },
            )

        # ------------------------------------------------------------------
        # Документ пользователя
        # ------------------------------------------------------------------
        user_doc = await mongo_db["users"].find_one({"_id": ObjectId(contact["user_id"])})

        # ------------------------------------------------------------------
        # Проверка блокировки
        # ------------------------------------------------------------------
        if user_doc is not None and user_doc.get("is_active", True) is False:
            raise HTTPException(
                status_code=403,
                detail={
                    "__all__": {
                        "ru": "Пользователь заблокирован.",
                        "en": "User is blocked.",
                        "pl": "Użytkownik jest zablokowany.",
                        "uk": "Користувача заблоковано.",
                        "de": "Benutzer ist blockiert.",
                        "be": "Карыстальнік заблакаваны.",
                    }
                },
            )

        # ------------------------------------------------------------------
        # Проверка пароля
        # ------------------------------------------------------------------
        if user_doc is None or data.check_password(user_doc.get("password", "")) is False:
            raise HTTPException(
                status_code=401,
                detail={
                    "password": {
                        "ru": "Неверный пароль.",
                        "en": "Wrong password.",
                        "pl": "Błędne hasło.",
                        "uk": "Невірний пароль.",
                        "de": "Falsches Passwort.",
                        "be": "Няправільны пароль.",
                    }
                },
            )

        # ------------------------------------------------------------------
        # Генерация и сохранение 2‑FA кода
        # ------------------------------------------------------------------
        code_2fa: str = "".join(random.choices("0123456789", k=6))
        TWO_FA_CODES[email_key] = code_2fa
        # TWO_FA_CODES[phone_key] = code_2fa  # для телефона

        # ------------------------------------------------------------------
        # Красивый HTML‑шаблон письма
        # ------------------------------------------------------------------
        html_body: str = f"""
        <div style="font-family: sans-serif; padding: 24px; background: #f2f2f2;">
            <div style="max-width: 500px; margin: auto; background: white; padding: 32px;
                        border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <h2 style="color: #333;">Код 2‑FA</h2>
                <p style="font-size: 16px;">Ваш код:</p>
                <p style="font-size: 28px; font-weight: bold; color: #007bff;
                        letter-spacing: 6px;">{code_2fa}</p>
                <p style="font-size: 14px; color: #777;">Он действителен в течение 5&nbsp;минут</p>
            </div>
        </div>
        """

        # ------------------------------------------------------------------
        # Отправка e‑mail (SMS оставлен закомментированным)
        # ------------------------------------------------------------------
        try:
            background_tasks.add_task(
                send_email,
                to_email=email_key,
                subject="Код 2‑FA",
                body=f"Ваш код 2‑FA: {code_2fa}",
                html_body=html_body,
            )

            # await send_sms(phone_key, f"Twój kod 2FA to: {code_2fa}")  # SMS‑вариант
        except Exception:
            return JSONResponse(
                status_code=400,
                content={
                    "errors": {
                        "email": {
                            "ru": "Ошибка при отправке e‑mail. Проверьте адрес.",
                            "en": "Failed to send e‑mail. Please check the address.",
                            "pl": "Nie udało się wysłać e‑maila. Sprawdź adres.",
                            "uk": "Не вдалося надіслати e‑mail. Перевірте адресу.",
                            "de": "E‑Mail konnte nicht gesendet werden. Bitte überprüfen Sie die Adresse.",
                            "be": "Не атрымалася адправіць e‑mail. Праверце адрас.",
                        },
                        # "phone": {
                        #     "ru": "Ошибка при отправке SMS. Проверьте номер телефона.",
                        #     "en": "Failed to send SMS. Please check your phone number.",
                        #     "pl": "Nie udało się wysłać SMS-a. Sprawdź numer telefonu.",
                        #     "uk": "Не вдалося надіслати SMS. Перевірте номер телефону.",
                        #     "de": "SMS konnte nicht gesendet werden. Bitte überprüfen Sie die Telefonnummer.",
                        #     "be": "Не атрымалася адправіць SMS. Праверце нумар тэлефона.",
                        # },
                    }
                },
            )

        return {
            "message": {
                "ru": "Код отправлен на e‑mail.",
                "en": "Code sent to e‑mail.",
                "pl": "Kod wysłany na e‑mail.",
                "uk": "Код надіслано на e‑mail.",
                "de": "Code an die E‑Mail gesendet.",
                "be": "Код адпраўлены на e‑mail.",
            }
        }


    # ------------------------------------------------------------------
    # Шаг 2 Логина → JWT
    # ------------------------------------------------------------------
    @router.post("/login_confirm")
    async def login_confirm(
        data: TwoFASchema,
        response: Response,
        Authorize: AuthJWT = Depends(),
    ):
        """
        Проверяет 2‑FA код и выдаёт JWT. Одновременно подтягивает свежие
        данные из CRM.
        """

        email_key: str = data.email.lower()
        # phone_key: str = normalize_numbers(data.phone)

        # ------------------------------------------------------------------
        # Проверка 2‑FA кода
        # ------------------------------------------------------------------
        if TWO_FA_CODES.get(email_key) != data.code:
            # if TWO_FA_CODES.get(phone_key) != data.code:  # телефон
            raise HTTPException(
                status_code=400,
                detail={
                    "code": {
                        "ru": "Неверный код.",
                        "en": "Invalid code.",
                        "pl": "Nieprawidłowy kod.",
                        "uk": "Невірний код.",
                        "de": "Ungültiger Code.",
                        "be": "Несапраўдны код.",
                    }
                },
            )

        # ------------------------------------------------------------------
        # Поиск контакта по e‑mail
        # ------------------------------------------------------------------
        contact = await mongo_db["patients_contact_info"].find_one({"email": email_key})

        # contact = await mongo_db["patients_contact_info"].find_one({"phone": phone_key})  # телефон

        if contact is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "email": {
                        "ru": "Пользователь не найден.",
                        "en": "User not found.",
                        "pl": "Użytkownik nie znaleziony.",
                        "uk": "Користувача не знайдено.",
                        "de": "Benutzer nicht gefunden.",
                        "be": "Карыстальнік не знойдзены.",
                    },
                    # "phone": {
                    #     "ru": "Пользователь не найден.",
                    #     "en": "User not found.",
                    #     "pl": "Użytkownik nie znaleziony.",
                    #     "uk": "Користувача не знайдено.",
                    #     "de": "Benutzer nicht gefunden.",
                    #     "be": "Карыстальнік не знойдзены.",
                    # },
                },
            )

        # ------------------------------------------------------------------
        # Проверка активности
        # ------------------------------------------------------------------
        user_doc = await mongo_db["users"].find_one({"_id": ObjectId(contact["user_id"])})
        if user_doc is not None and user_doc.get("is_active", True) is False:
            raise HTTPException(
                status_code=403,
                detail={
                    "__all__": {
                        "ru": "Пользователь заблокирован.",
                        "en": "User is blocked.",
                        "pl": "Użytkownik jest zablokowany.",
                        "uk": "Користувача заблоковано.",
                        "de": "Benutzer ist blockiert.",
                        "be": "Карыстальнік заблакаваны.",
                    }
                },
            )

        # ------------------------------------------------------------------
        # Основная информация пациента
        # ------------------------------------------------------------------
        main_doc = await mongo_db["patients_main_info"].find_one({"user_id": contact["user_id"]})
        user_id: str = str(main_doc["user_id"])
        patient_id: Optional[str] = main_doc.get("patient_id")

        # ------------------------------------------------------------------
        # Мягкая CRM‑синхронизация
        # ------------------------------------------------------------------
        if patient_id is not None:
            try:
                crm_data = await get_client().get_patient(patient_id)
                await mongo_db["patients_main_info"].update_one(
                    {"_id": main_doc["_id"]},
                    {
                        "$set": {
                            "first_name": crm_data.get("firstname"),
                            "last_name": crm_data.get("lastname"),
                            "crm_last_sync": datetime.utcnow(),
                        }
                    },
                )
            except CRMError:
                pass

        # ------------------------------------------------------------------
        # Генерация JWT
        # ------------------------------------------------------------------
        access_token: str = Authorize.create_access_token(subject=user_id)
        refresh_token: str = Authorize.create_refresh_token(subject=user_id)

        response.set_cookie(
            "access_token",
            access_token,
            httponly=False,
            secure=True,
            samesite="None",
        )
        response.set_cookie(
            "refresh_token",
            refresh_token,
            httponly=False,
            secure=True,
            samesite="None",
        )

        return {
            "message": {
                "ru": "Вход выполнен.",
                "en": "Logged in.",
                "pl": "Zalogowano.",
                "uk": "Вхід виконано.",
                "de": "Eingeloggt.",
                "be": "Уваход выкананы.",
            },
            "access_token": access_token,
        }


    # ------------------------------------------------------------------
    # CRUD-маршруты всех моделей
    # ------------------------------------------------------------------
    router.include_router(generate_base_routes(registry))

    return router