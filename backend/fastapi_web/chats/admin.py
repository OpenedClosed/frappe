"""Админ-панель приложения Чаты."""
import asyncio
import json
from datetime import datetime
from typing import List, Optional

from admin_core.base_admin import BaseAdmin, InlineAdmin
from chats.utils.help_functions import get_master_client_by_id
from crud_core.permissions import OperatorPermission
from crud_core.registry import admin_registry
from db.mongo.db_init import mongo_db
from infra import settings

from .db.mongo.schemas import ChatMessage, ChatSession, Client


class ChatMessageInline(InlineAdmin):
    """Инлайн сообщений чата."""

    model = ChatMessage
    collection_name = "chats"
    dot_field_path = "messages"
    permission_class = OperatorPermission()

    verbose_name = {
        "en": "Chat Message",
        "pl": "Wiadomość czatu",
        "uk": "Повідомлення чату",
        "ru": "Сообщение чата",
        "ka": "ჩეთის შეტყობინება"
    }
    plural_name = {
        "en": "Chat Messages",
        "pl": "Wiadomości czatu",
        "uk": "Повідомлення чату",
        "ru": "Сообщения чата",
        "ka": "ჩეთის შეტყობინებები"
    }

    icon = "pi pi-send"

    detail_fields = [
        "message",
        "sender_role",
        "timestamp",
        "confidence_status",
        "read_by_display"
    ]
    list_display = [
        "message",
        "sender_role",
        "timestamp",
        "confidence_status",
        "read_by_display"
    ]
    computed_fields = [
        "confidence_status",
        "read_by_display"
    ]
    read_only_fields = ["timestamp"]

    field_titles = {
        "message": {
            "en": "Message",
            "pl": "Wiadomość",
            "uk": "Повідомлення",
            "ru": "Сообщение",
            "ka": "შეტყობინება"
        },
        "sender_role": {
            "en": "Sender Role",
            "pl": "Rola nadawcy",
            "uk": "Роль відправника",
            "ru": "Роль отправителя",
            "ka": "გამგზავნის როლი"
        },
        "timestamp": {
            "en": "Timestamp",
            "pl": "Znacznik czasu",
            "uk": "Часова мітка",
            "ru": "Метка времени",
            "ka": "დროის შტამპი"
        },
        "confidence_status": {
            "en": "Confidence Status",
            "pl": "Poziom pewności",
            "uk": "Рівень впевненості",
            "ru": "Уровень уверенности",
            "ka": "დაჯერებულობის დონე"
        },
        "read_by_display": {
            "en": "Read By",
            "pl": "Przeczytane przez",
            "uk": "Прочитано ким",
            "ru": "Прочитано кем",
            "ka": "ვის მიერ წაკითხულია"
        }
    }

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        current_user: Optional[dict] = None,
    ) -> List[dict]:
        filters = filters or {}
        sort_by = sort_by or self.detect_id_field()

        messages = await super().get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            current_user=current_user
        )

        if sort_by:
            reverse = (order == -1)
            messages.sort(key=lambda x: x.get(sort_by), reverse=reverse)

        return await asyncio.gather(*[
            self.format_document(msg, current_user)
            for msg in messages
        ])

    async def get_confidence_status(self, obj: dict) -> str:
        evaluation = obj.get("gpt_evaluation", {})

        status = {
            "en": "Unknown",
            "pl": "Nieznany",
            "uk": "Невідомо",
            "ru": "Неизвестно",
            "ka": "უცნობია"
        }

        if evaluation:
            confidence = evaluation.get("confidence", 0)

            if evaluation.get("out_of_scope"):
                status = {
                    "en": "Out of Scope",
                    "pl": "Poza zakresem",
                    "uk": "Поза межами",
                    "ru": "Вне компетенции",
                    "ka": "გარეშე თემატიკაა"
                }
            elif evaluation.get("consultant_call"):
                status = {
                    "en": "Consultant Call",
                    "pl": "Wymagana konsultacja",
                    "uk": "Потрібна консультація",
                    "ru": "Требуется консультация",
                    "ka": "საჭიროა კონსულტაცია"
                }
            elif confidence >= 0.7:
                status = {
                    "en": "Confident",
                    "pl": "Pewny",
                    "uk": "Впевнений",
                    "ru": "Уверенный",
                    "ka": "დაჯერებული"
                }
            elif 0.3 <= confidence < 0.7:
                status = {
                    "en": "Uncertain",
                    "pl": "Niepewny",
                    "uk": "Невпевнений",
                    "ru": "Неуверенный",
                    "ka": "არაჯეროვანი"
                }
            else:
                status = {
                    "en": "Low Confidence",
                    "pl": "Niska pewność",
                    "uk": "Низька впевненість",
                    "ru": "Низкая уверенность",
                    "ka": "დაბალი დარწმუნებულობა"
                }

        return json.dumps(status, ensure_ascii=False)

    async def get_read_by_display(self, obj: dict) -> str:
        parent = getattr(self, "parent_document", None)
        if not parent:

            return json.dumps([], ensure_ascii=False)

        message_id = obj.get("id")
        read_state = parent.get("read_state", [])
        messages = parent.get("messages", [])
        idx_map = {m["id"]: i for i, m in enumerate(messages)}
        msg_idx = idx_map.get(message_id, -1)

        readers = []
        for ri in read_state:
            last_read = ri.get("last_read_msg")
            reader_id = ri.get("client_id")
            if reader_id and idx_map.get(last_read, -1) >= msg_idx:
                readers.append(reader_id)

        return json.dumps(readers, ensure_ascii=False)


