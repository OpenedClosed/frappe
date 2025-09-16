"""Формирование маршрутов приложения (ядро CRUD + кастомные экшены).

Здесь:
- стандартные эндпоинты авторизации (login / refresh / logout);
- генерация CRUD-маршрутов для зарегистрированных админ-моделей;
- автоподхват кастомных методов из админ-классов через декоратор @admin_route.
- прокидка декларативных конфигов поиска/фильтров/сортировки в /info для UI.
"""

import importlib
import logging
import os
import json
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, get_args, get_origin

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import ValidationError

from auth.utils.help_functions import add_token_to_blacklist, is_token_blacklisted, jwt_required
from db.mongo.db_init import mongo_db
from infra import settings
from users.db.mongo.schemas import LoginSchema, User
from users.utils.help_functions import get_current_user
from utils.help_functions import to_snake_case
import inspect

from .decorators import admin_route  # импорт, чтобы декоратор был виден при импорте модулей
from .models import InlineCrud
from .registry import BaseRegistry
from .utils.help_functions import (
    extract_list_inner_type,
    get_enum_choices,
    is_dict_type,
    is_email_type,
    is_enum_type,
    is_file_type,
    is_list_of_enum,
    is_list_of_file,
    is_list_of_photo,
    is_location_type,
    is_photo_type,
    is_range_value_type,
    is_rating_type,
    is_table_row_type,
    unwrap_optional,
)

logger = logging.getLogger(__name__)


# =====================================
# Автоимпорт модулей
# =====================================

async def auto_discover_modules(module_name: str) -> None:
    """Ищет и импортирует все файлы с именем module_name.py внутри BASE_DIR."""
    base_dir = settings.BASE_DIR
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file != f"{module_name}.py":
                continue
            relative = Path(root).relative_to(base_dir)
            module_path = relative.as_posix().replace("/", ".")
            full_module = f"{module_path}.{module_name}"
            try:
                importlib.import_module(full_module)
                logger.debug("Импортирован модуль: %s", full_module)
            except Exception as exc:
                logger.exception("Ошибка при импорте %s: %s", full_module, exc)


# =====================================
# Генерация маршрутов
# =====================================

