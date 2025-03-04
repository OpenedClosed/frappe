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


@shared_task(name="clean_unused_files")
def clean_unused_files():
    """Удаляет файлы в /media/, которых нет в базе знаний."""
    logger.info("Запущена очистка неиспользуемых файлов.")

    collection = sync_db.knowledge_collection
    kb_doc = collection.find_one({"app_name": "main"})
    if not kb_doc:
        logger.warning("База знаний не найдена.")
        return "No knowledge base found"

    used_files = set()
    for topic in kb_doc.get("knowledge_base", {}).values():
        for subtopic in topic.get("subtopics", {}).values():
            for answer in subtopic.get("questions", {}).values():
                used_files.update(answer.get("files", []))

    media_dir = settings.MEDIA_DIR
    if not os.path.exists(media_dir):
        logger.warning("Каталог медиафайлов не найден.")
        return "Media directory not found"

    removed_files = []
    for file_name in os.listdir(media_dir):
        file_path = f"/{media_dir}/{file_name}"
        if file_path not in used_files:
            os.remove(os.path.join(media_dir, file_name))
            removed_files.append(file_name)
            logger.info(f"Удалён файл: {file_name}")

    logger.info(f"Удалено {len(removed_files)} файлов.")
    return {"removed_files": removed_files}
