"""Админ-панель приложения Чаты."""
from datetime import datetime
from typing import List, Optional

from admin_core.admin_registry import admin_registry
from admin_core.base_admin import BaseAdmin, InlineAdmin
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
    icon: str = "pi pi-send"
    detail_fields = [
        "message",
        "sender_role",
        "timestamp",
        "confidence_status"]
    list_display = ["message", "sender_role", "timestamp", "confidence_status"]
    computed_fields = ["confidence_status"]
    read_only_fields = ["timestamp"]
    field_titles = {
        "message": {"en": "Message", "pl": "Wiadomość", "uk": "Повідомлення", "ru": "Сообщение"},
        "sender_role": {"en": "Sender Role", "pl": "Rola nadawcy", "uk": "Роль відправника", "ru": "Роль отправителя"},
        "timestamp": {"en": "Timestamp", "pl": "Znacznik czasu", "uk": "Часова мітка", "ru": "Метка времени"},
        "confidence_status": {"en": "Confidence Status", "pl": "Poziom pewności", "uk": "Рівень впевненості", "ru": "Уровень уверенности"},
    }

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1
    ) -> List[dict]:
        """Список сообщений."""
        filters = filters or {}
        results = await super().get_queryset(filters=filters, sort_by=sort_by, order=order)
        filtered = [
            msg for msg in results
            if msg.get("sender_role") == SenderRole.CLIENT and msg.get("gpt_evaluation")
        ]
        if sort_by:
            reverse_sort = (order == -1)
            filtered.sort(key=lambda x: x.get(sort_by), reverse=reverse_sort)
        return [await self.format_document(m) for m in filtered]

    async def get_confidence_status(self, obj: dict) -> str:
        """Статус уверенности."""
        evaluation = obj.get("gpt_evaluation", {})
        if evaluation:
            confidence = evaluation.get("confidence", 0)
            if evaluation.get("out_of_scope"):
                return "Out of Scope"
            if evaluation.get("consultant_call"):
                return "Consultant Call"
            if confidence >= 0.7:
                return "Confident"
            if 0.3 <= confidence < 0.7:
                return "Uncertain"
            return "Low Confidence"
        return "Unknown"


class ClientInline(InlineAdmin):
    """Инлайн для модели клиента."""

    model = Client
    collection_name = "chats"
    dot_field_path = "client"
    verbose_name = {
        "en": "Client",
        "pl": "Klient",
        "uk": "Клієнт",
        "ru": "Клиент"
    }
    plural_name = {
        "en": "Clients",
        "pl": "Klienci",
        "uk": "Клієнти",
        "ru": "Клиенты"
    }
    icon: str = "pi pi-user"
    detail_fields = ["client_id", "source", "external_id", "metadata_display"]
    list_display = ["client_id", "source", "external_id", "metadata_display"]
    computed_fields = ["metadata_display"]
    read_only_fields = ["client_id", "source", "external_id"]
    field_titles = {
        "client_id": {"en": "Client ID", "pl": "ID klienta", "uk": "Ідентифікатор клієнта", "ru": "ID клиента"},
        "source": {"en": "Source", "pl": "Źródło", "uk": "Джерело", "ru": "Источник"},
        "external_id": {"en": "External ID", "pl": "Zewnętrzny ID", "uk": "Зовнішній ID", "ru": "Внешний ID"},
        "metadata_display": {"en": "Metadata", "pl": "Metadane", "uk": "Метадані", "ru": "Метаданные"},
    }

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1
    ) -> List[dict]:
        """Получить список клиентов."""
        filters = filters or {}
        results = await super().get_queryset(filters=filters, sort_by=sort_by, order=order)
        
        unique_clients = {}
        for client in results:
            client_id = client.get("client_id")
            if client_id and client_id not in unique_clients:
                unique_clients[client_id] = client
        
        return [await self.format_document(client) for client in unique_clients.values()]

    async def get_metadata_display(self, obj: dict) -> str:
        """Отображение метаданных клиента."""
        metadata = obj.get("metadata", {})
        return ", ".join([f"{key}: {value}" for key, value in metadata.items(
        )]) if metadata else "No metadata"


