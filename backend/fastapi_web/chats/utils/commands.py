from typing import Any, Awaitable, Callable, Dict, Optional

from chats.db.mongo.enums import SenderRole
from chats.db.mongo.schemas import ChatMessage, ChatSession
from functools import wraps

from db.mongo.db_init import mongo_db

COMMAND_HANDLERS: Dict[str, Dict[str, Callable[..., Awaitable[None]]]] = {}

def command_handler(command: str, help_text: Optional[str] = None):
    """Декоратор для регистрации команд с возможностью добавления описания."""
    def decorator(func: Callable[..., Awaitable[None]]):
        COMMAND_HANDLERS[command] = {
            "handler": func,
            "help_text": help_text or "No description available."
        }
        return func
    return decorator
