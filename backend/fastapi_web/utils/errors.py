"""Обработка ошибок и исключений."""
from typing import Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import JSONResponse


class FieldValidationError(Exception):
    """Ошибка поля модели."""

    def __init__(self, field_name: str, message: str,
                 nested: Optional[dict] = None):
        self.field_name = field_name
        self.message = message
        self.nested = nested or {}
        super().__init__(self.message)

    def dict(self):
        error = {self.field_name: self.message}
        if self.nested:
            error[self.field_name] = self.nested
        return error


# async def validation_exception_handler(
#         request: Request, exc: RequestValidationError):
#     """Обработка исключения при запросе."""
#     errors = {}
#     for e in exc.errors():
#         loc = e['loc']
#         current = errors
#         for key in loc[:-1]:
#             current = current.setdefault(key, {})
#         current[loc[-1]] = str(e['ctx']['error'] if e.get('ctx') else e['msg'])

#     return JSONResponse(
#         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={
#             "errors": errors}
#     )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработка исключения при валидации запроса."""
    errors = {}
    for e in exc.errors():
        loc = e['loc']
        current = errors
        for key in loc[:-1]:
            current = current.setdefault(str(key), {})
        # Используем максимально безопасный способ получения текста ошибки
        message = e.get("ctx", {}).get("error") or e.get("msg", "Invalid input")
        current[str(loc[-1])] = message

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"errors": errors}
    )


async def general_exception_handler(request, exc):
    """Обработка исключения при запросе."""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)},
    )
