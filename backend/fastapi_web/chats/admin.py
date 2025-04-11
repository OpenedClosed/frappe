"""Админ-панель приложения Чаты."""
import json
from datetime import datetime
from typing import List, Optional

from admin_core.base_admin import BaseAdmin, InlineAdmin
from crud_core.registry import admin_registry
from db.mongo.db_init import mongo_db
from infra import settings

from .db.mongo.enums import SenderRole
from .db.mongo.schemas import ChatMessage, ChatSession, Client


class ChatMessageInline(InlineAdmin):
    """Инлайн сообщений чата."""

    model = ChatMessage
    collection_name = "chats"
    dot_field_path = "messages"

    verbose_name = {
        "en": "Chat Message",
        "pl": "Wiadomość czatu",
        "uk": "Повідомлення чату",
        "ru": "Сообщение чата"
    }
    plural_name = {
        "en": "Chat Messages",
        "pl": "Wiadomości czatu",
        "uk": "Повідомлення чату",
        "ru": "Сообщения чата"
    }
    icon = "pi pi-send"

    detail_fields = [
        "message",
        "sender_role",
        "timestamp",
        "confidence_status"]
    list_display = ["message", "sender_role", "timestamp", "confidence_status"]
    computed_fields = ["confidence_status"]
    read_only_fields = ["timestamp"]

    field_titles = {
        "message": {
            "en": "Message", "pl": "Wiadomość",
            "uk": "Повідомлення", "ru": "Сообщение"
        },
        "sender_role": {
            "en": "Sender Role", "pl": "Rola nadawcy",
            "uk": "Роль відправника", "ru": "Роль отправителя"
        },
        "timestamp": {
            "en": "Timestamp", "pl": "Znacznik czasu",
            "uk": "Часова мітка", "ru": "Метка времени"
        },
        "confidence_status": {
            "en": "Confidence Status", "pl": "Poziom pewności",
            "uk": "Рівень впевненості", "ru": "Уровень уверенности"
        },
    }

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        current_user: Optional[dict] = None,
    ) -> List[dict]:
        """Возвращает отфильтрованный и отсортированный список сообщений."""
        filters = filters or {}
        sort_by = sort_by or self.detect_id_field()

        messages = await super().get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            current_user=current_user
        )

        # (опциональный фильтр по роли или другим условиям — можно раскомментировать)
        # messages = [
        #     msg for msg in messages
        #     if msg.get("sender_role") == SenderRole.CLIENT
        # ]

        if sort_by:
            reverse = (order == -1)
            messages.sort(key=lambda x: x.get(sort_by), reverse=reverse)

        return [await self.format_document(msg) for msg in messages]

    async def get_confidence_status(self, obj: dict) -> str:
        """Возвращает статус уверенности в формате JSON (en/ru)."""
        evaluation = obj.get("gpt_evaluation", {})

        status = {
            "en": "Unknown",
            "ru": "Неизвестно"
        }

        if evaluation:
            confidence = evaluation.get("confidence", 0)

            if evaluation.get("out_of_scope"):
                status = {"en": "Out of Scope", "ru": "Вне компетенции"}
            elif evaluation.get("consultant_call"):
                status = {
                    "en": "Consultant Call",
                    "ru": "Требуется консультация"}
            elif confidence >= 0.7:
                status = {"en": "Confident", "ru": "Уверенный"}
            elif 0.3 <= confidence < 0.7:
                status = {"en": "Uncertain", "ru": "Неуверенный"}
            else:
                status = {"en": "Low Confidence", "ru": "Низкая уверенность"}

        return json.dumps(status, ensure_ascii=False)


class ClientInline(InlineAdmin):
    """Инлайн для модели клиента."""

    model = Client
    collection_name = "chats"
    dot_field_path = "client"

    verbose_name = {
        "en": "Client", "pl": "Klient", "uk": "Клієнт", "zh": "客户", "es": "Cliente", "ru": "Клиент"
    }
    plural_name = {
        "en": "Clients", "pl": "Klienci", "uk": "Клієнти", "zh": "客户", "es": "Clientes", "ru": "Клиенты"
    }
    icon = "pi pi-user"

    detail_fields = ["client_id", "source", "external_id", "metadata_display"]
    list_display = ["client_id", "source", "external_id", "metadata_display"]
    computed_fields = ["metadata_display"]
    read_only_fields = ["client_id", "source", "external_id"]

    field_titles = {
        "client_id": {
            "en": "Client ID", "pl": "ID klienta", "uk": "Ідентифікатор клієнта", "zh": "客户ID", "es": "ID de cliente", "ru": "ID клиента"
        },
        "source": {
            "en": "Source", "pl": "Źródło", "uk": "Джерело", "zh": "来源", "es": "Fuente", "ru": "Источник"
        },
        "external_id": {
            "en": "External ID", "pl": "Zewnętrzny ID", "uk": "Зовнішній ID", "zh": "外部ID", "es": "ID externo", "ru": "Внешний ID"
        },
        "metadata_display": {
            "en": "Metadata", "pl": "Metadane", "uk": "Метадані", "zh": "元数据", "es": "Metadatos", "ru": "Метаданные"
        },
    }

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        current_user: Optional[dict] = None
    ) -> List[dict]:
        """Возвращает список уникальных клиентов."""
        filters = filters or {}
        results = await super().get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            current_user=current_user
        )

        # Уникальность по client_id
        unique_clients = {
            client["client_id"]: client
            for client in results if "client_id" in client
        }

        return [await self.format_document(client) for client in unique_clients.values()]

    async def get_metadata_display(self, obj: dict) -> str:
        """Возвращает строковое представление метаданных клиента."""
        metadata = obj.get("metadata")
        return ", ".join(f"{key}: {value}" for key,
                         value in metadata.items()) if metadata else "No metadata"


