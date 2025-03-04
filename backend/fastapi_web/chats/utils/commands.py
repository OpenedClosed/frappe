"""Регистратор команд для приложения Чаты."""
from typing import Awaitable, Callable, Dict, Optional

COMMAND_HANDLERS: Dict[str, Dict[str, Callable[..., Awaitable[None]]]] = {}


def command_handler(command: str,
                    description: Optional[str] = None) -> Callable:
    """Декоратор для регистрации команд с возможностью добавления описания."""
    def decorator(func: Callable[..., Awaitable[None]]) -> Callable:
        COMMAND_HANDLERS[command] = {
            "handler": func,
            "help_text": description or "Описание отсутствует."
        }
        return func
    return decorator
