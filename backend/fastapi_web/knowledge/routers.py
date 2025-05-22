"""Обработчики маршрутов приложения Знания."""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Request,
                     Response, UploadFile)
from fastapi_jwt_auth import AuthJWT

from auth.utils.help_functions import jwt_required, permission_required
from chats.utils.help_functions import get_bot_context
from crud_core.permissions import AdminPanelPermission
from infra import settings
from knowledge.db.mongo.enums import ContextPurpose, ContextType

from .db.mongo.schemas import (ContextEntry, KnowledgeBase,
                               PatchKnowledgeRequest, UpdateResponse)
from .utils.help_functions import (build_gpt_message_blocks, deep_merge,
                                   diff_with_tags, ensure_entry_processed,
                                   generate_patch_body_via_gpt,
                                   get_knowledge_base, save_kb_doc,
                                   save_uploaded_file)

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
    """Возвращает текущую базу знаний."""
    kb_doc, _ = await get_knowledge_base()
    return KnowledgeBase(**kb_doc)


@knowledge_base_router.patch("/knowledge_base", response_model=UpdateResponse)
@jwt_required()
@permission_required(AdminPanelPermission)
async def patch_knowledge_base(
    request: Request,
    response: Response,
    req: PatchKnowledgeRequest,
    Authorize: AuthJWT = Depends()
):
    """Применяет патч к базе знаний."""
    now = datetime.utcnow()

    if req.base_data is not None:
        old_doc = {"knowledge_base": req.base_data}
    else:
        old_doc, _ = await get_knowledge_base()

    old_kb = old_doc.get("knowledge_base", old_doc)
    patch_kb = req.patch_data.get("knowledge_base", req.patch_data)
    merged_kb = deep_merge(old_kb, patch_kb)

    new_doc = {
        "app_name": settings.APP_NAME,
        "knowledge_base": merged_kb,
        "brief_questions": old_doc.get("brief_questions", {}),
        "context": old_doc.get("context", []),
        "update_date": now,
    }

    validated = KnowledgeBase(**new_doc)
    diff = diff_with_tags(old_doc, validated.model_dump(mode="python"))

    if req.base_data is None:
        await save_kb_doc(validated.model_dump(mode="python"))

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
    """Заменяет указанные поля базы знаний."""
    now = datetime.utcnow()
    new_data.update_date = now
    new_data.app_name = settings.APP_NAME

    patch_dict = new_data.model_dump(exclude_unset=True, mode="python")
    old_doc, _ = await get_knowledge_base()

    new_doc = {**old_doc, **patch_dict}
    diff = diff_with_tags(old_doc, new_doc)

    if not await save_kb_doc(new_doc):
        raise HTTPException(500, "Failed to update knowledge base")

    return UpdateResponse(knowledge=KnowledgeBase(**new_doc), diff=diff)


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
    Authorize: AuthJWT = Depends(),
):
    """Генерирует тело патча по сообщению пользователя."""
    if base_data_json is not None:
        kb_data = json.loads(base_data_json)
    else:
        kb_doc, _ = await get_knowledge_base()
        kb_data = kb_doc.get("knowledge_base", {})

    user_blocks = await build_gpt_message_blocks(user_message=user_message, files=files)
    patch_body = await generate_patch_body_via_gpt(
        user_blocks=user_blocks,
        user_info=user_info,
        knowledge_base=kb_data,
        ai_model=ai_model,
    )
    return patch_body


# ==============================
# БЛОК: Настройки бота
# ==============================

@knowledge_base_router.get("/bot_info", response_model=Dict[str, Any])
async def get_bot_info(
    request: Request,
    response: Response,
    Authorize: AuthJWT = Depends(),
) -> Dict[str, Any]:
    """Возвращает публичную информацию о боте."""
    bot_context = await get_bot_context()
    safe_fields = {"app_name", "bot_name", "avatar", "ai_model"}
    return {k: v for k, v in bot_context.items() if k in safe_fields}


# ==============================
# БЛОК: Работа с контекстом
# ==============================

