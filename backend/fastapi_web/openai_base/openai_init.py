"""Инициализация клиента ИИ OpenAI."""
from openai import AsyncOpenAI

from infra import settings

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
