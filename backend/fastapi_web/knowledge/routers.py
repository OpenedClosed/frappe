"""Обработчики маршрутов приложения База знаний."""
from chats.ws.ws_handlers import extract_knowledge
from fastapi import HTTPException, Request, status
from .db.mongo.schemas import DetermineChangesRequest, KnowledgeBase, PatchKnowledgeRequest, UpdateResponse
from fastapi import Query, Request
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request
from chats.utils.commands import COMMAND_HANDLERS, command_handler

from db.mongo.db_init import mongo_db
from db.redis.db_init import redis_db
from infra import settings
import json
from openai_base.openai_init import openai_client
import re
from pydantic import BaseModel, Field, field_validator


knowledge_base_router = APIRouter()


def mark_created_diff(val):
    """Рекурсивно помечает созданные значения с тегом 'created'."""
    if isinstance(val, dict):
        result = {"tag": "created"}
        for k, v in val.items():
            result[k] = mark_created_diff(v) if isinstance(v, dict) else v
        return result
    return val



def diff_with_tags(old: dict, new: dict) -> dict:
    """Сравнивает два словаря и возвращает различия с CRUD-тегами (created, updated, deleted), без дополнительной вложенности."""
    diff = {}
    for key in set(old.keys()) | set(new.keys()):
        if key not in old:
            diff[key] = {"tag": "created"}
        elif key not in new:
            diff[key] = {"tag": "deleted", "old": old[key]}
        else:
            if isinstance(old[key], dict) and isinstance(new[key], dict):
                nested = diff_with_tags(old[key], new[key])
                if nested:
                    # Если обнаружены вложенные изменения, помечаем ключ как updated и объединяем изменения
                    d = {"tag": "updated"}
                    d.update(nested)
                    diff[key] = d
            else:
                if old[key] != new[key]:
                    diff[key] = {"tag": "updated", "old": old[key], "new": new[key]}
    return diff

# def deep_merge(original: dict, patch: dict) -> dict:
#     """Рекурсивно сливает patch в original, удаляя ключи при значении None или при наличии _delete/_deleted: true."""
#     result = original.copy()
#     for key, value in patch.items():
#         if isinstance(value, dict) and (value.get("_delete") is True or value.get("_deleted") is True):
#             if key in result:
#                 del result[key]
#             continue
#         if value is None:
#             if key in result:
#                 del result[key]
#         elif isinstance(value, dict):
#             orig_val = result.get(key, {})
#             if not isinstance(orig_val, dict):
#                 orig_val = {}
#             result[key] = deep_merge(orig_val, value)
#         else:
#             result[key] = value
#     return result

def deep_merge(original: dict, patch: dict) -> dict:
    """
    Рекурсивно сливает patch в original, корректно обрабатывая удаление (_delete, _deleted).
    - Если `_delete: true`, удаляет соответствующий ключ.
    - Если новый элемент - словарь, рекурсивно объединяет.
    - Если новый элемент - список, заменяет список полностью.
    - В остальных случаях заменяет значение.
    """
    if not isinstance(original, dict) or not isinstance(patch, dict):
        return patch  # Если один из них не dict, просто заменяем

    result = original.copy()

    for key, value in patch.items():
        # Если _delete true — удаляем ключ
        if isinstance(value, dict) and value.get("_delete") is True:
            result.pop(key, None)
            continue

        if isinstance(value, dict):
            orig_val = result.get(key, {})
            if isinstance(orig_val, dict):
                result[key] = deep_merge(orig_val, value)
            else:
                result[key] = value  # Если было строкой или числом — заменяем на словарь
        elif isinstance(value, list):
            result[key] = value  # Списки не мерджим, а заменяем полностью
        else:
            result[key] = value  # Простые значения заменяем

    return result


@knowledge_base_router.get("/knowledge_base", response_model=KnowledgeBase)
async def get_knowledge_base():
    """Возвращает текущую базу знаний для приложения 'main'."""
    document = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
    if not document:
        raise HTTPException(404, "Knowledge base not found")
    document.pop("_id", None)
    return document

import logging

