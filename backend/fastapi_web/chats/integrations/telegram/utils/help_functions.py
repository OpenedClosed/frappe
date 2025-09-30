"""Вспомогательные функции интеграции Telegram."""
from typing import Any, Dict
from chats.integrations.basic.handlers import process_integration_message
from infra import settings
from typing import Any, Dict

from chats.db.mongo.enums import ChatSource, SenderRole
from infra import settings


def parse_telegram_payload(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Преобразует Telegram-объект в унифицированный формат (используется тестами)."""
    user = obj["from"]
    return {
        "sender_id": str(user["id"]),
        "recipient_id": str(settings.TELEGRAM_BOT_ID),
        "message_text": obj.get("text") or obj.get("caption", ""),
        "message_id": str(obj["message_id"]),
        "timestamp": int(obj["date"]) * 1000,
        "metadata": {
            "username": user.get("username"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "language_code": user.get("language_code"),
            "avatar_url": obj.get("avatar_url"),
        },
    }

async def process_telegram_message(
    sender_id: str,
    message_text: str,
    bot_id: str,
    client_external_id: str,
    metadata: Dict[str, Any],
    sender_role: SenderRole,
    external_id: str,
    user_language: str
):
    await process_integration_message(
        platform="telegram",
        chat_source=ChatSource.TELEGRAM,
        sender_id=sender_id,
        message_text=message_text,
        bot_id=bot_id,
        client_external_id=client_external_id,
        metadata=metadata,
        sender_role=sender_role,
        external_id=external_id,
        user_language=user_language,
    )
