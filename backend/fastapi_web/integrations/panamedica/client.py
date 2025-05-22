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


class CRMError(HTTPException):
    """Ошибка при взаимодействии с CRM."""
    pass


class CRMClient:
    """
    Клиент для работы с PaNa CRM API:
    - автоматическая авторизация через OAuth2 client_credentials
    - поиск и создание пациентов
    - обновление контактных данных
    - получение записей на приём
    """

    def __init__(self) -> None:
        self.token_data: str | None = None
        self.token_expiration: float = 0.0
        self.lock = asyncio.Lock()

    async def refresh_token(self) -> str:
        """
        Получает новый access_token по client_credentials.
        """
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
                logging.error(
                    "CRM token error %s %s",
                    resp.status_code,
                    resp.text)
                raise CRMError(status.HTTP_502_BAD_GATEWAY, "CRM auth failed")

            data = resp.json()
            self.token_data = data["access_token"]
            self.token_expiration = asyncio.get_event_loop().time() + \
                int(data["expires_in"]) - 60
            return self.token_data

    async def get_token(self) -> str:
        """
        Возвращает актуальный access_token. Обновляет при необходимости.
        """
        if self.token_data and asyncio.get_event_loop().time() < self.token_expiration:
            return self.token_data

        async with self.lock:
            if self.token_data and asyncio.get_event_loop().time() < self.token_expiration:
                return self.token_data
            return await self.refresh_token()

    async def call(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None
    ) -> dict:
        """
        Выполняет авторизованный HTTP-запрос в CRM.
        """
        headers = {
            "Authorization": f"Bearer {await self.get_token()}",
            "X-API-Client-Id": "PATIENT-PORTAL",
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.request(
                method.upper(),
                f"{settings.CRM_API_URL}{path}",
                headers=headers,
                params=params,
                json=json
            )

            if resp.status_code >= 400:
                logging.error(
                    "CRM %s %s -> %s %s",
                    method,
                    path,
                    resp.status_code,
                    resp.text)
                raise CRMError(
                    status.HTTP_502_BAD_GATEWAY,
                    "CRM request failed")

            return resp.json()

    async def find_patient(
        self,
        *,
        phone: str,
        pesel: str | None,
        gender: str,
        birth_date: str
    ) -> int | None:
        """
        Ищет пациента по телефону + PESEL (или пол + дата рождения).
        Возвращает ID пациента или None.
        """
        result = await self.call(
            "POST",
            "/registration",
            json={
                "action": "search",
                "phone": phone,
                "pesel": pesel,
                "gender": gender,
                "birthdate": birth_date,
            }
        )
        return result["id"] if result.get("found") else None

    async def create_patient(
        self,
        *,
        external_id: str,
        first_name: str,
        last_name: str,
        birth_date: str,
        phone: str,
        email: str | None,
        gender: str,
        pesel: str | None
    ) -> int:
        """
        Создаёт нового пациента и возвращает его ID.
        """
        result = await self.call(
            "POST",
            "/registration",
            json={
                "externalId": external_id,
                "firstname": first_name,
                "lastname": last_name,
                "birthdate": birth_date,
                "phone": phone,
                "email": email,
                "gender": gender,
                "pesel": pesel,
            }
        )
        return result["id"]

    async def patch_patient(self, patient_id: int, patch: dict) -> None:
        """
        Обновляет данные пациента по ID.
        """
        await self.call("PATCH", f"/patients/{patient_id}", json=patch)

    async def future_appointments(
            self, patient_id: int, *, from_date: date) -> list[dict]:
        """
        Возвращает список будущих визитов пациента, начиная с указанной даты.
        """
        result = await self.call(
            "GET",
            f"/patients/{patient_id}/appointments",
            params={"date_from": from_date.isoformat()}
        )
        return result["data"]

    async def find_or_create_patient(
            self, *, local_data: dict, contact_data: dict) -> int:
        """
        Находит пациента в CRM или создаёт, если его нет.
        Использует local_data (имя, дата рождения, пол) и contact_data (телефон, email, PESEL).
        """
        phone = normalize_numbers(contact_data.get("phone"))
        pesel = contact_data.get("pesel")
        gender = local_data.get("gender")
        bdate_raw = local_data.get("birth_date")
        bdate = bdate_raw.strftime("%Y-%m-%d") if bdate_raw else None

        if not phone or not gender or not bdate:
            raise CRMError(
                status.HTTP_400_BAD_REQUEST,
                "Not enough data to identify patient")

        patient_id = await self.find_patient(
            phone=phone,
            pesel=pesel,
            gender=gender,
            birth_date=bdate
        )
        if patient_id:
            return patient_id

        return await self.create_patient(
            external_id=str(uuid4()),
            first_name=local_data["first_name"],
            last_name=local_data["last_name"],
            birth_date=bdate,
            phone=phone,
            email=contact_data.get("email"),
            gender=gender,
            pesel=pesel
        )


@lru_cache
def get_client() -> CRMClient:
    """
    Возвращает синглтон клиента CRM.
    """
    return CRMClient()
