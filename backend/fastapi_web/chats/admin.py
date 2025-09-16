"""Админ-панель приложения Чаты."""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from admin_core.base_admin import BaseAdmin, InlineAdmin
from crud_core.decorators import admin_route
from chats.db.mongo.enums import SenderRole
from chats.utils.help_functions import build_sender_data_map, calculate_chat_status, get_master_client_by_id
from crud_core.permissions import OperatorPermission
from crud_core.registry import admin_registry
from db.mongo.db_init import mongo_db
from infra import settings
from utils.encoders import DateTimeEncoder
from pydantic import BaseModel, TypeAdapter, ValidationError

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

    async def get_confidence_status(self, obj: dict, current_user=None) -> str:
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

        return json.dumps(status, ensure_ascii=False, cls=DateTimeEncoder)

    async def get_read_by_display(self, obj: dict, current_user=None) -> str:
        parent = getattr(self, "parent_document", None)
        if not parent:

            return json.dumps([], ensure_ascii=False, cls=DateTimeEncoder)

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

        return json.dumps(readers, ensure_ascii=False, cls=DateTimeEncoder)


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

    async def get_metadata_display(self, obj: dict, current_user=None) -> str:
        """Возвращает строковое представление метаданных клиента."""
        metadata = obj.get("metadata")
        return ", ".join(f"{key}: {value}" for key,
                         value in metadata.items()) if metadata else "No metadata"


# class ChatSessionAdmin(BaseAdmin):
#     """Админ для сессий чата."""

#     # базовые настройки
#     model = ChatSession
#     collection_name = "chats"
#     permission_class = OperatorPermission()
#     icon = "pi pi-comments"

#     verbose_name = {
#         "en": "Chat Session", "pl": "Sesja czatu", "uk": "Сесія чату",
#         "ru": "Сессия чата", "ka": "ჩეთის სესია"
#     }
#     plural_name = {
#         "en": "Chat Sessions", "pl": "Sesje czatu", "uk": "Сесії чату",
#         "ru": "Сессии чата", "ka": "ჩეთის სესიები"
#     }

#     # названия полей
#     field_titles = {
#         "chat_id": {
#             "en": "Chat ID", "pl": "ID czatu", "uk": "ID чату",
#             "ru": "ID чата", "ka": "ჩეთის ID"
#         },
#         "client_id_display": {
#             "en": "Client ID", "pl": "ID klienta", "uk": "ID клієнта",
#             "ru": "ID клиента", "ka": "კლიენტის ID"
#         },
#         "client_source_display": {
#             "en": "Client Source", "pl": "Źródło klienta", "uk": "Джерело клієнта",
#             "ru": "Источник клиента", "ka": "კლიენტის წყარო"
#         },
#         "company_name": {
#             "en": "Company Name", "pl": "Nazwa firmy", "uk": "Назва компанії",
#             "ru": "Название компании", "ka": "კომპანიის სახელი"
#         },
#         "status_display": {
#             "en": "Status", "pl": "Status", "uk": "Статус",
#             "ru": "Статус", "ka": "სტატუსი"
#         },
#         "status_emoji": {
#             "en": "Status Emoji", "ru": "Эмодзи статуса"
#         },
#         "duration_display": {
#             "en": "Duration", "pl": "Czas trwania", "uk": "Тривалість",
#             "ru": "Длительность", "ka": "ხანგრძილობა"
#         },
#         "participants_display": {
#             "en": "Participants", "ru": "Участники"
#         },
#         "created_at": {
#             "en": "Created At", "pl": "Utworzono", "uk": "Створено",
#             "ru": "Создано", "ka": "შექმნის დრო"
#         },
#         "last_activity": {
#             "en": "Last Activity", "pl": "Ostatnia aktywność", "uk": "Остання активність",
#             "ru": "Последняя активность", "ka": "ბოლო აქტივობა"
#         },
#         "admin_marker": {
#             "en": "Admin Marker", "pl": "Znacznik administratora", "uk": "Позначка адміністратора",
#             "ru": "Админская метка", "ka": "ადმინის მარკერი"
#         },
#         "read_state": {
#             "en": "Read Status", "pl": "Stan przeczytania", "uk": "Статус прочитання",
#             "ru": "Прочитано кем", "ka": "წაკითხვის სტატუსი"
#         }
#     }

