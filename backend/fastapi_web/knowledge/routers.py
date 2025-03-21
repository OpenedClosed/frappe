"""Обработчики маршрутов приложения Знания."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request, Response, File, Form, HTTPException, UploadFile
from fastapi_jwt_auth import AuthJWT
from pydantic import ValidationError

from auth.utils.help_functions import jwt_required
from chats.utils.help_functions import get_bot_context
from db.mongo.db_init import mongo_db

from .db.mongo.schemas import (KnowledgeBase, PatchKnowledgeRequest,
                               UpdateResponse)
from .utils.help_functions import (build_gpt_message_blocks, deep_merge,
                                   diff_with_tags, generate_patch_body_via_gpt,
                                   get_knowledge_full_document)

knowledge_base_router = APIRouter()


@knowledge_base_router.get("/knowledge_base", response_model=KnowledgeBase)
@jwt_required()
async def find_knowledge_full_document(
    request: Request,
    response: Response,
    Authorize: AuthJWT = Depends()
):
    """Возвращает текущую базу знаний для приложения 'main'."""
    return await get_knowledge_full_document()


@knowledge_base_router.patch("/knowledge_base", response_model=UpdateResponse)
@jwt_required()
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


@knowledge_base_router.get("/bot_info", response_model=Dict[str, Any])
# @jwt_required()
async def get_bot_info(
    request: Request,
    response: Response,
    # Authorize: AuthJWT = Depends()
) -> Dict[str, Any]:
    """Возвращает безопасную информацию о боте, включая его основные настройки и используемую модель AI."""
    bot_context = await get_bot_context()
    safe_fields = {"app_name", "bot_name", "avatar", "ai_model"}
    return {key: value for key, value in bot_context.items()
            if key in safe_fields}
