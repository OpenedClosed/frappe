#!/bin/bash

MEDIA_CONTAINER="root_backend_1"
MEDIA_VOLUME_PATH="/app/media/"
MEDIA_BACKUP_PATH="./media_backups"

LOG_DIR="./logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/recovery_media_$(date +'%Y-%m-%d_%H-%M').log"

echo "=== Восстановление медиафайлов ===" | tee -a "$LOG_FILE"

LATEST_MEDIA_BACKUP=$(ls -Art "$MEDIA_BACKUP_PATH"/*.tar.gz | tail -n 1)
if [ -z "$LATEST_MEDIA_BACKUP" ]; then
  echo "❌ Нет доступных tar.gz-файлов для восстановления" | tee -a "$LOG_FILE"
  exit 1
fi

echo "Используем бэкап: $LATEST_MEDIA_BACKUP" | tee -a "$LOG_FILE"

docker cp "$LATEST_MEDIA_BACKUP" "$MEDIA_CONTAINER:/backup.tar.gz" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при копировании медиа-бэкапа в контейнер" | tee -a "$LOG_FILE"
  exit 1
fi

docker exec "$MEDIA_CONTAINER" tar xzvf /backup.tar.gz -C "$MEDIA_VOLUME_PATH" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при восстановлении медиафайлов" | tee -a "$LOG_FILE"
  exit 1
fi

echo "✅ Восстановление медиафайлов завершено." | tee -a "$LOG_FILE"
