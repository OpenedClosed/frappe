"""Инициализация клиента ИИ Gemini."""
from typing import Any, Dict, List

import aiohttp

from infra import settings


class GeminiClient:
    """Асинхронный клиент для взаимодействия с Google Gemini AI API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = aiohttp.ClientSession()
        self.headers = {"Content-Type": "application/json"}

    async def chat_generate(
        self, model: str, messages: List[Dict[str, Any]], temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Отправляет запрос в Google Gemini AI API и получает ответ."""

        payload = {
            "contents": [
                {
                    "role": msg["role"],
                    "parts": msg.get("parts", [{"text": msg.get("content", "")}]),
                }
                for msg in messages
            ],
            "generationConfig": {"temperature": temperature},
        }

        url = self.BASE_URL.format(model=model) + f"?key={self.api_key}"

        try:
            async with self.session.post(url, json=payload, headers=self.headers) as response:
                if response.status != 200:
                    return {"error": f"Gemini API returned status {response.status}", "details": await response.text()}
                return await response.json()
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    async def close(self):
        """Закрывает сессию при завершении работы."""
        await self.session.close()


# Глобальный клиент для Gemini AI
gemini_client = GeminiClient(api_key=settings.GEMINI_API_KEY)
