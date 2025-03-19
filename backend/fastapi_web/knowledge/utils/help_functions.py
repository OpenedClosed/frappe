"""Вспомогательные функции приложения Знания."""
import base64
import io
import json
import os
import re
from typing import Any, Dict, List, Optional, Union

import docx
import openpyxl
import pdfplumber
from fastapi import HTTPException, UploadFile

from chats.db.mongo.schemas import ChatMessage
from db.mongo.db_init import mongo_db
from gemini_base.gemini_init import gemini_client
from knowledge.utils.prompts import AI_PROMPTS
from openai_base.openai_init import openai_client

# ==============================
# БЛОК: Функции сравнения и слияния
# ==============================


def mark_created_diff(val):
    """Рекурсивно помечает созданные значения тегом 'created'."""
    if isinstance(val, dict):
        return {"tag": "created", **
                {k: mark_created_diff(v) for k, v in val.items()}}
    return val


def diff_with_tags(old: dict, new: dict) -> dict:
    """Сравнивает два словаря и возвращает различия с CRUD-тегами ('created', 'updated', 'deleted')."""
    diff = {}

    for key in old.keys() | new.keys():
        if key not in old:
            diff[key] = mark_created_diff(new[key])
        elif key not in new:
            diff[key] = {"tag": "deleted", "old": old[key]}
        else:
            nested_diff = _compare_values(old[key], new[key])
            if nested_diff:
                diff[key] = nested_diff

    return diff if diff else None


def _compare_values(old_value: Any, new_value: Any) -> Any:
    """Определяет разницу между значениями и добавляет тег 'updated', если изменилось."""
    if isinstance(old_value, dict) and isinstance(new_value, dict):
        nested_diff = diff_with_tags(old_value, new_value)
        return {"tag": "updated", **nested_diff} if nested_diff else None

    return {"tag": "updated", "old": old_value,
            "new": new_value} if old_value != new_value else None


def deep_merge(original: dict, patch: dict) -> dict:
    """Рекурсивно объединяет `patch` в `original`, корректно обрабатывая удаление (`_delete`)."""
    if not isinstance(original, dict) or not isinstance(patch, dict):
        return patch

    result = original.copy()

    for key, value in patch.items():
        if isinstance(value, dict) and value.get("_delete"):
            result.pop(key, None)
        elif isinstance(value, dict):
            result[key] = deep_merge(result.get(key, {}), value)
        else:
            result[key] = value

    return result


# ==============================
# БЛОК: Генерация патч-запроса
# ==============================

