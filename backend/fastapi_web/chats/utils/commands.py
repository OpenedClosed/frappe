from typing import Any, Awaitable, Callable, Dict

from chats.db.mongo.enums import SenderRole
from chats.db.mongo.schemas import ChatMessage, ChatSession

from db.mongo.db_init import mongo_db

COMMAND_HANDLERS: Dict[str, Callable[..., Awaitable[None]]] = {}

def command_handler(command: str):
    """Декоратор для регистрации хендлера в COMMAND_HANDLERS."""
    def decorator(func):
        COMMAND_HANDLERS[command] = func
        return func
    return decorator
