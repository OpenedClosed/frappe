"""Миксины для удобной работы с PaNa."""
from datetime import date, datetime

from fastapi import HTTPException

from utils.help_functions import normalize_numbers
from personal_account.client_interface.db.mongo.enums import AccountVerificationEnum

from .client import CRMError, get_client


class CRMIntegrationMixin:
    """
    Миксин для синхронизации пациента с внешней CRM PaNa.
    Подключается к админ-моделям MainInfo и ContactInfo.
    """

    async def sync_create_with_crm(self, valid: dict, contact: dict) -> dict:
        """
        Синхронизирует создание пациента:
        - Пытается найти по ID или по параметрам;
        - Если не найден, создаёт в CRM;
        - Устанавливает `patient_id` и `account_status` в объект;
        - Обновляет локальные данные на основе CRM.
        """
        crm = get_client()
        try:
            crm_data = await crm.find_or_create_patient(
                local_data=valid,
                contact_data=contact
            )
        except CRMError as e:
            raise HTTPException(502, "CRM error during creation") from e

        valid["patient_id"] = crm_data.get("externalId")
        valid["account_status"] = AccountVerificationEnum.UNVERIFIED
        valid["first_name"] = crm_data.get("firstname", valid.get("first_name"))
        valid["last_name"] = crm_data.get("lastname", valid.get("last_name"))
        valid["birth_date"] = datetime.fromisoformat(crm_data["birthdate"]) if "birthdate" in crm_data else valid.get("birth_date")
        valid["gender"] = crm_data.get("gender", valid.get("gender"))
        contact["email"] = crm_data.get("email", contact.get("email"))
        contact["phone"] = normalize_numbers(crm_data.get("phone")) if "phone" in crm_data else contact.get("phone")

        return valid

    async def patch_contacts_in_crm(self, patient_id: int, patch: dict) -> None:
        """
        Отправляет изменения телефона или email в CRM, если `patch` не пустой.
        Не вызывает исключений при ошибке — только логирует.
        """
        if not patch:
            return
        try:
            await get_client().patch_patient(patient_id, patch)
        except CRMError as e:
            print(f"[CRM] Ошибка при обновлении контактов: {e}")

    async def calc_account_status(self, patient_id: int) -> AccountVerificationEnum:
        """
        Проверяет наличие закрытых визитов в CRM:
        - Если хотя бы один визит со статусом 'closed' — статус 'verified';
        - Иначе — 'unverified'.
        При ошибке CRM возвращает 'unverified'.
        """
        try:
            appointments = await get_client().future_appointments(
                patient_id,
                from_date=date.today()
            )
            if any(a.get("status") == "closed" for a in appointments):
                return AccountVerificationEnum.VERIFIED
        except CRMError as e:
            print(f"[CRM] Ошибка при проверке визитов: {e}")
        return AccountVerificationEnum.UNVERIFIED