def _extract_json_from_gpt(raw_content: str) -> dict:
    """Извлекает JSON из ответа GPT, возвращая пустой словарь при ошибке."""
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
    knowledge_base: Dict[str, Any],
    ai_model: str = "gpt-4o",
) -> Dict[str, Any]:
    """Определяет релевантные топики, подтемы и вопросы в базе знаний по запросу пользователя."""
    kb_structure = {}
    for topic_name, topic_data in knowledge_base.items():
        kb_structure[topic_name] = {
            "subtopics": {
                sub_name: {
                    "questions": list(
                        sub_data.get(
                            "questions",
                            {}).keys())}
                for sub_name, sub_data in topic_data.get("subtopics", {}).items()
            }
        }

    system_prompt = AI_PROMPTS["analyze_update_snippets_prompt"].format(
        kb_full_structure=json.dumps(kb_structure, ensure_ascii=False)
    )

    messages = build_messages_for_model(
        system_prompt=system_prompt,
        messages_data=user_blocks,
        user_message="",
        model=ai_model
    )

    client, real_model = pick_model_and_client(ai_model)

    if real_model.startswith("gpt"):
        response = await client.chat.completions.create(model=real_model, messages=messages, temperature=0.1)
        raw_content = response.choices[0].message.content.strip()
    elif real_model.startswith("gemini"):
        response = await client.chat_generate(model=real_model, messages=messages, temperature=0.1)
        raw_content = response["candidates"][0]["content"]["parts"][0]["text"].strip(
        )
    else:
        response = await openai_client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.1)
        raw_content = response.choices[0].message.content.strip()

    # print("=== RAW RESULT SNIPPETS ===\n", raw_content)
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
    """Возвращает из базы знаний структуру по списку (topic/subtopic/questions)."""
    if knowledge_base is None:
        knowledge_base = await get_knowledge_full_document()

    extracted_data = {}
    for item in topics:
        topic_name = item.get("topic", "")
        subtopics = item.get("subtopics", [])
        if topic_name not in knowledge_base:
            continue

        if topic_name not in extracted_data:
            extracted_data[topic_name] = {"subtopics": {}}

        topic_data = knowledge_base[topic_name]
        subs = topic_data.get("subtopics", {})

        if subtopics:
            for subtopic_item in subtopics:
                subtopic_name = subtopic_item.get("subtopic")
                questions = subtopic_item.get("questions", [])
                if subtopic_name and subtopic_name in subs:
                    if subtopic_name not in extracted_data[topic_name]["subtopics"]:
                        extracted_data[topic_name]["subtopics"][subtopic_name] = {
                            "questions": {}}
                    sub_data = subs[subtopic_name]
                    if questions:
                        for q_text in questions:
                            if q_text in sub_data.get("questions", {}):
                                ans_text = sub_data["questions"][q_text]
                                extracted_data[topic_name]["subtopics"][subtopic_name]["questions"][q_text] = ans_text
                    else:
                        extracted_data[topic_name]["subtopics"][subtopic_name]["questions"] = sub_data.get(
                            "questions", {}).copy()
        else:
            for sub_name, sub_data in subs.items():
                if sub_name not in extracted_data[topic_name]["subtopics"]:
                    extracted_data[topic_name]["subtopics"][sub_name] = {
                        "questions": {}}
                extracted_data[topic_name]["subtopics"][sub_name]["questions"] = sub_data.get(
                    "questions", {}).copy()

    return extracted_data if extracted_data else {}


def pick_model_and_client(model: str):
    """Определяет, какой клиент (OpenAI/Gemini) использовать, и возвращает (client, real_model)."""
    if model.startswith("gpt"):
        return openai_client, model
    elif model.startswith("gemini"):
        return gemini_client, model
    return openai_client, "gpt-4o"


def build_messages_for_model(
    system_prompt: Optional[str],
    messages_data: Union[List[ChatMessage], List[Dict[str, Any]]],
    user_message: str,
    model: str
) -> List[Dict[str, Any]]:
    """Генерирует список `messages` в правильном формате для OpenAI (GPT) и Gemini."""
    messages = []

    if system_prompt:
        messages.append({
            "role": "system" if model.startswith("gpt") else "user",
            "content": system_prompt
        })

    for msg in messages_data:
        if isinstance(msg, ChatMessage):
            sender_role = extract_english_value(msg.sender_role.value)
            content = msg.message
        elif isinstance(msg, dict):
            sender_role = extract_english_value(msg.get("sender_role", "user"))
            content = msg
        else:
            continue

        role = "assistant" if sender_role.lower() in [
            "ai assistant", "assistant", "consultant"] else "user"

        structured_content = []

        if isinstance(content, str):
            structured_content.append({"type": "text", "text": content})
        elif isinstance(content, dict):
            if "text" in content:
                structured_content.append(
                    {"type": "text", "text": content["text"]})
            elif "image_url" in content:
                structured_content.append(
                    {"type": "image_url", "image_url": content["image_url"]})
        if structured_content:
            if model.startswith("gpt"):
                messages.append({"role": role, "content": structured_content})

            elif model.startswith("gemini"):
                gemini_parts = []
                for block in structured_content:
                    if block["type"] == "text":
                        gemini_parts.append({"text": block["text"]})
                    elif block["type"] == "image_url":
                        gemini_parts.append({
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                # Base64-кодирование
                                "data": block["image_url"]["url"].split(",")[1]
                            }
                        })
                if gemini_parts:
                    messages.append({"role": role, "parts": gemini_parts})

    if user_message.strip() and not structured_content:
        messages.append({"role": "user", "content": user_message})

    return messages