def generate_base_routes(registry: BaseRegistry) -> APIRouter:
    """Создает APIRouter со стандартными и кастомными маршрутами админ-панели."""
    router = APIRouter()
    logger.info("Генерируем маршруты...")

    # -------------------------------------
    # Вспомогательное: блэклист токена из cookie
    # -------------------------------------
    async def revoke_cookie_token(
        request: Request,
        Authorize: AuthJWT,
        cookie_name: str,
        token_kind: str,
        user_id: Optional[str] = None,
        check_refresh: bool = False,
    ) -> None:
        """Кладет токен из cookie в blacklist, если он присутствует."""
        token = request.cookies.get(cookie_name)
        if not token:
            return
        try:
            Authorize._token = token
            if check_refresh:
                Authorize.jwt_refresh_token_required()
            else:
                Authorize.jwt_required()
            raw = Authorize.get_raw_jwt()
            jti = raw["jti"]
            await add_token_to_blacklist(user_id or Authorize.get_jwt_subject(), token_kind, jti)
        except Exception:
            return

    # =====================================
    # AUTH ENDPOINTS
    # =====================================

    @router.post("/login")
    async def login(
        request: Request,
        response: Response,
        login_data: LoginSchema,
        Authorize: AuthJWT = Depends(),
    ) -> Dict[str, Any]:
        """Вход: проверка пользователя, блэклист старых токенов, выдача новых, запись в cookies."""
        user_doc = await mongo_db["users"].find_one({"username": login_data.username})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        if not user_doc.get("is_active", True):
            raise HTTPException(403, "User is blocked.")

        user = User(**user_doc)
        if not user.check_password(login_data.password):
            raise HTTPException(status_code=401, detail="Invalid credentials.")

        await revoke_cookie_token(request, Authorize, "access_token", "access", str(user_doc["_id"]))
        await revoke_cookie_token(request, Authorize, "refresh_token", "refresh", str(user_doc["_id"]), check_refresh=True)

        access_token = Authorize.create_access_token(subject=str(user_doc["_id"]))
        refresh_token = Authorize.create_refresh_token(subject=str(user_doc["_id"]))

        response.set_cookie(key="access_token", value=access_token, httponly=False, secure=True, samesite="None")
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=False, secure=True, samesite="None")
        return {"message": "Logged in", "access_token": access_token}

    @router.post("/refresh")
    async def refresh_tokens(
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends(),
    ) -> Dict[str, str]:
        """Обновление пары токенов: проверка refresh, блэклист старых, выдача новых, запись в cookies."""
        old_refresh = request.cookies.get("refresh_token")
        if not old_refresh:
            raise HTTPException(status_code=401, detail="Refresh token is missing")

        Authorize._token = old_refresh
        try:
            Authorize.jwt_refresh_token_required()
        except AuthJWTException:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        current_user = Authorize.get_jwt_subject()
        raw_refresh = Authorize.get_raw_jwt()
        refresh_jti = raw_refresh["jti"]

        if await is_token_blacklisted(current_user, "refresh", refresh_jti):
            raise HTTPException(status_code=401, detail="Refresh token is blacklisted")

        await add_token_to_blacklist(current_user, "refresh", refresh_jti)
        await revoke_cookie_token(request, Authorize, "access_token", "access", current_user)

        new_access = Authorize.create_access_token(subject=current_user)
        new_refresh = Authorize.create_refresh_token(subject=current_user)

        response.set_cookie(key="access_token", value=new_access, httponly=False, secure=True, samesite="None")
        response.set_cookie(key="refresh_token", value=new_refresh, httponly=False, secure=True, samesite="None")

        return {"message": "Tokens refreshed", "access_token": new_access}

    @router.post("/logout")
    @jwt_required()
    async def logout(
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends(),
    ) -> Dict[str, str]:
        """Выход: блэклист access/refresh из cookies, удаление cookies."""
        current_user = Authorize.get_jwt_subject()
        await revoke_cookie_token(request, Authorize, "access_token", "access", current_user)
        await revoke_cookie_token(request, Authorize, "refresh_token", "refresh", current_user, check_refresh=True)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return {"message": "Logged out"}

    # =====================================
    # CRUD и кастомные маршруты
    # =====================================

    def create_routes(name: str, instance):
        """
        Регистрирует CRUD-маршруты и кастомные методы (@admin_route) для одной модели.
        """
        snake_name = to_snake_case(name)

        # ---------- READ ----------
        if instance.allow_crud_actions.get("read", False):

            @router.get(f"/{snake_name}/", name=f"list_{snake_name}")
            @jwt_required()
            async def list_items(
                request: Request,
                response: Response,
                page: int = 1,
                page_size: int = 10,
                sort_by: Optional[str] = None,
                order: int = 1,
                Authorize: AuthJWT = Depends(),
            ):
                """
                Поддерживаем три способа передать критерии:
                  1) filters=<JSON>         — сложные фильтры (__filters / advanced)
                  2) search=<JSON или строка> — расширенный/простой поиск (__search / q)
                  3) q=<строка>             — короткий поиск
                Всё это мержится в единый dict и уходит в instance.list/list_with_meta().
                """
                user_doc = await get_current_user(Authorize)

                has_page = "page" in request.query_params
                has_page_size = "page_size" in request.query_params

                raw_filters = request.query_params.get("filters")
                raw_search = request.query_params.get("search")
                raw_q = request.query_params.get("q")

                parsed_filters: Optional[dict] = None
                if raw_filters:
                    try:
                        parsed_filters = json.loads(raw_filters)
                    except Exception:
                        raise HTTPException(status_code=400, detail="Invalid filters JSON")

                parsed_search: Optional[dict] = None
                if raw_search:
                    try:
                        if str(raw_search).strip().startswith("{"):
                            parsed_search = json.loads(raw_search)
                        else:
                            parsed_search = {"q": str(raw_search)}
                    except Exception:
                        parsed_search = {"q": str(raw_search)}
                elif raw_q:
                    parsed_search = {"q": str(raw_q)}

                combined_filters = None
                if parsed_filters or parsed_search:
                    combined_filters = {"__filters": parsed_filters or {}, "__search": parsed_search or {}}

                # singleton-режим без критериев
                if instance.max_instances_per_user == 1 and not (parsed_filters or parsed_search):
                    items = await instance.get_queryset(current_user=user_doc)
                    item: Optional[dict] = None
                    if items:
                        first_obj = items[0]
                        item_id = first_obj.get("_id") or first_obj.get("id")
                        if not item_id:
                            raise HTTPException(status_code=404, detail="Invalid document: missing _id")
                        item = await instance.get(object_id=item_id, current_user=user_doc)
                    if not item:
                        raise HTTPException(status_code=404, detail="Item not found")
                    return item

                use_meta = bool(parsed_filters or parsed_search or (has_page and has_page_size))
                if use_meta:
                    return await instance.list_with_meta(
                        page=page,
                        page_size=page_size,
                        sort_by=sort_by,
                        order=order,
                        filters=combined_filters,
                        current_user=user_doc,
                    )

                return await instance.list(
                    sort_by=sort_by,
                    order=order,
                    filters=combined_filters,
                    current_user=user_doc,
                )

            @router.get(f"/{snake_name}/{{item_id}}", name=f"get_{snake_name}")
            @jwt_required()
            async def get_item(
                request: Request,
                response: Response,
                item_id: str,
                Authorize: AuthJWT = Depends(),
            ):
                user_doc = await get_current_user(Authorize)
                item = await instance.get(object_id=item_id, current_user=user_doc)
                if not item:
                    raise HTTPException(status_code=404, detail="Item not found")
                return item

        # ---------- CREATE ----------
        if instance.allow_crud_actions.get("create", False):

            @router.post(f"/{snake_name}/", name=f"create_{snake_name}")
            @jwt_required()
            async def create_item(
                request: Request,
                response: Response,
                data: dict,
                Authorize: AuthJWT = Depends(),
            ):
                user_doc = await get_current_user(Authorize)
                try:
                    return await instance.create(data, current_user=user_doc)
                except ValidationError as exc:
                    errors = {err["loc"][-1]: err["msg"] for err in exc.errors()}
                    raise HTTPException(status_code=400, detail=errors)

        # ---------- UPDATE ----------
        if instance.allow_crud_actions.get("update", False):

            @router.patch(f"/{snake_name}/{{item_id}}", name=f"patch_{snake_name}")
            @jwt_required()
            async def patch_item(
                request: Request,
                response: Response,
                item_id: str,
                data: dict,
                Authorize: AuthJWT = Depends(),
            ):
                user_doc = await get_current_user(Authorize)
                try:
                    updated = await instance.update(object_id=item_id, data=data, current_user=user_doc)
                    if not updated:
                        raise HTTPException(status_code=404, detail="Item not updated")
                    return updated
                except ValidationError as exc:
                    errors = {err["loc"][-1]: err["msg"] for err in exc.errors()}
                    raise HTTPException(status_code=400, detail=errors)

        # ---------- DELETE ----------
        if instance.allow_crud_actions.get("delete", False):

            @router.delete(f"/{snake_name}/{{item_id}}", name=f"delete_{snake_name}")
            @jwt_required()
            async def delete_item(
                request: Request,
                response: Response,
                item_id: str,
                Authorize: AuthJWT = Depends(),
            ):
                user_doc = await get_current_user(Authorize)
                deleted = await instance.delete(object_id=item_id, current_user=user_doc)
                if not deleted:
                    raise HTTPException(status_code=404, detail="Item not deleted")
                return {"status": "success"}

        # ---------- CUSTOM (@admin_route) ----------
        for attr_name, handler in inspect.getmembers(instance, predicate=inspect.ismethod):
            func = getattr(handler, "__func__", handler)  # оригинальная функция из bound-метода
            meta_list = getattr(func, "admin_route_meta", None)
            if not isinstance(meta_list, list):
                continue

            for meta in meta_list:
                relative = meta["path"] if meta["path"].startswith("/") else f"/{meta['path']}"
                full_path = f"/{snake_name}{relative}"

                async def endpoint(
                    request: Request,
                    Authorize: AuthJWT = Depends(),
                    _h=handler,   # bound-метод (важно: оставляем bound, а не func)
                    _m=meta,
                ):
                    current_user = None
                    if _m["auth"]:
                        try:
                            Authorize.jwt_required()
                        except Exception:
                            raise HTTPException(status_code=401, detail="Not authenticated")
                        current_user = await get_current_user(Authorize)
                        try:
                            instance.check_permission(_m["permission_action"], current_user)
                        except HTTPException as e:
                            raise e
                        except Exception:
                            raise HTTPException(status_code=403, detail="Permission denied")

                    body: Dict[str, Any] = {}
                    if request.method in {"POST", "PUT", "PATCH"}:
                        try:
                            body = await request.json()
                        except Exception:
                            body = {}

                    path_params = dict(request.path_params)
                    query_params = dict(request.query_params)

                    result = _h(
                        data=body,
                        current_user=current_user,
                        request=request,
                        path_params=path_params,
                        query_params=query_params,
                    )
                    if callable(result):
                        result = result()
                    if hasattr(result, "__await__"):
                        result = await result
                    return result

                route_name = meta["name"] or f"{snake_name}_{meta['method'].lower()}_{relative.strip('/').replace('/', '_') or 'root'}"
                router.add_api_route(
                    full_path,
                    endpoint,
                    methods=[meta["method"]],
                    name=route_name,
                    status_code=meta["status_code"],
                    response_model=meta["response_model"],
                    summary=meta["summary"],
                    description=meta["description"],
                    tags=meta["tags"],
                )


    for registered_name, instance in registry.get_registered().items():
        create_routes(registered_name, instance)

    @router.get("/info")
    @jwt_required()
    async def get_info(
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends(),
    ):
        """Возвращает структуру описания админ-моделей и их маршрутов + декларативные конфиги для UI."""
        current_user = await get_current_user(Authorize)
        return await get_routes_by_apps(registry, current_user)

    return router


