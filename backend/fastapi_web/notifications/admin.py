# admin/apps/notifications/admin.py
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException

from crud_core.decorators import admin_route
from admin_core.base_admin import BaseCrud
from crud_core.permissions import AllowAll  # при необходимости замени
from .db.mongo.schemas import Notification
from .db.mongo.enums import Priority, NotificationChannel
from crud_core.registry import admin_registry
from db.mongo.db_init import mongo_db


class NotificationAdmin(BaseCrud):
    model = Notification
    collection_name = "notifications"
    permission_class = AllowAll()  # можно заменить на OperatorPermission()
    icon = "pi pi-bell"

    verbose_name = {
        "en": "Notification",
        "pl": "Powiadomienie",
        "uk": "Сповіщення",
        "ru": "Уведомление",
        "ka": "შეტყობინება",
    }
    plural_name = {
        "en": "Notifications",
        "pl": "Powiadomienia",
        "uk": "Сповіщення",
        "ru": "Уведомления",
        "ka": "შეტყობინებები",
    }

    list_display = [
        "created_at",
        "priority",
        "deliver_to",
        "kind",
        "message",
        "entity_display",
        "link_url",
        "is_read_for_current",
    ]
    detail_fields = list_display + ["meta"]
    computed_fields = ["entity_display", "is_read_for_current"]
    read_only_fields = ["created_at", "read_receipts"]

    field_titles = {
        "created_at": {
            "en": "Created",
            "pl": "Utworzono",
            "uk": "Створено",
            "ru": "Создано",
            "ka": "შექმნის დრო",
        },
        "priority": {
            "en": "Priority",
            "pl": "Priorytet",
            "uk": "Пріоритет",
            "ru": "Приоритет",
            "ka": "პრიორიტეტი",
        },
        "deliver_to": {
            "en": "Channels",
            "pl": "Kanały",
            "uk": "Канали",
            "ru": "Каналы",
            "ka": "არხები",
        },
        "kind": {
            "en": "Type Code",
            "pl": "Kod typu",
            "uk": "Код типу",
            "ru": "Код типа",
            "ka": "ტიპის კოდი",
        },
        "title": {
            "en": "Title",
            "pl": "Tytuł",
            "uk": "Заголовок",
            "ru": "Заголовок",
            "ka": "სათაური",
        },
        "message": {
            "en": "Message",
            "pl": "Wiadomość",
            "uk": "Повідомлення",
            "ru": "Сообщение",
            "ka": "შეტყობინება",
        },
        "entity": {
            "en": "Entity",
            "pl": "Encja",
            "uk": "Сутність",
            "ru": "Сущность",
            "ka": "ობიექტი",
        },
        "entity_display": {
            "en": "Entity",
            "pl": "Encja",
            "uk": "Сутність",
            "ru": "Сущность",
            "ka": "ობიექტი",
        },
        "link_url": {
            "en": "Link",
            "pl": "Link",
            "uk": "Посилання",
            "ru": "Ссылка",
            "ka": "ბმული",
        },
        "is_read_for_current": {
            "en": "Read (by me)",
            "pl": "Przeczytane (przeze mnie)",
            "uk": "Прочитано (мною)",
            "ru": "Прочитано мной",
            "ka": "წაკითხულია (ჩემ poolt)",
        },
        "read_receipts": {
            "en": "Read Receipts",
            "pl": "Potwierdzenia odczytu",
            "uk": "Відмітки про прочитання",
            "ru": "Кто прочитал",
            "ka": "ვინც წაიკითხა",
        },
        "meta": {
            "en": "Metadata",
            "pl": "Metadane",
            "uk": "Метадані",
            "ru": "Метаданные",
            "ka": "მეტამონაცემები",
        },
    }
    
    async def get_field_overrides(self, obj=None, current_user=None) -> dict:
        """
        Заполняет choices для multiselect «consents».
        """
        return {"is_read_for_current": {"type": "boolean", "settings": {
                "type": "boolean",}}}
    
    # ---------- computed ----------
    async def get_is_read_for_current(self, obj: dict, current_user=None) -> bool:
        if not current_user:
            return False
        uid = str(getattr(current_user, "id", None) or current_user.data.get("user_id"))
        if not uid:
            return False
        for rr in (obj.get("read_receipts") or []):
            if (rr.get("user_id") or "") == uid:
                return True
        return False

    async def get_entity_display(self, obj: dict, current_user=None) -> str:
        e = obj.get("entity") or {}
        et, eid = e.get("entity_type") or "—", e.get("entity_id") or "—"
        return f"{et}:{eid}"

    # ---------- Search / Filters / Sort ----------
    search_config = {
        "mode": "partial",
        "logic": "and",
        "fields": [
            {"path": "kind"},
            {"path": "message"},
            {"path": "title.en"},
            {"path": "title.pl"},
            {"path": "title.uk"},
            {"path": "title.ru"},
            {"path": "title.ka"},
            {"path": "entity.entity_type"},
            {"path": "entity.entity_id"},
            {"path": "deliver_to.en"},
            {
                "lookup": {
                    "collection": "users",
                    "query_field": "full_name",
                    "project_field": "_id",
                    "map_to": "recipient_user_id",
                    "operator": "regex",
                }
            },
        ],
    }

    filter_config = {
        "priority": {
            "type": "multienum",
            "title": {
                "en": "Priority",
                "pl": "Priorytet",
                "uk": "Пріоритет",
                "ru": "Приоритет",
                "ka": "პრიორიტეტი",
            },
            "paths": ["priority.en", "priority"],
            "choices": [
                {
                    "value": "Low",
                    "title": {"en": "Low", "pl": "Niski", "uk": "Низький", "ru": "Низкий", "ka": "დაბალი"},
                },
                {
                    "value": "Normal",
                    "title": {"en": "Normal", "pl": "Normalny", "uk": "Звичайний", "ru": "Обычный", "ka": "ჩვეულებრივი"},
                },
                {
                    "value": "High",
                    "title": {"en": "High", "pl": "Wysoki", "uk": "Високий", "ru": "Высокий", "ka": "მაღალი"},
                },
                {
                    "value": "Critical",
                    "title": {"en": "Critical", "pl": "Krytyczny", "uk": "Критичний", "ru": "Критичный", "ka": "კრიტიკული"},
                },
            ],
        },
        "channel": {
            "type": "multienum",
            "title": {"en": "Channel", "pl": "Kanał", "uk": "Канал", "ru": "Канал", "ka": "არხი"},
            "paths": ["deliver_to.en", "deliver_to"],
            "choices": [
                {
                    "value": "Web (in-app)",
                    "title": {
                        "en": "Web (in-app)",
                        "pl": "Web (w systemie)",
                        "uk": "Web (у системі)",
                        "ru": "Web (в системе)",
                        "ka": "Web (სისტემაში)",
                    },
                },
                {
                    "value": "Telegram",
                    "title": {"en": "Telegram", "pl": "Telegram", "uk": "Telegram", "ru": "Telegram", "ka": "ტელეგრამი"},
                },
                {
                    "value": "Web Push",
                    "title": {"en": "Web Push", "pl": "Web Push", "uk": "Web Push", "ru": "Web Push", "ka": "Web Push"},
                },
                {
                    "value": "Windows Notify",
                    "title": {
                        "en": "Windows Notify",
                        "pl": "Powiadomienie Windows",
                        "uk": "Сповіщення Windows",
                        "ru": "Windows уведомление",
                        "ka": "Windows შეტყობინება",
                    },
                },
                {
                    "value": "Email",
                    "title": {"en": "Email", "pl": "Email", "uk": "Email", "ru": "Email", "ka": "ელფოსტა"},
                },
            ],
        },
        "recipient": {
            "type": "generic",
            "title": {
                "en": "Recipient (user_id)",
                "pl": "Odbiorca (user_id)",
                "uk": "Одержувач (user_id)",
                "ru": "Получатель (user_id)",
                "ka": "მიმღები (user_id)",
            },
            "paths": ["recipient_user_id"],
        },
        "created": {
            "type": "range",
            "title": {"en": "Created", "pl": "Utworzono", "uk": "Створено", "ru": "Создано", "ka": "შექმნის დრო"},
            "paths": ["created_at"],
        },
        "entity_type": {
            "type": "generic",
            "title": {
                "en": "Entity Type",
                "pl": "Typ encji",
                "uk": "Тип сутності",
                "ru": "Тип сущности",
                "ka": "ობიექტის ტიპი",
            },
            "paths": ["entity.entity_type"],
        },
        "unread_for_me": {
            "kind": "computed_to_search",
            "title": {
                "en": "Unread for me",
                "pl": "Nieprzeczytane przeze mnie",
                "uk": "Непрочитано мною",
                "ru": "Непрочитано мной",
                "ka": "ჩემთვის წაუკითხავი",
            },
            "mapping": {
                "yes": {
                    "title": {"en": "Yes", "pl": "Tak", "uk": "Так", "ru": "Да", "ka": "დიახ"},
                    "__search": {"q": "false", "mode": "exact", "fields": ["is_read_for_current"]},
                },
                "no": {
                    "title": {"en": "No", "pl": "Nie", "uk": "Ні", "ru": "Нет", "ka": "არა"},
                    "__search": {"q": "true", "mode": "exact", "fields": ["is_read_for_current"]},
                },
            },
        },
    }

    sort_config = {
        "default_field": "created_at",
        "default_order": -1,
        "allow": ["created_at", "priority", "kind"],
    }

    # ---------- авто-пометка «прочитано мной» ----------
    async def _mark_read_for_current_user(self, raw_docs: List[dict], current_user) -> int:
        if not current_user or not raw_docs:
            return 0
        uid = str(getattr(current_user, "id", None) or current_user.data.get("user_id"))
        if not uid:
            return 0
        to_mark: List[ObjectId] = []
        for d in raw_docs:
            rec = d.get("recipient_user_id")
            if rec is not None and str(rec) != uid:
                continue
            already = any((rr.get("user_id") or "") == uid for rr in (d.get("read_receipts") or []))
            if not already and d.get("_id"):
                to_mark.append(d["_id"])
        if not to_mark:
            return 0
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        res = await self.db.update_many(
            {"_id": {"$in": to_mark}},
            {"$addToSet": {"read_receipts": {"user_id": uid, "read_at": now}}},
        )
        return res.modified_count or 0

    async def list(self, sort_by=None, order=1, page=None, page_size=None, filters=None, current_user=None):
        raw = await super().get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
            current_user=current_user,
            format=False,
        )
        await self._mark_read_for_current_user(raw, current_user)
        return await super().get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
            current_user=current_user,
            format=True,
        )

    async def list_with_meta(self, page=1, page_size=100, sort_by=None, order=1, filters=None, current_user=None):
        _ = await super().list_with_meta(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            order=order,
            filters=filters,
            current_user=current_user,
        )
        raw = await super().get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
            current_user=current_user,
            format=False,
        )
        await self._mark_read_for_current_user(raw, current_user)
        return await super().list_with_meta(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            order=order,
            filters=filters,
            current_user=current_user,
        )

    # ---------- кастомные эндпоинты ----------
    @admin_route(
        path="/mark_read",
        method="POST",
        auth=True,
        permission_action="update",
        summary="Mark notifications read",
        description="Помечает указанные уведомления как прочитанные текущим пользователем.",
        tags=["actions"],
        status_code=200,
        response_model=None,
        name="notifications_mark_read",
    )
    async def mark_read(self, *, data: dict, current_user: Any, request, path_params, query_params):
        ids = data.get("ids") or []
        if not isinstance(ids, list):
            raise HTTPException(400, "ids must be a list")
        raw = [d async for d in self.db.find({"_id": {"$in": [ObjectId(i) for i in ids]}})]
        updated = await self._mark_read_for_current_user(raw, current_user)
        return {"updated": updated}

    @admin_route(
        path="/unread_count",
        method="GET",
        auth=True,
        permission_action="read",
        summary="Unread count (for me)",
        description="Количество непрочитанных для текущего пользователя с учётом фильтров/поиска.",
        tags=["stats"],
        status_code=200,
        response_model=None,
        name="notifications_unread_count",
    )
    async def unread_count(self, *, data: dict, current_user: Any, request, path_params, query_params):
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
                parsed_search = (
                    json.loads(raw_search) if str(raw_search).strip().startswith("{") else {"q": str(raw_search)}
                )
            except Exception:
                parsed_search = {"q": str(raw_search)}
        elif raw_q:
            parsed_search = {"q": str(raw_q)}

        combined = (
            {"__filters": parsed_filters or {}, "__search": parsed_search or {}}
            if (parsed_filters or parsed_search)
            else {}
        )

        base_filter = await self.permission_class.get_base_filter(current_user)
        plain, search_params, filter_params = self.extract_advanced(combined)
        mongo_filters, post_filters = await self.build_mongo_filters(filter_params, current_user)
        search_mongo, computed_for_search, plain_for_search, q, mode, combine = await self.build_declarative_search(
            search_params
        )

        query: Dict[str, Any] = {**(plain or {}), **base_filter, **mongo_filters}
        if search_mongo:
            query = {"$and": [query, search_mongo]} if query else search_mongo

        docs: List[dict] = [d async for d in self.db.find(query)]
        uid = str(getattr(current_user, "id", None) or current_user.data.get("user_id"))

        def is_mine_and_unread(d: dict) -> bool:
            rec = d.get("recipient_user_id")
            if rec is not None and str(rec) != uid:
                return False
            rrs = d.get("read_receipts") or []
            return not any((rr.get("user_id") or "") == uid for rr in rrs)

        return {"count": sum(1 for d in docs if is_mine_and_unread(d))}


admin_registry.register("notifications", NotificationAdmin(mongo_db))
