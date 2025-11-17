from datetime import datetime
from typing import Any, Optional, List

from fastapi import APIRouter

from db.mongo.db_init import mongo_db
from integrations.frappe.schemas import BotSettingsSyncRequest

# здесь нужно импортнуть твои реальные модели/enum'ы
from knowledge.db.mongo.schemas import (
    BotSettings,
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
    if not value:
        return default
    try:
        return enum_cls(value)
    except Exception:
        try:
            return enum_cls[value]
        except Exception:
            return default


@frappe_bot_settings_router.post("/sync")
async def bot_settings_sync(data: BotSettingsSyncRequest):
    """Принять Bot Settings из Frappe и сохранить/обновить их в Mongo."""
    app_name = (data.app_name or data.project_name).strip()

    if data.created_at:
        try:
            created_at_dt = datetime.fromisoformat(data.created_at)
        except Exception:
            created_at_dt = datetime.utcnow()
    else:
        created_at_dt = datetime.utcnow()

    settings_obj = BotSettings(
        project_name=data.project_name,
        employee_name=data.employee_name,
        mention_name=data.mention_name,
        avatar=None,  # если захочешь — потом сделаешь из avatar_url объект Photo
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
        # postprocessing_instruction / language_instruction оставим по дефолту модели
    )

    doc = settings_obj.model_dump()
    doc["frappe_doctype"] = data.frappe_doctype
    doc["frappe_name"] = data.frappe_name
    doc["frappe_modified"] = data.frappe_modified

    await mongo_db.bot_settings.update_one(
        {"app_name": app_name},
        {"$set": doc},
        upsert=True,
    )

    return {"ok": True, "app_name": app_name}