"""Формирование маршрутов приложения ядро CRUD создания."""
import importlib
import os
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, get_args, get_origin

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import ValidationError

from auth.utils.help_functions import (add_token_to_blacklist,
                                       is_token_blacklisted, jwt_required)
from db.mongo.db_init import mongo_db
from infra import settings
from users.db.mongo.schemas import LoginSchema, User
from users.utils.help_functions import get_current_user
from utils.help_functions import to_snake_case

from .models import InlineCrud
from .registry import BaseRegistry
from .utils.help_functions import (extract_list_inner_type, get_enum_choices,
                                   is_dict_type, is_email_type, is_enum_type,
                                   is_file_type, is_list_of_enum,
                                   is_list_of_file, is_list_of_photo,
                                   is_location_type, is_photo_type,
                                   is_range_value_type, is_rating_type,
                                   is_table_row_type, unwrap_optional)


async def auto_discover_modules(module_name: str):
    """
    Автоматически находит и импортирует все файлы с указанным именем (например, "admin.py" или "account.py") в приложении.
    """
    for root, _, files in os.walk(settings.BASE_DIR):
        for file in files:
            if file == f"{module_name}.py":
                relative_path = Path(root).relative_to(settings.BASE_DIR)
                module_path = relative_path.as_posix().replace("/", ".")
                full_module_name = f"{module_path}.{module_name}"
                try:
                    importlib.import_module(full_module_name)
                    print(f"Импортирован модуль: {full_module_name}")
                except Exception as e:
                    print(f"Ошибка при импорте {full_module_name}: {e}")


