from datetime import date

from fastapi import HTTPException

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
        - Пытается найти по PESEL/полу и дате рождения;
        - Если не найден, создаёт в CRM;
        - Устанавливает `patient_id` и `account_status` в объект.
        """
        crm = get_client()
        try:
            patient_id = await crm.find_or_create_patient(
                local_data=valid,
                contact_data=contact
            )
        except CRMError as e:
            raise HTTPException(502, "CRM error during creation") from e

        valid["patient_id"] = patient_id
        valid["account_status"] = AccountVerificationEnum.unverified
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
        except CRMError:
            pass

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
        except CRMError:
            pass
        return AccountVerificationEnum.UNVERIFIED