class ChatSessionAdmin(BaseAdmin):
    """Админ для сессий чата."""

    model = ChatSession
    collection_name = "chats"

    verbose_name = {
        "en": "Chat Session", "pl": "Sesja czatu", "uk": "Сесія чату", "ru": "Сессия чата",
        "zh": "聊天会话", "es": "Sesión de chat"
    }
    plural_name = {
        "en": "Chat Sessions", "pl": "Sesje czatu", "uk": "Сесії чату", "ru": "Сессии чата",
        "zh": "聊天会话", "es": "Sesiones de chat"
    }
    icon = "pi pi-comments"

    list_display = [
        "chat_id", "client_id_display", "client_source_display",
        "company_name", "status_display", "duration_display",
        "created_at", "admin_marker"
    ]

    detail_fields = list_display.copy()
    computed_fields = [
        "client_id_display", "client_source_display",
        "status_display", "duration_display"
    ]
    read_only_fields = ["created_at", "last_activity"]

    field_titles = {
        "chat_id": {
            "en": "Chat ID", "ru": "ID чата"
        },
        "client_id_display": {
            "en": "Client ID", "ru": "ID клиента"
        },
        "client_source_display": {
            "en": "Client Source", "ru": "Источник клиента"
        },
        "company_name": {
            "en": "Company Name", "ru": "Название компании"
        },
        "status_display": {
            "en": "Status", "ru": "Статус"
        },
        "duration_display": {
            "en": "Duration", "ru": "Длительность"
        },
        "created_at": {
            "en": "Created At", "ru": "Создано"
        },
        "last_activity": {
            "en": "Last Activity", "ru": "Последняя активность"
        },
        "admin_marker": {
            "en": "Admin Marker", "ru": "Админская метка"
        },
    }

    inlines = {
        "messages": ChatMessageInline,
        "client": ClientInline
    }

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        current_user: Optional[dict] = None
    ) -> List[dict]:
        """Список чатов, у которых есть сообщения."""
        filters = filters or {}
        filters["messages"] = {"$exists": True, "$ne": []}
        return await super().get_queryset(filters=filters, sort_by=sort_by, order=order, current_user=current_user)

    async def get_status_display(self, obj: dict) -> str:
        """Статус чата (в виде JSON строки с переводами)."""
        ttl_value = 0
        if obj.get("last_activity"):
            diff = (datetime.utcnow() - obj["last_activity"]).total_seconds()
            ttl_value = settings.CHAT_TIMEOUT.total_seconds() - max(diff, 0)

        chat_session = ChatSession(**obj)
        status = chat_session.compute_status(ttl_value).value

        translated = {
            "en": status.replace("_", " ").capitalize(),
            "ru": {
                "active": "Активен",
                "inactive": "Неактивен",
                "expired": "Истёк"
            }.get(status, "Неизвестно")
        }
        return json.dumps(translated, ensure_ascii=False)

    async def get_duration_display(self, obj: dict) -> str:
        """Длительность чата (в виде JSON строки с переводами)."""
        created_at = obj.get("created_at")
        last_activity = obj.get("last_activity")
        if not created_at or not last_activity:
            return json.dumps({"en": "0h 0m", "ru": "0ч 0м"},
                              ensure_ascii=False)

        duration = last_activity - created_at
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)

        return json.dumps({
            "en": f"{int(hours)}h {int(minutes)}m",
            "ru": f"{int(hours)}ч {int(minutes)}м"
        }, ensure_ascii=False)

    async def get_client_id_display(self, obj: dict) -> str:
        """ID клиента или его внешний ID (в виде JSON строки)."""
        client_data = obj.get("client")
        value = "N/A"
        if isinstance(client_data, dict):
            client = Client(**client_data)
            value = client.external_id or client.client_id or "N/A"

        return json.dumps({"en": value, "ru": value}, ensure_ascii=False)

    async def get_client_source_display(self, obj: dict) -> str:
        """Источник клиента (в виде JSON строки)."""
        client_data = obj.get("client")
        value = "Unknown"
        if isinstance(client_data, dict):
            client = Client(**client_data)
            if isinstance(client.source, str):
                value = client.source.replace("_", " ").capitalize()

        return json.dumps({"en": value, "ru": value}, ensure_ascii=False)


admin_registry.register("chat_sessions", ChatSessionAdmin(mongo_db))
# admin_registry.register("clients", ClientInline(mongo_db))
# admin_registry.register("chat_messages", ChatMessageInline(mongo_db))