def generate_base_routes(registry: BaseRegistry):
    """
    Генерация базовых маршрутов для админских моделей и авторизации.
    """
    router = APIRouter()
    print("Генерируем маршруты...")

    @router.post("/login")
    async def login(
        request: Request,
        response: Response,
        login_data: LoginSchema,
        Authorize: AuthJWT = Depends()
    ):
        """
        Вход в систему.
        """
        user_doc = await mongo_db["users"].find_one({"username": login_data.username})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid credentials.")

        user = User(**user_doc)
        if not user.check_password(login_data.password):
            raise HTTPException(status_code=401, detail="Invalid credentials.")

        old_access = request.cookies.get("access_token")
        old_refresh = request.cookies.get("refresh_token")

        if old_access:
            try:
                Authorize._token = old_access
                Authorize.jwt_required()
                old_access_jti = Authorize.get_raw_jwt()["jti"]
                await add_token_to_blacklist(str(user_doc["_id"]), "access", old_access_jti)
            except Exception:
                pass

        if old_refresh:
            try:
                Authorize._token = old_refresh
                Authorize.jwt_refresh_token_required()
                old_refresh_jti = Authorize.get_raw_jwt()["jti"]
                await add_token_to_blacklist(str(user_doc["_id"]), "refresh", old_refresh_jti)
            except Exception:
                pass

        access_token = Authorize.create_access_token(
            subject=str(user_doc["_id"]))
        refresh_token = Authorize.create_refresh_token(
            subject=str(user_doc["_id"]))

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=False,
            secure=True,
            samesite="None"
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=False,
            secure=True,
            samesite="None"
        )
        return {"message": "Logged in", "access_token": access_token}

    @router.post("/refresh")
    async def refresh_tokens(
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Обновить токены.
        """
        old_refresh = request.cookies.get("refresh_token")
        if not old_refresh:
            raise HTTPException(
                status_code=401,
                detail="Refresh token is missing"
            )

        Authorize._token = old_refresh
        try:
            Authorize.jwt_refresh_token_required()
        except AuthJWTException:
            raise HTTPException(status_code=401,
                                detail="Invalid or expired refresh token")

        current_user = Authorize.get_jwt_subject()
        raw_refresh_jwt = Authorize.get_raw_jwt()
        refresh_jti = raw_refresh_jwt["jti"]

        if await is_token_blacklisted(current_user, "refresh", refresh_jti):
            raise HTTPException(
                status_code=401,
                detail="Refresh token is blacklisted")

        await add_token_to_blacklist(current_user, "refresh", refresh_jti)

        old_access = request.cookies.get("access_token")
        if old_access:
            try:
                Authorize._token = old_access
                Authorize.jwt_required()
                old_access_jti = Authorize.get_raw_jwt()["jti"]
                await add_token_to_blacklist(current_user, "access", old_access_jti)
            except Exception:
                pass

        new_access = Authorize.create_access_token(subject=current_user)
        new_refresh = Authorize.create_refresh_token(subject=current_user)

        response.set_cookie(
            key="access_token",
            value=new_access,
            httponly=False,
            secure=True,
            samesite="None"
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh,
            httponly=False,
            secure=True,
            samesite="None"
        )

        return {"message": "Tokens refreshed", "access_token": new_access}

    @router.post("/logout")
    @jwt_required()
    async def logout(
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Выход из системы.
        """
        current_user = Authorize.get_jwt_subject()

        access_token = request.cookies.get("access_token")
        refresh_token = request.cookies.get("refresh_token")

        if access_token:
            try:
                Authorize._token = access_token
                Authorize.jwt_required()
                old_access_jti = Authorize.get_raw_jwt()["jti"]
                await add_token_to_blacklist(current_user, "access", old_access_jti)
            except Exception:
                pass

        if refresh_token:
            try:
                Authorize._token = refresh_token
                Authorize.jwt_refresh_token_required()
                old_refresh_jti = Authorize.get_raw_jwt()["jti"]
                await add_token_to_blacklist(current_user, "refresh", old_refresh_jti)
            except Exception:
                pass

        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return {"message": "Logged out"}

    def create_routes(
        name: str,
        instance,
    ):
        """
        Генерация CRUD-маршрутов для каждой модели (instance) на базе FastAPI,
        с учётом прав (jwt) и загрузки пользователя из Mongo.
        """
        snake_name = to_snake_case(name)

        # --- READ ---
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
                Authorize: AuthJWT = Depends()
            ):
                """
                Возвращает список объектов (учитывая max_instances_per_user, права доступа и т.д.).
                """
                user_doc = await get_current_user(Authorize)

                has_page_in_query = ('page' in request.query_params)
                has_page_size_in_query = ('page_size' in request.query_params)

                if instance.max_instances_per_user == 1:

                    items = await instance.get_queryset(current_user=user_doc)
                    item = None
                    if items:
                        first_obj = items[0]
                        item_id = first_obj.get("_id") or first_obj.get("id")
                        if not item_id:
                            raise HTTPException(
                                status_code=404, detail="Invalid document: missing _id")

                        item = await instance.get(object_id=item_id, current_user=user_doc)
                    if not item:
                        raise HTTPException(
                            status_code=404, detail="Item not found")
                    return item

                if has_page_in_query and has_page_size_in_query:
                    return await instance.list_with_meta(
                        page=page,
                        page_size=page_size,
                        sort_by=sort_by,
                        order=order,
                        current_user=user_doc
                    )

                else:
                    return await instance.list(
                        sort_by=sort_by,
                        order=order,
                        current_user=user_doc
                    )

            @router.get(f"/{snake_name}/{{item_id}}", name=f"get_{snake_name}")
            @jwt_required()
            async def get_item(
                request: Request,
                response: Response,
                item_id: str,
                Authorize: AuthJWT = Depends()
            ):
                """
                Получение конкретного объекта (учитывая права).
                """
                user_doc = await get_current_user(Authorize)

                item = await instance.get(object_id=item_id, current_user=user_doc)
                if not item:
                    raise HTTPException(
                        status_code=404, detail="Item not found")
                return item

        # --- CREATE ---
        if instance.allow_crud_actions.get("create", False):

            @router.post(f"/{snake_name}/", name=f"create_{snake_name}")
            @jwt_required()
            async def create_item(
                request: Request,
                response: Response,
                data: dict,
                Authorize: AuthJWT = Depends()
            ):
                """
                Создание нового объекта (учёт max_instances_per_user, прав и т.д.).
                """
                user_doc = await get_current_user(Authorize)

                try:
                    return await instance.create(data, current_user=user_doc)
                except ValidationError as e:
                    errors = {err["loc"][-1]: err["msg"] for err in e.errors()}
                    raise HTTPException(status_code=400, detail=errors)

        # --- UPDATE ---
        if instance.allow_crud_actions.get("update", False):

            @router.patch(f"/{snake_name}/{{item_id}}",
                          name=f"patch_{snake_name}")
            @jwt_required()
            async def patch_item(
                request: Request,
                response: Response,
                item_id: str,
                data: dict,
                Authorize: AuthJWT = Depends()
            ):
                """
                Обновление конкретного объекта (учитывая права).
                """
                user_doc = await get_current_user(Authorize)

                try:
                    updated = await instance.update(
                        object_id=item_id,
                        data=data,
                        current_user=user_doc
                    )
                    if not updated:
                        raise HTTPException(
                            status_code=404, detail="Item not updated")
                    return updated
                except ValidationError as e:
                    errors = {err["loc"][-1]: err["msg"] for err in e.errors()}
                    raise HTTPException(status_code=400, detail=errors)

        # --- DELETE ---
        if instance.allow_crud_actions.get("delete", False):

            @router.delete(f"/{snake_name}/{{item_id}}",
                           name=f"delete_{snake_name}")
            @jwt_required()
            async def delete_item(
                request: Request,
                response: Response,
                item_id: str,
                Authorize: AuthJWT = Depends()
            ):
                """
                Удаление конкретного объекта (учитывая права).
                """
                user_doc = await get_current_user(Authorize)

                deleted = await instance.delete(object_id=item_id, current_user=user_doc)
                if not deleted:
                    raise HTTPException(
                        status_code=404, detail="Item not deleted")
                return {"status": "success"}

    for name, instance in registry.get_registered().items():
        create_routes(name, instance)

    @router.get("/info")
    @jwt_required()
    async def get_info(
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Информация для админа (список зарегистрированных моделей и т.д.).
        """
        current_user = await get_current_user(Authorize)
        return get_routes_by_apps(registry, current_user)

    return router


def map_python_type_to_ui(py_type):
    """
    Определяет UI-тип для заданного Python-типа,
    если у поля нет настроек в settings["type"].
    """
    type_mapping = {
        str: "string",
        int: "number",
        float: "float",
        bool: "boolean",
        datetime: "datetime",
        dict: "json",
    }

    if py_type in type_mapping:
        return type_mapping[py_type]
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


def get_schema_data(instance):
    """
    Возвращает свойства (properties) и список обязательных полей (required) схемы модели.
    """
    try:
        schema = instance.model.schema(by_alias=False)
        return schema.get("properties", {}), schema.get("required", [])
    except Exception:
        return {}, []


def get_instance_attributes(instance):
    """
    Извлекает атрибуты модели, используемые при построении схемы.
    """
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
        "allow_crud": getattr(instance, "allow_crud_actions", {"create": True, "read": True, "update": True, "delete": True}),
    }


def determine_field_type_and_choices(py_type, field, read_only_fields):
    """
    Определяет UI-тип и возможные варианты выбора (choices) для поля.
    """
    if py_type is None:
        return "unknown", None

    if is_enum_type(py_type):
        return "select", get_enum_choices(py_type)
    if is_list_of_enum(py_type):
        return "multiselect", get_enum_choices(
            extract_list_inner_type(py_type))
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
    return auto_ui if auto_ui != "unknown" else py_type, None


def get_schema_data(instance):
    """Возвращает свойства (properties) и список обязательных полей (required) схемы модели."""
    try:
        schema = instance.model.schema(by_alias=False)
        return schema.get("properties", {}), schema.get("required", [])
    except Exception:
        return {}, []


def extract_default_value_and_settings(instance, field_name, default_value):
    """
    Определяет значение по умолчанию и settings для поля:
    - из обычного словаря (default={'settings': {...}})
    - из json_schema_extra внутри Field(...)
    """
    field_def = getattr(instance.model, "model_fields", {}).get(field_name)

    if default_value is None and field_def and hasattr(
            field_def, "default_factory"):
        try:
            factory_value = field_def.default_factory()
            if isinstance(factory_value, dict) and "settings" in factory_value and len(
                    factory_value) == 1:
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


def build_field_schema(instance, field, schema_props, model_annotations,
                       read_only_fields, computed_fields, help_texts, field_titles):
    """
    Создаёт структуру данных для одного поля, корректно извлекая тип, настройки, стандартное значение и обязательность.
    """
    field_info = schema_props.get(field, {})
    field_title = field_titles.get(field, field_info.get("title", {}))

    field_default, field_settings = extract_default_value_and_settings(
        instance, field, field_info.get("default")
    )

    py_type = model_annotations.get(field)
    is_optional = False
    is_list = False

    if py_type:
        is_optional = get_origin(py_type) is Union and type(
            None) in get_args(py_type)
        py_type = unwrap_optional(py_type)
        is_list = get_origin(py_type) in (list, List)
        inner_type = extract_list_inner_type(py_type) if is_list else py_type
    else:
        inner_type = None

    field_type, choices = determine_field_type_and_choices(
        py_type, field, read_only_fields
    )

    if "choices" in field_settings:
        choices = field_settings["choices"]

    if "type" in field_settings:
        field_type = field_settings["type"]

    placeholder = field_settings.pop("placeholder", None)

    has_explicit_default = field_default is not None
    has_factory = callable(
        getattr(
            instance.model.model_fields.get(
                field,
                {}),
            "default_factory",
            None))
    is_empty_dict = isinstance(field_default, dict) and not field_default
    has_only_settings = isinstance(
        field_info, dict) and "settings" in field_info and len(field_info) == 1
    required_flag = not is_optional or (
        not has_explicit_default and not has_factory and (
            is_empty_dict or has_only_settings)
    )

    return {
        "name": field,
        "type": field_type,
        "title": field_title,
        "help_text": help_texts.get(field, {}),
        "read_only": field in read_only_fields or field in computed_fields,
        "default": field_default if has_explicit_default else None,
        "required": required_flag,
        "choices": choices,
        "placeholder": placeholder,
        "settings": field_settings,
    }


def build_inlines(instance, inlines_dict, model_annotations):
    """
    Формирует список inlines (вложенных моделей), учитывая их тип (single или list).
    """
    inlines_list = []
    for inline_field, inline_cls in inlines_dict.items():
        inline_instance = inline_cls(instance.db)
        inline_type = "single"

        if inline_field in model_annotations:
            field_annotation = unwrap_optional(model_annotations[inline_field])
            origin = get_origin(field_annotation)
            if origin in (list, List):
                inline_type = "list"
            elif origin is Union:
                args = get_args(field_annotation)
                if any(get_origin(arg) in (list, List) for arg in args):
                    inline_type = "list"

        inlines_list.append(
            build_inline_schema(
                inline_field,
                inline_instance,
                inline_type))

    return inlines_list


def build_field_groups(field_groups):
    """
    Собирает структуру групп полей.
    """
    return [
        {
            "title": group["title"],
            "fields": group["fields"],
            "help_text": group.get("help_text", {}),
            "column": group.get("column", 0)
        }
        for group in field_groups
    ]


def build_model_info(instance) -> dict:
    """
    Формирует структуру описания админ-модели или инлайна.
    """
    attrs = get_instance_attributes(instance)
    schema_props, _ = get_schema_data(instance)
    model_annotations = getattr(instance.model, "__annotations__", {})

    combined_fields = list(
        dict.fromkeys(
            attrs["list_display"] +
            attrs["detail_fields"]))
    fields_schema = [
        build_field_schema(instance, field, schema_props, model_annotations, attrs["read_only_fields"],
                           attrs["computed_fields"], attrs["help_texts"], attrs["field_titles"])
        for field in combined_fields
    ]

    groups_schema = build_field_groups(attrs["field_groups"])
    inlines_list = build_inlines(
        instance,
        attrs["inlines_dict"],
        model_annotations)

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
        "field_styles": instance.field_styles,
        "inlines": inlines_list,
        "is_inline": isinstance(instance, InlineCrud),
        "max_instances_per_user": attrs["max_instances"],
        "allow_crud_actions": attrs["allow_crud"],
    }


def build_inline_schema(inline_field: str, inline_instance,
                        inline_type: str) -> dict:
    """Формирует схему для инлайна с учётом вложений и типа (single или list)."""
    base_schema = build_model_info(inline_instance)
    base_schema["field"] = inline_field
    base_schema["inline_type"] = inline_type
    return base_schema


def get_app_info(module_path: str, registry_name: str) -> tuple:
    """Определяет имя приложения, его verbose_name, иконку и цвет."""
    mod_parts = module_path.split(".")
    app_name = mod_parts[-1]

    if registry_name in mod_parts:
        idx = mod_parts.index(registry_name)
        app_name = mod_parts[idx - 1] if idx > 0 else "unknown"

    module_root = ".".join(mod_parts[:-1])

    try:
        config_module = import_module(f"{module_root}.config")
        return (
            app_name,
            getattr(config_module, "verbose_name", app_name),
            getattr(config_module, "icon", ""),
            getattr(config_module, "color", "")
        )
    except ModuleNotFoundError:
        return app_name, app_name, "", ""


def get_model_routes(api_prefix: str, registered_name: str, instance) -> list:
    """
    Создаёт список маршрутов для модели, используя snake_case.
    Учитывает разрешённые действия из allow_crud_actions.
    """
    snake_name = to_snake_case(registered_name)
    routes = []

    if instance.allow_crud_actions.get("read", False):
        routes.append({
            "method": "GET",
            "path": f"{api_prefix}/{snake_name}/",
            "name": f"list_{snake_name}"
        })
        routes.append({
            "method": "GET",
            "path": f"{api_prefix}/{snake_name}/{{item_id}}",
            "name": f"get_{snake_name}"
        })

    if instance.allow_crud_actions.get("create", False):
        routes.append({
            "method": "POST",
            "path": f"{api_prefix}/{snake_name}/",
            "name": f"create_{snake_name}"
        })

    if instance.allow_crud_actions.get("update", False):
        routes.append({
            "method": "PATCH",
            "path": f"{api_prefix}/{snake_name}/{{item_id}}",
            "name": f"patch_{snake_name}"
        })

    if instance.allow_crud_actions.get("delete", False):
        routes.append({
            "method": "DELETE",
            "path": f"{api_prefix}/{snake_name}/{{item_id}}",
            "name": f"delete_{snake_name}"
        })

    return routes


def build_model_entry(instance, api_prefix,
                      registered_name) -> Dict[str, Any]:
    """Формирует информацию о модели, включая маршруты."""
    return {
        "registered_name": registered_name,
        "model": build_model_info(instance),
        "routes": get_model_routes(api_prefix, registered_name, instance)
    }


def get_routes_by_apps(registry, current_user) -> Dict[str, Any]:
    """Формирует структуру описания моделей с учётом прав пользователя."""
    apps = {}
    api_prefix = f"/api/{registry.name}"

    for registered_name, instance in registry.get_registered().items():
        module_path = instance.__module__

        try:
            instance.check_permission("read", user=current_user)
        except HTTPException:
            continue

        app_name, verbose_name, icon, color = get_app_info(
            module_path, registry.name)

        if app_name not in apps:
            apps[app_name] = {
                "verbose_name": verbose_name,
                "icon": icon,
                "color": color,
                "entities": []}

        apps[app_name]["entities"].append(
            build_model_entry(
                instance,
                api_prefix,
                registered_name))

    return apps