@knowledge_base_router.patch("/knowledge_base", response_model=UpdateResponse)
async def patch_knowledge_base(req: PatchKnowledgeRequest):
    """Частично обновляет базу знаний с учётом удаления по ключу _delete и валидации структуры."""
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
    logging.info('===========================HERE===========================')
    logging.info('===========================OLD===========================')
    logging.info(old_knowledge)
    logging.info('===========================PATCH===========================')
    logging.info(patch_knowledge)
    logging.info('===========================RESULT===========================')
    logging.info(merged_data)
    merged_doc = {
        "app_name": "main",
        "knowledge_base": merged_data if isinstance(merged_data, dict) else {},
        "brief_questions": old_doc.get("brief_questions", {}),
        "update_date": now
    }
    logging.info(merged_doc)
    # print(merged_doc)

    # merged_doc["app_name"] = "main"
    try:
        # validated = KnowledgeBase(**{k: v for k, v in merged_doc.items() if k != "app_name"})
        validated = KnowledgeBase(**merged_doc)
    except Exception as e:
        raise HTTPException(422, f"Validation error: {e}")
    new_doc = {**validated.dict()}
    diff = diff_with_tags(old_doc, new_doc)
    # result = await mongo_db.knowledge_collection.replace_one(
    #     {"app_name": "main"}, new_doc, upsert=True
    # )
    # if result.modified_count == 0 and not result.upserted_id:
    #     raise HTTPException(500, "Failed to update knowledge base")
    return UpdateResponse(knowledge=validated, diff=diff)

@knowledge_base_router.put("/knowledge_base/apply", response_model=UpdateResponse)
async def apply_knowledge_base(new_data: KnowledgeBase):
    """Полностью заменяет базу знаний предоставленными данными после валидации."""
    now = datetime.now()
    new_data.update_date = now
    new_doc = {"app_name": "main", **new_data.dict()}
    old_doc = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
    if old_doc:
        old_doc.pop("_id", None)
    else:
        old_doc = {}
    diff = diff_with_tags(old_doc, new_doc)
    result = await mongo_db.knowledge_collection.replace_one(
        {"app_name": "main"}, new_doc, upsert=True
    )
    if result.modified_count == 0 and not result.upserted_id:
        raise HTTPException(500, "Failed to update knowledge base")
    return UpdateResponse(knowledge=new_data, diff=diff)







# Модель запроса для генерации тела патч запроса на основе текста пользователя с опциональными исходными данными.
class GeneratePatchRequest(BaseModel):
    """Запрос для генерации тела патч запроса на основе текста пользователя с опциональными исходными данными."""
    user_message: str
    user_info: Optional[str] = ""
    base_data: Optional[dict] = None

async def analyze_update_snippets_via_gpt(
    user_message: str,
    user_info: str,
    knowledge_base: Dict[str, Any]
) -> Dict[str, Any]:
    """Calls GPT to analyze existing topics, subtopics, and Q&A and returns a JSON with update areas, preserving the user's language."""
    snippet_lines = []
    # Do not change the language of the snippets; use the keys as in the current knowledge base.
    for topic_name, topic_data in knowledge_base.items():
        line = f"Topic: {topic_name}"
        subtopics = topic_data.get("subtopics", {})
        if subtopics:
            sub_lines = []
            for subtopic_name, subtopic_data in subtopics.items():
                questions = subtopic_data.get("questions", {})
                q_keys = ", ".join(questions.keys()) if questions else "No questions"
                sub_lines.append(f"Subtopic: {subtopic_name} (Questions: {q_keys})")
            line += " | " + " || ".join(sub_lines)
        snippet_lines.append(line)
    kb_full_structure = "\n".join(snippet_lines)

    system_prompt = f"""

You are an AI assistant specialized in analyzing a dentist's knowledge base.
Your task is to determine which **existing** topics, subtopics, and questions from the actual knowledge base are **relevant** to the user's request.
You **MUST NOT** create new topics, subtopics, or questions. 
You **MUST NOT** modify or infer missing information.
You **MUST STRICTLY USE ONLY EXISTING DATA** from the knowledge base.

### **Actual Knowledge Base Structure**
The knowledge base consists of the following topics, subtopics, and questions:
{kb_full_structure} (if empty: return {{"topics": []}})

### **Rules**:
1. **Strictly Use Existing Data**:
   - You **must only return** topics, subtopics, and questions **that already exist** in the knowledge base.

2. **Preserve the Original Structure**:
   - Each `"topic"` contains `"subtopics"`, and each `"subtopic"` contains `"questions"`.
   - You **MUST NOT** modify this hierarchy.
   - You **MUST NOT** rename or restructure any fields.

3. **Match Language**:
   - The topics, subtopics, and questions **must remain in their original language** unless the user explicitly requests a translation.
   - If the request does not specify a language change, **strictly maintain the existing language**.

4. **Handling General Requests**:
   - If the user's request is **vague** (e.g., "Improve responses"), assume it applies to **the entire knowledge base**.
   - In such cases, return **all relevant topics and subtopics that exist**.

5. **Output Format**:
   - The response **must strictly** follow this JSON format:
```json
{{
  "topics": [
    {{
      "topic": "Existing Topic Name",
      "subtopics": [
        {{
          "subtopic": "Existing Subtopic Name",
          "questions": ["Existing Question 1", "Existing Question 2"]
        }}
      ]
    }}
  ]
}}
"""


    messages = [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_message.strip()}
    ]
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1
    )
    raw_content = response.choices[0].message.content.strip()
    match = re.search(r"\{.*\}", raw_content, re.DOTALL)
    if not match:
        return {"topics": []}
    json_text = match.group(0)
    try:
        result = json.loads(json_text)
        return {"topics": result.get("topics", [])}
    except json.JSONDecodeError:
        return {"topics": []}

