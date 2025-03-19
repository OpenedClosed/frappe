"""Файл запуска приложения."""
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from basic.routers import basic_router
from chats.integrations.instagram.instagram import instagram_router
from chats.routers import chat_router
from crud_core.registry import account_registry, admin_registry
from crud_core.routes_generator import (auto_discover_modules,
                                        generate_base_routes, get_routes_by_apps)
from db.mongo.db_init import mongo_db_on_startapp
from infra import settings
from infra.middlewares import BasicAuthMiddleware
from knowledge.routers import knowledge_base_router
from personal_account.routes_generator import generate_base_account_routes
from utils.errors import (general_exception_handler,
                          validation_exception_handler)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI()

base_api_router = APIRouter(prefix="/api")


async def print_routes():
    """Вывод зарегистрированных маршрутов."""
    print("Зарегистрированные админские маршруты:")
    for route in get_routes_by_apps(admin_registry):
        print(route)


@app.on_event("startup")
async def on_startup():
    """Действия при запуске приложения."""
    from chats.ws import websockets as _

    # await auto_discover_admin_modules()
    await auto_discover_modules("admin")
    await auto_discover_modules("account")
    await mongo_db_on_startapp()
    app.mount(
        "/media",
        StaticFiles(directory=settings.MEDIA_DIR),
        name="media"
    )
    app.mount(
        "/static",
        StaticFiles(directory=settings.STATIC_DIR),
        name="static"
    )

    admin_router = generate_base_routes(admin_registry)
    personal_account_router = generate_base_account_routes(account_registry)
    app.include_router(personal_account_router, prefix="/api/personal_account")
    app.include_router(admin_router, prefix="/api/admin")


@app.on_event("shutdown")
async def on_shutdown():
    """Действия при остановке приложения."""
    pass

chat_router.include_router(instagram_router, prefix="/instagram")
base_api_router.include_router(chat_router, prefix="/chats")
base_api_router.include_router(knowledge_base_router, prefix="/knowledge")
base_api_router.include_router(basic_router, prefix="/basic")
app.include_router(base_api_router)

app.add_middleware(BasicAuthMiddleware, username="admin", password="admin")
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
