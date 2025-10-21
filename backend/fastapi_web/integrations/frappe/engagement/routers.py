from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .utils.help_functions import (
    sync_one_by_chat_id,
    sync_recent,
    sync_recent_users,   # NEW
)

engagement_router = APIRouter()


class SyncByChatIdRequest(BaseModel):
    chat_id: str


class SyncRecentRequest(BaseModel):
    minutes: int = Field(default=10, ge=1, le=1440)
    limit: Optional[int] = Field(default=None)  # None => без лимита


class SyncRecentUsersRequest(BaseModel):
    minutes: int = Field(default=10, ge=1, le=1440)
    limit: Optional[int] = Field(default=None)


@engagement_router.post("/sync_by_chat_id")
async def engagement_sync_by_chat_id(payload: SyncByChatIdRequest):
    print(f"[engagement_sync_by_chat_id] payload={payload.model_dump()}")
    res = await sync_one_by_chat_id(payload.chat_id)
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail="Chat not found")
    return res


@engagement_router.post("/sync_recent")
async def engagement_sync_recent(payload: SyncRecentRequest):
    # лимит внутри sync_recent временно форсится на 50 — см. реализацию
    print(
        f"[engagement_sync_recent] start minutes={payload.minutes} "
        f"limit={'NO_LIMIT' if payload.limit is None else payload.limit}"
    )
    res = await sync_recent(minutes=payload.minutes, limit=payload.limit)
    print(
        f"[engagement_sync_recent] done result=created:{res.get('created',0)} "
        f"updated:{res.get('updated',0)} scanned:{res.get('scanned',0)}"
    )
    return res


# -------- NEW: синк по пользователям (создаём кейсы из Mongo-пользователей на Deals) --------
@engagement_router.post("/sync_recent_users")
async def engagement_sync_recent_users(payload: SyncRecentUsersRequest):
    print(
        f"[engagement_sync_recent_users] start minutes={payload.minutes} "
        f"limit={'NO_LIMIT' if payload.limit is None else payload.limit}"
    )
    res = await sync_recent_users(minutes=payload.minutes, limit=payload.limit)
    print(
        f"[engagement_sync_recent_users] done created:{res.get('created',0)} "
        f"updated:{res.get('updated',0)} scanned:{res.get('scanned',0)}"
    )
    return res