#     # отображение и поведение
#     list_display = [
#         "chat_id", "client_id_display", "client_source_display",
#         "company_name", "status_emoji", "status_display",
#         "duration_display", "participants_display",
#         "created_at", "admin_marker"
#     ]
#     detail_fields = list_display + ["read_state"]
#     computed_fields = [
#         "client_id_display", "client_source_display",
#         "status_display", "status_emoji",
#         "duration_display", "participants_display"
#     ]
#     read_only_fields = ["created_at", "last_activity"]
#     inlines = {"messages": ChatMessageInline, "client": ClientInline}

#     STATUS_EMOJI_MAP = {
#         # Brief / анкетирование
#         "Brief In Progress": "📋🛠️",
#         "Brief Completed": "📋✅",

#         # Новая сессия
#         "New Session": "💬🆕",

#         # AI и авто
#         "Waiting for AI": "🤖⏳",
#         "Waiting for Client (AI)": "🤖✅",

#         # Консультант
#         "Waiting for Consultant": "👨‍⚕️❗",
#         "Read by Consultant": "👨‍⚕️⚠️",
#         "Waiting for Client": "👨‍⚕️✅",

#         # Завершено
#         "Closed – No Messages": "📪🚫",
#         "Closed by Timeout": "📪⌛️",
#         "Closed by Operator": "📪🔒"
#     }

#     async def get_queryset(
#         self,
#         filters: Optional[dict] = None,
#         sort_by: Optional[str] = None,
#         order: int = 1,
#         page: Optional[int] = None,
#         page_size: Optional[int] = None,
#         current_user: Optional[dict] = None,
#         format: bool = True
#     ) -> List[dict]:
#         """
#         Базовая выборка по чатам.
#         По умолчанию показываем только чаты, где уже есть сообщения.
#         Если sort_by не указан или равен "updated_at", сортируем по последнему клиентскому сообщению.
#         Для demo_admin ограничиваем список клиентами этого пользователя.
#         """
#         filters = filters or {}
#         filters["messages"] = {"$exists": True, "$ne": []}

#         # Ограничение для демо-админа
#         if current_user and getattr(current_user, "role", None) == "demo_admin":
#             current_user_id = current_user.data.get("user_id")
#             if not current_user_id:
#                 return []
#             master_clients = await mongo_db.clients.find(
#                 {"user_id": current_user_id}, {"client_id": 1}
#             ).to_list(None)
#             allowed_client_ids = [c["client_id"] for c in master_clients]
#             if allowed_client_ids:
#                 filters["client.client_id"] = {"$in": allowed_client_ids}
#             else:
#                 return []

#         is_updated_at_sort = not sort_by or sort_by == "updated_at"

#         if not is_updated_at_sort:
#             return await super().get_queryset(
#                 filters=filters, sort_by=sort_by, order=order,
#                 page=page, page_size=page_size,
#                 current_user=current_user, format=format
#             )

#         # Своя сортировка по "последнему клиентскому сообщению"
#         raw_docs = await super().get_queryset(
#             filters=filters, sort_by=None, order=order, page=None, page_size=None,
#             current_user=current_user, format=False
#         )

#         def get_updated_at(doc: dict) -> datetime:
#             messages = doc.get("messages") or []
#             for msg in reversed(messages):
#                 role = msg.get("sender_role")
#                 if isinstance(role, str):
#                     try:
#                         role = json.loads(role)
#                     except Exception:
#                         continue
#                 if isinstance(role, dict) and role.get("en") == SenderRole.CLIENT.en_value:
#                     return msg.get("timestamp") or doc.get("last_activity") or doc.get("created_at")
#             return doc.get("last_activity") or doc.get("created_at")

#         raw_docs.sort(key=get_updated_at, reverse=(order == -1))

