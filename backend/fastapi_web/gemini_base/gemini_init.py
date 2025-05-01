"""Инициализация клиента ИИ Gemini."""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

import aiohttp

from infra import settings

MAX_INPUT_TOKENS = 4000
MAX_OUTPUT_TOKENS = 12000


class GeminiClient:
    """
    Асинхронный клиент для Google Gemini AI.
    Если последнее user-сообщение слишком велико,
    оно будет разбито на чанки, а ответы склеятся
    и вернутся в формате:
    {
      "candidates": [
        {
          "content": {
            "parts": [
              {
                "text": "..."
              }
            ]
          }
        }
      ]
    }
    Это совместимо с кодом, который обращается к
    response["candidates"][0]["content"]["parts"][0]["text"].
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = aiohttp.ClientSession()
        self.headers = {"Content-Type": "application/json"}

    async def close(self):
        """Закрывает HTTP-сессию."""
        await self.session.close()

    async def chat_generate(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Если последнее user-сообщение <= MAX_INPUT_TOKENS слов, делаем один запрос.
        Если больше — разбиваем последнее сообщение (user) на чанки.
        Для каждого чанка вызываем _chat_generate_single, но НЕ записываем ответ
        в историю, чтобы каждый чанк НЕ учитывал предыдущие ответы (твой запрос).
        При этом предыдущая история (без последнего user) всё равно учитывается.
        В конце склеиваем все ответы (JSON + text) в единый финал.
        """

        user_text = self._extract_last_user_text(messages)
        total_input_words = self._count_words(user_text)
        logging.info(
            f"[GeminiClient] chat_generate called. Last user message ~{total_input_words} words.")

        if total_input_words <= MAX_INPUT_TOKENS:
            logging.info("[GeminiClient] Input within limit, single request.")
            single_resp = await self._chat_generate_single(model, messages, system_instruction, temperature)
            if 'error' in single_resp:
                logging.error(f"[GeminiClient] Ошибка {single_resp['detail']}")
            answer_text = self._extract_text(single_resp)
            answer_words = self._count_words(answer_text)
            logging.info(
                f"[GeminiClient] Single answer ~ {answer_words} words.")
            return self._convert_to_parts_format(single_resp)

        logging.info(
            "[GeminiClient] Input exceeds limit, splitting into chunks.")
        chunks = self._split_text(user_text, MAX_INPUT_TOKENS)
        logging.info(f"[GeminiClient] Got {len(chunks)} chunks.")

        for idx, ch in enumerate(chunks, start=1):
            ch_words = self._count_words(ch)
            logging.info(f"[GeminiClient] Chunk {idx} ~ {ch_words} words.")

        merged_json: Dict[str, Any] = {}
        merged_text = ""

        history = messages[:-1]

        for i, chunk_content in enumerate(chunks, start=1):
            logging.info(
                f"[GeminiClient] Processing chunk {i}/{len(chunks)}. History length: {len(history)}")

            chunk_user_msg = {
                "role": "user",
                "content": chunk_content
            }
            chunk_messages = history + [chunk_user_msg]

            part_resp = await self._chat_generate_single(model, chunk_messages, system_instruction, temperature)
            if "error" in part_resp:
                logging.error(
                    f"[GeminiClient] Error on chunk {i}: {part_resp['error']}")
                return part_resp

            chunk_answer_text = self._extract_text(part_resp)
            chunk_answer_words = self._count_words(chunk_answer_text)
            logging.info(
                f"[GeminiClient] Chunk {i} answer ~ {chunk_answer_words} words.")

            parsed_json = self._extract_json_from_resp(part_resp)
            if parsed_json is not None:
                logging.info(
                    f"[GeminiClient] Chunk {i} -> recognized JSON, merging.")
                self._merge_dicts(merged_json, parsed_json)
            else:
                logging.info(
                    f"[GeminiClient] Chunk {i} -> recognized text, appending.")
                merged_text = self._merge_texts(merged_text, chunk_answer_text)

        final_str = self._combine_final_output(merged_json, merged_text)
        logging.info(
            "[GeminiClient] All chunks processed, returning unified answer.")

        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": final_str
                            }
                        ]
                    }
                }
            ]
        }

    async def _chat_generate_single(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Один запрос к Gemini, учитывает parts/content, retry при 429.
        """
        payload = {
            "contents": [
                {
                    "role": msg["role"],
                    "parts": (
                        msg["parts"] if "parts" in msg and isinstance(msg["parts"], list)
                        else [{"text": msg.get("content", "")}]
                    )
                }
                for msg in messages
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": MAX_OUTPUT_TOKENS
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        url = self.BASE_URL.format(model=model) + f"?key={self.api_key}"
        try:
            async with self.session.post(url, json=payload, headers=self.headers) as r:
                if r.status == 429:
                    logging.warning(
                        "[GeminiClient] Rate limited (429). Retrying in 10s...")
                    await asyncio.sleep(10)
                    return await self._chat_generate_single(model, messages, temperature)
                if r.status != 200:
                    err_body = await r.text()
                    return {
                        "error": f"Gemini API returned status {r.status}",
                        "detail": err_body
                    }
                await asyncio.sleep(1)
                return await r.json()
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    def _convert_to_parts_format(
            self, original_resp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Если original_resp уже в error-форме, возвращаем как есть.
        Иначе пытаемся извлечь контент, завернуть в { "parts": [{"text": ...}] }.
        """
        if "error" in original_resp:
            return original_resp
        content_str = self._extract_text(original_resp)
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": content_str
                            }
                        ]
                    }
                }
            ]
        }

    def _extract_last_user_text(self, messages: List[Dict[str, Any]]) -> str:
        """Возвращает текст последнего user-сообщения."""
        for m in reversed(messages):
            if m.get("role") == "user":
                c = m.get("content", "")
                if c:
                    return c
                if "parts" in m and isinstance(m["parts"], list):
                    return " ".join(str(p.get("text", "")) for p in m["parts"])
        return ""

    def _count_words(self, text: str) -> int:
        """Возвращает приблизительное число слов."""
        return len(text.split())

    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """Делит text на части ~chunk_size слов."""
        words = text.split()
        return [
            " ".join(words[i:i + chunk_size])
            for i in range(0, len(words), chunk_size)
        ]

    def _extract_json_from_resp(
            self, resp: Dict[str, Any]) -> Union[Dict[str, Any], None]:
        """
        Пробуем найти JSON в resp["candidates"][0]["content"],
        если это строка, выдергиваем { ... } и json.loads().
        """
        text_data = self._extract_text(resp)
        match = re.search(r"(\{[\s\S]+\})", text_data)
        if not match:
            return None
        raw_json = match.group(1)
        try:
            return json.loads(raw_json)
        except Exception:
            return None

    def _extract_text(self, resp: Dict[str, Any]) -> str:
        """
        Извлекает строку из resp["candidates"][0]["content"]["parts"][0]["text"], если оно есть.
        Может быть, что content = str, тогда просто возвращаем.
        """
        cands = resp.get("candidates", [])
        if not cands:
            return ""
        c = cands[0].get("content", "")
        if isinstance(c, dict):
            parts = c.get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
            return ""
        return str(c).strip()

    def _merge_dicts(
            self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Рекурсивно сливает source в target.
        """
        for k, v in source.items():
            if k in target and isinstance(
                    target[k], dict) and isinstance(v, dict):
                self._merge_dicts(target[k], v)
            else:
                target[k] = v

    def _merge_texts(self, acc: str, piece: str) -> str:
        """Добавляем piece к acc с переводом строки."""
        if not acc:
            return piece
        return acc + "\n" + piece

    def _combine_final_output(self, merged_json: dict,
                              merged_text: str) -> str:
        """
        Если есть JSON и текст, вернём JSON + "--- TEXT ---" + текст.
        Если только JSON, вернём JSON.
        Если только текст, вернём текст.
        """
        if merged_json and merged_text.strip():
            return (
                json.dumps(merged_json, ensure_ascii=False)
                + "\n--- TEXT ---\n"
                + merged_text
            )
        elif merged_json:
            return json.dumps(merged_json, ensure_ascii=False)
        else:
            return merged_text


gemini_client = GeminiClient(api_key=settings.GEMINI_API_KEY)
