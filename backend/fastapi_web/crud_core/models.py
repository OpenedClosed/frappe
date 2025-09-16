# admin_core.py
import asyncio
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Tuple, Set, Iterable

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel, ValidationError

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
    search_fields: List[str] = []
    searchable_computed_fields: List[str] = []
    default_search_mode: str = "partial"  # "exact" | "partial"
    default_search_combine: str = "or"    # "or" | "and"

    # Расширенный поиск
    search_config: Dict[str, Any] = {}

    # Декларативные фильтры
    filter_config: Dict[str, Dict[str, Any]] = {}

    # Декларативная сортировка (поддержка старого и нового форматов)
    sort_config: Dict[str, Any] = {}

    # Лимит сканирования для «union» по computed при logic="or"
    computed_scan_limit: int = 2000

    def __init__(self, db: AsyncIOMotorCollection) -> None:
        self.db = db

    # ------------------------------
    # Контроль доступа
    # ------------------------------
    def check_crud_enabled(self, action: str) -> None:
        if not self.allow_crud_actions.get(action, False):
            raise HTTPException(403, f"{action.capitalize()} is disabled for this model.")

    def check_object_permission(
        self,
        action: str,
        user: Optional[BaseModel],
        obj: Optional[dict] = None
    ) -> None:
        self.permission_class.check(action, user, obj)

    def check_permission(
        self,
        action: str,
        user: Optional[BaseModel],
        obj: Optional[dict] = None
    ) -> None:
        self.check_crud_enabled(action)
        self.check_object_permission(action, user, obj)

    # ------------------------------
    # Вспомогательные методы
    # ------------------------------
    def detect_id_field(self) -> str:
        return "id" if "id" in self.model.__fields__ else "_id"

    def get_user_field_name(self) -> str:
        return "_id" if self.user_collection_name == self.db.name else "user_id"

    def _is_computed(self, name: str) -> bool:
        return name in (self.computed_fields or []) or name in (self.searchable_computed_fields or [])

    def get_search_fields(self) -> List[str]:
        """По умолчанию даём искать и по searchable_computed_fields тоже."""
        base = list(self.search_fields or list(getattr(self.model, "__annotations__", {}).keys()))
        extra = [f for f in self.searchable_computed_fields if f not in base]
        return base + extra

    def get_filter_config(self) -> Dict[str, Dict[str, Any]]:
        return self.filter_config

    def get_search_config(self) -> Dict[str, Any]:
        return self.search_config or {}

    def get_sort_config(self) -> Dict[str, Any]:
        return self.sort_config or {}

    def customize_search_query(self, mongo_part: dict, params: dict, current_user: Optional[BaseModel]) -> dict:
        return mongo_part

    def customize_filter_query(self, mongo_part: dict, params: dict, current_user: Optional[BaseModel]) -> dict:
        return mongo_part

    # ------------------------------
    # Coercion utils (фильтры)
    # ------------------------------
    @staticmethod
    def _coerce_scalar(v: Any) -> Any:
        """Пытается привести строковые значения к bool/int/float/datetime."""
        if isinstance(v, str):
            s = v.strip()
            # bool
            if s.lower() in ("true", "false"):
                return s.lower() == "true"
            # datetime ISO
            if (("T" in s) or (" " in s)) and s[:1].isdigit():
                try:
                    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except Exception:
                    pass
            # int/float
            try:
                if re.fullmatch(r"-?\d+", s):
                    return int(s)
                if re.fullmatch(r"-?\d+\.\d+", s):
                    return float(s)
            except Exception:
                pass
        return v

    @classmethod
    def _coerce_value(cls, v: Any) -> Any:
        if isinstance(v, list):
            return [cls._coerce_scalar(i) for i in v]
        if isinstance(v, dict):
            return {k: cls._coerce_value(val) for k, val in v.items()}
        return cls._coerce_scalar(v)

    # ------------------------------
    # Поисковая утилита: токенизация
    # ------------------------------
    @staticmethod
    def _tokenize_query(q: str) -> List[str]:
        """Разбивает запрос на токены по пробелам/знакам пунктуации."""
        if not q:
            return []
        tokens = [t for t in re.split(r"[\s,;]+", q) if t]
        return tokens

    # ------------------------------
    # Сопоставление текста (используется в computed-поиске)
    # ------------------------------
    def _match_token(self, s: str, token: str) -> bool:
        return re.search(re.escape(token), s, flags=re.IGNORECASE) is not None

    def match_text(self, value: Any, q: str, mode: str) -> bool:
        """single-value match; для многословных запросов требует вхождение всех токенов в одну строку."""
        if value is None:
            return False
        s = str(value)
        if mode == "exact":
            return s == q
        tokens = self._tokenize_query(q)
        if len(tokens) <= 1:
            return self._match_token(s, q)
        return all(self._match_token(s, t) for t in tokens)

    # ------------------------------
    # ЛОГИКА computed-поиска
    # ------------------------------
    async def search_match_computed(
        self,
        doc: dict,
        computed_fields: Set[str],
        q: str,
        mode: str,
        current_user: Optional[BaseModel],
        combine: str,
    ) -> bool:
        print(f"[search] search_match_computed mode={mode} combine={combine} computed_fields={list(computed_fields)} q='{q}'")
        if not computed_fields:
            return False

        if mode == "exact":
            results: List[bool] = []
            for cf in computed_fields:
                method = getattr(self, f"get_{cf}", None)
                if not callable(method):
                    continue
                v = method(doc, current_user=current_user)
                if hasattr(v, "__await__"):
                    v = await v
                results.append(self.match_text(v, q, mode))
            ok = any(results) if combine == "or" else (all(results) if results else False)
            print("[search] search_match_computed exact →", ok)
            return ok

        tokens = self._tokenize_query(q)
        if len(tokens) <= 1:
            results: List[bool] = []
            for cf in computed_fields:
                method = getattr(self, f"get_{cf}", None)
                if not callable(method):
                    continue
                v = method(doc, current_user=current_user)
                if hasattr(v, "__await__"):
                    v = await v
                results.append(self.match_text(v, q, mode))
            ok = any(results) if combine == "or" else (all(results) if results else False)
            print("[search] search_match_computed single token →", ok)
            return ok

        # многословный: каждый токен должен найтись хотя бы в одном из computed-полей
        values: List[str] = []
        for cf in computed_fields:
            method = getattr(self, f"get_{cf}", None)
            if not callable(method):
                continue
            v = method(doc, current_user=current_user)
            if hasattr(v, "__await__"):
                v = await v
            values.append("" if v is None else str(v))

        if not values:
            print("[search] search_match_computed no values for computed fields → False")
            return False

        for t in tokens:
            if not any(self._match_token(val, t) for val in values):
                print("[search] search_match_computed miss token:", t, "→ False")
                return False
        print("[search] search_match_computed all tokens matched → True")
        return True

    # ------------------------------
    # Служебные: нормализация полей для поиска
    # ------------------------------
    def _normalize_field_list(self, fields) -> List[str]:
        print("[search] _normalize_field_list IN:", repr(fields))
        out: List[str] = []
        if not fields:
            print("[search] _normalize_field_list OUT: [] (empty input)")
            return out

        if isinstance(fields, (list, tuple, set)):
            for it in fields:
                if isinstance(it, str):
                    if it.strip():
                        out.append(it.strip())
                elif isinstance(it, dict):
                    path = str(it.get("path", "")).strip()
                    if path:
                        out.append(path)
                else:
                    print("[search] _normalize_field_list WARN skip item:", repr(it))
        elif isinstance(fields, str):
            parts = [s.strip() for s in fields.split(",") if s.strip()]
            out.extend(parts)
        else:
            print("[search] _normalize_field_list WARN unsupported type:", type(fields))

        print("[search] _normalize_field_list OUT:", out)
        return out

    def _split_search_config_fields(self, fields_cfg) -> Tuple[List[str], Set[str]]:
        print("[search] _split_search_config_fields IN:", repr(fields_cfg))
        plain: List[str] = []
        computed: Set[str] = set()

        for item in (fields_cfg or []):
            if isinstance(item, str):
                path = item.strip()
                item_computed = False
            elif isinstance(item, dict):
                path = str(item.get("path", "")).strip()
                item_computed = bool(item.get("computed")) or (str(item.get("kind", "")).lower() == "computed")
            else:
                print("[search] _split_search_config_fields WARN skip item:", repr(item))
                continue

            if not path:
                continue

            if item_computed or self._is_computed(path):
                computed.add(path)
            else:
                plain.append(path)

        print("[search] _split_search_config_fields OUT plain:", plain, "computed:", computed)
        return plain, computed

    # ------------------------------
    # Построение поиска (базовый + декларативный)
    # ------------------------------
    def build_mongo_search(self, params: Optional[dict | str]) -> Tuple[dict, Set[str], str, str, str]:
        print("[search] build_mongo_search IN params:", repr(params))
        if not params:
            print("[search] build_mongo_search OUT: empty params")
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
            fields_raw = params.get("fields")
            fields = self._normalize_field_list(fields_raw) if fields_raw else self.get_search_fields()

        print(f"[search] build_mongo_search q='{q}' mode='{mode}' combine='{combine}' fields={fields}")

        if not q or not fields:
            print("[search] build_mongo_search OUT: no q or no fields")
            return {}, set(), "", mode, combine

        tokens = self._tokenize_query(q) if mode != "exact" else [q]
        plain_fields = [f for f in fields if not self._is_computed(f)]
        computed: Set[str] = {f for f in fields if self._is_computed(f)}
        print("[search] tokens:", tokens)
        print("[search] plain_fields:", plain_fields, "computed_fields:", computed)

        if mode == "exact":
            parts = [{f: q} for f in plain_fields]
            mongo_part = {"$and": parts} if (combine == "and" and parts) else {"$or": parts} if parts else {}
        else:
            if len(tokens) <= 1:
                parts = [{f: {"$regex": re.escape(tokens[0]), "$options": "i"}} for f in plain_fields]
                mongo_part = {"$and": parts} if (combine == "and" and parts) else {"$or": parts} if parts else {}
            else:
                per_token_blocks: List[dict] = []
                for t in tokens:
                    token_ors = [{f: {"$regex": re.escape(t), "$options": "i"}} for f in plain_fields]
                    if token_ors:
                        per_token_blocks.append({"$or": token_ors})
                mongo_part = {"$and": per_token_blocks} if per_token_blocks else {}

        mongo_part = self.customize_search_query(mongo_part, {"q": q, "mode": mode, "combine": combine, "fields": fields}, None)
        print("[search] build_mongo_search OUT mongo_part:", mongo_part)
        return mongo_part, computed, q, mode, combine

    async def build_declarative_search(self, params: Optional[dict]) -> Tuple[dict, Set[str], str, str, str]:
        cfg = self.get_search_config()
        if not cfg:
            print("[search] build_declarative_search: no cfg → fallback to build_mongo_search")
            return self.build_mongo_search(params)

        logic = str(cfg.get("logic", self.default_search_combine)).lower()
        mode = str(cfg.get("mode", self.default_search_mode)).lower()
        fields_cfg = cfg.get("fields", [])

        print("[search] build_declarative_search IN params:", repr(params))
        print("[search] cfg logic:", logic, "mode:", mode, "fields_cfg:", repr(fields_cfg))

        q = ""
        computed: Set[str] = set()
        param_exprs: Dict[str, List[dict]] = {}

        def acc_expr(param_name: str, expr: Optional[dict]) -> None:
            if expr:
                param_exprs.setdefault(param_name, []).append(expr)

        # делим поля из конфига на обычные/вычисляемые
        plain_fields_cfg, computed_from_cfg = self._split_search_config_fields(fields_cfg)
        computed |= computed_from_cfg

        # --- Базовые поля для param "q"
        if params:
            q = str(params.get("q", "") or "")
            print(f"[search] q='{q}'")
            if q.strip() and plain_fields_cfg:
                tokens = self._tokenize_query(q) if mode != "exact" else [q]
                print("[search] tokens:", tokens)
                if mode == "exact":
                    bf_parts = [{f: q.strip()} for f in plain_fields_cfg]
                    base_expr = {"$and": bf_parts} if (logic == "and" and bf_parts) else {"$or": bf_parts} if bf_parts else {}
                else:
                    if len(tokens) <= 1:
                        bf_parts = [{f: {"$regex": re.escape(tokens[0]), "$options": "i"}} for f in plain_fields_cfg]
                        base_expr = {"$and": bf_parts} if (logic == "and" and bf_parts) else {"$or": bf_parts} if bf_parts else {}
                    else:
                        per_token_blocks: List[dict] = []
                        for t in tokens:
                            token_ors = [{f: {"$regex": re.escape(t), "$options": "i"}} for f in plain_fields_cfg]
                            if token_ors:
                                per_token_blocks.append({"$or": token_ors})
                        base_expr = {"$and": per_token_blocks} if per_token_blocks else {}
                print("[search] base_expr for q over plain fields:", base_expr)
                acc_expr("q", base_expr)

        # --- Lookups
        for item in fields_cfg:
            if not isinstance(item, dict) or "lookup" not in item:
                continue
            lkp = item["lookup"] or {}

            param_name = lkp.get("param", "q")
            val = (params or {}).get(param_name)
            if not val or not isinstance(val, str) or not val.strip():
                if param_name == "q":
                    val = (params or {}).get("q")
                if not val or not isinstance(val, str) or not val.strip():
                    continue
            val = val.strip()

            collection = lkp.get("collection")
            query_field = lkp.get("query_field")
            project_field = lkp.get("project_field")
            map_to = lkp.get("map_to")
            operator = str(lkp.get("operator", "regex")).lower()

            print(f"[search] lookup param='{param_name}' val='{val}' → {collection}.{query_field} -> {map_to} ({operator})")

            dbh = self.db.database if hasattr(self.db, "database") else None
            if dbh is None:
                print("[search] lookup SKIP: no database handle")
                continue

            if operator == "exact":
                lq = {query_field: val}
            else:
                lq = {query_field: {"$regex": re.escape(val), "$options": "i"}}

            cursor = dbh[collection].find(lq, {project_field: 1, "_id": 0})
            values = [doc.get(project_field) async for doc in cursor if doc.get(project_field) is not None]
            values = list({v for v in values})

            expr = {"_id": {"$in": []}} if not values else {map_to: {"$in": values}}
            print("[search] lookup expr:", expr)
            acc_expr(param_name, expr)

        # Склейка mongo-части
        if not param_exprs:
            mongo = {}
            print("[search] build_declarative_search mongo: {} (only computed or nothing)")
        else:
            grouped: List[dict] = []
            for pname, exprs in param_exprs.items():
                if not exprs:
                    continue
                grouped.append(exprs[0] if len(exprs) == 1 else {"$or": exprs})
            mongo = grouped[0] if len(grouped) == 1 else {"$and": grouped}
            print("[search] build_declarative_search mongo grouped:", mongo)

        mongo = self.customize_search_query(
            mongo,
            {"q": q or "", "mode": mode, "combine": logic, "fields": fields_cfg},
            None
        )
        print("[search] build_declarative_search OUT mongo:", mongo, "computed:", computed)
        return mongo, computed, (q or ""), mode, logic

    # ------------------------------
    # Фильтры (generic + декларативные) + пост-фильтры по computed
    # ------------------------------
    def impossible_filter(self) -> dict:
        return {"_id": {"$in": []}}

    def preset_to_range(self, preset: str) -> Tuple[datetime, datetime]:
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        if preset == "week":
            start = now - timedelta(days=7)
        elif preset == "month":
            start = now - timedelta(days=30)
        elif preset in {"3m", "3months", "90d"}:
            start = now - timedelta(days=90)
        else:
            start = now - timedelta(days=7)
        return start, now

    async def build_mongo_filters(
        self,
        params: Optional[dict],
        current_user: Optional[BaseModel],
    ) -> Tuple[dict, List[dict]]:
        """
        Возвращает (mongo_filter_part, post_filters).
        Поддерживает choices как список словарей: {"value": ..., "title": {...}}
        и daterange.field_choices как список словарей: {"value": "...", "map_to": "...", "title": {...}}
        """
        base_cfg = self.get_filter_config() or {}

        result: Dict[str, Any] = {}
        post_filters: List[dict] = []

        # аккумулятор для kind: computed_to_search → объединяем в один IN по полю
        computed_to_search_acc: Dict[str, Set[Any]] = {}

        if not params and not base_cfg.get("_base"):
            return {}, []

        if "_base" in base_cfg and isinstance(base_cfg["_base"], dict):
            result.update(base_cfg["_base"])

        if not params:
            return self.customize_filter_query(result, params or {}, current_user), []

        def extract_values(raw: Any) -> List[Any]:
            items = raw if isinstance(raw, list) else [raw]
            out: List[Any] = []
            for it in items:
                if isinstance(it, dict) and "value" in it:
                    out.append(it.get("value"))
                else:
                    out.append(it)
            return [self._coerce_scalar(v) for v in out]

        for key, value in params.items():
            # явный computed-постфильтр по имени вычисляемого поля
            if self._is_computed(key):
                pf = {"field": key, "raw": value}
                post_filters.append(pf)
                continue

            if key in base_cfg:
                cfg = base_cfg[key]
                ftype = str(cfg.get("type", "eq")).lower()
                kind = str(cfg.get("kind", "")).lower()

                # ---------- KIND: computed_to_search ----------
                if kind == "computed_to_search":
                    mapping = cfg.get("mapping", {}) or {}
                    raw_vals = extract_values(value)
                    for rv in raw_vals:
                        m = mapping.get(rv)
                        if not isinstance(m, dict):
                            continue
                        s = m.get("__search") or {}
                        fields = s.get("fields") or []
                        if isinstance(fields, str):
                            fields = [fields]
                        qval = s.get("q", None)
                        mode = str(s.get("mode", "exact")).lower()
                        for fld in fields:
                            if mode == "exact":
                                coerced = self._coerce_scalar(qval)
                                computed_to_search_acc.setdefault(fld, set()).add(coerced)
                            else:
                                post_filters.append({"field": fld, "raw": {"op": "contains", "value": str(qval)}})
                    continue

                # ---------- TYPE: multienum ----------
                if ftype == "multienum":
                    vals = extract_values(value)
                    paths = cfg.get("paths") or [key]
                    path_parts: List[dict] = []
                    for p in paths:
                        if p.endswith(".en"):
                            path_parts.append({p: {"$in": vals}})
                        else:
                            ors = [{p: {"$regex": re.escape(str(v)), "$options": "i"}} for v in vals]
                            path_parts.append({"$or": ors})
                    if path_parts:
                        result.setdefault("$and", [])
                        result["$and"].append({"$or": path_parts})

                # ---------- TYPE: daterange/range ----------
                elif ftype in {"daterange", "range"}:
                    paths = cfg.get("paths") or [key]
                    gte = None
                    lte = None

                    if isinstance(value, dict) and ("from" in value or "to" in value):
                        gte = self._coerce_scalar(value.get("from"))
                        lte = self._coerce_scalar(value.get("to"))
                    else:
                        preset = value.get("preset") if isinstance(value, dict) else None
                        if isinstance(preset, dict):
                            preset = preset.get("value")
                        if preset:
                            start, end = self.preset_to_range(str(preset).lower())
                            gte, lte = start, end

                    rng: Dict[str, Any] = {}
                    if gte is not None:
                        rng["$gte"] = gte
                    if lte is not None:
                        rng["$lte"] = lte

                    if rng:
                        if len(paths) == 1:
                            result[paths[0]] = rng
                        else:
                            result.setdefault("$and", [])
                            result["$and"].append({"$or": [{p: rng} for p in paths]})

                # ---------- TYPE: virtual ----------
                elif ftype == "virtual":
                    vals = extract_values(value)
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

                # ---------- TYPE: enum_lookup ----------
                elif ftype == "enum_lookup":
                    vals = extract_values(value)
                    resolver = cfg.get("resolver", {})
                    collection = resolver.get("collection")
                    key_field = resolver.get("key")
                    cases = resolver.get("cases", {})
                    map_to = cfg.get("map_to")
                    if not (collection and key_field and map_to and cases):
                        continue

                    dbh = self.db.database if hasattr(self.db, "database") else None
                    if dbh is None:
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

                # ---------- TYPE: generic ----------
                else:
                    if isinstance(value, dict):
                        op = str(value.get("op", "eq")).lower()
                        if op == "eq":
                            v = value.get("value", None)
                            if isinstance(v, dict) and "value" in v:
                                v = v["value"]
                            result[key] = self._coerce_scalar(v)
                        elif op == "in":
                            raw = value.get("values") or []
                            vals = extract_values(raw)
                            result[key] = {"$in": vals}
                        elif op == "range":
                            gte = self._coerce_scalar(value.get("gte", None))
                            lte = self._coerce_scalar(value.get("lte", None))
                            rng: Dict[str, Any] = {}
                            if gte is not None:
                                rng["$gte"] = gte
                            if lte is not None:
                                rng["$lte"] = lte
                            if rng:
                                result[key] = rng
                        elif op == "contains":
                            val = value.get("value", "")
                            if isinstance(val, dict) and "value" in val:
                                val = val["value"]
                            val = str(val)
                            result[key] = {"$regex": re.escape(val), "$options": "i"}
                    else:
                        v = value.get("value") if isinstance(value, dict) and "value" in value else value
                        result[key] = self._coerce_scalar(v)
            else:
                # нет описания в filter_config — поддержка старого синтаксиса
                if isinstance(value, dict):
                    op = str(value.get("op", "eq")).lower()
                    if op == "eq":
                        v = value.get("value", None)
                        if isinstance(v, dict) and "value" in v:
                            v = v["value"]
                        result[key] = self._coerce_scalar(v)
                    elif op == "in":
                        raw = value.get("values") or []
                        vals = extract_values(raw)
                        result[key] = {"$in": vals}
                    elif op == "range":
                        gte = self._coerce_scalar(value.get("gte", None))
                        lte = self._coerce_scalar(value.get("lte", None))
                        rng: Dict[str, Any] = {}
                        if gte is not None:
                            rng["$gte"] = gte
                        if lte is not None:
                            rng["$lte"] = lte
                        if rng:
                            result[key] = rng
                    elif op == "contains":
                        val = value.get("value", "")
                        if isinstance(val, dict) and "value" in val:
                            val = val["value"]
                        val = str(val)
                        result[key] = {"$regex": re.escape(val), "$options": "i"}
                else:
                    v = value.get("value") if isinstance(value, dict) and "value" in value else value
                    result[key] = self._coerce_scalar(v)

        # Превращаем накопленные computed_to_search в пост-фильтры
        for fld, vals in computed_to_search_acc.items():
            if not vals:
                continue
            if len(vals) == 1:
                post_filters.append({"field": fld, "raw": {"op": "eq", "value": list(vals)[0]}})
            else:
                post_filters.append({"field": fld, "raw": {"op": "in", "values": list(vals)}})

        return self.customize_filter_query(result, params, current_user), post_filters

    # ------------------------------
    # Пост-обработка computed-фильтров
    # ------------------------------
    @staticmethod
    def _match_op(val: Any, spec: dict) -> bool:
        if not isinstance(spec, dict):
            return False
        op = str(spec.get("op", "eq")).lower()
        if op == "eq":
            return val == spec.get("value")
        if op == "in":
            values = spec.get("values") or []
            return val in values
        if op == "contains":
            needle = str(spec.get("value", "") or "")
            return re.search(re.escape(needle), str(val or ""), flags=re.IGNORECASE) is not None
        if op == "range":
            gte = spec.get("gte", None)
            lte = spec.get("lte", None)
            if gte is not None and (val is None or val < gte):
                return False
            if lte is not None and (val is None or val > lte):
                return False
            return True
        return False

    async def _compute_values_for_fields(
        self, docs: List[dict], fields: Iterable[str], current_user: Optional[BaseModel]
    ) -> Dict[str, List[Any]]:
        result: Dict[str, List[Any]] = {}
        for f in fields:
            method = getattr(self, f"get_{f}", None)
            if not callable(method):
                result[f] = [None] * len(docs)
                continue
            values: List[Any] = []
            for d in docs:
                v = method(d, current_user=current_user)
                if hasattr(v, "__await__"):
                    v = await v
                values.append(v)
            result[f] = values
        return result

    async def _apply_post_filters(
        self, docs: List[dict], post_filters: List[dict], current_user: Optional[BaseModel]
    ) -> List[dict]:
        if not docs or not post_filters:
            return docs

        normalized: List[dict] = []
        fields_needed: Set[str] = set()
        for pf in post_filters:
            field = pf.get("field")
            raw = pf.get("raw", {})
            spec = raw if isinstance(raw, dict) else {"op": "eq", "value": raw}
            spec = self._coerce_value(spec)
            normalized.append({"field": field, "spec": spec})
            fields_needed.add(field)

        field_values = await self._compute_values_for_fields(docs, fields_needed, current_user)

        kept: List[dict] = []
        for idx, d in enumerate(docs):
            ok = True
            for pf in normalized:
                field = pf["field"]
                spec = pf["spec"]
                val = field_values.get(field, [None] * len(docs))[idx]
                if not self._match_op(val, spec):
                    ok = False
                    break
            if ok:
                kept.append(d)
        return kept

    def extract_advanced(self, filters: Optional[dict | str]) -> Tuple[dict, Optional[dict], Optional[dict]]:
        print("[search] extract_advanced IN:", repr(filters))
        if not filters:
            print("[search] extract_advanced OUT: empty")
            return {}, None, None

        if isinstance(filters, str):
            filters = {"q": filters}

        if not isinstance(filters, dict):
            print("[search] extract_advanced OUT: not dict → empty")
            return {}, None, None

        f = dict(filters)

        search_params = f.pop("__search", None) or f.pop("search", None)
        q = f.pop("q", None)
        mode = f.pop("mode", None)
        combine = f.pop("combine", None)
        fields = f.pop("fields", None)

        if isinstance(fields, str):
            fields = [s.strip() for s in fields.split(",") if s.strip()]
        elif isinstance(fields, (list, tuple, set)):
            fields = self._normalize_field_list(list(fields))
        elif fields is not None:
            print("[search] extract_advanced WARN 'fields' unsupported type:", type(fields))
            fields = None

        if search_params is None and any(x is not None for x in (q, mode, combine, fields)):
            sp: dict = {}
            if q is not None:
                sp["q"] = q
            if mode is not None:
                sp["mode"] = mode
            if combine is not None:
                sp["combine"] = combine
            if fields is not None:
                sp["fields"] = fields
            search_params = sp

        filter_params = f.pop("__filters", None) or f.pop("advanced", None)
        print("[search] extract_advanced OUT plain:", f, "search_params:", search_params, "filter_params:", filter_params)
        return f, search_params, filter_params

    # ------------------------------
    # Сортировка
    # ------------------------------
    def resolve_sort(self, sort_by: Optional[str], order: int) -> Tuple[str, int, Optional[str], Optional[dict]]:
        cfg = self.get_sort_config()

        default_field = cfg.get("default_field")
        default_order = cfg.get("default_order")

        default_cfg = cfg.get("default", {})
        by = sort_by or default_cfg.get("by") or default_field or self.detect_id_field()
        ord_val = order if order in (-1, 1) else (default_cfg.get("order") or default_order or 1)

        alias = (cfg.get("aliases") or {}).get(by)
        if alias:
            by = alias

        strategies = cfg.get("strategies") or {}
        if by in strategies:
            return by, ord_val, by, strategies[by]
        return by, ord_val, None, None

    async def compute_strategy_value(self, doc: dict, strategy: dict) -> Any:
        stype = strategy.get("type")
        if stype == "array_last_match_ts":
            arr_name = strategy["array"]
            role_field = strategy["role_field"]
            role_value = strategy.get("role_value")
            ts_field = strategy.get("timestamp_field", "timestamp")
            fallbacks = strategy.get("fallbacks", [])

            def norm(v: Any) -> str:
                if isinstance(v, dict):
                    v = v.get("en")
                return (str(v).strip().lower() if v is not None else "")

            targets = role_value if isinstance(role_value, list) else [role_value]
            targets_norm = {norm(v) for v in targets}

            arr = doc.get(arr_name) or []
            for i in range(len(arr) - 1, -1, -1):
                item = arr[i]
                role = item.get(role_field)
                role_en = None
                if isinstance(role, dict):
                    role_en = role.get("en")
                else:
                    role_en = str(role) if role is not None else None

                if norm(role_en) in targets_norm:
                    return item.get(ts_field) or None

            for fb in fallbacks:
                if doc.get(fb) is not None:
                    return doc.get(fb)
            return None

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
        self.check_permission("read", current_user)

        base_filter = await self.permission_class.get_base_filter(current_user)

        plain_filters, search_params, filter_params = self.extract_advanced(filters)
        mongo_filters, post_filters = await self.build_mongo_filters(filter_params, current_user)
        search_mongo, computed_for_search, q, mode, combine = await self.build_declarative_search(search_params)

        # базовая часть без поискового mongo — нужна для union по computed (logic="or")
        pre_search_query: Dict[str, Any] = {**(plain_filters or {}), **base_filter, **mongo_filters}

        # полная mongo-часть, если есть
        query: Dict[str, Any] = pre_search_query
        if search_mongo:
            query = {"$and": [query, search_mongo]} if query else search_mongo

        print("[search] get_queryset pre_search_query:", pre_search_query)
        print("[search] get_queryset final query:", query)

        sort_key, ord_val, strategy_name, strategy_cfg = self.resolve_sort(sort_by, order)

        # если нет computed/пост-фильтров/стратегий — отдаём всё силами mongo
        needs_post = bool(computed_for_search) or bool(post_filters) or (sort_key in self.computed_fields) or bool(strategy_name)

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

        # --- post-путь
        raw_docs: List[dict] = [d async for d in self.db.find(query)]

        # объединение/пересечение computed-поиска
        if computed_for_search and q.strip():
            if combine == "and":
                # усиливаем mongo-результаты
                flags = await asyncio.gather(*[
                    self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in raw_docs
                ])
                raw_docs = [d for d, ok in zip(raw_docs, flags) if ok]
                print(f"[search] AND computed filter kept {len(raw_docs)} docs")
            else:
                # OR: оставляем mongo-совпадения и ДОБАВЛЯЕМ документы,
                # которые соответствуют computed, но не попали в mongo-поиск
                print("[search] OR computed union: scanning candidates up to", self.computed_scan_limit)
                # кандидатами возьмём документы без mongo-поиска (только базовые фильтры)
                candidates: List[dict] = [d async for d in self.db.find(pre_search_query).limit(self.computed_scan_limit)]
                flags = await asyncio.gather(*[
                    self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in candidates
                ])
                computed_only = [d for d, ok in zip(candidates, flags) if ok]
                # склеиваем по _id
                seen: Set[str] = {str(x.get("_id")) for x in raw_docs}
                extra = [d for d in computed_only if str(d.get("_id")) not in seen]
                print(f"[search] OR computed union adds {len(extra)} docs")
                raw_docs.extend(extra)

        if post_filters:
            raw_docs = await self._apply_post_filters(raw_docs, post_filters, current_user)

        # сортировка
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

        # пагинация
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
        mongo_filters, post_filters = await self.build_mongo_filters(filter_params, current_user)
        search_mongo, computed_for_search, q, mode, combine = await self.build_declarative_search(search_params)

        pre_search_query: Dict[str, Any] = {**(plain_filters or {}), **base_filter, **mongo_filters}
        query: Dict[str, Any] = pre_search_query
        if search_mongo:
            query = {"$and": [query, search_mongo]} if query else search_mongo

        # считаем total с учётом computed-поиска и пост-фильтров
        if computed_for_search or post_filters:
            # База: берём либо mongo-поиск (если AND), либо базовые кандидаты (если OR)
            if computed_for_search and q.strip() and combine == "or":
                print("[search] list_with_meta total via OR union scan")
                all_docs: List[dict] = [d async for d in self.db.find(pre_search_query)]
                flags = await asyncio.gather(*[
                    self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in all_docs
                ])
                # mongo-матчеры
                base_set_ids = {str(x.get("_id")) for x in await self.db.find(query).to_list(None)}
                # computed-матчеры
                comp_ids = {str(d.get("_id")) for d, ok in zip(all_docs, flags) if ok}
                # объединяем
                union_ids = base_set_ids | comp_ids
                total_count = len(union_ids)
            else:
                all_docs: List[dict] = [d async for d in self.db.find(query)]
                if computed_for_search and q.strip() and combine == "and":
                    flags = await asyncio.gather(*[
                        self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in all_docs
                    ])
                    all_docs = [d for d, ok in zip(all_docs, flags) if ok]
                if post_filters:
                    all_docs = await self._apply_post_filters(all_docs, post_filters, current_user)
                total_count = len(all_docs)
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
        self.check_permission("create", current_user)

        user_field = self.get_user_field_name()

        if self.max_instances_per_user is not None and current_user:
            filter_by_user = {user_field: str(getattr(current_user, "id", None))}
            count = await self.db.count_documents(filter_by_user)
            if count >= self.max_instances_per_user:
                raise HTTPException(403, "You have reached the maximum number of allowed instances.")

        valid_data = await self.process_data(data=data)

        if current_user and user_field == "user_id" and "user_id" not in valid_data:
            user_id = current_user.data.get("user_id")
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
        self.check_crud_enabled("update")

        obj = await self.db.find_one({"_id": ObjectId(object_id)})
        if not obj:
            raise HTTPException(404, "Item not found.")

        self.check_object_permission("update", current_user, obj)

        if "updated_at" in self.model.__annotations__:
            data["updated_at"] = datetime.utcnow().replace(tzinfo=timezone.utc)

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
        return {}

    # ------------------------------
    # Валидация и обработка данных
    # ------------------------------
    def serialize_value(self, value: Any) -> Any:
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
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, (dict, list, str)):
                    return self.parse_json_recursive(parsed)
            except json.JSONDecodeError:
                pass

            if any(c in value for c in ("T", " ")) and value[:1].isdigit():
                try:
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
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
        fields_set = list(set(self.list_display + self.detail_fields))
        result: Dict[str, Any] = {"id": str(doc.get("_id", doc.get("id")))}

        for field in fields_set:
            result[field] = self.parse_json_recursive(doc.get(field))

        for cf in self.computed_fields:
            method = getattr(self, f"get_{cf}", None)
            if method:
                v = method(doc, current_user=current_user)
                if hasattr(v, "__await__"):
                    v = await v
                result[cf] = self.parse_json_recursive(v)

        result.update(await self.get_inlines(doc, current_user))
        return result

    async def validate_data(
        self,
        data: dict,
        *,
        partial: bool = False
    ) -> dict:
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

                if partial and field not in incoming and msg in {
                    "Field required", "Missing required field", "value is required"
                }:
                    continue

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
        valid = await self.validate_data(data, partial=partial)
        if self.inlines:
            inline_data = await self.process_inlines(existing_obj, data, partial=partial)
            valid.update(inline_data)
        return valid

    # ------------------------------
    # Поиск во вложенных структурах
    # ------------------------------
    def nested_find(self, doc: Any, target_id: str) -> bool:
        if isinstance(doc, dict):
            if str(doc.get("id")) == target_id:
                return True
            return any(self.nested_find(v, target_id) for v in doc.values())
        if isinstance(doc, list):
            return any(self.nested_find(i, target_id) for i in doc)
        return False

    def find_container(self, doc: Any, target_id: str) -> Optional[dict]:
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
        direct = await self.db.find_one({"_id": ObjectId(any_id)})
        if direct:
            return direct
        async for parent in self.db.find({}):
            if self.nested_find(parent, any_id):
                return parent
        return None

    async def get_parent_container(self, any_id: str) -> Optional[dict]:
        root = await self.get_root_document(any_id)
        return self.find_container(root, any_id) if root else None

    def __str__(self) -> str:
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

        # Инлайн обычно форматируется в родителе; тут вернём как есть
        return results

    async def get(
        self,
        object_id: str,
        current_user: Optional[dict] = None
    ) -> Optional[dict]:
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
        self.check_crud_enabled("update")

        if "updated_at" in self.model.__annotations__:
            data["updated_at"] = datetime.utcnow().replace(tzinfo=timezone.utc)

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
        self.check_permission("read", current_user)

        base_filter = await self.permission_class.get_base_filter(current_user)

        plain_filters, search_params, filter_params = self.extract_advanced(filters)
        mongo_filters, post_filters = await self.build_mongo_filters(filter_params, current_user)
        search_mongo, computed_for_search, q, mode, combine = await self.build_declarative_search(search_params)

        pre_search_query: Dict[str, Any] = {**(plain_filters or {}), **base_filter, **mongo_filters}
        query: Dict[str, Any] = pre_search_query
        if search_mongo:
            query = {"$and": [query, search_mongo]} if query else search_mongo

        print("[search] (BaseCrud) get_queryset pre_search_query:", pre_search_query)
        print("[search] (BaseCrud) get_queryset final query:", query)

        sort_key, ord_val, strategy_name, strategy_cfg = self.resolve_sort(sort_by, order)
        needs_post = bool(computed_for_search) or bool(post_filters) or (sort_key in self.computed_fields) or bool(strategy_name)

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

        # объединение/пересечение computed-поиска
        if computed_for_search and q.strip():
            if combine == "and":
                flags = await asyncio.gather(*[
                    self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in raw_docs
                ])
                raw_docs = [d for d, ok in zip(raw_docs, flags) if ok]
                print(f"[search] (BaseCrud) AND computed filter kept {len(raw_docs)} docs")
            else:
                print("[search] (BaseCrud) OR computed union: scanning candidates up to", self.computed_scan_limit)
                candidates: List[dict] = [d async for d in self.db.find(pre_search_query).limit(self.computed_scan_limit)]
                flags = await asyncio.gather(*[
                    self.search_match_computed(d, computed_for_search, q, mode, current_user, combine) for d in candidates
                ])
                computed_only = [d for d, ok in zip(candidates, flags) if ok]
                seen: Set[str] = {str(x.get("_id")) for x in raw_docs}
                extra = [d for d in computed_only if str(d.get("_id")) not in seen]
                print(f"[search] (BaseCrud) OR computed union adds {len(extra)} docs")
                raw_docs.extend(extra)

        if post_filters:
            raw_docs = await self._apply_post_filters(raw_docs, post_filters, current_user)

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