def extract_english_value(value: Any) -> Any:
    """Пытается извлечь английскую версию строк из JSON. Возвращает исходное значение при ошибках."""
    if isinstance(value, str):
        try:
            parsed_value = json.loads(value)
            return parsed_value.get("en", value)
        except (json.JSONDecodeError, TypeError):
            return value
    if isinstance(value, dict):
        return value.get("en", value)
    if isinstance(value, list):
        return [extract_english_value(item) for item in value]
    return value


async def generate_patch_body_via_gpt(
    user_blocks: List[Dict[str, Any]],
    user_info: str,
    knowledge_base: Dict[str, Any],
    ai_model: str = "gpt-4o",
) -> Dict[str, Any]:
    """Формирует патч-JSON для обновления базы знаний, извлекая релевантные сниппеты."""
    snippets = await analyze_update_snippets_via_gpt(user_blocks, user_info, knowledge_base, ai_model)
    snippets_list = snippets.get("topics", [])
    kb_snippets_text = await extract_knowledge_with_structure(topics=snippets_list, knowledge_base=knowledge_base)

    system_prompt = AI_PROMPTS["patch_body_prompt"].format(
        kb_snippets_text=kb_snippets_text)
    messages = build_messages_for_model(
        system_prompt, user_blocks, "", ai_model)

    client, real_model = pick_model_and_client(ai_model)

    if real_model.startswith("gpt"):
        response = await client.chat.completions.create(model=real_model, messages=messages, temperature=0.1)
        raw_content = response.choices[0].message.content.strip()
    elif real_model.startswith("gemini"):
        response = await client.chat_generate(model=real_model, messages=messages, temperature=0.1)
        raw_content = response["candidates"][0]["content"]["parts"][0]["text"].strip(
        )
    else:
        response = await openai_client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.1)
        raw_content = response.choices[0].message.content.strip()

    # print("=== RAW PATCH RESULT ===\n", raw_content)
    patch_result = _extract_json_from_gpt(raw_content)
    return patch_result


# ==============================
# БЛОК: Функции парсинга PDF, DOCX, XLSX =====
# ==============================

async def parse_pdf(file: UploadFile) -> str:
    """Извлекает текст из PDF-файла."""
    file_bytes = await file.read()
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        return "\n".join(
            [page.extract_text() or "" for page in pdf.pages]).strip()


async def parse_docx(file: UploadFile) -> str:
    """Извлекает текст из DOCX-файла."""
    file_bytes = await file.read()
    document = docx.Document(io.BytesIO(file_bytes))
    return "\n".join([p.text for p in document.paragraphs]).strip()


async def parse_excel(file: UploadFile) -> str:
    """Извлекает текст из XLS/XLSX-файла."""
    file_bytes = await file.read()
    workbook = openpyxl.load_workbook(io.BytesIO(file_bytes))
    return "\n".join([
        " ".join([str(cell) if cell else "" for cell in row])
        for sheet in workbook.worksheets
        for row in sheet.iter_rows(values_only=True)
    ]).strip()


async def parse_file(upload_file: UploadFile) -> Optional[str]:
    """Определяет обработчик для файла по расширению и возвращает текстовое содержимое."""
    ext = os.path.splitext(upload_file.filename.lower())[1]

    parsers = {
        ".pdf": parse_pdf,
        ".docx": parse_docx,
        ".xlsx": parse_excel,
        ".xls": parse_excel
    }

    if ext in parsers:
        return await parsers[ext](upload_file)

    return None if ext in (".png", ".jpg", ".jpeg") else None


# ==============================
# БЛОК: Формирования блоков сообщений =====
# ==============================

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

    user_message = user_message.strip()
    if user_message:
        blocks.append({"type": "text", "text": user_message})

    for file in files:
        filename = file.filename
        extension = os.path.splitext(filename)[1].lower()

        if extension in (".pdf", ".docx", ".xlsx", ".xls"):
            parsed_text = await parse_file(file)
            if parsed_text:
                blocks.append({
                    "type": "text",
                    "text": f"[Файл: {filename}]\n{parsed_text}"
                })

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
            blocks.append({
                "type": "text",
                "text": f"[Файл: {filename}] Unknown format, skipped."
            })

    return blocks
