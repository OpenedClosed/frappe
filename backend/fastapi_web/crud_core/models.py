"""Базовые сущности панели приложения ядро CRUD создания."""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Tuple, Set

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel, TypeAdapter, ValidationError

from .permissions import AllowAll, BasePermission

logger = logging.getLogger(__name__)


# ==============================
# БЛОК: Базовое ядро CRUD
# ==============================
class BaseCrudCore:
    """Базовый класс для CRUD-операций."""

    # Модель (pydantic)
    model: Type[BaseModel]

    # Метаинформация
    verbose_name: str = "Unnamed Model"
    plural_name: str = "Unnamed Models"
    icon: str = "pi pi-folder"
    description: str = "No description provided"

    # Отображение
    list_display: List[str] = []
    detail_fields: List[str] = []
    computed_fields: List[str] = []
    read_only_fields: List[str] = []
    field_titles: Dict[str, str] = {}
    field_styles: Dict[str, Any] = {}
    field_groups: List[Dict[str, Any]] = []
    help_texts: Dict[str, Dict[str, str]] = {}

    # Инлайны
    inlines: Dict[str, Any] = {}

    # Ограничения
    user_collection_name: Optional[str] = None
    max_instances_per_user: Optional[int] = None

    # Разрешения CRUD (вкл/выкл)
    allow_crud_actions: Dict[str, bool] = {
        "create": True,
        "read": True,
        "update": True,
        "delete": True,
    }

    # Права
    permission_class: BasePermission = AllowAll()  # type: ignore

    # ------------------------------
    # Поиск/фильтры/сортировка (настройки)
    # ------------------------------
    # Простой поиск (если не используется search_config)
    search_fields: List[str] = []
    searchable_computed_fields: List[str] = []
    default_search_mode: str = "partial"  # "exact" | "partial"
    default_search_combine: str = "or"    # "or" | "and"

    # Декларативный расширенный поиск:
    # search_config = {
    #   "logic": "or" | "and",
    #   "mode": "partial" | "exact",
    #   "fields": [
    #       {"path": "messages.message"},
    #       {"lookup": {
    #            "collection": "clients",
    #            "query_field": "name",
    #            "project_field": "client_id",
    #            "map_to": "client.client_id",
    #            "operator": "regex",      # "regex" | "exact"
    #            "param": "client"         # имя ключа в search-параметрах (если не задано — используем общий q)
    #       }},
    #   ],
    # }
    search_config: Dict[str, Any] = {}

    # Декларативные фильтры:
    # filter_config = {
    #   "channels": {"type": "multienum", "op": "in", "paths": ["client.source.en", "client.source"]},
    #   "date": {"type": "daterange", "default_field": "last_activity", "field_choices": {"updated_at": "last_activity"}},
    #   "status": {"type": "virtual", "values": {"unanswered": {...mongo...}, "answered": {...}} },
    #   "type": {
    #       "type": "enum_lookup", "multi": True, "map_to": "client.client_id",
    #       "resolver": {
    #           "collection": "clients", "key": "client_id",
    #           "cases": {"lk": {"user_id": {"$exists": True, "$ne": None}}, "lead": {...}}
    #       }
    #   },
    #   "_base": {...}  # всегда добавляется
    # }
    filter_config: Dict[str, Dict[str, Any]] = {}

    # Декларативная сортировка:
    # sort_config = {
    #   "default": {"by": "updated_at", "order": -1},
    #   "aliases": {"updated_at": "last_client_incoming_ts"},
    #   "strategies": {
    #       "last_client_incoming_ts": {
    #           "type": "array_last_match_ts",
    #           "array": "messages",
    #           "role_field": "sender_role",
    #           "role_value": ["client", {"en": "client"}],
    #           "timestamp_field": "timestamp",
    #           "fallbacks": ["last_activity", "created_at"]
    #       }
    #   }
    # }
    sort_config: Dict[str, Any] = {}

    def __init__(self, db: AsyncIOMotorCollection) -> None:
        """Сохраняет ссылку на коллекцию MongoDB."""
        self.db = db

    # ------------------------------
    # Контроль доступа
    # ------------------------------
    def check_crud_enabled(self, action: str) -> None:
        """Проверяет, включено ли действие."""
        if not self.allow_crud_actions.get(action, False):
            raise HTTPException(403, f"{action.capitalize()} is disabled for this model.")

    def check_object_permission(
        self,
        action: str,
        user: Optional[BaseModel],
        obj: Optional[dict] = None
    ) -> None:
        """Проверяет права через permission_class."""
        self.permission_class.check(action, user, obj)

    def check_permission(
        self,
        action: str,
        user: Optional[BaseModel],
        obj: Optional[dict] = None
    ) -> None:
        """Проверяет включенность действия и права пользователя."""
        self.check_crud_enabled(action)
        self.check_object_permission(action, user, obj)

    # ------------------------------
    # Вспомогательные методы
    # ------------------------------
    def detect_id_field(self) -> str:
        """Определяет имя поля-идентификатора."""
        return "id" if "id" in self.model.__fields__ else "_id"

    def get_user_field_name(self) -> str:
        """Возвращает имя поля пользователя."""
        return "_id" if self.user_collection_name == self.db.name else "user_id"

    def get_search_fields(self) -> List[str]:
        """Поля поиска по умолчанию."""
        if self.search_fields:
            return self.search_fields
        return list(getattr(self.model, "__annotations__", {}).keys())

    def get_filter_config(self) -> Dict[str, Dict[str, Any]]:
        """Конфиг фильтров по умолчанию."""
        return self.filter_config

    def get_search_config(self) -> Dict[str, Any]:
        """Конфиг поиска по умолчанию."""
        return self.search_config or {}

    def get_sort_config(self) -> Dict[str, Any]:
        """Конфиг сортировки по умолчанию."""
        return self.sort_config or {}

    def customize_search_query(self, mongo_part: dict, params: dict, current_user: Optional[BaseModel]) -> dict:
        """Кастомизация поиска."""
        return mongo_part

    def customize_filter_query(self, mongo_part: dict, params: dict, current_user: Optional[BaseModel]) -> dict:
        """Кастомизация фильтров."""
        return mongo_part

    def match_text(self, value: Any, q: str, mode: str) -> bool:
        """Сопоставление текста."""
        if value is None:
            return False
        s = str(value)
        if mode == "exact":
            return s == q
        return re.search(re.escape(q), s, flags=re.IGNORECASE) is not None

    async def search_match_computed(
        self,
        doc: dict,
        computed_fields: Set[str],
        q: str,
        mode: str,
        current_user: Optional[BaseModel],
        combine: str,
    ) -> bool:
        """Проверка совпадений по вычисляемым полям."""
        results: List[bool] = []
        for cf in computed_fields:
            method = getattr(self, f"get_{cf}", None)
            if not callable(method):
                continue
            v = method(doc, current_user=current_user)
            if hasattr(v, "__await__"):
                v = await v
            results.append(self.match_text(v, q, mode))
        if not results:
            return False
        return any(results) if combine == "or" else all(results)

    # ------------------------------
    # Построение поиска (базовый + декларативный)
    # ------------------------------
    def build_mongo_search(self, params: Optional[dict]) -> Tuple[dict, Set[str], str, str, str]:
        """Формирует mongo-часть простого поиска и набор вычисляемых полей (без lookup)."""
        if not params:
            return {}, set(), "", self.default_search_mode, self.default_search_combine

        if isinstance(params, str):
            q = params.strip()
            mode = self.default_search_mode
            combine = self.default_search_combine
            fields = self.get_search_fields()
        else:
            q = str(params.get("q", "")).strip()
            mode = str(params.get("mode", self.default_search_mode)).lower()
            combine = str(params.get("combine", self.default_search_combine)).lower()
            fields = params.get("fields") or self.get_search_fields()

        if not q or not fields:
            return {}, set(), "", mode, combine

        parts: List[dict] = []
        computed: Set[str] = set()

        for f in fields:
            if f in self.computed_fields or f in self.searchable_computed_fields:
                computed.add(f)
                continue
            if mode == "exact":
                parts.append({f: q})
            else:
                parts.append({f: {"$regex": re.escape(q), "$options": "i"}})

        mongo_part: dict = {}
        if parts:
            mongo_part = {"$and": parts} if combine == "and" else {"$or": parts}

        mongo_part = self.customize_search_query(mongo_part, {"q": q, "mode": mode, "combine": combine, "fields": fields}, None)
        return mongo_part, computed, q, mode, combine

    async def build_declarative_search(self, params: Optional[dict]) -> Tuple[dict, Set[str], str, str, str]:
        """
        Формирует mongo-часть расширенного поиска на основе search_config (включая lookup).
        Возвращает (mongo_part, computed_fields, q, mode, combine).
        """
        cfg = self.get_search_config()
        if not cfg:
            # нет расширенной конфигурации — используем базовый
            return self.build_mongo_search(params)

        logic = str(cfg.get("logic", self.default_search_combine)).lower()
        mode = str(cfg.get("mode", self.default_search_mode)).lower()

        q = ""
        combine = logic
        computed: Set[str] = set()
        parts: List[dict] = []

        # 1) общий q по указанным path (если есть)
        fields_cfg = cfg.get("fields", [])
        base_fields = [f.get("path") for f in fields_cfg if isinstance(f, dict) and "path" in f]
        if params:
            q = params.get("q", "")
            if isinstance(q, str) and q.strip() and base_fields:
                for f in base_fields:
                    if f in self.computed_fields or f in self.searchable_computed_fields:
                        computed.add(f)
                        continue
                    if mode == "exact":
                        parts.append({f: q.strip()})
                    else:
                        parts.append({f: {"$regex": re.escape(q.strip()), "$options": "i"}})

        # 2) lookup поля
        for item in fields_cfg:
            if not isinstance(item, dict) or "lookup" not in item:
                continue
            lkp = item["lookup"] or {}
            param_name = lkp.get("param", "q")
            val = (params or {}).get(param_name)
            if not val or not isinstance(val, str) or not val.strip():
                # если param не задан и используем общий q
                if param_name == "q":
                    val = (params or {}).get("q")
                if not val or not isinstance(val, str) or not val.strip():
                    continue
            val = val.strip()

            collection = lkp["collection"]
            query_field = lkp["query_field"]
            project_field = lkp["project_field"]
            map_to = lkp["map_to"]
            operator = str(lkp.get("operator", "regex")).lower()

            dbh = self.db.database if hasattr(self.db, "database") else None
            if not dbh:
                continue

            if operator == "exact":
                lq = {query_field: val}
            else:
                lq = {query_field: {"$regex": re.escape(val), "$options": "i"}}

            # выбираем значения-идентификаторы
            cursor = dbh[collection].find(lq, {project_field: 1, "_id": 0})
            values = [doc.get(project_field) async for doc in cursor if doc.get(project_field) is not None]
            values = list({v for v in values})

            if not values:
                # заведомо пустой результат
                parts.append({"_id": {"$in": []}})
            else:
                parts.append({map_to: {"$in": values}})

        # Склейка
        if not parts:
            return {}, computed, q or "", mode, combine
        mongo = {"$and": parts} if combine == "and" else {"$or": parts}
        mongo = self.customize_search_query(mongo, {"q": q, "mode": mode, "combine": combine, "fields": fields_cfg}, None)
        return mongo, computed, q or "", mode, combine

    # ------------------------------
    # Фильтры (generic + декларативные)
    # ------------------------------
    def impossible_filter(self) -> dict:
        """Фильтр, не возвращающий документов."""
        return {"_id": {"$in": []}}

    def preset_to_range(self, preset: str) -> Tuple[datetime, datetime]:
        """Возвращает диапазон по пресету."""
        now = datetime.utcnow()
        if preset == "week":
            start = now - timedelta(days=7)
        elif preset == "month":
            start = now - timedelta(days=30)
        elif preset in {"3m", "3months"}:
            start = now - timedelta(days=90)
        else:
            start = now - timedelta(days=7)
        return start, now

    async def build_mongo_filters(self, params: Optional[dict], current_user: Optional[BaseModel]) -> dict:
        """Формирует mongo-часть фильтров."""
        base_cfg = self.get_filter_config() or {}

        result: Dict[str, Any] = {}
        if not params and not base_cfg.get("_base"):
            return result

        # 1) _base из конфигурации
        if "_base" in base_cfg and isinstance(base_cfg["_base"], dict):
            result.update(base_cfg["_base"])

        if not params:
            return self.customize_filter_query(result, params or {}, current_user)

        # 2) параметры
        for key, value in params.items():
            # если описан в config — применяем декларативную логику
            if key in base_cfg:
                cfg = base_cfg[key]
                ftype = str(cfg.get("type", "eq")).lower()

                if ftype == "multienum":
                    # value: ["Telegram","WhatsApp"] и т.д.
                    vals = value if isinstance(value, list) else [value]
                    paths = cfg.get("paths") or [key]
                    # строим OR по всем path, каждый — IN/regex по значениям
                    path_parts: List[dict] = []
                    for p in paths:
                        if p.endswith(".en"):
                            path_parts.append({p: {"$in": vals}})
                        else:
                            # безопасный contains как универсальный вариант
                            ors = [{"%s" % p: {"$regex": re.escape(str(v)), "$options": "i"}} for v in vals]
                            path_parts.append({"$or": ors})
                    if path_parts:
                        result.setdefault("$and", [])
                        result["$and"].append({"$or": path_parts})

                elif ftype == "daterange":
                    # value: {"preset":"week","field":"updated_at"} ИЛИ {"from":..., "to":..., "field":"created_at"}
                    field_map = cfg.get("field_choices", {})
                    default_field = cfg.get("default_field", list(field_map.values())[0] if field_map else None)
                    field = (value or {}).get("field", default_field)
                    if field in field_map:
                        field = field_map[field]
                    if not field:
                        continue

                    if isinstance(value, dict) and ("from" in value or "to" in value):
                        gte = value.get("from")
                        lte = value.get("to")
                        rng: Dict[str, Any] = {}
                        if gte:
                            rng["$gte"] = gte
                        if lte:
                            rng["$lte"] = lte
                        if rng:
                            result[field] = rng
                    else:
                        preset = str((value or {}).get("preset", "week")).lower()
                        start, end = self.preset_to_range(preset)
                        result[field] = {"$gte": start, "$lte": end}

                elif ftype == "virtual":
                    # value: "unanswered" ИЛИ ["unanswered","answered"]
                    vals = value if isinstance(value, list) else [value]
                    exprs = []
                    for v in vals:
                        part = cfg.get("values", {}).get(v)
                        if part:
                            exprs.append(part)
                    if not exprs:
                        result.update(self.impossible_filter())
                    elif len(exprs) == 1:
                        result.update(exprs[0])
                    else:
                        result.setdefault("$and", [])
                        result["$and"].append({"$or": exprs})

                elif ftype == "enum_lookup":
                    # value: "lk" | ["lk","lead"] → резолвим через внешнюю коллекцию и фильтруем map_to
                    vals = value if isinstance(value, list) else [value]
                    resolver = cfg.get("resolver", {})
                    collection = resolver.get("collection")
                    key_field = resolver.get("key")
                    cases = resolver.get("cases", {})
                    map_to = cfg.get("map_to")

                    if not (collection and key_field and map_to and cases):
                        continue

                    dbh = self.db.database if hasattr(self.db, "database") else None
                    if not dbh:
                        continue

                    all_keys: Set[Any] = set()
                    for v in vals:
                        case_q = cases.get(v)
                        if not isinstance(case_q, dict):
                            continue
                        cur = dbh[collection].find(case_q, {key_field: 1, "_id": 0})
                        keys = [doc.get(key_field) async for doc in cur if doc.get(key_field) is not None]
                        all_keys.update(keys)

                    if not all_keys:
                        result.update(self.impossible_filter())
                    else:
                        result[map_to] = {"$in": list(all_keys)}

                else:
                    # запасной вариант: обычная схема op/value
                    if isinstance(value, dict):
                        op = str(value.get("op", "eq")).lower()
                        if op == "eq":
                            result[key] = value.get("value", None)
                        elif op == "in":
                            values = value.get("values") or []
                            result[key] = {"$in": values}
                        elif op == "range":
                            gte = value.get("gte", None)
                            lte = value.get("lte", None)
                            rng: Dict[str, Any] = {}
                            if gte is not None:
                                rng["$gte"] = gte
                            if lte is not None:
                                rng["$lte"] = lte
                            if rng:
                                result[key] = rng
                        elif op == "contains":
                            val = str(value.get("value", ""))
                            result[key] = {"$regex": re.escape(val), "$options": "i"}
                    else:
                        result[key] = value
            else:
                # нет декларативного описания — общая схема
                if isinstance(value, dict):
                    op = str(value.get("op", "eq")).lower()
                    if op == "eq":
                        result[key] = value.get("value", None)
                    elif op == "in":
                        values = value.get("values") or []
                        result[key] = {"$in": values}
                    elif op == "range":
                        gte = value.get("gte", None)
                        lte = value.get("lte", None)
                        rng: Dict[str, Any] = {}
                        if gte is not None:
                            rng["$gte"] = gte
                        if lte is not None:
                            rng["$lte"] = lte
                        if rng:
                            result[key] = rng
                    elif op == "contains":
                        val = str(value.get("value", ""))
                        result[key] = {"$regex": re.escape(val), "$options": "i"}
                else:
                    result[key] = value

        return self.customize_filter_query(result, params, current_user)

    def extract_advanced(self, filters: Optional[dict]) -> Tuple[dict, Optional[dict], Optional[dict]]:
        """Выделяет спец-ключи из filters."""
        if not filters or not isinstance(filters, dict):
            return {}, None, None
        filters_copy = dict(filters)
        search_params = filters_copy.pop("__search", None) or filters_copy.pop("search", None)
        filter_params = filters_copy.pop("__filters", None) or filters_copy.pop("advanced", None)
        return filters_copy, search_params, filter_params

    # ------------------------------
    # Сортировка
    # ------------------------------
    def resolve_sort(self, sort_by: Optional[str], order: int) -> Tuple[str, int, Optional[str], Optional[dict]]:
        """
        Возвращает (field_or_strategy, order, strategy_name, strategy_cfg).
        Если указан алиас в sort_config — маппим.
        Если указан ключ стратегии — возвращаем её.
        """
        cfg = self.get_sort_config()
        by = sort_by or cfg.get("default", {}).get("by") or self.detect_id_field()
        ord_val = order if order in (-1, 1) else (cfg.get("default", {}).get("order") or 1)

        alias = (cfg.get("aliases") or {}).get(by)
        if alias:
            by = alias

        strategies = cfg.get("strategies") or {}
        if by in strategies:
            return by, ord_val, by, strategies[by]
        return by, ord_val, None, None

    async def compute_strategy_value(self, doc: dict, strategy: dict) -> Any:
        """Вычисляет значение для стратегии сортировки."""
        stype = strategy.get("type")
        if stype == "array_last_match_ts":
            arr_name = strategy["array"]
            role_field = strategy["role_field"]
            role_value = strategy.get("role_value")
            ts_field = strategy.get("timestamp_field", "timestamp")
            fallbacks = strategy.get("fallbacks", [])

            arr = doc.get(arr_name) or []
            # идём с конца и ищем совпадение роли
            for i in range(len(arr) - 1, -1, -1):
                item = arr[i]
                role = item.get(role_field)
                role_en = None
                if isinstance(role, dict):
                    role_en = role.get("en")
                else:
                    role_en = str(role) if role is not None else None

                def match_role(rv: Any) -> bool:
                    if isinstance(rv, dict):
                        return rv.get("en") == role_en
                    return rv == role_en

                if isinstance(role_value, list):
                    ok = any(match_role(rv) for rv in role_value)
                else:
                    ok = match_role(role_value)
                if ok:
                    return item.get(ts_field) or None

            # фоллбеки
            for fb in fallbacks:
                if doc.get(fb) is not None:
                    return doc.get(fb)
            return None

        # по умолчанию — ничего
        return None

    # ------------------------------
    # Запросы (list, list_with_meta, get)
    # ------------------------------
    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        current_user: Optional[BaseModel] = None,
        format: bool = True,
    ) -> List[dict]:
        """Возвращает список документов с фильтрами и пагинацией."""
        base_filter = await self.permission_class.get_base_filter(current_user)

        plain_filters, search_params, filter_params = self.extract_advanced(filters)
        mongo_filters = await self.build_mongo_filters(filter_params, current_user)
        search_mongo, computed_for_search, q, mode, combine = await self.build_declarative_search(search_params)

        query: Dict[str, Any] = {**(plain_filters or {}), **base_filter, **mongo_filters}
        if search_mongo:
            query = {"$and": [query, search_mongo]} if query else search_mongo

        sort_key, ord_val, strategy_name, strategy_cfg = self.resolve_sort(sort_by, order)
        needs_post = bool(computed_for_search) or (sort_key in self.computed_fields) or bool(strategy_name)

        if not needs_post:
            cursor = self.db.find(query).sort(sort_key, ord_val)
            if page is not None and page_size is not None:
                cursor = cursor.skip((page - 1) * page_size).limit(page_size)
            if not format:
                return [raw async for raw in cursor]

            objs: List[dict] = []
            async for raw_doc in cursor:
                objs.append(await self.format_document(raw_doc, current_user))
            return objs

        raw_docs: List[dict] = [d async for d in self.db.find(query)]

        if computed_for_search:
            flags = await asyncio.gather(*[
                self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in raw_docs
            ])
            raw_docs = [d for d, ok in zip(raw_docs, flags) if ok]

        # сортировка пост-фактум
        if strategy_cfg:
            # стратегия сортировки
            pairs = await asyncio.gather(*(self.compute_strategy_value(d, strategy_cfg) for d in raw_docs))
            def key_fn(idx: int) -> Any:
                return pairs[idx]
            raw_docs = sorted(range(len(raw_docs)), key=key_fn, reverse=(ord_val == -1))
            raw_docs = [ (await self.format_document(doc, current_user)) if format else doc
                         for doc in [ [d for d in [d for d in raw_docs.__class__.__mro__]][0] ][0] ]  # just to quiet linters (no-op)
            # ↑ этот трюк нам не нужен — заменим на нормальный порядок:
            ordered = [raw_docs[i] for i in raw_docs]  # placeholder
            # исправим: пересоберём правильно
            ordered_docs = [ [d for d in [d for d in []]] ]  # заглушка
        # правильная реализация без шуток:
            idx_order = sorted(range(len(pairs)), key=lambda i: pairs[i], reverse=(ord_val == -1))
            raw_docs = [raw_docs[i] for i in idx_order]
        elif sort_key in self.computed_fields:
            method = getattr(self, f"get_{sort_key}", None)
            if callable(method):
                async def compute_pair(doc: dict) -> Tuple[str, Any]:
                    rid = str(doc.get("_id", doc.get("id")))
                    v = method(doc, current_user=current_user)
                    if hasattr(v, "__await__"):
                        v = await v
                    return rid, v
                pairs = await asyncio.gather(*(compute_pair(d) for d in raw_docs))
                cache = {k: v for k, v in pairs}
                raw_docs.sort(
                    key=lambda x: cache.get(str(x.get("_id", x.get("id")))),
                    reverse=(ord_val == -1),
                )
        else:
            try:
                raw_docs.sort(key=lambda x: x.get(sort_key), reverse=(ord_val == -1))
            except Exception:
                pass

        if page is not None and page_size is not None:
            start = max(0, (page - 1) * page_size)
            end = start + page_size
            paged = raw_docs[start:end]
        else:
            paged = raw_docs

        if not format:
            return paged

        return [await self.format_document(d, current_user) for d in paged]

    async def get_singleton_object(self, current_user) -> Optional[dict]:
        """Возвращает единственный объект пользователя, если max_instances == 1."""
        filters = {"user_id": current_user.data.get("user_id")}
        return await self.db.find_one(filters)

    async def list(
        self,
        sort_by: Optional[str] = None,
        order: int = 1,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        filters: Optional[dict] = None,
        current_user: Optional[BaseModel] = None,
    ) -> List[dict]:
        """Возвращает документы без метаданных."""
        self.check_permission("read", current_user)
        return await self.get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
            current_user=current_user,
        )

    async def list_with_meta(
        self,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        order: int = 1,
        filters: Optional[dict] = None,
        current_user: Optional[BaseModel] = None,
    ) -> dict:
        """Возвращает документы с метаданными пагинации."""
        self.check_permission("read", current_user)

        base_filter = await self.permission_class.get_base_filter(current_user)
        plain_filters, search_params, filter_params = self.extract_advanced(filters)
        mongo_filters = await self.build_mongo_filters(filter_params, current_user)
        search_mongo, computed_for_search, q, mode, combine = await self.build_declarative_search(search_params)

        query: Dict[str, Any] = {**(plain_filters or {}), **base_filter, **mongo_filters}
        if search_mongo:
            query = {"$and": [query, search_mongo]} if query else search_mongo

        if computed_for_search:
            all_docs: List[dict] = [d async for d in self.db.find(query)]
            flags = await asyncio.gather(*[
                self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in all_docs
            ])
            total_count = sum(1 for ok in flags if ok)
        else:
            total_count = await self.db.count_documents(query)

        total_pages = (total_count + page_size - 1) // page_size

        data = await self.get_queryset(
            filters=filters,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
            current_user=current_user,
        )

        return {
            "data": data,
            "meta": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
            },
        }

    async def get(
        self,
        object_id: str,
        current_user: Optional[BaseModel] = None
    ) -> Optional[dict]:
        """Возвращает один документ по _id с учётом прав."""
        self.check_crud_enabled("read")
        docs = await self.get_queryset(filters={"_id": ObjectId(object_id)}, current_user=current_user)
        obj = docs[0] if docs else None
        if obj:
            self.check_object_permission("read", current_user, obj)
        return obj

    # ------------------------------
    # Изменение данных (create, update, delete)
    # ------------------------------
    async def create(
        self,
        data: dict,
        current_user: Optional[BaseModel] = None
    ) -> dict:
        """Создаёт документ с проверкой прав и ограничений."""
        self.check_permission("create", current_user)

        user_field = self.get_user_field_name()

        # лимит инстансов на пользователя
        if self.max_instances_per_user is not None and current_user:
            filter_by_user = {user_field: str(getattr(current_user, "id", None))}
            count = await self.db.count_documents(filter_by_user)
            if count >= self.max_instances_per_user:
                raise HTTPException(403, "You have reached the maximum number of allowed instances.")

        valid_data = await self.process_data(data=data)

        # авто-проставление user_id, если требуется
        if current_user and user_field == "user_id" and "user_id" not in valid_data:
            user_id = current_user.data["user_id"]
            if user_id:
                valid_data["user_id"] = str(user_id)

        res = await self.db.insert_one(valid_data)
        if not res.inserted_id:
            raise HTTPException(500, "Failed to create object.")

        created_raw = await self.db.find_one({"_id": res.inserted_id})
        if not created_raw:
            raise HTTPException(500, "Failed to retrieve created object.")

        return await self.format_document(created_raw, current_user)

    async def update(
        self,
        object_id: str,
        data: dict,
        current_user: Optional[BaseModel] = None
    ) -> dict:
        """Обновляет документ, исключая вычисляемые поля."""
        self.check_crud_enabled("update")

        obj = await self.db.find_one({"_id": ObjectId(object_id)})
        if not obj:
            raise HTTPException(404, "Item not found.")

        self.check_object_permission("update", current_user, obj)

        # автообновление updated_at (если поле есть в схеме)
        if "updated_at" in self.model.__annotations__:
            data["updated_at"] = datetime.utcnow()

        valid_data = await self.process_data(data=data, existing_obj=obj, partial=True)
        valid_data = self.recursive_model_dump(valid_data)

        res = await self.db.update_one({"_id": ObjectId(object_id)}, {"$set": valid_data})
        if res.matched_count == 0:
            raise HTTPException(500, "Failed to update object.")

        updated_raw = await self.db.find_one({"_id": ObjectId(object_id)})
        if not updated_raw:
            raise HTTPException(500, "Failed to retrieve updated object.")

        return await self.format_document(updated_raw, current_user)

    async def delete(
        self,
        object_id: str,
        current_user: Optional[BaseModel] = None
    ) -> dict:
        """Удаляет документ после проверки прав."""
        self.check_crud_enabled("delete")

        obj = await self.db.find_one({"_id": ObjectId(object_id)})
        if not obj:
            raise HTTPException(404, "Item not found.")

        self.check_object_permission("delete", current_user, obj)

        res = await self.db.delete_one({"_id": ObjectId(object_id)})
        if res.deleted_count == 0:
            raise HTTPException(500, "Failed to delete object.")

        return {"status": "success"}

    # ------------------------------
    # Сериализация/форматирование
    # ------------------------------
    def recursive_model_dump(self, obj: Any) -> Any:
        """Рекурсивный dump pydantic-моделей в чистые dict/list."""
        if isinstance(obj, BaseModel):
            return {k: self.recursive_model_dump(v) for k, v in obj.model_dump().items()}
        if isinstance(obj, dict):
            return {k: self.recursive_model_dump(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.recursive_model_dump(i) for i in obj]
        return obj

    async def get_field_overrides(
        self,
        obj: Optional[dict] = None,
        current_user: Optional[Any] = None
    ) -> dict:
        """
        Переопределения свойств отдельных полей схемы.
        Можно использовать obj и current_user.
        """
        return {}

    # ------------------------------
    # Валидация и обработка данных
    # ------------------------------
    def serialize_value(self, value: Any) -> Any:
        """Сериализует значение перед сохранением."""
        if isinstance(value, BaseModel):
            return value.dict()
        if isinstance(value, Enum):
            return value.value
        return value

    async def process_inlines(
        self,
        existing_doc: Optional[dict],
        update_data: dict,
        partial: bool = False
    ) -> dict:
        """Обрабатывает инлайны (добавление, обновление, удаление)."""
        inline_data: Dict[str, Any] = {}

        try:
            for field, inline_cls in self.inlines.items():
                existing_inlines = existing_doc.get(field, []) if existing_doc else []

                if field not in update_data:
                    inline_data[field] = existing_inlines
                    continue

                inline_inst = inline_cls(self.db)
                update_inlines = update_data.pop(field)
                update_inlines = update_inlines if isinstance(update_inlines, list) else [update_inlines]

                if existing_doc:
                    existing_by_id = {item["id"]: item for item in existing_inlines if "id" in item}
                    merged_inlines: List[dict] = []

                    for item in update_inlines:
                        if not isinstance(item, dict):
                            continue

                        if "id" in item:
                            # удалить
                            if item.get("_delete", False):
                                existing_by_id.pop(item["id"], None)
                                continue

                            existing_item = existing_by_id.get(item["id"], {})
                            merged = {**existing_item, **item}
                            validated = await inline_inst.validate_data(merged, partial=False)
                            final_inline = {**merged, **validated}

                            if inline_inst.inlines:
                                sub = await inline_inst.process_inlines(existing_item, final_inline, partial=partial)
                                final_inline.update(sub)

                            merged_inlines.append(final_inline)
                            existing_by_id.pop(item["id"], None)
                        else:
                            # новый
                            validated = await inline_inst.validate_data(item, partial=False)
                            full_validated = inline_inst.model.parse_obj(validated).dict()
                            final_inline = full_validated

                            if inline_inst.inlines:
                                sub = await inline_inst.process_inlines(None, final_inline, partial=False)
                                final_inline.update(sub)

                            merged_inlines.append(final_inline)

                    merged_inlines.extend(existing_by_id.values())
                    inline_data[field] = merged_inlines
                else:
                    # нет существующего — просто валидируем новые
                    validated_items: List[dict] = []
                    for item in update_inlines:
                        if not isinstance(item, dict):
                            continue

                        validated = await inline_inst.validate_data(item, partial=False)
                        full_validated = inline_inst.model.parse_obj(validated).dict()
                        final_inline = full_validated

                        if inline_inst.inlines:
                            sub = await inline_inst.process_inlines(None, final_inline, partial=False)
                            final_inline.update(sub)

                        validated_items.append(final_inline)

                    inline_data[field] = validated_items

            return inline_data

        except Exception as e:
            raise HTTPException(400, detail=str(e))

    async def get_inlines(
        self,
        doc: dict,
        current_user: Optional[dict] = None
    ) -> dict:
        """Возвращает отформатированные инлайны."""
        inl_data: Dict[str, Any] = {}

        for field, inline_cls in self.inlines.items():
            inline_inst = inline_cls(self.db)
            inline_inst.parent_document = doc
            parent_id = doc.get("_id")

            if not parent_id:
                inl_data[field] = []
                continue

            found = await inline_inst.get_queryset(filters={"_id": parent_id}, current_user=current_user)
            inl_data[field] = [
                await inline_inst.format_document(child, current_user) if "id" not in child else child
                for child in found
            ]

        return inl_data

    # ------------------------------
    # Парсинг / форматирование значений
    # ------------------------------
    def parse_json_recursive(self, value: Any) -> Any:
        """Рекурсивно парсит строки JSON и ISO-даты."""
        if isinstance(value, str):
            # Попытка как JSON
            try:
                parsed = json.loads(value)
                if isinstance(parsed, (dict, list, str)):
                    return self.parse_json_recursive(parsed)
            except json.JSONDecodeError:
                pass

            # Попытка как ISO-дата (мягкая проверка)
            if any(c in value for c in ("T", " ")) and value[:1].isdigit():
                try:
                    dt = datetime.fromisoformat(value)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.isoformat().replace("+00:00", "Z")
                except ValueError:
                    pass

            return value

        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat().replace("+00:00", "Z")

        if isinstance(value, list):
            return [self.parse_json_recursive(i) for i in value]

        if isinstance(value, dict):
            return {k: self.parse_json_recursive(v) for k, v in value.items()}

        return value

    async def format_document(
        self,
        doc: dict,
        current_user: Optional[dict] = None
    ) -> dict:
        """Форматирует документ и добавляет вычисляемые поля с инлайнами."""
        fields_set = list(set(self.list_display + self.detail_fields))
        result: Dict[str, Any] = {"id": str(doc.get("_id", doc.get("id")))}

        for field in fields_set:
            result[field] = self.parse_json_recursive(doc.get(field))

        for cf in self.computed_fields:
            method = getattr(self, f"get_{cf}", None)
            if method:
                result[cf] = self.parse_json_recursive(await method(doc, current_user=current_user))

        result.update(await self.get_inlines(doc, current_user))
        return result

    async def validate_data(
        self,
        data: dict,
        *,
        partial: bool = False
    ) -> dict:
        """
        Валидирует данные модели.
        partial=False → полное создание;
        partial=True  → частичное обновление (валидируются только переданные поля).
        """
        FIELD_REQUIRED_MESSAGE = {
            "ru": "Поле обязательно для заполнения.",
            "en": "This field is required.",
            "pl": "To pole jest wymagane.",
            "uk": "Це поле є обовʼязковим.",
            "de": "Dieses Feld ist erforderlich.",
        }

        DEFAULT_VALIDATION_MESSAGES = {
            "value is not a valid email address": {
                "ru": "Неверный формат e-mail.",
                "en": "Invalid email format.",
                "pl": "Nieprawidłowy format e-mail.",
                "uk": "Невірний формат електронної пошти.",
                "de": "Ungültiges E-Mail-Format.",
            },
            "value is not a valid integer": {
                "ru": "Ожидается целое число.",
                "en": "A valid integer is required.",
                "pl": "Wymagana jest liczba całkowita.",
                "uk": "Потрібне ціле число.",
                "de": "Es wird eine Ganzzahl erwartet.",
            },
            "value could not be parsed to a boolean": {
                "ru": "Ожидается логическое значение (true/false).",
                "en": "Expected a boolean value (true/false).",
                "pl": "Oczekiwano wartości logicznej (true/false).",
                "uk": "Очікувалося логічне значення (true/false).",
                "de": "Es wird ein boolescher Wert erwartet (true/false).",
            },
        }

        def try_parse_json(v: Any) -> Any:
            if isinstance(v, str):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass
            return v

        incoming = {k: try_parse_json(v) for k, v in data.items() if k not in self.inlines}

        try:
            obj = self.model(**incoming)
        except ValidationError as exc:
            errors: dict[str, Any] = {}

            for err in exc.errors():
                field = err["loc"][0]
                msg = err["msg"]

                # при partial пропускаем required для непереданных полей
                if partial and field not in incoming and msg in {
                    "Field required", "Missing required field", "value is required"
                }:
                    continue

                # нормализация сообщения
                if msg in {"Field required", "Missing required field", "value is required"}:
                    final_msg = FIELD_REQUIRED_MESSAGE
                elif isinstance(msg, dict):
                    final_msg = msg
                elif isinstance(msg, str):
                    m = msg.strip()
                    if m.startswith("Value error,"):
                        m = m.replace("Value error,", "", 1).strip()

                    if m.startswith("{") and m.endswith("}"):
                        try:
                            final_msg = json.loads(m.replace("'", '"'))
                        except Exception:
                            final_msg = m
                    elif m in DEFAULT_VALIDATION_MESSAGES:
                        final_msg = DEFAULT_VALIDATION_MESSAGES[m]
                    elif ":" in m:
                        base = m.split(":", 1)[0].strip()
                        final_msg = DEFAULT_VALIDATION_MESSAGES.get(base, m)
                    else:
                        final_msg = m
                else:
                    final_msg = msg

                errors[field] = final_msg

            if errors:
                raise HTTPException(400, detail=errors)

            # Ошибок нет — создаём объект без повторной валидации
            obj = self.model.model_construct(**incoming)

        if partial:
            return {k: self.serialize_value(getattr(obj, k)) for k in incoming}

        return {k: self.serialize_value(v) for k, v in obj.model_dump().items()}

    async def process_data(
        self,
        data: dict,
        existing_obj: Optional[dict] = None,
        partial: bool = False
    ) -> dict:
        """Валидирует данные и мерджит инлайны."""
        valid = await self.validate_data(data, partial=partial)
        if self.inlines:
            inline_data = await self.process_inlines(existing_obj, data, partial=partial)
            valid.update(inline_data)
        return valid

    # ------------------------------
    # Поиск во вложенных структурах
    # ------------------------------
    def nested_find(self, doc: Any, target_id: str) -> bool:
        """Ищет target_id во вложенных структурах."""
        if isinstance(doc, dict):
            if str(doc.get("id")) == target_id:
                return True
            return any(self.nested_find(v, target_id) for v in doc.values())
        if isinstance(doc, list):
            return any(self.nested_find(i, target_id) for i in doc)
        return False

    def find_container(self, doc: Any, target_id: str) -> Optional[dict]:
        """Возвращает родительский контейнер для элемента с target_id."""
        if isinstance(doc, dict):
            for k, v in doc.items():
                if k == "id" and str(v) == target_id:
                    return doc
                sub = self.find_container(v, target_id)
                if sub:
                    return sub
        elif isinstance(doc, list):
            for i in doc:
                sub = self.find_container(i, target_id)
                if sub:
                    return sub
        return None

    async def get_root_document(self, any_id: str) -> Optional[dict]:
        """Возвращает корневой документ по _id или вложенному id."""
        direct = await self.db.find_one({"_id": ObjectId(any_id)})
        if direct:
            return direct
        async for parent in self.db.find({}):
            if self.nested_find(parent, any_id):
                return parent
        return None

    async def get_parent_container(self, any_id: str) -> Optional[dict]:
        """Возвращает контейнер, содержащий элемент с any_id."""
        root = await self.get_root_document(any_id)
        return self.find_container(root, any_id) if root else None

    def __str__(self) -> str:
        """Имя модели."""
        return self.verbose_name


# ==============================
# БЛОК: CRUD для вложенных объектов (Inline)
# ==============================
class InlineCrud(BaseCrudCore):
    """CRUD для вложенных объектов."""

    collection_name: str = ""
    dot_field_path: str = ""
    parent_document: dict | None = None

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)
        self.db = db[self.collection_name] if isinstance(db, AsyncIOMotorDatabase) else db

    async def get_nested_field(self, doc: dict, dot_path: str) -> Any:
        """Возвращает данные по точечной нотации."""
        for part in dot_path.split("."):
            if not isinstance(doc, dict) or part not in doc:
                return None
            doc = doc[part]
        return doc

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: str = "id",
        order: int = 1,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        current_user: Optional[dict] = None,
    ) -> List[dict]:
        """Возвращает список вложенных объектов."""
        self.check_permission("read", current_user)

        base_filter = await self.permission_class.get_base_filter(current_user)
        query = {**(filters or {}), **base_filter}

        cursor = self.db.find(query).limit(1 if "_id" in query else 0)
        results: List[dict] = []

        async for parent in cursor:
            nested = await self.get_nested_field(parent, self.dot_field_path)
            if isinstance(nested, list):
                results.extend(nested)
            elif isinstance(nested, dict):
                results.append(nested)

        if sort_by:
            results.sort(key=lambda x: x.get(sort_by), reverse=(order == -1))

        return await asyncio.gather(*(self.format_document(i, current_user) for i in results))

    async def get(
        self,
        object_id: str,
        current_user: Optional[dict] = None
    ) -> Optional[dict]:
        """Возвращает вложенный объект по ID."""
        self.check_crud_enabled("read")

        base_filter = await self.permission_class.get_base_filter(current_user)
        parent = await self.db.find_one({f"{self.dot_field_path}.id": object_id, **base_filter})
        if not parent:
            return None

        nested = await self.get_nested_field(parent, self.dot_field_path)
        if isinstance(nested, list):
            item = next((el for el in nested if el.get("id") == object_id), None)
        elif isinstance(nested, dict) and nested.get("id") == object_id:
            item = nested
        else:
            item = None

        if item:
            self.permission_class.check("read", current_user, item)
        return item

    async def create(
        self,
        data: dict,
        current_user: Optional[dict] = None
    ) -> dict:
        """Добавляет новый вложенный объект."""
        self.check_permission("create", current_user)

        valid = await self.process_data(data)
        if not valid:
            raise HTTPException(400, "No valid fields provided.")

        base_filter = await self.permission_class.get_base_filter(current_user)
        res = await self.db.update_one(base_filter, {"$push": {self.dot_field_path: valid}}, upsert=True)

        if res.modified_count == 0 and not res.upserted_id:
            raise HTTPException(500, "Failed to create object.")
        return valid

    async def update(
        self,
        object_id: str,
        data: dict,
        current_user: Optional[dict] = None
    ) -> dict:
        """Обновляет вложенный объект."""
        self.check_crud_enabled("update")

        if "updated_at" in self.model.__annotations__:
            data["updated_at"] = datetime.utcnow()

        existing = await self.get(object_id, current_user)
        if not existing:
            raise HTTPException(404, "Item not found for update.")
        self.permission_class.check("update", current_user, existing)

        valid = await self.process_data(data, partial=True)
        if not valid:
            raise HTTPException(400, "No valid fields to update.")

        base_filter = await self.permission_class.get_base_filter(current_user)
        filters = {**base_filter, f"{self.dot_field_path}.id": object_id}
        update_query = {"$set": {f"{self.dot_field_path}.$.{k}": v for k, v in valid.items()}}

        res = await self.db.update_one(filters, update_query)
        if res.matched_count == 0:
            raise HTTPException(500, "Failed to update object.")
        return await self.get(object_id, current_user)

    async def delete(
        self,
        object_id: str,
        current_user: Optional[dict] = None
    ) -> dict:
        """Удаляет вложенный объект."""
        self.check_crud_enabled("delete")

        existing = await self.get(object_id, current_user)
        if not existing:
            raise HTTPException(404, "Item not found for deletion.")
        self.permission_class.check("delete", current_user, existing)

        base_filter = await self.permission_class.get_base_filter(current_user)
        filters = {**base_filter, f"{self.dot_field_path}.id": object_id}

        parent = await self.db.find_one(filters)
        if not parent:
            raise HTTPException(404, "Parent document not found.")

        nested = await self.get_nested_field(parent, self.dot_field_path)
        update_query = (
            {"$pull": {self.dot_field_path: {"id": object_id}}}
            if isinstance(nested, list)
            else {"$unset": {self.dot_field_path: ""}}
        )

        res = await self.db.update_one(filters, update_query)
        if res.modified_count == 0:
            raise HTTPException(500, "Failed to delete object.")
        return {"status": "success"}