#         if page is not None and page_size:
#             start, end = (page - 1) * page_size, (page - 1) * page_size + page_size
#             raw_docs = raw_docs[start:end]

#         if not format:
#             return raw_docs

#         # Параллельное форматирование документов
#         return await asyncio.gather(*(self.format_document(d, current_user) for d in raw_docs))

#     # вычисляемые поля

#     async def get_status_display(self, obj: dict, current_user=None) -> str:
#         """Возвращает i18n-значение статуса (dict или JSON-str в зависимости от enum-реализации)."""
#         chat_session = ChatSession(**obj)
#         redis_key = f"chat:session:{chat_session.chat_id}"
#         status = await calculate_chat_status(chat_session, redis_key)
#         return status.value

#     async def get_status_emoji(self, obj: dict, current_user=None) -> str:
#         """Подбирает эмодзи по английской метке статуса."""
#         status_value = await self.get_status_display(obj)  # dict или JSON-str
#         try:
#             status_json = json.loads(status_value) if isinstance(status_value, str) else status_value
#         except Exception:
#             return "❓"

#         en_label = status_json.get("en") if isinstance(status_json, dict) else None
#         return self.STATUS_EMOJI_MAP.get(en_label, "❓")

#     async def get_duration_display(self, obj: dict, current_user=None) -> str:
#         """Форматирует длительность как 'Xh Ym' / 'Xч Yм'."""
#         created_at, last_activity = obj.get("created_at"), obj.get("last_activity")
#         if not created_at or not last_activity:
#             return json.dumps({"en": "0h 0m", "ru": "0ч 0м"}, ensure_ascii=False, cls=DateTimeEncoder)
#         duration = last_activity - created_at
#         hours, remainder = divmod(duration.total_seconds(), 3600)
#         minutes, _ = divmod(remainder, 60)
#         return json.dumps(
#             {"en": f"{int(hours)}h {int(minutes)}m",
#              "ru": f"{int(hours)}ч {int(minutes)}м"},
#             ensure_ascii=False, cls=DateTimeEncoder
#         )

#     async def get_client_id_display(self, obj: dict, current_user=None) -> str:
#         """Возвращает нормализованный client_id из мастер-клиента (если есть)."""
#         client_data = obj.get("client")
#         value = "N/A"
#         if isinstance(client_data, dict):
#             client = Client(**client_data)
#             master = await get_master_client_by_id(client.client_id)
#             if master:
#                 value = master.client_id
#         return value

#     async def get_client_source_display(self, obj: dict, current_user=None) -> str:
#         """Возвращает человекочитаемый источник клиента (en/ru), сериализованный в JSON."""
#         client_data = obj.get("client")
#         value = "Unknown"
#         if isinstance(client_data, dict):
#             client = Client(**client_data)
#             src = client.source
#             try:
#                 if isinstance(src, str):
#                     parsed = json.loads(src)
#                     value = parsed.get("en") or parsed.get("ru") or "Unknown"
#                 elif isinstance(src, dict):
#                     value = src.get("en") or src.get("ru") or "Unknown"
#                 else:
#                     parsed = json.loads(getattr(src, "value", "{}"))
#                     value = parsed.get("en") or parsed.get("ru") or "Unknown"
#             except Exception:
#                 value = "Unknown"
#         return json.dumps(value, ensure_ascii=False, cls=DateTimeEncoder)

#     async def get_participants_display(self, obj: dict, current_user=None) -> str:
#         """
#         Возвращает список участников с дополнительными данными отправителей.
#         JSON-строка, где каждый элемент включает client_id и sender_info.
#         """
#         messages = obj.get("messages", [])
#         if not messages:
#             return json.dumps([], ensure_ascii=False, cls=DateTimeEncoder)

#         sender_data = await build_sender_data_map(
#             messages,
#             extra_client_id=obj.get("client", {}).get("client_id")
#         )
#         participants = [{"client_id": cid, "sender_info": data} for cid, data in sender_data.items()]
#         return json.dumps(participants, ensure_ascii=False, cls=DateTimeEncoder)



