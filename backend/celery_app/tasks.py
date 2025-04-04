"""Задачи Celery."""
import logging
import os

from celery import shared_task
from fastapi_web.infra import settings
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# Подключение к MongoDB (синхронное)
mongo_client = MongoClient(settings.MONGO_URL)
sync_db = mongo_client[settings.MONGO_DB_NAME]


@shared_task(name="count_documents")
def count_documents():
    """Считает количество документов в базе знаний."""
    collection = sync_db.knowledge_collection
    count = collection.count_documents({})
    logger.info(f"Общее количество документов: {count}")
    return {"total_documents": count}


@shared_task(name="clean_unused_media_files")
def clean_unused_media_files():
    """
    Удаляет файлы в MEDIA_DIR, которые нигде не используются:
    - ни в базе знаний
    - ни в настройках ботов
    """
    logger.info("Запущена комплексная очистка медиафайлов.")
    used_files = set()

    # 1. Проверка в knowledge_collection
    kb_doc = sync_db.knowledge_collection.find_one({"app_name": "main"})
    if kb_doc:
        for topic in kb_doc.get("knowledge_base", {}).values():
            for subtopic in topic.get("subtopics", {}).values():
                for answer in subtopic.get("questions", {}).values():
                    for file_path in answer.get("files", []):
                        used_files.add(_normalize_path(file_path))

    # 2. Проверка в bot_settings
    for bot in sync_db.bot_settings.find({}, {"avatar.url": 1}):
        avatar_path = bot.get("avatar", {}).get("url")
        if avatar_path and not avatar_path.startswith("http"):
            used_files.add(_normalize_path(avatar_path))

    # 3. Очистка неиспользуемых файлов из MEDIA_DIR
    media_dir = settings.MEDIA_DIR
    if not os.path.exists(media_dir):
        logger.warning(f"Каталог медиафайлов не найден: {media_dir}")
        return "Media directory not found"

    removed_files = []
    for file_name in os.listdir(media_dir):
        full_path = os.path.join(media_dir, file_name)
        normalized = _normalize_path(full_path)

        if normalized not in used_files:
            os.remove(full_path)
            removed_files.append(file_name)
            logger.info(f"Удалён файл: {file_name}")

    logger.info(f"Удалено {len(removed_files)} неиспользуемых файлов.")
    return {"removed_files": removed_files}


def _normalize_path(path: str) -> str:
    """
    Приводит путь к унифицированной форме: только имя файла, без путей и префиксов.
    Например: "/media/images/test.png" -> "test.png"
    """
    return os.path.basename(path.strip()).lower() 
