"""Обработчики маршрутов приложения Знания."""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from db.mongo.db_init import mongo_db

from .db.mongo.schemas import KnowledgeBase, PatchKnowledgeRequest, UpdateResponse
from .utils.help_functions import (build_gpt_message_blocks, deep_merge,
                                   diff_with_tags, generate_patch_body_via_gpt,
                                   get_knowledge_full_document)

knowledge_base_router = APIRouter()


@knowledge_base_router.get("/knowledge_base", response_model=KnowledgeBase)
async def find_knowledge_full_document():
    """Возвращает текущую базу знаний для приложения 'main'."""
    return await get_knowledge_full_document()


@knowledge_base_router.patch("/knowledge_base", response_model=UpdateResponse)
async def patch_knowledge_base(req: PatchKnowledgeRequest):
    """Частично обновляет базу знаний, обрабатывая _delete и валидируя структуру."""
    now = datetime.now()

    if req.base_data is not None:
        old_doc = req.base_data
    else:
        old_doc = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
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
    logging.info(merged_doc)

    try:
        validated = KnowledgeBase(**merged_doc)
    except ValidationError as e:
        raise HTTPException(422, f"Validation error: {e}")

    new_doc = validated.dict()
    diff = diff_with_tags(old_doc, new_doc)

    # Можно сохранить в БД, например:
    # result = await mongo_db.knowledge_collection.replace_one({"app_name": "main"}, new_doc, upsert=True)
    # if result.modified_count == 0 and not result.upserted_id:
    #     raise HTTPException(500, "Failed to update knowledge base")

    return UpdateResponse(knowledge=validated, diff=diff)


@knowledge_base_router.put("/knowledge_base/apply",
                           response_model=UpdateResponse)
async def apply_knowledge_base(new_data: KnowledgeBase):
    """Полностью заменяет базу знаний валидированными данными."""
    now = datetime.now()
    new_data.update_date = now
    new_data.app_name = "main"

    new_doc = new_data.model_dump()

    old_doc = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
    if old_doc:
        old_doc.pop("_id", None)
    else:
        old_doc = {}

    diff = diff_with_tags(old_doc, new_doc)

    result = await mongo_db.knowledge_collection.replace_one({"app_name": "main"}, new_doc, upsert=True)
    if result.modified_count == 0 and not result.upserted_id:
        raise HTTPException(500, "Failed to update knowledge base")

    return UpdateResponse(knowledge=new_data, diff=diff)


@knowledge_base_router.post("/generate_patch", response_model=Dict[str, Any])
async def generate_patch(
    user_message: str = Form(...),
    user_info: str = Form(""),
    base_data_json: Optional[str] = Form(None),
    files: List[UploadFile] = File([]),
):
    """Генерирует тело патча для базы знаний, анализируя текст пользователя и файлы."""
    if base_data_json:
        try:
            kb_data = json.loads(base_data_json)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON in 'base_data_json'")
    else:
        kb_doc = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
        if not kb_doc:
            raise HTTPException(404, "Knowledge base not found")
        kb_doc.pop("_id", None)
        kb_data = kb_doc.get("knowledge_base", {})

    user_blocks = await build_gpt_message_blocks(user_message=user_message, files=files)
    patch_body = await generate_patch_body_via_gpt(
        user_blocks=user_blocks,
        user_info=user_info,
        knowledge_base=kb_data
    )
    return patch_body
