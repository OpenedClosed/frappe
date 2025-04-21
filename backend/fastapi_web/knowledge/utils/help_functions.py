"""Вспомогательные функции приложения Знания."""
import base64
import hashlib
import io
import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import aiofiles
import docx
import httpx
import openpyxl
import pdfplumber
from bs4 import BeautifulSoup
from fastapi import HTTPException, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile

from chats.db.mongo.schemas import ChatMessage
from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from gemini_base.gemini_init import gemini_client
# from knowledge.db.mongo.schemas import ContextEntry
from infra import settings
from knowledge.db.mongo.enums import ContextPurpose
from knowledge.db.mongo.schemas import ContextEntry, KnowledgeBase
from knowledge.utils.prompts import AI_PROMPTS
from openai_base.openai_init import openai_client

# from chats.utils.help_functions import get_knowledge_base
from .knowledge_base import KNOWLEDGE_BASE

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

def merge_external_structures(
    main_kb: Dict[str, Any],
    externals: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Возвращает **новую** базу знаний, где все внешние кусочки
    «накатываются» поверх основной.
    Приоритет: externals[0] … externals[-1] → main_kb.
    """
    merged = deepcopy(main_kb)
    for ext in externals:
        merged = deep_merge(merged, ext)
    return merged


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
    bot_context_prompt: str = "",
    ai_model: str = "gpt-4o",
) -> Dict[str, Any]:
    """
    Определяет релевантные темы, подтемы и вопросы в базе знаний по запросу пользователя.
    Шпаргалка для бота (bot_context_prompt) вставляется в system prompt.
    """
    kb_structure = {
        topic_name: {
            "subtopics": {
                sub_name: {
                    "questions": list(sub_data.get("questions", {}).keys())
                }
                for sub_name, sub_data in topic_data.get("subtopics", {}).items()
            }
        }
        for topic_name, topic_data in knowledge_base.items()
    }

    system_prompt = AI_PROMPTS["analyze_update_snippets_prompt"].format(
        kb_full_structure=json.dumps(kb_structure, ensure_ascii=False),
        bot_snippets_text=bot_context_prompt
    )

    messages = build_messages_for_model(
        system_prompt=system_prompt,
        messages_data=user_blocks,
        user_message="",  # ⬅️ теперь не дублируем bot_prompt
        model=ai_model
    )

    client, real_model = pick_model_and_client(ai_model)

    if real_model.startswith("gpt"):
        response = await client.chat.completions.create(model=real_model, messages=messages, temperature=0.1)
        raw_content = response.choices[0].message.content.strip()
    elif real_model.startswith("gemini"):
        response = await client.chat_generate(model=real_model, messages=messages, temperature=0.1)
        raw_content = response["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        response = await openai_client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.1)
        raw_content = response.choices[0].message.content.strip()

    result = _extract_json_from_gpt(raw_content)
    return {"topics": normalize_snippets_structure(result)}



def normalize_snippets_structure(
        result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Нормализовать структуру сниппетов под ожидаемый формат."""
    normalized_topics = []

    for topic in result.get("topics", []):
        if not isinstance(topic, dict):
            continue
        topic_name = topic.get("topic")
        if not isinstance(topic_name, str):
            continue

        norm_subtopics = []
        for sub in topic.get("subtopics", []):
            if isinstance(sub, str):
                norm_subtopics.append({"subtopic": sub, "questions": {}})
            elif isinstance(sub, dict):
                sub_name = sub.get("subtopic")
                questions = sub.get("questions", {})
                if isinstance(sub_name, str):
                    if isinstance(questions, list):
                        questions = {q: {"text": "", "files": []}
                                     for q in questions if isinstance(q, str)}
                    elif isinstance(questions, dict):
                        questions = {
                            q: {
                                "text": (a.get("text") if isinstance(a, dict) else ""),
                                "files": (a.get("files") if isinstance(a, dict) and isinstance(a.get("files"), list) else [])
                            }
                            for q, a in questions.items() if isinstance(q, str)
                        }
                    else:
                        questions = {}
                    norm_subtopics.append(
                        {"subtopic": sub_name, "questions": questions})

        normalized_topics.append({
            "topic": topic_name,
            "subtopics": norm_subtopics
        })

    return normalized_topics


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
    """
    Формирует патч-JSON для обновления базы знаний.
    Учитывает:
    - релевантные фрагменты из базы знаний;
    - шпаргалки из контекста (назначение: bot/both);
    - (но НЕ учитывает внешние структуры при генерации патча).
    """
    kb_doc, kb_model = await get_knowledge_base()

    # 2. Получаем шпаргалку (bot context)
    _, bot_prompt = await collect_bot_context_snippets(kb_model.context)

    # 3. Поиск релевантных тем на основе текущей БЗ и user_blocks
    snippets = await analyze_update_snippets_via_gpt(
        user_blocks=user_blocks,
        user_info=user_info,
        knowledge_base=knowledge_base,
        bot_context_prompt=bot_prompt,
        ai_model=ai_model,
    )
    snippets_list = snippets.get("topics", [])

    # 4. Извлекаем куски знаний по темам (только из основной БЗ)
    kb_snippets_text = await extract_knowledge_with_structure(
        topics=snippets_list,
        knowledge_base=knowledge_base
    )

    # 5. Финальный system prompt
    system_prompt = AI_PROMPTS["patch_body_prompt"].format(
        bot_snippets_text=bot_prompt,         # ⬅️ шпаргалка встроена
        kb_snippets_text=kb_snippets_text
    )

    # 6. Собираем сообщения
    messages = build_messages_for_model(
        system_prompt=system_prompt,
        messages_data=user_blocks,
        user_message="",  # ⬅️ bot_prompt уже в system_prompt
        model=ai_model
    )

    # 7. Запрос к LLM
    client, real_model = pick_model_and_client(ai_model)

    if real_model.startswith("gpt"):
        response = await client.chat.completions.create(
            model=real_model, messages=messages, temperature=0.1
        )
        raw_content = response.choices[0].message.content.strip()
    elif real_model.startswith("gemini"):
        response = await client.chat_generate(
            model=real_model, messages=messages, temperature=0.1
        )
        raw_content = response["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        response = await openai_client.chat.completions.create(
            model="gpt-4o", messages=messages, temperature=0.1
        )
        raw_content = response.choices[0].message.content.strip()

    return _extract_json_from_gpt(raw_content)

async def get_knowledge_base() -> Dict[str, dict]:
    """Получает базу знаний."""
    document = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
    if not document:
        raise HTTPException(404, "Knowledge base not found.")
    document.pop("_id", None)
    if document["knowledge_base"] is not None:
        kb_doc = document["knowledge_base"]
        kb_model = KnowledgeBase(**kb_doc)
    else:
        kb_doc = KNOWLEDGE_BASE
        kb_model = None
    return kb_doc, kb_model

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


# ==============================
# БЛОК: Функции работы с контекстом
# ==============================


async def generate_kb_structure_via_gpt(
    raw_text: str,
    ai_model: str = "gpt-4o"
) -> Dict[str, any]:
    """
    Отдаёт GPT‑модели «голый» текст и получает
    валидный JSON по иерархии Topic → subtopics → questions.
    """
    system_prompt = AI_PROMPTS["kb_structure_prompt"]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": raw_text}
    ]

    client, real_model = pick_model_and_client(ai_model)
    if real_model.startswith("gpt"):
        resp = await client.chat.completions.create(
            model=real_model, messages=messages, temperature=0.1
        )
        raw = resp.choices[0].message.content.strip()
    elif real_model.startswith("gemini"):
        resp = await client.chat_generate(
            model=real_model, messages=messages, temperature=0.1
        )
        raw = resp["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        resp = await client.chat.completions.create(
            model="gpt-4o", messages=messages, temperature=0.1
        )
        raw = resp.choices[0].message.content.strip()

    return _extract_json_from_gpt(raw)


