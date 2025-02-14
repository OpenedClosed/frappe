"""Формирование маршрутов админ-панели."""
import importlib
import os
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import ValidationError

from admin_core.admin_registry import AdminRegistry
from auth.utils.help_functions import (add_token_to_blacklist,
                                       is_token_blacklisted, jwt_required)
from db.mongo.db_init import mongo_db
from infra import settings
from users.db.mongo.schemas import LoginSchema, User
from utils.help_functions import to_snake_case


async def auto_discover_admin_modules():
    """
    Автоматически находит и импортирует все admin.py файлы в приложении.
    """
    base_dir = settings.BASE_DIR
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file == "admin.py":
                relative_path = Path(root).relative_to(base_dir)
                module_path = relative_path.as_posix().replace("/", ".")
                module_name = f"{module_path}.admin"
                try:
                    importlib.import_module(module_name)
                except Exception as e:
                    print(f"Ошибка при импорте {module_name}: {e}")


def generate_admin_routes(admin_registry: AdminRegistry):
    """
    Генерирует маршруты для зарегистрированных админок, включая авторизацию.
    """
    admin_router = APIRouter()
    print("Генерируем маршруты админки...")

    @admin_router.post("/login")
    async def admin_login(
        request: Request,
        response: Response,
        login_data: LoginSchema,
        Authorize: AuthJWT = Depends()
    ):
        """
        Вход в админку.
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

    @admin_router.post("/refresh")
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
                detail="Refresh token is missing")

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

    @admin_router.post("/logout")
    @jwt_required()
    async def admin_logout(
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Выход из админки (логаут).
        Аннулирует все активные куки и помещает текущие токены в блэклист.
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

    def create_routes(name, admin_instance):
        """Создание CRUD-маршрутов админки."""
        snake_name = to_snake_case(name)

        @admin_router.get(f"/{snake_name}/", name=f"list_{snake_name}")
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
            """Замыкание получения объектов."""
            has_page_in_query = ('page' in request.query_params)
            has_page_size_in_query = ('page_size' in request.query_params)

            if has_page_in_query and has_page_size_in_query:
                return await admin_instance.list_with_meta(
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    order=order
                )
            else:
                return await admin_instance.list(
                    sort_by=sort_by,
                    order=order
                )

        @admin_router.get(f"/{snake_name}/{{item_id}}",
                          name=f"get_{snake_name}")
        @jwt_required()
        async def get_item(
            request: Request,
            response: Response,
            item_id: str,
            Authorize: AuthJWT = Depends()
        ):
            """Замыкание получения объекта."""
            item = await admin_instance.get(item_id)
            if not item:
                raise HTTPException(status_code=404, detail="Item not found")
            return item

        @admin_router.post(f"/{snake_name}/", name=f"create_{snake_name}")
        @jwt_required()
        async def create_item(
            request: Request,
            response: Response,
            data: dict,
            Authorize: AuthJWT = Depends()
        ):
            """Замыкание создания объекта."""
            try:
                return await admin_instance.create(data)
            except ValidationError as e:
                errors = {err["loc"][-1]: err["msg"] for err in e.errors()}
                raise HTTPException(status_code=400, detail=errors)

        @admin_router.patch(f"/{snake_name}/{{item_id}}",
                            name=f"patch_{snake_name}")
        @jwt_required()
        async def patch_item(
            request: Request,
            response: Response,
            item_id: str,
            data: dict,
            Authorize: AuthJWT = Depends()
        ):
            """Замыкание обновления объекта."""
            try:
                updated = await admin_instance.update(object_id=item_id, data=data)
                if not updated:
                    raise HTTPException(
                        status_code=404, detail="Item not updated")
                return updated
            except ValidationError as e:
                errors = {err["loc"][-1]: err["msg"] for err in e.errors()}
                raise HTTPException(status_code=400, detail=errors)

        @admin_router.delete(f"/{snake_name}/{{item_id}}",
                             name=f"delete_{snake_name}")
        @jwt_required()
        async def delete_item(
            request: Request,
            response: Response,
            item_id: str,
            Authorize: AuthJWT = Depends()
        ):
            """Замыкание удаление объекта."""
            deleted = await admin_instance.delete(object_id=item_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Item not deleted")
            return {"status": "success"}

    for name, admin_instance in admin_registry.get_registered_admins().items():
        create_routes(name, admin_instance)

    @admin_router.get("/info")
    @jwt_required()
    async def get_admin_info(
        request: Request,
        response: Response,
        Authorize: AuthJWT = Depends()
    ):
        """
        Информация для админа.
        """
        return get_admin_routes_by_apps(admin_registry)

    return admin_router


def _build_model_info(admin_instance) -> dict:
    """Получение структуры данных для админ-модели или инлайна."""
    list_display = getattr(admin_instance, "list_display", [])
    detail_fields = getattr(admin_instance, "detail_fields", [])
    computed_fields = getattr(admin_instance, "computed_fields", [])
    read_only_fields = getattr(admin_instance, "read_only_fields", [])
    inlines_dict = getattr(admin_instance, "inlines", {})

    field_titles = getattr(admin_instance, "field_titles", {})

    combined_fields = list(dict.fromkeys(list_display + detail_fields))
    schema_props = admin_instance.model.schema().get("properties", {})
    model_annotations = getattr(admin_instance.model, "__annotations__", {})
    fields_schema = []

    for field in combined_fields:
        field_info = schema_props.get(field, {})
        field_type = field_info.get("type", "unknown")
        field_title = field_titles.get(
            field, field_info.get(
                "title", {}))  # Делаем title словарем
        choices = None
        py_type = model_annotations.get(field)
        if py_type and hasattr(py_type, "__members__"):
            choices = [{"value": m.value, "label": m.name} for m in py_type]

        fields_schema.append({
            "name": field,
            "type": field_type,
            "title": field_title,  # Словарь переводов по языкам
            "read_only": (field in read_only_fields or field in computed_fields),
            "default": field_info.get("default"),
            "required": field in admin_instance.model.schema().get("required", []),
            "choices": choices
        })

    inlines_list = []
    for inline_field, inline_cls in inlines_dict.items():
        inline_instance = inline_cls(admin_instance.db)
        inlines_list.append(build_inline_schema(inline_field, inline_instance))

    return {
        "name": admin_instance.model.__name__,
        "verbose_name": admin_instance.verbose_name,
        "plural_name": admin_instance.plural_name,
        "icon": admin_instance.icon,
        "list_display": list_display,
        "detail_fields": detail_fields,
        "computed_fields": computed_fields,
        "read_only_fields": read_only_fields,
        "fields": fields_schema,
        "inlines": inlines_list
    }


def build_inline_schema(inline_field: str, inline_instance) -> dict:
    """Формирует схему для инлайна с учётом вложений."""
    base_schema = _build_model_info(inline_instance)
    base_schema["field"] = inline_field
    return base_schema


def get_admin_routes_by_apps(admin_registry: AdminRegistry) -> Dict[str, Any]:
    """Формирует структуру описания админ-моделей."""
    apps = {}
    for registered_name, admin_instance in admin_registry.get_registered_admins().items():
        module_path = admin_instance.__module__
        mod_parts = module_path.split(".")
        if "admin" in mod_parts:
            idx = mod_parts.index("admin")
            app_name = mod_parts[idx - 1] if idx > 0 else "unknown"
        else:
            app_name = mod_parts[-1]
        module_root = ".".join(mod_parts[:-1])

        try:
            config_module = import_module(f"{module_root}.config")
            verbose_name = getattr(config_module, "verbose_name", app_name)
            icon = getattr(config_module, "icon", "")
            color = getattr(config_module, "color", "")
        except ModuleNotFoundError:
            verbose_name, icon, color = app_name, "", ""

        if app_name not in apps:
            apps[app_name] = {
                "verbose_name": verbose_name,
                "icon": icon,
                "color": color,
                "entities": []}

        snake_name = to_snake_case(registered_name)
        model_info = _build_model_info(admin_instance)

        model_routes = [
            {"method": "GET",
             "path": f"/api/admin/{snake_name}/",
             "name": f"list_{snake_name}"},
            {"method": "GET",
             "path": f"/api/admin/{snake_name}/{{item_id}}",
             "name": f"get_{snake_name}"},
            {"method": "POST",
             "path": f"/api/admin/{snake_name}/",
             "name": f"create_{snake_name}"},
            {"method": "PATCH",
             "path": f"/api/admin/{snake_name}/{{item_id}}",
             "name": f"patch_{snake_name}"},
            {"method": "DELETE",
             "path": f"/api/admin/{snake_name}/{{item_id}}",
             "name": f"delete_{snake_name}"}
        ]

        apps[app_name]["entities"].append({
            "registered_name": registered_name,
            "model": model_info,
            "routes": model_routes
        })

    return apps