class ChatSessionAdmin(BaseAdmin):
    """Админ для сессий чата."""

    model = ChatSession
    collection_name = "chats"
    verbose_name = {
        "en": "Chat Session",
        "pl": "Sesja czatu",
        "uk": "Сесія чату",
        "ru": "Сессия чата"
    }
    plural_name = {
        "en": "Chat Sessions",
        "pl": "Sesje czatu",
        "uk": "Сесії чату",
        "ru": "Сессии чата"
    }
    icon: str = "pi pi-comments"
    
    # Отображаемые поля
    list_display = [
        "chat_id",
        "client_id_display",
        "client_source_display",
        "company_name",
        "status_display",
        "duration_display",
        "created_at",
        "admin_marker",
    ] 
    
    # Поля в деталях
    detail_fields = [
        "chat_id",
        "client_id_display",
        "client_source_display",
        "company_name",
        "status_display",
        "duration_display",
        "created_at",
        "admin_marker",
    ]
    
    # Вычисляемые поля
    computed_fields = ["client_id_display", "client_source_display", "status_display", "duration_display"]

    # Только для чтения
    read_only_fields = ["created_at", "last_activity"]

    # Заголовки полей с переводом
    field_titles = {
        "chat_id": {"en": "Chat ID", "pl": "ID czatu", "uk": "Ідентифікатор чату", "ru": "ID чата"},
        "client_id_display": {"en": "Client ID", "pl": "ID klienta", "uk": "Ідентифікатор клієнта", "ru": "ID клиента"},
        "client_source_display": {"en": "Client Source", "pl": "Źródło klienta", "uk": "Джерело клієнта", "ru": "Источник клиента"},
        "company_name": {"en": "Company Name", "pl": "Nazwa firmy", "uk": "Назва компанії", "ru": "Название компании"},
        "status_display": {"en": "Status", "pl": "Status", "uk": "Статус", "ru": "Статус"},
        "duration_display": {"en": "Duration", "pl": "Czas trwania", "uk": "Тривалість", "ru": "Длительность"},
        "created_at": {"en": "Created At", "pl": "Utworzono", "uk": "Створено", "ru": "Создано"},
        "last_activity": {"en": "Last Activity", "pl": "Ostatnia aktywność", "uk": "Остання активність", "ru": "Последняя активность"},
        "admin_marker": {"en": "Admin Marker", "pl": "Znacznik administratora", "uk": "Мітка адміністратора", "ru": "Админская метка"},
    }

    # Инлайн-модели
    inlines = {"messages": ChatMessageInline, "client": ClientInline}

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1
    ) -> List[dict]:
        """Список чатов, у которых есть сообщения."""
        filters = filters or {}
        filters["messages"] = {"$exists": True, "$ne": []}
        return await super().get_queryset(filters=filters, sort_by=sort_by, order=order)

    async def get_status_display(self, obj: dict) -> str:
        """Статус чата."""
        ttl_value = 0
        if obj.get("last_activity"):
            diff = (datetime.utcnow() - obj["last_activity"]).total_seconds()
            ttl_value = settings.CHAT_TIMEOUT.total_seconds() - max(diff, 0)
        chat_session = ChatSession(**obj)
        return chat_session.compute_status(ttl_value).value.capitalize().replace('_', ' ')

    async def get_duration_display(self, obj: dict) -> str:
        """Длительность чата."""
        created_at = obj.get("created_at")
        last_activity = obj.get("last_activity")
        if not created_at or not last_activity:
            return "0h 0m"
        duration = last_activity - created_at
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m"

    async def get_client_id_display(self, obj: dict) -> str:
        """Возвращает ID клиента (external_id если есть, иначе client_id)."""
        if "client" in obj and isinstance(obj["client"], dict):
            return obj["client"].get("external_id", obj["client"].get("client_id", "N/A"))
        return "N/A"

    async def get_client_source_display(self, obj: dict) -> str:
        """Возвращает источник клиента."""
        if "client" in obj and isinstance(obj["client"], dict):
            return obj["client"].get("source", "Unknown").replace("_", " ").capitalize()
        return "Unknown"



admin_registry.register("chat_sessions", ChatSessionAdmin(mongo_db))
admin_registry.register("clients", ClientInline(mongo_db))
admin_registry.register("chat_messages", ChatMessageInline(mongo_db))
