#!/bin/bash

# Параметры
MEDIA_CONTAINER="root_backend_1"
MEDIA_VOLUME_PATH="app/media/"
MEDIA_BACKUP_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../media_backups"

# Логи
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$MEDIA_BACKUP_PATH" "$LOG_DIR"

LOG_FILE="$LOG_DIR/backup_media_$(date +'%Y-%m-%d_%H-%M').log"
echo "=== Создание бэкапа медиафайлов ===" | tee -a "$LOG_FILE"

# Запуск бэкапа
docker run --rm --volumes-from "$MEDIA_CONTAINER" \
  -v "$MEDIA_BACKUP_PATH:/backup" ubuntu \
  tar czvf "/backup/media_backup_$(TZ=Europe/Moscow date +%d-%m-%Y_%H-%M).tar.gz" "$MEDIA_VOLUME_PATH" 2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при создании бэкапа медиа" | tee -a "$LOG_FILE"
  exit 1
fi

# Удаление старых архивов
find "$MEDIA_BACKUP_PATH" -type f -name '*.tar.gz' -mtime +2 -exec rm {} \; 2>&1 | tee -a "$LOG_FILE"

echo "✅ Бэкап медиафайлов завершён." | tee -a "$LOG_FILE"