# =====================================
# Помощники для UI-схемы
# =====================================

def map_python_type_to_ui(py_type: Any) -> str:
    """Маппинг python-типа в тип UI-поля по умолчанию."""
    mapping: Dict[Any, str] = {
        str: "string",
        int: "number",
        float: "float",
        bool: "boolean",
        dict: "json",
        datetime: "datetime",
    }
    if py_type in mapping:
        return mapping[py_type]
    if is_enum_type(py_type):
        return "select"
    if is_list_of_enum(py_type):
        return "multiselect"

    origin = get_origin(py_type)
    if origin in (list, List):
        return "multiselect"
    if origin in (dict, Dict):
        return "json"
    if origin is Union:
        return "unknown"
    return "unknown"


def get_instance_attributes(instance: Any) -> Dict[str, Any]:
    """Возвращает основные атрибуты админ-класса, нужные для построения схемы."""
    return {
        "list_display": getattr(instance, "list_display", []),
        "detail_fields": getattr(instance, "detail_fields", []),
        "computed_fields": getattr(instance, "computed_fields", []),
        "read_only_fields": getattr(instance, "read_only_fields", []),
        "inlines_dict": getattr(instance, "inlines", {}),
        "field_titles": getattr(instance, "field_titles", {}),
        "field_groups": getattr(instance, "field_groups", []),
        "help_texts": getattr(instance, "help_texts", {}),
        "max_instances": getattr(instance, "max_instances_per_user", None),
        "allow_crud": getattr(
            instance,
            "allow_crud_actions",
            {"create": True, "read": True, "update": True, "delete": True},
        ),
    }


