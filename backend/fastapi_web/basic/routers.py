"""Обработчики маршрутов приложения Базовые."""
import os
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile

from infra import settings

basic_router = APIRouter()


@basic_router.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):
    """Загружает файл, сохраняет и возвращает путь к нему."""
    if not file.filename:
        raise HTTPException(400, "No file name provided")

    _, ext = os.path.splitext(file.filename)
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"{now_str}{ext}"

    save_dir = settings.MEDIA_DIR
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    save_path = os.path.join(save_dir, new_filename)

    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)

    return {"file_path": f"/media/{new_filename}"}
