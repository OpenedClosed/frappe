from datetime import datetime
from typing import Any, Optional
import json

from fastapi import APIRouter

from db.mongo.db_init import mongo_db
from integrations.frappe.schemas import BotSettingsSyncRequest

from knowledge.db.mongo.schemas import (
    BotSettings,
    Photo,
)
from knowledge.db.mongo.enums import (
    BotColorEnum,
    CommunicationStyleEnum,
    PersonalityTraitsEnum,
    TargetActionEnum,
    FunctionalityEnum,
    ForbiddenTopicsEnum,
    AIModelEnum,
)

frappe_bot_settings_router = APIRouter()


def parse_enum_value(enum_cls, value: Optional[str], default: Optional[Any] = None):
    """Аккуратно замапить строку (из Frappe/старой админки) в наш enum с JSON-значением."""
    if not value:
        return default

    # 1. Прямое значение enum (вдруг уже json-строка или Enum)
    try:
        return enum_cls(value)
    except Exception:
        pass

    # 2. По имени члена enum (например, "FRIENDLY", "GREEN")
    try:
        return enum_cls[value]
    except Exception:
        pass

    # 3. По человекочитаемым label'ам из JSON ("en"/"ru")
    try:
        normalized = str(value).strip().lower()
    except Exception:
        return default

    for member in enum_cls:
        raw = getattr(member, "value", None)
        if raw is None:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        en_label = str(data.get("en", "")).strip().lower()
        ru_label = str(data.get("ru", "")).strip().lower()

        if normalized == en_label or normalized == ru_label:
            return member

    return default


@frappe_bot_settings_router.post("/sync")
async def bot_settings_sync(data: BotSettingsSyncRequest):
    """Принять Bot Settings из Frappe и сохранить/обновить их в Mongo."""
    app_name = (data.app_name or data.project_name).strip()
    project_name = data.project_name.strip()

    if data.created_at:
        try:
            created_at_dt = datetime.fromisoformat(data.created_at)
        except Exception:
            created_at_dt = datetime.utcnow()
    else:
        created_at_dt = datetime.utcnow()

    avatar = None
    if data.avatar_url:
        avatar = Photo(
            url=data.avatar_url,
            uploaded_at=created_at_dt,
        )

    settings_obj = BotSettings(
        project_name=data.project_name,
        employee_name=data.employee_name,
        mention_name=data.mention_name,
        avatar=avatar,
        bot_color=parse_enum_value(BotColorEnum, data.bot_color, BotColorEnum.RED),
        communication_tone=parse_enum_value(
            CommunicationStyleEnum,
            data.communication_tone,
            CommunicationStyleEnum.CASUAL,
        ),
        personality_traits=parse_enum_value(
            PersonalityTraitsEnum,
            data.personality_traits,
            PersonalityTraitsEnum.BALANCED,
        ),
        additional_instructions=data.additional_instructions or "",
        role=data.role or "Default Role",
        target_action=[
            v for v in (
                parse_enum_value(TargetActionEnum, value)
                for value in data.target_action
            )
            if v is not None
        ],
        core_principles=data.core_principles or "",
        special_instructions=[
            v for v in (
                parse_enum_value(FunctionalityEnum, value)
                for value in data.special_instructions
            )
            if v is not None
        ],
        forbidden_topics=[
            v for v in (
                parse_enum_value(ForbiddenTopicsEnum, value)
                for value in data.forbidden_topics
            )
            if v is not None
        ],
        greeting=data.greeting or {},
        error_message=data.error_message or {},
        farewell_message=data.farewell_message or {},
        fallback_ai_error_message=data.fallback_ai_error_message or {},
        app_name=app_name,
        ai_model=parse_enum_value(AIModelEnum, data.ai_model, AIModelEnum.GPT_4_O),
        created_at=created_at_dt,
        is_active=getattr(data, "is_active", False),
    )

    doc = settings_obj.model_dump()
    doc["frappe_doctype"] = data.frappe_doctype
    doc["frappe_name"] = data.frappe_name
    doc["frappe_modified"] = data.frappe_modified

    filter_doc = {
        "app_name": app_name,
        "project_name": project_name,
    }

    await mongo_db.bot_settings.update_one(
        filter_doc,
        {"$set": doc},
        upsert=True,
    )

    if getattr(data, "is_active", False):
        await mongo_db.bot_settings.update_many(
            {
                "is_active": True,
                "$or": [
                    {"app_name": {"$ne": app_name}},
                    {"project_name": {"$ne": project_name}},
                ],
            },
            {"$set": {"is_active": False}},
        )

    return {"ok": True, "app_name": app_name, "project_name": project_name}