async def wrap_upload_file(path: Path) -> UploadFile:
    """Считывает файл с диска и возвращает UploadFile для `parse_file()`."""
    async with aiofiles.open(path, "rb") as f:
        data = await f.read()
    return StarletteUploadFile(filename=path.name, file=io.BytesIO(data))


async def parse_url(url: str, timeout: int = 10) -> str:
    """Скачивает страницу и извлекает видимый текст."""
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (knowledge-context-bot)"}
    ) as client:
        r = await client.get(url)
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "noscript", "header", "footer", "form"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


async def cache_url_snapshot(url: str, ttl: int = settings.CONTEXT_TTL) -> str:
    """
    Возвращает текст страницы, используя Redis‑кэш.

    Ключ: `url_cache:<sha1(url)>`.
    """
    redis_key = f"url_cache:{hashlib.sha1(url.encode()).hexdigest()}"
    cached = await redis_db.get(redis_key)
    if cached:
        return cached

    parsed = await parse_url(url)
    await redis_db.set(redis_key, parsed, ex=ttl)
    return parsed

async def parse_file_from_path(path: Path) -> str:
    """Извлекает текст из файла на диске через ваш `parse_file()`."""
    upload = await wrap_upload_file(path)
    parsed = await parse_file(upload) or ""
    return parsed