def determine_field_type_and_choices(
    py_type: Any,
    field: str,
    read_only_fields: List[str],
) -> Tuple[str, Optional[List[Any]]]:
    """Возвращает кортеж (ui_type, choices) на основании аннотации поля."""
    if py_type is None:
        return "unknown", None
    if is_enum_type(py_type):
        return "select", get_enum_choices(py_type)
    if is_list_of_enum(py_type):
        return "multiselect", get_enum_choices(extract_list_inner_type(py_type))
    if is_file_type(py_type):
        return "file", None
    if is_list_of_file(py_type):
        return "multifile", None
    if is_photo_type(py_type):
        return "image", None
    if is_list_of_photo(py_type):
        return "multiimage", None
    if is_location_type(py_type):
        return "location", None
    if is_rating_type(py_type):
        return "rating", None
    if is_range_value_type(py_type):
        return "range_value", None
    if is_table_row_type(py_type):
        return "table_row", None
    if is_email_type(py_type):
        return "email", None
    if is_dict_type(py_type):
        return "json", None
    if py_type is datetime and field not in read_only_fields:
        return "calendar", None

    auto_ui = map_python_type_to_ui(py_type)
    return (auto_ui if auto_ui != "unknown" else py_type, None)  # type: ignore[return-value]


def get_schema_data(instance: Any) -> Tuple[Dict[str, Any], List[str]]:
    """Возвращает свойства и обязательные поля pydantic-схемы модели."""
    try:
        schema = instance.model.schema(by_alias=False)
        return schema.get("properties", {}), schema.get("required", [])
    except Exception:
        return {}, []


