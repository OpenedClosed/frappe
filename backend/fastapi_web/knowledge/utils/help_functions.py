"""Вспомогательные функции приложения Знания."""
import base64
import io
import json
import os
import re
from typing import Any, Dict, List, Optional

import docx
import openpyxl
import pdfplumber
from fastapi import HTTPException, UploadFile

from db.mongo.db_init import mongo_db
from knowledge.utils.prompts import AI_PROMPTS
from openai_base.openai_init import openai_client

# ===== Функции сравнения и слияния =====


def mark_created_diff(val):
    """Рекурсивно помечает созданные значения с тегом 'created'."""
    if isinstance(val, dict):
        result = {"tag": "created"}
        for k, v in val.items():
            result[k] = mark_created_diff(v) if isinstance(v, dict) else v
        return result
    return val


def diff_with_tags(old: dict, new: dict) -> dict:
    """Сравнивает два словаря и возвращает различия с CRUD-тегами (created, updated, deleted)."""
    diff = {}
    for key in set(old.keys()) | set(new.keys()):
        if key not in old:
            diff[key] = mark_created_diff(new[key])
        elif key not in new:
            diff[key] = {"tag": "deleted", "old": old[key]}
        else:
            if isinstance(old[key], dict) and isinstance(new[key], dict):
                nested = diff_with_tags(old[key], new[key])
                if nested:
                    diff[key] = {"tag": "updated", **nested}
            elif old[key] != new[key]:
                diff[key] = {
                    "tag": "updated",
                    "old": old[key],
                    "new": new[key]}
    return diff


def deep_merge(original: dict, patch: dict) -> dict:
    """Рекурсивно сливает patch в original, корректно обрабатывая удаление (_delete)."""
    if not isinstance(original, dict) or not isinstance(patch, dict):
        return patch

    result = original.copy()

    for key, value in patch.items():
        if isinstance(value, dict) and value.get("_delete") is True:
            result.pop(key, None)
            continue

        if isinstance(value, dict):
            orig_val = result.get(key, {})
            if isinstance(orig_val, dict):
                result[key] = deep_merge(orig_val, value)
            else:
                result[key] = value
        elif isinstance(value, list):
            if isinstance(result.get(key), list):
                result[key] = value
            else:
                result[key] = value
        else:
            result[key] = value

    return result


# ===== Генерация патч запроса =====

def _extract_json_from_gpt(raw_content: str) -> dict:
    """Извлекает JSON из текста, возвращая пустой словарь при ошибках."""
    match = re.search(r"\{.*\}", raw_content, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}

async def analyze_update_snippets_via_gpt(
    user_blocks: List[Dict[str, Any]],
    user_info: str,
    knowledge_base: Dict[str, Any]
) -> Dict[str, Any]:
    """Ищет релевантные топики, подтемы и вопросы в базе знаний по сообщению пользователя."""
    snippet_lines = []
    for topic_name, topic_data in knowledge_base.items():
        line = f"Topic: {topic_name}"
        subtopics = topic_data.get("subtopics", {})
        if subtopics:
            sub_lines = []
            for subtopic_name, subtopic_data in subtopics.items():
                questions = subtopic_data.get("questions", {})
                q_keys = ", ".join(
                    questions.keys()) if questions else "No questions"
                sub_lines.append(
                    f"Subtopic: {subtopic_name} (Questions: {q_keys})")
            line += " | " + " || ".join(sub_lines)
        snippet_lines.append(line)
    kb_full_structure = "\n".join(snippet_lines)

    system_prompt = AI_PROMPTS["analyze_update_snippets_prompt"].format(
        kb_full_structure=kb_full_structure)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_blocks}
    ]

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.1
    )
    raw_content = response.choices[0].message.content.strip()
    print("=== RAW RESULT SNIPPETS ===\n", raw_content)

    result = _extract_json_from_gpt(raw_content)
    return {"topics": result.get("topics", [])}


async def get_knowledge_full_document():
    """Возвращает текущую базу знаний для приложения 'main'."""
    document = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
    if not document:
        raise HTTPException(404, "Knowledge base not found")
    document.pop("_id", None)
    return document