class ChatSessionAdmin(BaseAdmin):
    """Админ для сессий чата. Поиск/фильтры/сортировка из базового ядра."""

    model = ChatSession
    collection_name = "chats"
    permission_class = OperatorPermission()
    icon = "pi pi-comments"

    verbose_name = {
        "en": "Chat Session", "pl": "Sesja czatu", "uk": "Сесія чату",
        "ru": "Сессия чата", "ka": "ჩეთის სესია"
    }
    plural_name = {
        "en": "Chat Sessions", "pl": "Sesje czatu", "uk": "Сесії чату",
        "ru": "Сессии чата", "ka": "ჩეთის სესიები"
    }

    field_titles = {
        "chat_id": {"en": "Chat ID", "pl": "ID czatu", "uk": "ID чату", "ru": "ID чата", "ka": "ჩეთის ID"},
        "client_id_display": {"en": "Client ID", "pl": "ID klienta", "uk": "ID клієнта", "ru": "ID клиента", "ka": "კლიენტის ID"},
        "client_source_display": {"en": "Client Source", "pl": "Źródło klienta", "uk": "Джерело клієнта", "ru": "Источник клиента", "ka": "კლიენტის წყარო"},
        "company_name": {"en": "Company", "pl": "Firma", "uk": "Компанія", "ru": "Компания", "ka": "კომპანია"},
        "status_display": {"en": "Status", "pl": "Status", "uk": "Статус", "ru": "Статус", "ka": "სტატუსი"},
        "status_emoji": {"en": "Status Emoji", "pl": "Emoji statusu", "uk": "Емодзі статусу", "ru": "Эмодзи статуса", "ka": "სტატუსის ემოჯი"},
        "duration_display": {"en": "Duration", "pl": "Czas trwania", "uk": "Тривалість", "ru": "Длительность", "ka": "ხანგრძლივობა"},
        "participants_display": {"en": "Participants", "pl": "Uczestnicy", "uk": "Учасники", "ru": "Участники", "ka": "მონაწილეები"},
        "created_at": {"en": "Created", "pl": "Utworzono", "uk": "Створено", "ru": "Создано", "ka": "შექმნის დრო"},
        "last_activity": {"en": "Last Activity", "pl": "Ostatnia aktywność", "uk": "Остання активність", "ru": "Последняя активность", "ka": "ბოლო აქტივობა"},
        "admin_marker": {"en": "Admin Marker", "pl": "Znacznik administratora", "uk": "Позначка адміністратора", "ru": "Админская метка", "ka": "ადმინის მარკერი"},
        "read_state": {"en": "Read Status", "pl": "Stan przeczytania", "uk": "Статус прочитання", "ru": "Прочитано кем", "ka": "წაკითხვის სტატუსი"},
        "updated_at": {"en": "Updated", "pl": "Zaktualizowano", "uk": "Оновлено", "ru": "Обновлён", "ka": "განახლდა"},
        "is_unanswered": {"en": "Unanswered", "pl": "Bez odpowiedzi", "uk": "Без відповіді", "ru": "Неотвечён", "ka": "უპასუხო"}
    }

    list_display = [
        "chat_id", "client_id_display", "client_source_display",
        "company_name", "status_emoji", "status_display",
        "duration_display", "participants_display",
        "created_at", "admin_marker"
    ]
    detail_fields = list_display + ["read_state"]
    computed_fields = [
        "client_id_display", "client_source_display",
        "status_display", "status_emoji",
        "duration_display", "participants_display",
        "updated_at", "is_unanswered",
    ]
    read_only_fields = ["created_at", "last_activity"]
    inlines = {"messages": ChatMessageInline, "client": ClientInline}

    # Поиск: лучше через декларативный конфиг (lookup по имени клиента)
    search_config = {
        "mode": "partial",
        "logic": "or",
        "fields": [
            {"path": "messages.message"},
            {"path": "company_name"},
            {"path": "chat_id"},
            {"lookup": {
                "collection": "master_clients",
                "query_field": "name",
                "project_field": "client_id",
                "map_to": "client.client_id",
                "operator": "regex"
            }}
        ]
    }

    # Оставлю и классический список на всякий случай
    search_fields = [
        "messages.message",
        "company_name",
        "chat_id",
    ]
    searchable_computed_fields = ["is_unanswered"]
    default_search_mode = "partial"
    default_search_combine = "or"

    filter_config = {
        "channel": {
            "type": "multienum",
            "title": {
                "en": "Channel", "pl": "Kanał", "uk": "Канал", "ru": "Канал", "ka": "არხი"
            },
            "paths": ["client.source.en", "client.source"],
            "choices": [
                {"value": "Telegram",  "title": {"en": "Telegram",  "pl": "Telegram",  "uk": "Telegram",  "ru": "Telegram",  "ka": "ტელეგრამი"}},
                {"value": "WhatsApp",  "title": {"en": "WhatsApp",  "pl": "WhatsApp",  "uk": "WhatsApp",  "ru": "WhatsApp",  "ka": "უოთსაპი"}},
                {"value": "Web",       "title": {"en": "Website",   "pl": "Strona",    "uk": "Сайт",      "ru": "Сайт",     "ka": "ვებ-საიტი"}},
                {"value": "Instagram", "title": {"en": "Instagram", "pl": "Instagram", "uk": "Instagram", "ru": "Instagram", "ka": "ინსტაგრამი"}},
                {"value": "Internal",  "title": {"en": "Internal",  "pl": "Wewnętrzny","uk": "Внутрішній","ru": "Внутренний","ka": "შიდა"}}
            ]
        },
        "date": {
            "type": "daterange",
            "title": {
                "en": "Date", "pl": "Data", "uk": "Дата", "ru": "Дата", "ka": "თარიღი"
            },
            "field_choices": [
                {"value": "updated", "map_to": "last_activity", "title": {"en": "Last activity", "pl": "Ostatnia aktywność", "uk": "Остання активність", "ru": "Последняя активность", "ka": "ბოლო აქტივობა"}},
                {"value": "created", "map_to": "created_at",    "title": {"en": "Created",       "pl": "Utworzono",         "uk": "Створено",           "ru": "Создано",            "ka": "შექმნის დრო"}}
            ],
            "default_field": "last_activity",
            # фронт пришлёт либо {"preset": {"value": "week"}}, либо {"from": ..., "to": ...}
            "choices": [
                {"value": "week",  "title": {"en": "Last 7 days",  "pl": "Ostatnie 7 dni",  "uk": "Останні 7 днів",  "ru": "Последние 7 дней",  "ka": "ბოლო 7 დღე"}},
                {"value": "month", "title": {"en": "Last 30 days", "pl": "Ostatnie 30 dni", "uk": "Останні 30 днів", "ru": "Последние 30 дней", "ka": "ბოლო 30 დღე"}},
                {"value": "3m",    "title": {"en": "Last 3 months","pl": "Ostatnie 3 mies.", "uk": "Останні 3 міс.", "ru": "Последние 3 месяца","ka": "ბოლო 3 თვე"}}
            ]
        },
        "client_type": {
            "type": "multienum",
            "title": {
                "en": "Type", "pl": "Typ", "uk": "Тип", "ru": "Тип", "ka": "ტიპი"
            },
            "paths": ["client.metadata.type", "metadata.client_type"],
            "choices": [
                {"value": "lead",    "title": {"en": "Lead",     "pl": "Lead",     "uk": "Лід",     "ru": "Лид",     "ka": "ლიდი"}},
                {"value": "account", "title": {"en": "Account",  "pl": "Konto",    "uk": "Кабінет", "ru": "Клиент ЛК","ka": "კაბინეტი"}}
            ]
        },
        "status": {
            "kind": "computed_to_search",
            "title": {"en": "Answer", "pl": "Odpowiedź", "uk": "Відповідь", "ru": "Ответ", "ka": "პასუხი"},
            "mapping": {
                "unanswered": {
                    "title": {"en": "Unanswered", "pl": "Bez odpowiedzi", "uk": "Без відповіді", "ru": "Неотвечён", "ka": "უპასუხო"},
                    "__search": {"q": "true",  "mode": "exact", "fields": ["is_unanswered"]}
                },
                "answered": {
                    "title": {"en": "Answered", "pl": "Odpowiedziane", "uk": "Відповідь надана", "ru": "Отвечён", "ka": "პასუხგაცემული"},
                    "__search": {"q": "false", "mode": "exact", "fields": ["is_unanswered"]}
                }
            }
        }
    }

    sort_config = {
        "default_field": "updated_at",
        "default_order": -1,
        "allow": ["updated_at", "last_activity", "created_at"],
        "strategies": {
            "updated_at": {
                "type": "array_last_match_ts",
                "array": "messages",
                "role_field": "sender_role",
                "role_value": "client",
                "timestamp_field": "timestamp",
                "fallbacks": ["last_activity", "created_at"]
            }
        }
    }

    STATUS_EMOJI_MAP = {
        "Brief In Progress": "📋🛠️",
        "Brief Completed": "📋✅",
        "New Session": "💬🆕",
        "Waiting for AI": "🤖⏳",
        "Waiting for Client (AI)": "🤖✅",
        "Waiting for Consultant": "👨‍⚕️❗",
        "Read by Consultant": "👨‍⚕️⚠️",
        "Waiting for Client": "👨‍⚕️✅",
        "Closed – No Messages": "📪🚫",
        "Closed by Timeout": "📪⌛️",
        "Closed by Operator": "📪🔒"
    }

    async def get_status_display(self, obj: dict, current_user=None) -> dict:
        chat_session = ChatSession(**obj)
        redis_key = f"chat:session:{chat_session.chat_id}"
        status = await calculate_chat_status(chat_session, redis_key)
        val = status.value
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except Exception:
                val = {"en": str(val)}
        return val


    async def get_status_emoji(self, obj: dict, current_user=None) -> str:
        status_value = await self.get_status_display(obj)
        en_label = None
        if isinstance(status_value, dict):
            en_label = status_value.get("en")
        return self.STATUS_EMOJI_MAP.get(en_label, "❓")


    async def get_duration_display(self, obj: dict, current_user=None) -> dict:
        created_at, last_activity = obj.get("created_at"), obj.get("last_activity")
        if not created_at or not last_activity:
            return {"en": "0h 0m", "ru": "0ч 0м", "pl": "0g 0m", "uk": "0г 0хв", "ka": "0სთ 0წთ"}
        duration = last_activity - created_at
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        return {
            "en": f"{int(hours)}h {int(minutes)}m",
            "ru": f"{int(hours)}ч {int(minutes)}м",
            "pl": f"{int(hours)}g {int(minutes)}m",
            "uk": f"{int(hours)}г {int(minutes)}хв",
            "ka": f"{int(hours)}სთ {int(minutes)}წთ"
        }

    async def get_client_id_display(self, obj: dict, current_user=None) -> str:
        client_data = obj.get("client")
        value = "N/A"
        if isinstance(client_data, dict):
            client = Client(**client_data)
            master = await get_master_client_by_id(client.client_id)
            if master:
                value = master.client_id
        return value

    async def get_client_source_display(self, obj: dict, current_user=None) -> str:
        client_data = obj.get("client")
        value = "Unknown"
        if isinstance(client_data, dict):
            client = Client(**client_data)
            src = client.source
            try:
                if isinstance(src, str):
                    parsed = json.loads(src)
                    value = parsed.get("en") or parsed.get("ru") or "Unknown"
                elif isinstance(src, dict):
                    value = src.get("en") or src.get("ru") or "Unknown"
                else:
                    parsed = json.loads(getattr(src, "value", "{}"))
                    value = parsed.get("en") or parsed.get("ru") or "Unknown"
            except Exception:
                value = "Unknown"
        return value

    async def get_participants_display(self, obj: dict, current_user=None) -> str:
        messages = obj.get("messages", [])
        if not messages:
            return json.dumps([], ensure_ascii=False, cls=DateTimeEncoder)
        sender_data = await build_sender_data_map(messages, extra_client_id=obj.get("client", {}).get("client_id"))
        participants = [{"client_id": cid, "sender_info": data} for cid, data in sender_data.items()]
        return json.dumps(participants, ensure_ascii=False, cls=DateTimeEncoder)

    async def get_updated_at(self, obj: dict, current_user=None) -> datetime:
        def role_en(msg_role) -> str:
            try:
                return json.loads(msg_role)["en"] if isinstance(msg_role, str) else msg_role.en_value
            except Exception:
                return "Unknown"
        messages = obj.get("messages") or []
        for msg in reversed(messages):
            role = msg.get("sender_role")
            if role_en(role) == SenderRole.CLIENT.en_value:
                return msg.get("timestamp") or obj.get("last_activity") or obj.get("created_at")
        return obj.get("last_activity") or obj.get("created_at") or datetime.utcnow()

    async def get_is_unanswered(self, obj: dict, current_user=None) -> bool:
        def role_en(msg_role) -> str:
            try:
                return json.loads(msg_role)["en"] if isinstance(msg_role, str) else msg_role.en_value
            except Exception:
                return "Unknown"
        msgs = obj.get("messages") or []
        if not msgs:
            return False
        last_role = role_en(msgs[-1].get("sender_role"))
        return last_role == SenderRole.CLIENT.en_value

    @admin_route(
        path="/unanswered_count",
        method="GET",
        auth=True,
        permission_action="read",
        summary="Unanswered chats count",
        description="Количество неотвеченных чатов с учётом активных фильтров/поиска.",
        tags=["stats"],
        status_code=200,
        response_model=None,
        name="chat_sessions_unanswered_count",
    )
    async def unanswered_count(self, *, data: dict, current_user: Any, request, path_params, query_params):
        raw_filters = query_params.get("filters")
        raw_search = query_params.get("search")
        raw_q = query_params.get("q")

        parsed_filters: Optional[dict] = None
        if raw_filters:
            try:
                parsed_filters = json.loads(raw_filters)
            except Exception:
                raise Exception("Invalid filters JSON")

        parsed_search: Optional[dict] = None
        if raw_search:
            try:
                parsed_search = json.loads(raw_search) if str(raw_search).strip().startswith("{") else {"q": str(raw_search)}
            except Exception:
                parsed_search = {"q": str(raw_search)}
        elif raw_q:
            parsed_search = {"q": str(raw_q)}

        combined = {"__filters": parsed_filters or {}, "__search": parsed_search or {}} if (parsed_filters or parsed_search) else {}

        base_filter = await self.permission_class.get_base_filter(current_user)
        plain, search_params, filter_params = self.extract_advanced(combined)
        mongo_filters, post_filters = await self.build_mongo_filters(filter_params, current_user)
        search_mongo, computed_for_search, q, mode, combine = await self.build_declarative_search(search_params)

        query: Dict[str, Any] = {**(plain or {}), **base_filter, **mongo_filters}
        if search_mongo:
            query = {"$and": [query, search_mongo]} if query else search_mongo

        query = {"$and": [query, {"messages": {"$exists": True, "$ne": []}}]} if query else {"messages": {"$exists": True, "$ne": []}}

        raw_docs: List[dict] = [d async for d in self.db.find(query)]

        if computed_for_search:
            flags = await asyncio.gather(*[
                self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in raw_docs
            ])
            raw_docs = [d for d, ok in zip(raw_docs, flags) if ok]

        flags = await asyncio.gather(*[self.get_is_unanswered(d) for d in raw_docs])
        count = sum(1 for x in flags if x)
        return {"count": count}



admin_registry.register("chat_sessions", ChatSessionAdmin(mongo_db))
# Временно уберем сообщения и клиентов из админки
# admin_registry.register("clients", ClientInline(mongo_db))
# admin_registry.register("chat_messages", ChatMessageInline(mongo_db))