def extract_default_value_and_settings(
    instance: Any,
    field_name: str,
    default_value: Any,
) -> Tuple[Any, Dict[str, Any]]:
    """Возвращает default и settings для поля из json-схемы и json_schema_extra."""
    field_def = getattr(instance.model, "model_fields", {}).get(field_name)

    if default_value is None and field_def and hasattr(field_def, "default_factory"):
        try:
            factory_value = field_def.default_factory()
            if isinstance(factory_value, dict) and "settings" in factory_value and len(factory_value) == 1:
                return None, factory_value["settings"]
            return factory_value, {}
        except Exception:
            pass

    if isinstance(default_value, dict) and "settings" in default_value:
        return default_value.get("default"), default_value["settings"]

    json_schema_extra = getattr(field_def, "json_schema_extra", None)
    if isinstance(json_schema_extra, dict):
        return None, json_schema_extra.get("settings", {})

    return default_value, {}


def build_field_schema(
    instance: Any,
    field: str,
    schema_props: Dict[str, Any],
    model_annotations: Dict[str, Any],
    read_only_fields: List[str],
    computed_fields: List[str],
    help_texts: Dict[str, Dict[str, str]],
    field_titles: Dict[str, Any],
) -> Dict[str, Any]:
    """Собирает описание поля для UI."""
    field_info = schema_props.get(field, {})
    field_title = field_titles.get(field, field_info.get("title", {}))
    field_default, field_settings = extract_default_value_and_settings(instance, field, field_info.get("default"))

    py_type = model_annotations.get(field)
    is_optional = False
    if py_type:
        is_optional = get_origin(py_type) is Union and type(None) in get_args(py_type)
        py_type = unwrap_optional(py_type)

    field_type, choices = determine_field_type_and_choices(py_type, field, read_only_fields)

    if "choices" in field_settings:
        choices = field_settings["choices"]
    if "type" in field_settings:
        field_type = field_settings["type"]

    placeholder = field_settings.pop("placeholder", None)

    has_explicit_default = field_default is not None
    has_factory = callable(getattr(getattr(instance.model, "model_fields", {}).get(field, {}), "default_factory", None))
    is_empty_dict = isinstance(field_default, dict) and not field_default
    has_only_settings = isinstance(field_info, dict) and "settings" in field_info and len(field_info) == 1
    read_only = field in read_only_fields or field in computed_fields

    required_flag = not is_optional or (not has_explicit_default and not has_factory and (is_empty_dict or has_only_settings))

    return {
        "name": field,
        "type": field_type,
        "title": field_title,
        "help_text": help_texts.get(field, {}),
        "read_only": read_only,
        "default": field_default if has_explicit_default else None,
        "required": required_flag,
        "choices": choices,
        "placeholder": placeholder,
        "settings": field_settings,
    }


async def build_inlines(
    instance: Any,
    inlines_dict: Dict[str, Any],
    model_annotations: Dict[str, Any],
    current_user: Any,
) -> List[dict]:
    """Возвращает список описаний inline-моделей (single или list)."""
    result: List[dict] = []
    for inline_field, inline_cls in inlines_dict.items():
        inline_instance = inline_cls(instance.db)
        inline_type = "single"
        if inline_field in model_annotations:
            field_ann = unwrap_optional(model_annotations[inline_field])
            origin = get_origin(field_ann)
            if origin in (list, List):
                inline_type = "list"
            elif origin is Union and any(get_origin(arg) in (list, List) for arg in get_args(field_ann)):
                inline_type = "list"
        result.append(await build_inline_schema(inline_field, inline_instance, inline_type, current_user))
    return result


