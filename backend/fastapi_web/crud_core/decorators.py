"""Декораторы для админ-классов (кастомные маршруты)."""
from __future__ import annotations

from typing import Any, Callable, List, Optional


__all__ = ["admin_route"]


def admin_route(
    path: str,
    method: str = "POST",
    *,
    name: Optional[str] = None,
    permission_action: str = "read",
    auth: bool = True,
    status_code: int = 200,
    response_model: Optional[Any] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Callable:
    """
    Декоратор для методов админ-класса. Позволяет объявлять дополнительные
    эндпоинты прямо в классе, а генератор маршрутов их автоматически подхватит.

    Пример:
        class OrdersAdmin(BaseCrud):
            @admin_route("/sync", method="POST", permission_action="update")
            async def sync(self, *, data, current_user, request, path_params, query_params):
                return {"ok": True}

    Аргументы:
        path: относительный путь внутри сущности (начиная с '/' или без).
        method: HTTP-метод ("GET" | "POST" | "PATCH" | "PUT" | "DELETE").
        name: имя маршрута (если не задано — сформируется автоматически).
        permission_action: действие для проверки прав через permission_class.
        auth: требовать ли JWT-аутентификацию.
        status_code: код успешного ответа.
        response_model: Pydantic-модель ответа (пробрасывается в FastAPI).
        summary: краткое описание для OpenAPI.
        description: подробное описание для OpenAPI.
        tags: список тегов OpenAPI.
    """
    method = method.upper()

    def wrapper(func: Callable) -> Callable:
        meta_list = getattr(func, "admin_route_meta", [])
        meta_list.append({
            "path": path if path.startswith("/") else f"/{path}",
            "method": method,
            "name": name,
            "permission_action": permission_action,
            "auth": auth,
            "status_code": status_code,
            "response_model": response_model,
            "summary": summary,
            "description": description,
            "tags": tags or [],
        })
        setattr(func, "admin_route_meta", meta_list)
        return func

    return wrapper