async def extract_knowledge_with_structure(
    topics: List[Dict[str, Optional[str]]],
    user_message: Optional[str] = None,
    knowledge_base: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Возвращает из базы знаний структуру по списку тем, подтем и вопросам."""
    if knowledge_base is None:
        knowledge_base = await get_knowledge_full_document()

    extracted_data = {}
    for item in topics:
        topic_name = item.get("topic", "")
        subtopics = item.get("subtopics", [])

        if topic_name not in knowledge_base:
            continue
        topic_data = knowledge_base[topic_name]
        subs = topic_data.get("subtopics", {})

        if topic_name not in extracted_data:
            extracted_data[topic_name] = {"subtopics": {}}

        if subtopics:
            for subtopic_item in subtopics:
                subtopic_name = subtopic_item.get("subtopic", None)
                questions = subtopic_item.get("questions", [])
                if subtopic_name and subtopic_name in subs:
                    sub_data = subs[subtopic_name]
                    if subtopic_name not in extracted_data[topic_name]["subtopics"]:
                        extracted_data[topic_name]["subtopics"][subtopic_name] = {
                            "questions": {}}
                    if questions:
                        for q_text in questions:
                            if q_text in sub_data.get("questions", {}):
                                ans_text = sub_data["questions"][q_text]
                                extracted_data[topic_name]["subtopics"][subtopic_name]["questions"][q_text] = ans_text
                    else:
                        extracted_data[topic_name]["subtopics"][subtopic_name]["questions"] = sub_data.get(
                            "questions", {}).copy()
        else:
            for subtopic_name, sub_data in subs.items():
                if subtopic_name not in extracted_data[topic_name]["subtopics"]:
                    extracted_data[topic_name]["subtopics"][subtopic_name] = {
                        "questions": {}}
                extracted_data[topic_name]["subtopics"][subtopic_name]["questions"] = sub_data.get(
                    "questions", {}).copy()

    return extracted_data if extracted_data else {}


async def generate_patch_body_via_gpt(
    user_blocks: List[Dict[str, Any]],
    user_info: str,
    knowledge_base: Dict[str, Any]
) -> Dict[str, Any]:
    """Формирует патч для базы знаний через GPT, извлекая релевантные сниппеты и создавая финальный JSON."""

    # print("=== KNOWLEDGE ===\n", snippets_list)
    print(knowledge_base)

    snippets = await analyze_update_snippets_via_gpt(
        user_blocks=user_blocks,
        user_info=user_info,
        knowledge_base=knowledge_base
    )
    snippets_list = snippets.get("topics", [])
    # print("=== SNIPPETS ===\n", snippets_list)

    kb_snippets_text = await extract_knowledge_with_structure(topics=snippets_list, knowledge_base=knowledge_base)
    system_prompt = AI_PROMPTS["patch_body_prompt"].format(
        kb_snippets_text=kb_snippets_text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_blocks}
    ]

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.1
    )
    raw_content = response.choices[0].message.content.strip()
    print("=== RAW PATCH RESULT ===\n", raw_content)

    patch_result = _extract_json_from_gpt(raw_content)
    # print("=== PARSED PATCH RESULT ===\n", patch_result)
    return patch_result


# ===== Функции парсинга PDF, DOCX, XLSX =====


async def parse_pdf(file: UploadFile) -> str:
    """Читает PDF в байтовом виде и извлекает текст при помощи pdfplumber."""
    file_bytes = await file.read()
    text_content = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_content += page_text + "\n"
    return text_content.strip()


async def parse_docx(file: UploadFile) -> str:
    """Читает DOCX и извлекает параграфы при помощи python-docx."""
    file_bytes = await file.read()
    document = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in document.paragraphs]
    return "\n".join(paragraphs).strip()


async def parse_excel(file: UploadFile) -> str:
    """Читает XLS/XLSX и извлекает данные построчно."""
    file_bytes = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
    text_content = []
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            row_text = " ".join([str(cell) if cell else "" for cell in row])
            text_content.append(row_text)
    return "\n".join(text_content).strip()


async def parse_file(upload_file: UploadFile) -> Optional[str]:
    """
    Определяет по расширению файла, как его парсить.
    Возвращает текст (str) или None, если это изображение (только base64)
    или неизвестный формат.
    """
    filename = upload_file.filename.lower()

    if filename.endswith(".pdf"):
        return await parse_pdf(upload_file)

    elif filename.endswith(".docx"):
        return await parse_docx(upload_file)

    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
        return await parse_excel(upload_file)

    elif filename.endswith(".png") or filename.endswith(".jpg") or filename.endswith(".jpeg"):
        # Возвращаем None, если хотим передавать изображения сразу в
        # base64-блок (без OCR)
        return None

    # Любые иные форматы — возвращаем None или обрабатываем по желанию
    return None


# -------------------------------------------------------------------
# 3. Формируем контент-блоки для GPT ("type": "text" / "type": "image_url")
# -------------------------------------------------------------------

async def build_gpt_message_blocks(
    user_message: str,
    files: List[UploadFile]
) -> List[Dict[str, Any]]:
    """
    Принимает:
      - строку user_message (текст от пользователя);
      - список файлов (может быть пустым).
    Возвращает список блоков контента для role="user":
    [
      {"type": "text", "text": "..."},
      {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
      ...
    ]
    """
    blocks: List[Dict[str, Any]] = []

    # (1) Добавляем текст пользователя (если он не пуст)
    user_message = user_message.strip()
    if user_message:
        blocks.append({"type": "text", "text": user_message})

    # (2) Перебираем файлы
    for file in files:
        filename = file.filename
        extension = os.path.splitext(filename)[1].lower()

        # Парсим текстовые форматы
        if extension in (".pdf", ".docx", ".xlsx", ".xls"):
            parsed_text = await parse_file(file)
            if parsed_text:
                blocks.append({
                    "type": "text",
                    "text": f"[Файл: {filename}]\n{parsed_text}"
                })

        # Для изображений — оборачиваем в base64
        elif extension in (".png", ".jpg", ".jpeg"):
            file_bytes = await file.read()
            base64_data = base64.b64encode(file_bytes).decode("utf-8")
            # base64_data = b'pass'
            blocks.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_data}"
                }
            })

        else:
            # Неизвестный формат
            blocks.append({
                "type": "text",
                "text": f"[Файл: {filename}] Unknown format, skipped."
            })

    return blocks
