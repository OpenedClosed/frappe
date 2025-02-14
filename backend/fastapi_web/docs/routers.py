"""Функции представления для Документации."""
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.responses import JSONResponse

from main import app


@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    """Документация OpenAPI."""
    return JSONResponse(get_openapi(
        title="My API", version="1.0.0", routes=app.routes))


@app.get("/docs", include_in_schema=False)
async def get_documentation():
    """Документация Swagger."""
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")
