"""Приложение Celery."""
from fastapi_web.infra import settings
import logging
import os
import sys
from pathlib import Path

from celery import Celery
from celery.schedules import timedelta
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv(dotenv_path=Path("../infra/.env"))

# Добавляем путь к fastapi_web
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# Настройка Celery
celery = Celery(
    "celery_web_bot_app",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    broker_connection_retry_on_startup=True,
)

# Автоматический поиск задач
celery.autodiscover_tasks(["celery_app"])

# Настройка Beat
celery.conf.beat_schedule = {
    "clean-unused-media-daily": {
        "task": "clean_unused_media_files",
        "schedule": timedelta(hours=1),
        # "schedule": timedelta(seconds=5),
    },
}

logger.info("Celery инициализирован.")