async def invalidate_url_cache(url: str):
    """Удаляет кэш конкретного URL."""
    redis_key = f"url_cache:{hashlib.sha1(url.encode()).hexdigest()}"
    await redis_db.delete(redis_key)




async def get_context_entry_content(entry: ContextEntry) -> str:
    """
    Получить актуальный текст из ContextEntry.
    Для URL — с кешем, для FILE — без кеша.
    """
    if entry.type == entry.type.TEXT:
        return entry.text or ""

    if entry.type == entry.type.FILE and entry.file_path:
        return await parse_file(entry.file_path) or ""

    if entry.type == entry.type.URL and entry.url:
        content = await cache_url_snapshot(str(entry.url))
        entry.snapshot_text = content
        return content

    return ""


async def build_kb_structure_from_context_entry(entry: ContextEntry, ai_model: str = "gpt-4o") -> dict:
    """
    Преобразует содержимое ContextEntry в структуру БЗ (топик ➝ подтема ➝ Q/A).
    """
    raw = await get_context_entry_content(entry)
    return await generate_kb_structure_via_gpt(raw, ai_model)


async def collect_bot_context_snippets(entries: List[ContextEntry]) -> Tuple[List[str], str]:
    """
    Собирает текстовые фрагменты контекста с purpose = bot или both.
    Возвращает:
    - список текстов;
    - строку промпта с описанием и фрагментами.
    """
    result = []
    for entry in entries:
        if entry.purpose in {ContextPurpose.BOT, ContextPurpose.BOTH}:
            content = await get_context_entry_content(entry)
            if content:
                result.append(content.strip())

    prompt_text = (
        "The following text fragments are contextual references for the assistant.\n"
        "They serve as **background knowledge** and may be used to enhance responses,\n"
        "but should NOT be copied directly into structured outputs.\n\n"
    )
    full_prompt = prompt_text + "\n\n".join(result)
    return result, full_prompt


async def collect_kb_structures_from_context(entries: List[ContextEntry], ai_model: str = "gpt-4o") -> Tuple[List[Dict], str]:
    """
    Собирает мини-структуры БЗ из всех подходящих записей контекста.
    Возвращает:
    - список словарей (структура как в KnowledgeBase);
    - строку промпта с описанием и вставленными структурами.
    """
    structures = []
    blocks = []

    for entry in entries:
        if entry.purpose in {ContextPurpose.KB, ContextPurpose.BOTH}:
            struct = await build_kb_structure_from_context_entry(entry, ai_model=ai_model)
            if struct:
                structures.append(struct)
                blocks.append(
                    f"From: **{entry.title}**\n"
                    f"```json\n{json.dumps(struct, indent=2, ensure_ascii=False)}\n```"
                )

    prompt_text = (
        "The following structured knowledge blocks are extracted from source content\n"
        "and intended to be integrated into the main knowledge base.\n"
        "Use them as-is or adapt them to fit existing structure.\n\n"
    )
    full_prompt = prompt_text + "\n\n".join(blocks)
    return structures, full_prompt
