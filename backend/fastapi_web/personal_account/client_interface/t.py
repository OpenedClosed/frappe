from datetime import date

from admin.base import BaseAccount  # твой базовый
from admin.crm_mixin import CRMIntegrationMixin
from app.db import mongo_db
from bson import ObjectId
from schemas.patient import (AccountVerificationEnum, AppointmentSchema,
                             ContactInfoSchema, MainInfoSchema)
from utils.help_functions import normalize_numbers

# ---------- 3.1  Основная информация ------------------------------------


class MainInfoAccount(CRMIntegrationMixin, BaseAccount):
    model = MainInfoSchema
    collection_name = "patients_main_info"

    computed_fields = ["patient_id", "account_status"]
    read_only_fields = [
        "patient_id",
        "account_status",
        "created_at",
        "updated_at"]

    async def create(self, data: dict, current_user=None):
        valid = await self.process_data(data)
        contact = await mongo_db["patients_contact_info"].find_one({"user_id": str(current_user.id)})
        valid = await self.sync_create_with_crm(valid, contact)
        ins = await self.db.insert_one(valid)
        created = await self.db.find_one({"_id": ins.inserted_id})
        return await self.format_document(created, current_user)

    async def update(self, object_id: str, data: dict, current_user=None):
        obj = await self.db.find_one({"_id": ObjectId(object_id)})
        await self.patch_contacts_in_crm(
            obj.get("patient_id"),
            {k: normalize_numbers(v) if k == "phone" else v for k,
             v in data.items() if k in ("phone", "email")}
        )
        return await super().update(object_id, data, current_user)

    async def get_account_status(self, obj: dict):
        return await self.calc_account_status(obj.get("patient_id"))

# ---------- 3.2  Контактная информация ----------------------------------


class ContactInfoAccount(CRMIntegrationMixin, BaseAccount):
    model = ContactInfoSchema
    collection_name = "patients_contact_info"

    async def update(self, object_id: str, data: dict, current_user=None):
        main = await mongo_db["patients_main_info"].find_one({"user_id": str(current_user.id)})
        await self.patch_contacts_in_crm(
            main.get("patient_id"),
            {k: normalize_numbers(v) if k == "phone" else v for k,
             v in data.items() if k in ("phone", "email")}
        )
        return await super().update(object_id, data, current_user)

# ---------- 3.3  Список визитов (read-only) -----------------------------


class AppointmentAccount(BaseAccount):
    model = AppointmentSchema
    collection_name = "__virtual__appointments"

    list_display = ["date", "start", "end", "doctor"]
    detail_fields = list_display
    allow_crud_actions = {
        "create": False,
        "read": True,
        "update": False,
        "delete": False}

    async def get_queryset(
        self, filters=None, sort_by=None, order=1, page=None, page_size=None, current_user=None, format=True
    ):
        main = await mongo_db["patients_main_info"].find_one({"user_id": str(current_user.id)})
        if not main or "patient_id" not in main:
            return []
        data = await get_client().future_appointments(
            main["patient_id"],
            from_date=main["created_at"].date(
            ) if "created_at" in main else date.today()
        )
        return [
            {
                "id": a["id"],
                "date": a["date"],
                "start": a["start"],
                "end": a["end"],
                "doctor": a["doctor"]["name"],
            }
            for a in data
        ]