def build_field_groups(field_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Собирает описание групп полей для UI."""
    return [
        {
            "title": group["title"],
            "fields": group["fields"],
            "help_text": group.get("help_text", {}),
            "column": group.get("column", 0),
        }
        for group in field_groups
    ]


def deep_update(dst: dict, src: dict) -> None:
    """Глубокое слияние словаря src в dst."""
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_update(dst[k], v)
        else:
            dst[k] = v


async def build_model_info(instance: Any, current_user: Any) -> dict:
    """Формирует описание админ-модели для UI: поля, группы, инлайны, разрешения и декларативные конфиги запросов."""
    attrs = get_instance_attributes(instance)
    schema_props, _ = get_schema_data(instance)
    model_annotations = getattr(instance.model, "__annotations__", {})

    combined_fields = list(dict.fromkeys(attrs["list_display"] + attrs["detail_fields"]))
    fields_schema = [
        build_field_schema(
            instance,
            field,
            schema_props,
            model_annotations,
            attrs["read_only_fields"],
            attrs["computed_fields"],
            attrs["help_texts"],
            attrs["field_titles"],
        )
        for field in combined_fields
    ]

    overrides: Dict[str, Any] = {}
    override_obj: Optional[dict] = None
    if hasattr(instance, "get_field_overrides"):
        try:
            if attrs["max_instances"] == 1:
                override_obj = await instance.get_singleton_object(current_user)
            overrides = await instance.get_field_overrides(obj=override_obj, current_user=current_user)
        except Exception as exc:
            logger.debug("get_field_overrides error for %s: %s", instance, exc)
            overrides = {}

    for fld in fields_schema:
        if fld["name"] in overrides:
            deep_update(fld, overrides[fld["name"]])

    groups_schema = build_field_groups(attrs["field_groups"])
    inlines_list = await build_inlines(instance, attrs["inlines_dict"], model_annotations, current_user)

    # Прокидываем декларативные конфиги для фронта (чтобы рисовать UI поиска/фильтров/сортировки)
    search_config = getattr(instance, "get_search_config", None)
    filter_config = getattr(instance, "get_filter_config", None)
    sort_config = getattr(instance, "get_sort_config", None)

    search_cfg = search_config() if callable(search_config) else (getattr(instance, "search_config", {}) or {})
    filter_cfg = filter_config() if callable(filter_config) else (getattr(instance, "filter_config", {}) or {})
    sort_cfg = sort_config() if callable(sort_config) else (getattr(instance, "sort_config", {}) or {})

    query_ui = {
        "search": {
            "default_mode": getattr(instance, "default_search_mode", "partial"),
            "default_combine": getattr(instance, "default_search_combine", "or"),
            "fields": getattr(instance, "search_fields", []),
            "computed_fields": getattr(instance, "searchable_computed_fields", []),
            "config": search_cfg,
        },
        "filters": {
            "config": filter_cfg
        },
        "sort": {
            "config": sort_cfg
        },
        # Подсказка фронту: как правильно слать параметры в list:
        # GET /{entity}/?sort_by=...&order=1&filters=<JSON>&search=<JSON>|q=...
        "request_params_hints": {
            "filters_param": "filters",  # JSON, внутри можно указывать __filters и __search
            "search_param": "search",    # JSON ИЛИ строка; альтернативно q=<string>
            "q_param": "q",
        }
    }

    return {
        "name": instance.model.__name__,
        "verbose_name": instance.verbose_name,
        "plural_name": instance.plural_name,
        "icon": instance.icon,
        "list_display": attrs["list_display"],
        "detail_fields": attrs["detail_fields"],
        "computed_fields": attrs["computed_fields"],
        "read_only_fields": attrs["read_only_fields"],
        "fields": fields_schema,
        "field_groups": groups_schema,
        "field_styles": getattr(instance, "field_styles", {}),
        "inlines": inlines_list,
        "is_inline": isinstance(instance, InlineCrud),
        "max_instances_per_user": attrs["max_instances"],
        "allow_crud_actions": attrs["allow_crud"],
        "query_ui": query_ui,
    }


async def build_inline_schema(inline_field: str, inline_instance: Any, inline_type: str, current_user: Any) -> dict:
    """Формирует описание inline-модели, добавляя поле 'field' и тип инлайна."""
    base_schema = await build_model_info(inline_instance, current_user)
    base_schema["field"] = inline_field
    base_schema["inline_type"] = inline_type
    return base_schema


def get_app_info(module_path: str, registry_name: str) -> tuple[str, str, str, str]:
    """Определяет имя приложения, verbose-имя, иконку и цвет по модулю модели."""
    parts = module_path.split(".")
    app_name = parts[-1]
    if registry_name in parts:
        idx = parts.index(registry_name)
        app_name = parts[idx - 1] if idx > 0 else "unknown"

    module_root = ".".join(parts[:-1])
    try:
        config_module = import_module(f"{module_root}.config")
        return (
            app_name,
            getattr(config_module, "verbose_name", app_name),
            getattr(config_module, "icon", ""),
            getattr(config_module, "color", ""),
        )
    except ModuleNotFoundError:
        return app_name, app_name, "", ""


def get_model_routes(api_prefix: str, registered_name: str, instance: Any) -> List[Dict[str, str]]:
    """Возвращает список маршрутов модели: CRUD + кастомные @admin_route."""
    snake_name = to_snake_case(registered_name)
    routes: List[Dict[str, str]] = []

    # CRUD
    if instance.allow_crud_actions.get("read", False):
        routes.append({"method": "GET", "path": f"{api_prefix}/{snake_name}/", "name": f"list_{snake_name}"})
        routes.append({"method": "GET", "path": f"{api_prefix}/{snake_name}/{{item_id}}", "name": f"get_{snake_name}"})
    if instance.allow_crud_actions.get("create", False):
        routes.append({"method": "POST", "path": f"{api_prefix}/{snake_name}/", "name": f"create_{snake_name}"})
    if instance.allow_crud_actions.get("update", False):
        routes.append({"method": "PATCH", "path": f"{api_prefix}/{snake_name}/{{item_id}}", "name": f"patch_{snake_name}"})
    if instance.allow_crud_actions.get("delete", False):
        routes.append({"method": "DELETE", "path": f"{api_prefix}/{snake_name}/{{item_id}}", "name": f"delete_{snake_name}"})

    # Кастомные методы: перебираем только bound-методы, метаданные ищем у .__func__
    for _, handler in inspect.getmembers(instance, predicate=inspect.ismethod):
        func = getattr(handler, "__func__", handler)
        meta_list = getattr(func, "admin_route_meta", None)
        if not isinstance(meta_list, list):
            continue

        for meta in meta_list:
            relative = meta["path"] if meta["path"].startswith("/") else f"/{meta['path']}"
            full_path = f"{api_prefix}/{snake_name}{relative}"
            route_name = meta["name"] or f"{snake_name}_{meta['method'].lower()}_{relative.strip('/').replace('/', '_') or 'root'}"
            routes.append({"method": meta["method"], "path": full_path, "name": route_name})

    return routes



async def build_model_entry(instance: Any, api_prefix: str, registered_name: str, current_user: Any) -> Dict[str, Any]:
    """Возвращает описание модели для UI: схема и перечень маршрутов."""
    return {
        "registered_name": registered_name,
        "model": await build_model_info(instance, current_user),
        "routes": get_model_routes(api_prefix, registered_name, instance),
    }


async def get_routes_by_apps(registry: BaseRegistry, current_user: Any) -> Dict[str, Any]:
    """Группирует модели по приложениям и возвращает структуру для админ-интерфейса."""
    apps: Dict[str, Any] = {}
    api_prefix = f"/api/{registry.name}"

    for registered_name, instance in registry.get_registered().items():
        module_path = instance.__module__
        try:
            instance.check_permission("read", user=current_user)
        except HTTPException:
            continue

        app_name, verbose_name, icon, color = get_app_info(module_path, registry.name)
        if app_name not in apps:
            apps[app_name] = {"verbose_name": verbose_name, "icon": icon, "color": color, "entities": []}

        apps[app_name]["entities"].append(
            await build_model_entry(instance, api_prefix, registered_name, current_user)
        )

    return apps