class ClientInline(InlineAdmin):
    """Инлайн для модели клиента."""

    model = Client
    collection_name = "chats"
    dot_field_path = "client"
    permission_class = OperatorPermission()

    verbose_name = {
        "en": "Client",
        "pl": "Klient",
        "uk": "Клієнт",
        "ru": "Клиент",
        "ka": "კლიენტი"
    }
    plural_name = {
        "en": "Clients",
        "pl": "Klienci",
        "uk": "Клієнти",
        "ru": "Клиенты",
        "ka": "კლიენტები"
    }

    icon = "pi pi-user"

    detail_fields = ["client_id", "source", "external_id", "metadata_display"]
    list_display = ["client_id", "source", "external_id", "metadata_display"]
    computed_fields = ["metadata_display"]
    read_only_fields = ["client_id", "source", "external_id"]

    field_titles = {
        "client_id": {
            "en": "Client ID",
            "pl": "ID klienta",
            "uk": "Ідентифікатор клієнта",
            "ru": "ID клиента",
            "ka": "კლიენტის ID"
        },
        "source": {
            "en": "Source",
            "pl": "Źródło",
            "uk": "Джерело",
            "ru": "Источник",
            "ka": "წყარო"
        },
        "external_id": {
            "en": "External ID",
            "pl": "Zewnętrzny ID",
            "uk": "Зовнішній ID",
            "ru": "Внешний ID",
            "ka": "გარე ID"
        },
        "metadata_display": {
            "en": "Metadata",
            "pl": "Metadane",
            "uk": "Метадані",
            "ru": "Метаданные",
            "ka": "მეტამონაცემები"
        },
    }

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        current_user: Optional[dict] = None
    ) -> List[dict]:
        """Возвращает список уникальных клиентов."""
        filters = filters or {}
        results = await super().get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
            current_user=current_user
        )

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
    permission_class = OperatorPermission()

    verbose_name = {
        "en": "Chat Session",
        "pl": "Sesja czatu",
        "uk": "Сесія чату",
        "ru": "Сессия чата",
        "ka": "ჩეთის სესია"
    }
    plural_name = {
        "en": "Chat Sessions",
        "pl": "Sesje czatu",
        "uk": "Сесії чату",
        "ru": "Сессии чата",
        "ka": "ჩეთის სესიები"
    }

    icon = "pi pi-comments"

    list_display = [
        "chat_id", "client_id_display", "client_source_display",
        "company_name", "status_display", "duration_display",
        "created_at", "admin_marker"
    ]

    detail_fields = list_display + ["read_state"]
    computed_fields = [
        "client_id_display", "client_source_display",
        "status_display", "duration_display"
    ]
    read_only_fields = ["created_at", "last_activity"]

    field_titles = {
        "chat_id": {
            "en": "Chat ID",
            "pl": "ID czatu",
            "uk": "ID чату",
            "ru": "ID чата",
            "ka": "ჩეთის ID"
        },
        "client_id_display": {
            "en": "Client ID",
            "pl": "ID klienta",
            "uk": "ID клієнта",
            "ru": "ID клиента",
            "ka": "კლიენტის ID"
        },
        "client_source_display": {
            "en": "Client Source",
            "pl": "Źródło klienta",
            "uk": "Джерело клієнта",
            "ru": "Источник клиента",
            "ka": "კლიენტის წყარო"
        },
        "company_name": {
            "en": "Company Name",
            "pl": "Nazwa firmy",
            "uk": "Назва компанії",
            "ru": "Название компании",
            "ka": "კომპანიის სახელი"
        },
        "status_display": {
            "en": "Status",
            "pl": "Status",
            "uk": "Статус",
            "ru": "Статус",
            "ka": "სტატუსი"
        },
        "duration_display": {
            "en": "Duration",
            "pl": "Czas trwania",
            "uk": "Тривалість",
            "ru": "Длительность",
            "ka": "ხანგრძლივობა"
        },
        "created_at": {
            "en": "Created At",
            "pl": "Utworzono",
            "uk": "Створено",
            "ru": "Создано",
            "ka": "შექმნის დრო"
        },
        "last_activity": {
            "en": "Last Activity",
            "pl": "Ostatnia aktywność",
            "uk": "Остання активність",
            "ru": "Последняя активность",
            "ka": "ბოლო აქტივობა"
        },
        "admin_marker": {
            "en": "Admin Marker",
            "pl": "Znacznik administratora",
            "uk": "Позначка адміністратора",
            "ru": "Админская метка",
            "ka": "ადმინის მარკერი"
        },
        "read_state": {
            "en": "Read Status",
            "pl": "Stan przeczytania",
            "uk": "Статус прочитання",
            "ru": "Прочитано кем",
            "ka": "წაკითხვის სტატუსი"
        }
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
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        current_user: Optional[dict] = None
    ) -> List[dict]:
        """Список чатов, у которых есть сообщения."""
        filters = filters or {}
        filters["messages"] = {"$exists": True, "$ne": []}
        return await super().get_queryset(filters=filters, sort_by=sort_by, order=order, page=page, page_size=page_size, current_user=current_user)

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
            master = await get_master_client_by_id(client.client_id)
            if master:
                value = master.external_id or master.client_id

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
# Временно уберем сообщения и клиентов из админки
# admin_registry.register("clients", ClientInline(mongo_db))
# admin_registry.register("chat_messages", ChatMessageInline(mongo_db))