async def extract_knowledge_with_structure(
    topics: List[Dict[str, Optional[str]]], 
    user_message: Optional[str] = None, 
    knowledge_base: Optional[Dict[str, dict]] = {}
) -> Dict[str, Any]:
    """Извлекает структурированные данные из knowledge_base для списка тем, подтем и вопросов."""

    extracted_data = {}

    if not knowledge_base:
        knowledge_base = await get_knowledge_base()

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
                    subtopic_data = subs[subtopic_name]

                    if subtopic_name not in extracted_data[topic_name]["subtopics"]:
                        extracted_data[topic_name]["subtopics"][subtopic_name] = {"questions": {}}

                    if questions:
                        for q_text in questions:
                            if q_text in subtopic_data.get("questions", {}):
                                ans_text = subtopic_data["questions"][q_text]
                                extracted_data[topic_name]["subtopics"][subtopic_name]["questions"][q_text] = ans_text
                    else:
                        extracted_data[topic_name]["subtopics"][subtopic_name]["questions"] = subtopic_data.get("questions", {}).copy()

        else:
            for subtopic_name, subtopic_data in subs.items():
                if subtopic_name not in extracted_data[topic_name]["subtopics"]:
                    extracted_data[topic_name]["subtopics"][subtopic_name] = {"questions": {}}
                extracted_data[topic_name]["subtopics"][subtopic_name]["questions"] = subtopic_data.get("questions", {}).copy()

    return extracted_data if extracted_data else {}


async def generate_patch_body_via_gpt(
    user_message: str,
    user_info: str,
    knowledge_base: Dict[str, Any]
) -> Dict[str, Any]:
    """Calls GPT to generate a patch request body for updating the knowledge base based on the user's message and current data, preserving the original language and structure."""
    snippets = await analyze_update_snippets_via_gpt(user_message=user_message, user_info=user_info, knowledge_base=knowledge_base)
    snippets_list = snippets["topics"]
    kb_snippets_text = await extract_knowledge_with_structure(topics=snippets_list, knowledge_base=knowledge_base)
    
#     system_prompt = f"""
# You are an AI assistant that generates a patch request body for updating a knowledge base.

# ## Knowledge Base Structure
# 1. The knowledge base uses exactly one **dominant language** for all topics, subtopics, and questions.
# 2. Each top-level key is a **topic**.
# 3. Each topic has a `"subtopics"` dictionary.
# 4. Each subtopic has a `"questions"` dictionary (keys = question text, values = answers).

# An example minimal structure (placeholder language, purely illustrative):
# {{
#   "TopicExample": {{
#     "subtopics": {{
#       "SubtopicExample": {{
#         "questions": {{
#           "QuestionExample": "AnswerExample"
#         }}
#       }}
#     }}
#   }}
# }}

# ## Your Task
# Produce a valid JSON patch that updates the knowledge base according to the user's instructions.

# ## Rules

# 1. **Preserve Hierarchy**
#    - Do not add extra layers or rename "subtopics" / "questions".
#    - Follow the existing pattern: Topic -> subtopics -> questions.

# 2. **Language Consistency**
#    - The knowledge base is in **one dominant language** (the user text might indicate which).
#    - If the user’s text is in Russian and the base is also in Russian, keep all new topics/subtopics/questions in Russian.
#    - If the user explicitly requests a rename or translation, mark old entries with `"_delete": true` and create the new ones with the updated language/keys.
#    - Otherwise, keep everything in the same language as the existing knowledge base.

# 3. **Split Information**
#    - If the user’s text lumps multiple distinct facts, do **not** merge them into one question/answer.  
#    - Instead, create multiple questions and/or subtopics as logically needed.  
#    - Do not be afraid to create multiple top-level topics if the content covers clearly separate domains.

# 4. **Patch Operations**
#    - **Add** new content by introducing a new topic/subtopic/question with a text value.
#    - **Update** existing answers by providing a new string for that question.
#    - **Delete** an existing topic/subtopic/question by marking it with `"_delete": true`.
#    - **Rename** by marking the old key with `"_delete": true` and adding the new key with the updated text.

