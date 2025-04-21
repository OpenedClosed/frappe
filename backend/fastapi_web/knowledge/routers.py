"""Обработчики маршрутов приложения Знания."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiofiles
from fastapi import (APIRouter, Depends, File, Form, HTTPException, Request,
                     Response, UploadFile)
from fastapi_jwt_auth import AuthJWT
from pydantic import HttpUrl, ValidationError

from auth.utils.help_functions import jwt_required, permission_required
from chats.utils.help_functions import get_bot_context
from crud_core.permissions import AdminPanelPermission
from db.mongo.db_init import mongo_db
from infra import settings
from knowledge.db.mongo.enums import ContextPurpose, ContextType

from .db.mongo.schemas import (ContextEntry, KnowledgeBase,
                               PatchKnowledgeRequest, UpdateResponse)
from .utils.help_functions import (build_gpt_message_blocks,
                                   cache_url_snapshot, deep_merge,
                                   diff_with_tags, generate_patch_body_via_gpt,
                                   get_knowledge_full_document, get_knowledge_base)

knowledge_base_router = APIRouter()


# ==============================
# БЛОК: База знаний
# ==============================


@knowledge_base_router.get("/knowledge_base", response_model=KnowledgeBase)
@jwt_required()
@permission_required(AdminPanelPermission)
async def find_knowledge_full_document(
    request: Request,
    response: Response,
    Authorize: AuthJWT = Depends()
):
    """Возвращает текущую базу знаний для приложения 'main'."""
    return await get_knowledge_full_document()


@knowledge_base_router.patch("/knowledge_base", response_model=UpdateResponse)
@jwt_required()
@permission_required(AdminPanelPermission)
async def patch_knowledge_base(
    request: Request,
    response: Response,
    req: PatchKnowledgeRequest,
    Authorize: AuthJWT = Depends()
):
    """Частично обновляет базу знаний, обрабатывая _delete и валидируя структуру."""
    now = datetime.now()

    old_doc = {"knowledge_base": req.base_data} if req.base_data else await mongo_db.knowledge_collection.find_one({"app_name": "main"})
    if not old_doc:
        raise HTTPException(404, "Knowledge base not found")

    old_doc.pop("_id", None)
    old_knowledge = old_doc.get("knowledge_base", old_doc)
    patch_knowledge = req.patch_data.get("knowledge_base", req.patch_data)

    merged_data = deep_merge(old_knowledge, patch_knowledge)
    merged_doc = {
        "app_name": "main",
        "knowledge_base": merged_data if isinstance(merged_data, dict) else {},
        "brief_questions": old_doc.get("brief_questions", {}),
        "update_date": now
    }

    try:
        validated = KnowledgeBase(**merged_doc)
    except ValidationError as e:
        raise HTTPException(422, f"Validation error: {e}")

    new_doc = validated.dict()
    diff = diff_with_tags(old_doc, new_doc)

    return UpdateResponse(knowledge=validated, diff=diff)


@knowledge_base_router.put("/knowledge_base/apply",
                           response_model=UpdateResponse)
@jwt_required()
@permission_required(AdminPanelPermission)
async def apply_knowledge_base(
    request: Request,
    response: Response,
    new_data: KnowledgeBase,
    Authorize: AuthJWT = Depends()
):
    """Полностью заменяет базу знаний валидированными данными."""
    now = datetime.now()
    new_data.update_date = now
    new_data.app_name = "main"

    new_doc = new_data.model_dump()
    old_doc = await mongo_db.knowledge_collection.find_one({"app_name": "main"}) or {}

    old_doc.pop("_id", None)
    diff = diff_with_tags(old_doc, new_doc)

    result = await mongo_db.knowledge_collection.replace_one({"app_name": "main"}, new_doc, upsert=True)
    if result.modified_count == 0 and not result.upserted_id:
        raise HTTPException(500, "Failed to update knowledge base")

    return UpdateResponse(knowledge=new_data, diff=diff)


@knowledge_base_router.post("/generate_patch", response_model=Dict[str, Any])
@jwt_required()
@permission_required(AdminPanelPermission)
async def generate_patch(
    request: Request,
    response: Response,
    user_message: str = Form(...),
    user_info: str = Form(""),
    base_data_json: Optional[str] = Form(None),
    files: List[UploadFile] = File([]),
    ai_model: str = Form("gpt-4o"),
    Authorize: AuthJWT = Depends()
):
    """Генерирует тело патча для базы знаний, анализируя текст пользователя и файлы."""
    if base_data_json:
        try:
            kb_data = json.loads(base_data_json)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON in 'base_data_json'")
    else:
        kb_doc = await mongo_db.knowledge_collection.find_one({"app_name": "main"}) or {}
        kb_doc.pop("_id", None)
        kb_data = kb_doc.get("knowledge_base", {})

    user_blocks = await build_gpt_message_blocks(user_message=user_message, files=files)
    patch_body = await generate_patch_body_via_gpt(
        user_blocks=user_blocks,
        user_info=user_info,
        knowledge_base=kb_data,
        ai_model=ai_model
    )
    return patch_body


# ==============================
# БЛОК: Настройки бота
# ==============================



@knowledge_base_router.get("/bot_info", response_model=Dict[str, Any])
async def get_bot_info(
    request: Request,
    response: Response,
    Authorize: AuthJWT = Depends()
) -> Dict[str, Any]:
    """Возвращает безопасную информацию о боте, включая его основные настройки и используемую модель AI."""
    bot_context = await get_bot_context()
    safe_fields = {"app_name", "bot_name", "avatar", "ai_model"}
    return {key: value for key, value in bot_context.items()
            if key in safe_fields}



# ==============================
# БЛОК: Работа с контекстом
# ==============================


# ───────────────────────── CREATE ──────────────────────────
@knowledge_base_router.post(
    "/context_entity",
    response_model=ContextEntry,
    status_code=201
)
@jwt_required()
@permission_required(AdminPanelPermission)
async def create_context_entity(
    request: Request,
    response: Response,
    type: ContextType = Form(...),
    purpose: ContextPurpose = Form(ContextPurpose.NONE),
    title: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    url: Optional[HttpUrl] = Form(None),
    file: UploadFile = File(None),
    Authorize: AuthJWT = Depends(),
):
    kb_doc, _ = await get_knowledge_base()
    kb_doc.setdefault("context", [])

    # ——— единственное место, где используем Pydantic‑модель  ———
    if type is ContextType.TEXT:
        if not text:
            raise HTTPException(422, "Параметр 'text' обязателен")
        entry = ContextEntry(
            type=type,
            purpose=purpose,
            title=title or text[:80],
            text=text,
        )

    elif type is ContextType.URL:
        if not url:
            raise HTTPException(422, "Параметр 'url' обязателен")
        entry = ContextEntry(
            type=type,
            purpose=purpose,
            title=title or str(url),
            url=url,
            snapshot_text=await cache_url_snapshot(str(url)),
        )

    elif type is ContextType.FILE:
        if not file:
            raise HTTPException(422, "Файл обязателен")
        uid = uuid4().hex
        dst_dir = Path(settings.CONTEXT_PATH) / uid
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_path = dst_dir / file.filename
        async with aiofiles.open(dst_path, "wb") as f:
            await f.write(await file.read())
        entry = ContextEntry(
            type=type,
            purpose=purpose,
            title=title or file.filename,
            file_path=str(dst_path),
        )
    else:
        raise HTTPException(422, f"Неизвестный тип: {type}")

    kb_doc["context"].append(entry.model_dump(mode="python"))
    kb_doc["update_date"] = datetime.utcnow()
    await mongo_db.knowledge_collection.replace_one({"app_name": "main"}, kb_doc)

    return entry                     # FastAPI выдаст как ContextEntry


# ───────────────────────── DELETE ─────────────────────────
@knowledge_base_router.delete("/context_entity/{ctx_id}", status_code=204)
@jwt_required()
@permission_required(AdminPanelPermission)
async def delete_context_entity(
    request: Request,
    response: Response,
    ctx_id: str,
    Authorize: AuthJWT = Depends(),
):
    kb_doc, _ = await get_knowledge_base()

    before = len(kb_doc.get("context", []))
    kb_doc["context"] = [c for c in kb_doc["context"] if str(c.get("id")) != ctx_id]
    if len(kb_doc["context"]) == before:
        raise HTTPException(404, "Context entry not found")

    kb_doc["update_date"] = datetime.utcnow()
    await mongo_db.knowledge_collection.replace_one({"app_name": "main"}, kb_doc)


# ───────────────────────── GET ALL ────────────────────────
@knowledge_base_router.get("/context_entity", )
@jwt_required()
@permission_required(AdminPanelPermission)
async def get_all_context(
    request: Request,
    response: Response,
    Authorize: AuthJWT = Depends(),
):
    kb_doc, _ = await get_knowledge_base()


    updated = False
    for ctx in kb_doc.get("context", []):
        if ctx["type"] == ContextType.URL and not ctx.get("snapshot_text"):
            ctx["snapshot_text"] = await cache_url_snapshot(str(ctx["url"]))
            updated = True
    if updated:
        kb_doc["update_date"] = datetime.utcnow()
        await mongo_db.knowledge_collection.replace_one({"app_name": "main"}, kb_doc)
    print(kb_doc["context"])
    print("отданные id", [doc["id"] for doc in kb_doc["context"]])
    return kb_doc["context"]       # <- raw list; FastAPI валидирует


# ───────────────────────── PATCH purpose ───────────────────
@knowledge_base_router.patch(
    "/context_entity/{ctx_id}/purpose",
)
@jwt_required()
@permission_required(AdminPanelPermission)
async def update_context_purpose(
    request: Request,
    response: Response,
    ctx_id: str,
    new_purpose: ContextPurpose = Form(...),
    Authorize: AuthJWT = Depends(),
):
    kb_doc, _ = await get_knowledge_base()
    print("полученный id", ctx_id)

    entry = next((c for c in kb_doc["context"] if str(c.get("id")) == ctx_id), None)
    if not entry:
        raise HTTPException(404, "Context entry not found")

    entry["purpose"] = new_purpose.value
    kb_doc["update_date"] = datetime.utcnow()
    await mongo_db.knowledge_collection.replace_one({"app_name": "main"}, kb_doc)

    return entry                    # <- raw dict; FastAPI валидирует