@knowledge_base_router.post("/context_entity", status_code=201)
@jwt_required()
@permission_required(AdminPanelPermission)
async def create_context_entity(
    request: Request,
    response: Response,
    type: ContextType = Form(...),
    purpose: ContextPurpose = Form(ContextPurpose.NONE),
    title: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    file: UploadFile = File(None),
    ai_model: str = Form(settings.MODEL_DEFAULT),
    Authorize: AuthJWT = Depends(),
):
    """Создать единицу контекста."""
    kb_doc, _ = await get_knowledge_base()
    kb_doc.setdefault("context", [])

    if type is ContextType.TEXT:
        if not text:
            raise HTTPException(422, "Parameter 'text' is required")
        entry = ContextEntry(type=type, purpose=purpose,
                             title=title or text[:80], text=text)

    elif type is ContextType.URL:
        if not url:
            raise HTTPException(422, "Parameter 'url' is required")
        entry = ContextEntry(
            type=type,
            purpose=purpose,
            title=title or url,
            url=url)

    elif type is ContextType.FILE:
        if not file:
            raise HTTPException(422, "File required")
        uid = uuid4().hex
        dst_path = await save_uploaded_file(file, uid)
        entry = ContextEntry(
            type=type,
            purpose=purpose,
            title=title or file.filename,
            file_path=str(dst_path))

    else:
        raise HTTPException(422, f"Unknown type: {type}")

    kb_doc["context"].append(entry.model_dump(mode="python"))
    kb_doc["update_date"] = datetime.utcnow()
    await save_kb_doc(kb_doc)
    asyncio.create_task(ensure_entry_processed(entry, ai_model))

    return entry


@knowledge_base_router.delete("/context_entity/{ctx_id}", status_code=204)
@jwt_required()
@permission_required(AdminPanelPermission)
async def delete_context_entity(
    request: Request,
    response: Response,
    ctx_id: str,
    Authorize: AuthJWT = Depends(),
):
    """Удаляет запись контекста по ID."""
    kb_doc, _ = await get_knowledge_base()
    before = len(kb_doc.get("context", []))
    kb_doc["context"] = [
        c for c in kb_doc.get(
            "context",
            []) if str(
            c.get("id")) != ctx_id]

    if len(kb_doc.get("context", [])) == before:
        raise HTTPException(404, "Context entry not found")

    kb_doc["update_date"] = datetime.utcnow()
    await save_kb_doc(kb_doc)


@knowledge_base_router.get("/context_entity")
@jwt_required()
@permission_required(AdminPanelPermission)
async def get_all_context(
    request: Request,
    response: Response,
    Authorize: AuthJWT = Depends(),
):
    """Возвращает весь контекст, дополняя недостающие данные (snapshot, структура БЗ)."""
    kb_doc, _ = await get_knowledge_base()
    context = kb_doc.get("context", [])

    updated = False
    for ctx_data in context:
        ctx_entry = ContextEntry(**ctx_data)
        is_updated = asyncio.create_task(ensure_entry_processed(ctx_entry))
        if is_updated:
            for i, item in enumerate(context):
                if item.get("id") == ctx_entry.id:
                    context[i] = ctx_entry.model_dump(mode="python")
                    updated = True
                    break

    if updated:
        kb_doc["update_date"] = datetime.utcnow()
        await save_kb_doc(kb_doc)

    return context


@knowledge_base_router.patch("/context_entity/{ctx_id}/purpose")
@jwt_required()
@permission_required(AdminPanelPermission)
async def update_context_purpose(
    request: Request,
    response: Response,
    ctx_id: str,
    new_purpose: ContextPurpose = Form(...),
    Authorize: AuthJWT = Depends(),
):
    """Меняет назначение записи контекста."""
    kb_doc, _ = await get_knowledge_base()
    entry = next(
        (c for c in kb_doc.get(
            "context",
            []) if str(
            c.get("id")) == ctx_id),
        None)

    if not entry:
        raise HTTPException(404, "Context entry not found")

    entry["purpose"] = new_purpose.value
    kb_doc["update_date"] = datetime.utcnow()
    await save_kb_doc(kb_doc)

    return entry
