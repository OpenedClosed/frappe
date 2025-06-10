"""Миксины для удобной работы с PaNa."""
from datetime import date, datetime
import json

from fastapi import HTTPException

from utils.help_functions import normalize_numbers
from db.redis.db_init import redis_db
from .utils.help_functions import format_crm_phone
from personal_account.client_interface.db.mongo.enums import AccountVerificationEnum
from db.mongo.db_init import mongo_db
from .client import CRMError, get_client

class CRMIntegrationMixin:
    """
    Миксин для синхронизации пациента с PaNa CRM.
    Используется в админ-моделях MainInfo / ContactInfo.
    """
    async def get_master_client_by_user(self, user):
        user_id = user.data.get("user_id")
        main = None
        if user_id:
            main = await mongo_db["patients_main_info"].find_one({"user_id": str(user_id)})
        return main

    async def get_patient_id_for_user(self, user) -> str | None:
        client = await self.get_master_client_by_user(user)
        return client.get("patient_id") if client else None

    async def get_patient_cached(self, patient_id: str) -> dict | None:
        """
        Возвращает пациента из CRM с кешированием на 10 секунд.
        Если CRM недоступна — возвращает None.
        """
        if not patient_id:
            return None

        cache_key = f"crm:patient:{patient_id}"
        cached = await redis_db.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass  # повреждённый кеш игнорируем

        try:
            patient = await get_client().find_patient(patient_id=patient_id)
            await redis_db.set(cache_key, json.dumps(patient), ex=30)
            return patient
        except CRMError:
            return None


    async def sync_create_with_crm(self, valid: dict, contact: dict) -> dict:
        """
        • Пытается найти пациента в CRM; если нет — создаёт.
        • Записывает `patient_id` (наш externalId) и `UNVERIFIED`.
        • Обновляет локальные поля значениями из CRM.
        """
        crm = get_client()
        try:
            crm_data, _ = await crm.find_or_create_patient(
                local_data=valid,
                contact_data=contact,
            )
        except CRMError as e:
            raise HTTPException(e.status_code, "CRM error during creation") from e

        valid["patient_id"] = crm_data.get("externalId")
        valid["account_status"] = AccountVerificationEnum.UNVERIFIED
        valid["first_name"] = crm_data.get("firstname", valid.get("first_name"))
        valid["last_name"] = crm_data.get("lastname", valid.get("last_name"))
        if crm_data.get("birthdate"):
            valid["birth_date"] = datetime.fromisoformat(crm_data["birthdate"])
        valid["gender"] = crm_data.get("gender", valid.get("gender"))

        contact["email"] = crm_data.get("email", contact.get("email"))
        contact["phone"] = (
            normalize_numbers(crm_data.get("phone"))
            if crm_data.get("phone")
            else contact.get("phone")
        )

        return valid

    async def patch_contacts_in_crm(self, patient_id: str, patch: dict) -> None:
        """
        Обновляет телефон и email в CRM.
        Приводит телефон к нужному формату.
        Пропускает вызов, если поля отсутствуют.
        Если в ответе есть ошибка — вызывает HTTPException с errors.
        """
        allowed = {}
        if phone := patch.get("phone"):
            normalized_numbers = normalize_numbers(phone)
            allowed["phone"] = format_crm_phone(normalized_numbers)
        if email := patch.get("email"):
            allowed["email"] = email

        if not allowed:
            return

        try:
            response = await get_client().patch_patient(patient_id, allowed)

            if isinstance(response, dict) and "errors" in response:
                raise HTTPException(status_code=502, detail={
                    "errors": {
                        "ru": response["errors"].get("ru", "Ошибка CRM"),
                        "en": response["errors"].get("en", "CRM error")
                    }
                })

        except CRMError as e:
            raise HTTPException(status_code=400, detail={
                "__all__": {
                    "ru": f"Ошибка CRM: {str(e)}",
                    "en": f"CRM error: {str(e)}"
                }
            })



    async def get_account_status_from_crm(
        self, patient_id: str | None
    ) -> AccountVerificationEnum:
        """
        • Если `profile == "normal"` → VERIFIED.
        • Любое другое значение или ошибка → UNVERIFIED.
        Кешируется по patient_id на 10 секунд.
        """
        if not patient_id:
            return AccountVerificationEnum.UNVERIFIED

        cache_key = f"crm:patient_profile:{patient_id}"
        cached = await redis_db.get(cache_key)
        if cached:
            return AccountVerificationEnum(cached.decode())

        try:
            patient = await get_client().find_patient(patient_id=patient_id)
            status_enum = (
                AccountVerificationEnum.VERIFIED
                if patient.get("profile") == "normal"
                else AccountVerificationEnum.UNVERIFIED
            )
            await redis_db.set(cache_key, status_enum.value, ex=60)
            return status_enum
        except CRMError:
            return AccountVerificationEnum.UNVERIFIED

    async def get_future_appointments_cached(
        self, patient_id: str, from_date: date
    ) -> tuple[list[dict], CRMError | None]:
        cache_key = f"crm:appointments:{patient_id}:{from_date.isoformat()}"
        cached = await redis_db.get(cache_key)
        if cached:
            try:
                parsed = json.loads(cached)
                error_data = parsed.get("error")
                error = CRMError(**error_data) if error_data else None
                return parsed.get("data", []), error
            except Exception:
                pass

        try:
            appointments = await get_client().future_appointments(
                patient_id, from_date=from_date
            )
            await redis_db.set(cache_key, json.dumps({
                "data": appointments,
                "error": None
            }), ex=60)
            return appointments, None
        except CRMError as e:
            await redis_db.set(cache_key, json.dumps({
                "data": [],
                "error": {"status_code": e.status_code, "detail": e.detail}
            }), ex=60)
            return [], e

    async def get_consents_cached(
        self, patient_id: str, ttl: int = 60
    ) -> tuple[list[dict], CRMError | None]:
        if not patient_id:
            return [], None

        cache_key = f"crm:consents:{patient_id}"
        cached = await redis_db.get(cache_key)
        if cached:
            try:
                parsed = json.loads(cached)
                error_data = parsed.get("error")
                error = CRMError(**error_data) if error_data else None
                return parsed.get("data", []), error
            except Exception:
                pass

        try:
            consents = await get_client().get_consents(patient_id)
            await redis_db.set(cache_key, json.dumps({
                "data": consents,
                "error": None
            }), ex=ttl)
            return consents, None
        except CRMError as e:
            await redis_db.set(cache_key, json.dumps({
                "data": [],
                "error": {"status_code": e.status_code, "detail": e.detail}
            }), ex=ttl)
            return [], e

    async def get_bonuses_history_cached(
        self, patient_id: str, ttl: int = 60
    ) -> tuple[list[dict], CRMError | None]:
        if not patient_id:
            return [], None

        cache_key = f"crm:bonuses:{patient_id}"
        cached = await redis_db.get(cache_key)
        if cached:
            try:
                return json.loads(cached), None
            except Exception:
                pass

        try:
            data = await get_client().get_bonus_history(patient_id)
            await redis_db.set(cache_key, json.dumps(data), ex=ttl)
            return data, None
        except CRMError as e:
            await redis_db.set(cache_key, json.dumps([]), ex=ttl)  # кешируем пусто
            return [], e

