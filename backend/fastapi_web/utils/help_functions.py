"""Вспомогательные функции проекта."""
import json
import random
import re
import string
from datetime import datetime
from typing import Any, Dict, Union


def to_snake_case(name: str) -> str:
    """Привести строку в snake_case."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def generate_random_filename(extension: str) -> str:
    """Сгенерировать случайное имя для файла с временной меткой."""
    random_str = ''.join(
        random.choices(
            string.ascii_letters + string.digits,
            k=6
        )
    )
    date_str = datetime.now().strftime("%Y%m%d")
    return f"{random_str}_{date_str}{extension}"


def try_parse_json(text: str) -> Union[Dict[str, Any], str]:
    """Пытается парсить JSON из text. Если неуспешно — возвращает текст как есть."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON", "original": text}