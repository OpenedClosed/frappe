"""Клиент для взаимодействия с PaNa."""
import asyncio
import json
import logging
from datetime import date
from functools import lru_cache
import random
import string
from uuid import uuid4

from bson import ObjectId
from db.mongo.db_init import mongo_db
import httpx
from fastapi import HTTPException, status

from infra import settings
from utils.help_functions import normalize_numbers
from .utils.help_functions import format_crm_phone

class CRMError(HTTPException):
    """Ошибка при взаимодействии с CRM."""
    pass

class CRMClient:
    """
    Асинхронный клиент PaNa CRM.
    Обеспечивает авторизацию и методы работы с пациентами, визитами и согласиями.
    """

    # ==============================================================
    # БЛОК: Базовые методы
    # ==============================================================

    def normalize_payload(self, payload: dict) -> dict:
        """
        Приводит значения-словари или JSON-строки вида {"en": "..."} к payload["ключ"] = значение_en.
        Остальные значения оставляет без изменений.
        """
        def extract_en(val):
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict) and "en" in parsed:
                        return parsed["en"]
                except Exception:
                    return val
            elif isinstance(val, dict):
                return val.get("en", val)
            return val

        return {k: extract_en(v) for k, v in payload.items()}
    
    async def handle_missing_patient_by_id(self, patient_id: str):
        """
        Проверяет локальные документы, связанные с patient_id.
        Если пользователь — клиент, удаляет все.
        Иначе — сбрасывает patient_id в None.
        """
        main_doc = await mongo_db["patients_main_info"].find_one({"patient_id": patient_id})
        if not main_doc:
            return  # нечего делать

        user_id = main_doc.get("user_id")
        if not user_id:
            return

        user = await mongo_db["users"].find_one({"_id": ObjectId(user_id)})
        is_client = user and user.get("role") == "client"

        collections = [
            "patients_main_info",
            "patients_contact_info",
            "patients_bonus",
            "patients_consents",
            "patients_family",
        ]

        if is_client:
            for coll in collections:
                await mongo_db[coll].delete_many({"user_id": str(user_id)})
        else:
            await mongo_db["patients_contact_info"].update_many(
                {"user_id": str(user_id)},
                {"$unset": {"phone": None}}
            )
            for coll in collections:
                await mongo_db[coll].update_many(
                    {"user_id": str(user_id)},
                    {"$unset": {"patient_id": None}}
                )

    async def is_patient_id_unique(self, candidate_id: str) -> bool:
        """
        Проверяет, существует ли такой patient_id в локальной базе main_info.
        """
        existing = await mongo_db["patients_main_info"].find_one({"patient_id": candidate_id})
        return existing is None
    
    async def generate_unique_patient_id(self) -> str:
        """
        Генерирует ID формата ABC123 (ровно 6 символов: 3 буквы + 3 цифры),
        перемешивая их в случайном порядке. Гарантирует уникальность.
        """
        for _ in range(100):
            letters = random.choices(string.ascii_uppercase, k=3)
            digits  = random.choices(string.digits,           k=3)
            mixed   = letters + digits
            random.shuffle(mixed)
            candidate_id = "".join(mixed)

            if await self.is_patient_id_unique(candidate_id):
                return candidate_id

        raise RuntimeError("Не удалось сгенерировать уникальный patient_id")


    # ==============================================================
    # БЛОК: Аутентификация
    # ==============================================================

    def __init__(self) -> None:
        self.token_data: str | None = None
        self.token_expiration: float = 0.0
        self.lock = asyncio.Lock()

    async def refresh_token(self) -> str:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.CRM_API_URL}/oauth/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": settings.CRM_CLIENT_ID,
                    "client_secret": settings.CRM_CLIENT_SECRET,
                },
            )

        if resp.status_code >= 400:
            raise CRMError(status.HTTP_502_BAD_GATEWAY, "CRM auth failed")

        data = resp.json()
        self.token_data = data["access_token"]
        self.token_expiration = (
            asyncio.get_event_loop().time() + int(data["expires_in"]) - 60
        )
        return self.token_data

    async def get_token(self) -> str:
        if self.token_data and asyncio.get_event_loop().time() < self.token_expiration:
            return self.token_data

        async with self.lock:
            if self.token_data and asyncio.get_event_loop().time() < self.token_expiration:
                return self.token_data
            return await self.refresh_token()

    # ==============================================================
    # БЛОК: Основной вызов
    # ==============================================================

    async def call(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict:

        headers = {
            "Authorization": f"Bearer {await self.get_token()}",
            "X-API-Client-Id": "PATIENT-PORTAL",
        }

        json = self.normalize_payload(json) if json else None
        params = self.normalize_payload(params) if params else None

        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            resp = await client.request(
                method.upper(),
                f"{settings.CRM_API_URL}{path}",
                headers=headers,
                params=params,
                json=json,
            )

        if resp.status_code == 302:
            raise CRMError(status.HTTP_302_FOUND, "CRM returned redirect")
        if resp.status_code == 404:
            raise CRMError(status.HTTP_404_NOT_FOUND, "Not found")
        if resp.status_code == 403:
            raise CRMError(status.HTTP_403_FORBIDDEN, "Forbidden")
        if resp.status_code >= 400:
            raise CRMError(status.HTTP_502_BAD_GATEWAY, f"CRM error {resp.status_code}")
        if not resp.content:
            raise CRMError(status.HTTP_502_BAD_GATEWAY, "Empty response from CRM")

        try:
            return resp.json()
        except Exception:
            raise CRMError(status.HTTP_502_BAD_GATEWAY, "Invalid JSON from CRM")

    # ==============================================================
    # БЛОК: Пациенты
    # ==============================================================

    async def find_patient(
        self,
        *,
        patient_id: str | None = None,
        phone: str | None = None,
        pesel: str | None = None,
        gender: str | None = None,
        birth_date: str | None = None,
    ) -> dict | None:

        # 1) поиск по нашему внешнему ID
        if patient_id:
            try:
                return await self.get_patient(patient_id)
            except CRMError as e:
                if e.status_code == status.HTTP_404_NOT_FOUND:
                    await self.handle_missing_patient_by_id(patient_id)
                    return None
                raise

        # 2) поиск по параметрам
        phone_key = normalize_numbers(phone)
        crm_phone = format_crm_phone(phone_key)
        params = {"phone": crm_phone}

        if pesel:
            params["pesel"] = pesel
        else:
            if not (gender and birth_date):
                raise CRMError(status.HTTP_400_BAD_REQUEST, "Недостаточно данных для поиска")
            params.update({"gender": gender, "birthdate": birth_date})

        try:
            found = await self.call("GET", "/patients/search", params=params)
            return await self.get_patient(found["id"])
        except CRMError as e:
            if e.status_code == status.HTTP_404_NOT_FOUND:
                return None
            raise

    async def create_patient(
        self,
        *,
        external_id: str,
        first_name: str,
        last_name: str,
        birth_date: str,
        phone: str,
        email: str,
        gender: str,
        referral_id: str,
        pesel: str | None = None,
    ) -> dict:
        payload = {
            "externalId": external_id,
            "firstname": first_name,
            "lastname": last_name,
            "birthdate": birth_date,
            "phone": phone,
            "email": email,
            "gender": gender,
            "pesel": pesel,
            "referralId": referral_id,
        }
        data = await self.call("POST", "/patients", json=payload)
        # CRM может не вернуть externalId — добавляем сами
        data.setdefault("externalId", external_id)
        return data

    async def get_patient(self, patient_id: str) -> dict:
        data = await self.call("GET", f"/patients/{patient_id}")
        # если CRM не передала externalId, добавляем своё
        data.setdefault("externalId", patient_id)
        return data

    async def patch_patient(self, patient_id: str, patch: dict) -> dict:
        return await self.call("PATCH", f"/patients/{patient_id}", json=patch)

    async def find_or_create_patient(
        self, *, local_data: dict, contact_data: dict
    ) -> tuple[dict, bool]:
        """
        Возвращает (crm_data, created_now).
        """

        phone_key = normalize_numbers(contact_data.get("phone"))
        crm_phone = format_crm_phone(phone_key)
        pesel = contact_data.get("pesel")
        gender = local_data.get("gender")
        bdate_raw = local_data.get("birth_date")
        referral_id = local_data.get("referral_id")
        bdate = bdate_raw.strftime("%Y-%m-%d") if bdate_raw else None
        email = contact_data.get("email", "")

        if not crm_phone or not gender or not bdate:
            raise CRMError(
                status.HTTP_400_BAD_REQUEST,
                "Телефон, пол и дата рождения обязательны",
            )

        # ищем
        found = await self.find_patient(
            patient_id=local_data.get("patient_id"),
            phone=crm_phone,
            pesel=pesel,
            gender=gender,
            birth_date=bdate,
        )
        if found:
            return found, False

        # создаём
        external_id = await self.generate_unique_patient_id()
        created = await self.create_patient(
            external_id=external_id,
            first_name=local_data["first_name"],
            last_name=local_data["last_name"],
            birth_date=bdate,
            phone=crm_phone,
            email=email,
            gender=gender,
            referral_id=referral_id,
            pesel=pesel,
        )
        # получаем полную карточку + гарантируем внешний ID
        full = await self.find_patient(patient_id=created["externalId"])
        full.setdefault("externalId", external_id)
        return full, True

    # ==============================================================
    # БЛОК: Визиты
    # ==============================================================

    async def future_appointments(
        self, patient_id: str, *, from_date: date
    ) -> list[dict]:
        res = await self.call(
            "GET",
            f"/patients/{patient_id}/appointments",
            params={"date_from": from_date.isoformat()},
        )
        return res["data"]

    # ==============================================================
    # БЛОК: Согласия
    # ==============================================================

    async def get_consents(self, patient_id: str) -> list[dict]:
        return await self.call("GET", f"/patients/{patient_id}/consents")

    async def update_consent(
        self, patient_id: str, consent_id: int, accept: bool
    ) -> dict:
        payload = {"accept": accept}
        return await self.call(
            "PATCH", f"/patients/{patient_id}/consents/{consent_id}", json=payload
        )
    
    # ==============================================================
    # БЛОК: Бонусы
    # ==============================================================

    async def get_bonus_balance(self, patient_id: str) -> int:
        """Возвращает текущий баланс бонусов пациента."""
        patient = await self.find_patient(patient_id=patient_id)
        return int(patient.get("bonuses", 0))

    async def get_bonus_history(self, patient_id: str) -> list[dict]:
        """Возвращает историю начислений и списаний бонусов."""
        return await self.call("GET", f"/patients/{patient_id}/history-charges")



@lru_cache
def get_client() -> CRMClient:
    """
    Возвращает синглтон клиента CRM.
    """
    return CRMClient()