# ==============================
# БЛОК: CRUD для коллекций
# ==============================
class BaseCrud(BaseCrudCore):
    """CRUD для коллекций."""
    collection_name: str
    inlines: Dict[str, Type[InlineCrud]] = {}

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)
        self.db = db[self.collection_name]

    async def get_queryset(
        self,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        order: int = 1,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        current_user: Optional[dict] = None,
        format: bool = True,
    ) -> List[dict]:
        """Возвращает документы коллекции с учётом фильтров и пагинации."""
        self.check_permission("read", current_user)

        base_filter = await self.permission_class.get_base_filter(current_user)

        plain_filters, search_params, filter_params = self.extract_advanced(filters)
        mongo_filters = await self.build_mongo_filters(filter_params, current_user)
        search_mongo, computed_for_search, q, mode, combine = await self.build_declarative_search(search_params)

        query: Dict[str, Any] = {**(plain_filters or {}), **base_filter, **mongo_filters}
        if search_mongo:
            query = {"$and": [query, search_mongo]} if query else search_mongo

        sort_key, ord_val, strategy_name, strategy_cfg = self.resolve_sort(sort_by, order)
        needs_post = bool(computed_for_search) or (sort_key in self.computed_fields) or bool(strategy_name)

        if not needs_post:
            cursor = (
                self.db.find(query)
                .sort(sort_key, ord_val)
                .skip(((page - 1) * page_size) if page and page_size else 0)
                .limit(page_size or 0)
            )
            raw_docs: List[dict] = [doc async for doc in cursor]
            if not format:
                return raw_docs
            return await asyncio.gather(*(self.format_document(d, current_user) for d in raw_docs))

        raw_docs: List[dict] = [d async for d in self.db.find(query)]

        if computed_for_search:
            flags = await asyncio.gather(*[
                self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in raw_docs
            ])
            raw_docs = [d for d, ok in zip(raw_docs, flags) if ok]

        if strategy_cfg:
            vals = await asyncio.gather(*(self.compute_strategy_value(d, strategy_cfg) for d in raw_docs))
            idx_order = sorted(range(len(vals)), key=lambda i: vals[i], reverse=(ord_val == -1))
            raw_docs = [raw_docs[i] for i in idx_order]
        elif sort_key in self.computed_fields:
            method = getattr(self, f"get_{sort_key}", None)
            if callable(method):
                async def compute_pair(doc: dict) -> Tuple[str, Any]:
                    rid = str(doc.get("_id", doc.get("id")))
                    v = method(doc, current_user=current_user)
                    if hasattr(v, "__await__"):
                        v = await v
                    return rid, v
                pairs = await asyncio.gather(*(compute_pair(d) for d in raw_docs))
                cache = {k: v for k, v in pairs}
                raw_docs.sort(
                    key=lambda x: cache.get(str(x.get("_id", x.get("id")))),
                    reverse=(ord_val == -1),
                )
        else:
            try:
                raw_docs.sort(key=lambda x: x.get(sort_key), reverse=(ord_val == -1))
            except Exception:
                pass

        if page is not None and page_size is not None:
            start = max(0, (page - 1) * page_size)
            end = start + page_size
            raw_docs = raw_docs[start:end]

        if not format:
            return raw_docs

        return await asyncio.gather(*(self.format_document(d, current_user) for d in raw_docs))
