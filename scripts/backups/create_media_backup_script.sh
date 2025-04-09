#!/bin/bash

# Параметры для бэкапа медиафайлов
MEDIA_CONTAINER="root-backend-1"
MEDIA_VOLUME_PATH="app/media/"
MEDIA_BACKUP_PATH="./media_backups"

LOG_DIR="./logs"
mkdir -p "$MEDIA_BACKUP_PATH" "$LOG_DIR"
LOG_FILE="$LOG_DIR/backup_media_$(date +'%Y-%m-%d_%H-%M').log"

echo "=== Создание бэкапа медиафайлов ===" | tee -a "$LOG_FILE"

docker run --rm --volumes-from "$MEDIA_CONTAINER" \
  -v "$(pwd)/$MEDIA_BACKUP_PATH:/backup" ubuntu \
  tar czvf "/backup/media_backup_$(TZ=Europe/Moscow date +%d-%m-%Y_%H-%M).tar.gz" "$MEDIA_VOLUME_PATH" 2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при создании бэкапа медиа" | tee -a "$LOG_FILE"
  exit 1
fi

# Удаление старых бэкапов
find "$MEDIA_BACKUP_PATH" -type f -name '*.tar.gz' -mtime +2 -exec rm {} \; 2>&1 | tee -a "$LOG_FILE"

echo "✅ Бэкап медиафайлов завершён." | tee -a "$LOG_FILE"
