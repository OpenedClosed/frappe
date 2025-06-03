"""Клиент для взаимодействия с PaNa."""
import asyncio
import logging
from datetime import date
from functools import lru_cache
from uuid import uuid4

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
    Клиент PaNa CRM.  
    Авторизация, поиск/создание пациентов, чтение и обновление данных,
    включая согласия и визиты.
    """

    # ==============================================================
    # БЛОК: Аутентификация
    # ==============================================================

    def __init__(self) -> None:
        self.token_data: str | None = None
        self.token_expiration: float = 0.0
        self.lock = asyncio.Lock()

    async def refresh_token(self) -> str:
        print("\n======= refresh_token() =======")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.CRM_API_URL}/oauth/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": settings.CRM_CLIENT_ID,
                    "client_secret": settings.CRM_CLIENT_SECRET,
                },
            )
        print("Ответ от CRM:", resp.status_code, resp.text)

        if resp.status_code >= 400:
            raise CRMError(status.HTTP_502_BAD_GATEWAY, "CRM auth failed")

        data = resp.json()
        self.token_data = data["access_token"]
        self.token_expiration = asyncio.get_event_loop().time() + int(data["expires_in"]) - 60
        return self.token_data

    async def get_token(self) -> str:
        if self.token_data and asyncio.get_event_loop().time() < self.token_expiration:
            return self.token_data

        async with self.lock:
            if self.token_data and asyncio.get_event_loop().time() < self.token_expiration:
                return self.token_data
            return await self.refresh_token()

    # ==============================================================
    # БЛОК: Методы вызова
    # ==============================================================

    async def call(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict:
        print("\n======= call() =======")
        print("Method:", method)
        print("Path:", path)
        print("Params:", params)
        print("JSON:", json)

        headers = {
            "Authorization": f"Bearer {await self.get_token()}",
            "X-API-Client-Id": "PATIENT-PORTAL",
        }

        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            resp = await client.request(
                method.upper(),
                f"{settings.CRM_API_URL}{path}",
                headers=headers,
                params=params,
                json=json,
            )

        print("Ответ от CRM:", resp.status_code, resp.text)

        if resp.status_code == 302:
            print("CRM redirect location:", resp.headers.get("Location"))
            raise CRMError(status.HTTP_502_BAD_GATEWAY, "CRM returned redirect")

        if resp.status_code == 404:
            raise CRMError(status.HTTP_404_NOT_FOUND, "Не найдено")

        if resp.status_code >= 400:
            raise CRMError(status.HTTP_502_BAD_GATEWAY, f"Ошибка CRM: {resp.status_code}")

        if not resp.content:
            raise CRMError(status.HTTP_502_BAD_GATEWAY, "Пустой ответ от CRM")

        try:
            return resp.json()
        except Exception:
            raise CRMError(status.HTTP_502_BAD_GATEWAY, "Невалидный JSON от CRM")

    # ==============================================================
    # БЛОК: Пациенты
    # ==============================================================

    async def find_patient(
        self,
        *,
        patient_id: int | None = None,
        phone: str | None = None,
        pesel: str | None = None,
        gender: str | None = None,
        birth_date: str | None = None,
    ) -> dict | None:
        print("\n======= find_patient() =======")

        # 1) По внешнему ID
        if patient_id:
            try:
                return await self.get_patient(patient_id)
            except CRMError:
                return None

        # 2) По параметрам поиска
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
        pesel: str | None = None,
    ) -> dict:
        print("\n======= create_patient() =======")
        payload = {
            "externalId": external_id,
            "firstname": first_name,
            "lastname": last_name,
            "birthdate": birth_date,
            "phone": phone,
            "email": email,
            "gender": gender,
            "pesel": pesel,
        }
        return await self.call("POST", "/patients", json=payload)

    async def get_patient(self, patient_id: int) -> dict:
        print("\n======= get_patient() =======")
        return await self.call("GET", f"/patients/{patient_id}")

    async def patch_patient(self, patient_id: int, patch: dict) -> dict:
        print("\n======= patch_patient() =======")
        return await self.call("PATCH", f"/patients/{patient_id}", json=patch)

    async def find_or_create_patient(self, *, local_data: dict, contact_data: dict) -> dict:
        print("\n======= find_or_create_patient() =======")

        phone_key = normalize_numbers(contact_data.get("phone"))
        crm_phone = format_crm_phone(phone_key)
        pesel = contact_data.get("pesel")
        gender = local_data.get("gender")
        bdate_raw = local_data.get("birth_date")
        bdate = bdate_raw.strftime("%Y-%m-%d") if bdate_raw else None
        email = contact_data.get("email", "")

        if not crm_phone or not gender or not bdate:
            raise CRMError(status.HTTP_400_BAD_REQUEST, "Необходимо указать телефон, пол и дату рождения")

        # Пробуем найти (по ID или по параметрам)
        patient_id = local_data.get("patient_id")
        found_data = await self.find_patient(
            patient_id=patient_id,
            phone=crm_phone,
            pesel=pesel,
            gender=gender,
            birth_date=bdate,
        )
        if found_data:
            return found_data

        # Создаём нового
        external_id = str(uuid4())
        created = await self.create_patient(
            external_id=external_id,
            first_name=local_data["first_name"],
            last_name=local_data["last_name"],
            birth_date=bdate,
            phone=crm_phone,
            email=email,
            gender=gender,
            pesel=pesel,
        )
        return await self.get_patient(created["id"])

    # ==============================================================
    # БЛОК: Визиты
    # ==============================================================

    async def future_appointments(self, patient_id: int, *, from_date: date) -> list[dict]:
        print("\n======= future_appointments() =======")
        res = await self.call(
            "GET",
            f"/patients/{patient_id}/appointments",
            params={"date_from": from_date.isoformat()},
        )
        return res["data"]

    # ==============================================================
    # БЛОК: Согласия
    # ==============================================================

    async def get_consents(self, patient_id: int) -> list[dict]:
        """
        Возвращает список согласий пациента.
        """
        print("\n======= get_consents() =======")
        return await self.call("GET", f"/patients/{patient_id}/consents")

    async def update_consent(self, patient_id: int, consent_id: int, accept: bool) -> dict:
        """
        Обновляет (принимает/отзывает) конкретное согласие пациента.
        """
        print("\n======= update_consent() =======")
        payload = {"accept": accept}
        return await self.call(
            "PATCH",
            f"/patients/{patient_id}/consents/{consent_id}",
            json=payload,
        )





@lru_cache
def get_client() -> CRMClient:
    """
    Возвращает синглтон клиента CRM.
    """
    return CRMClient()