# 5. **Output Format**
#    - Return **only valid JSON** that represents the patch. No extra commentary or text.
#    - Example patch (generic placeholders):
# ```json
# {{
#   "SomeTopic": {{
#     "subtopics": {{
#       "SomeSubtopic": {{
#         "questions": {{
#           "OldQuestionToRemove": {{ "_delete": true }},
#           "AnUpdatedQuestion": "New answer text here",
#           "NewQuestion": "Brand new answer text here"
#         }}
#       }}
#     }}
#   }},
#   "AnotherTopic": {{
#     "subtopics": {{
#       "SomethingElse": {{
#         "questions": {{
#           "OneMoreQuestion": "Some answer"
#         }}
#       }}
#     }}
#   }}
# }}
# """

    system_prompt = f"""
You are an AI assistant that generates a patch request body for updating a knowledge base.

## Knowledge Base Structure
1. The knowledge base uses exactly one **dominant language** for all topics, subtopics, and questions.
2. Each top-level key is a **topic**.
3. Each topic has a `"subtopics"` dictionary.
4. Each subtopic has a `"questions"` dictionary (keys = question text, values = answers).

An example minimal structure (placeholder language, purely illustrative):
{{
  "TopicExample": {{
    "subtopics": {{
      "SubtopicExample": {{
        "questions": {{
          "QuestionExample": "AnswerExample"
        }}
      }}
    }}
  }}
}}

## Your Task
Produce a valid JSON patch that updates the knowledge base according to the user's instructions.

## Relevant Extracted Knowledge Base Snippets
The following snippets contain **relevant** topics, subtopics, and questions that match the user's request:
{kb_snippets_text}

## Rules

1. **Preserve Hierarchy**
   - Do not add extra layers or rename "subtopics" / "questions".
   - Follow the existing pattern: Topic -> subtopics -> questions.

2. **Strictly Use Existing Topics/Subtopics Where Possible**
   - When modifying data, **always use existing topics, subtopics, and questions** if they are relevant.
   - **DO NOT create new topics, subtopics, or questions unless there is no relevant place to add the information.**
   - If there is a suitable topic/subtopic/question where the requested information fits, **update it instead of creating new keys**.
   - If the requested information is new and does not fit into existing categories, then **only create new entries**.

3. **Language Consistency**
   - The knowledge base is in **one dominant language** (the user text might indicate which).
   - If the user’s text is in Russian and the base is also in Russian, keep all new topics/subtopics/questions in Russian.
   - If the user explicitly requests a rename or translation, mark old entries with `"_delete": true` and create the new ones with the updated language/keys.
   - Otherwise, keep everything in the same language as the existing knowledge base.

4. **Split Information**
   - If the user’s text lumps multiple distinct facts, do **not** merge them into one question/answer.  
   - Instead, create multiple questions and/or subtopics as logically needed.  
   - Do not be afraid to create multiple top-level topics if the content covers clearly separate domains.

5. **Patch Operations**
   - **Add** new content by introducing a new topic/subtopic/question **ONLY if no suitable existing entry exists**.
   - **Update** existing answers by modifying their values.
   - **Delete** an existing topic/subtopic/question by marking it with `"_delete": true`.
   - **Rename** by marking the old key with `"_delete": true` and adding the new key with the updated text.

6. **Output Format**
   - Return **only valid JSON** that represents the patch. No extra commentary or text.
   - Example patch (generic placeholders):
```json
{{
  "SomeTopic": {{
    "subtopics": {{
      "SomeSubtopic": {{
        "questions": {{
          "OldQuestionToRemove": {{ "_delete": true }},
          "AnUpdatedQuestion": "New answer text here",
          "NewQuestion": "Brand new answer text here"
        }}
      }}
    }}
  }},
  "AnotherTopic": {{
    "subtopics": {{
      "SomethingElse": {{
        "questions": {{
          "OneMoreQuestion": "Some answer"
        }}
      }}
    }}
  }}
}}
"""

    messages = [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_message.strip()}
    ]
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.1
    )
    raw_content = response.choices[0].message.content.strip()
    match = re.search(r"\{.*\}", raw_content, re.DOTALL)

    
    if not match:
        return {}
    json_text = match.group(0)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return {}





@knowledge_base_router.post("/generate_patch", response_model=Dict[str, Any])
async def generate_patch(req: GeneratePatchRequest):
    """
    Generates a patch request body for updating the knowledge base.
    It first extracts update areas (topics, subtopics, and Q&A) from the current knowledge base (or provided base data),
    then uses the user's request along with these snippets to generate the patch body via GPT.
    The generated patch must follow the knowledge base structure exactly.
    """
    if req.base_data is not None:
        kb_data = req.base_data
    else:
        kb_doc = await mongo_db.knowledge_collection.find_one({"app_name": "main"})
        if not kb_doc:
            raise HTTPException(404, "Knowledge base not found")
        kb_doc.pop("_id", None)
        kb_data = kb_doc.get("knowledge_base", {})

    patch_body = await generate_patch_body_via_gpt(req.user_message, req.user_info, kb_data)
    return patch_body
