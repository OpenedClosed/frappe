"""Файл запуска приложения."""
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.errors import (general_exception_handler,
                          validation_exception_handler)
from users.routers import user_router
from personal_account.routes_generator import generate_base_account_routes
from knowledge.routers import knowledge_base_router
from infra.middlewares import BasicAuthMiddleware
from infra import settings
from db.mongo.db_init import mongo_db_on_startapp
from crud_core.routes_generator import (auto_discover_modules,
                                        generate_base_routes,
                                        get_routes_by_apps)
from crud_core.registry import account_registry, admin_registry
from chats.routers import chat_router
from chats.integrations.meta.whatsapp.whatsapp import whatsapp_router
from chats.integrations.meta.instagram.instagram import instagram_router
from basic.routers import basic_router
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI


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
chat_router.include_router(whatsapp_router, prefix="/whatsapp")
base_api_router.include_router(chat_router, prefix="/chats")
base_api_router.include_router(user_router, prefix="/users")
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
