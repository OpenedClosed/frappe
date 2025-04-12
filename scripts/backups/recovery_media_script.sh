#!/bin/bash

MEDIA_CONTAINER="root_backend_1"
MEDIA_VOLUME_PATH="/app/fastapi_web/media/"
MEDIA_BACKUP_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../media_backups"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/recovery_media_$(date +'%Y-%m-%d_%H-%M').log"

echo "=== Восстановление медиафайлов ===" | tee -a "$LOG_FILE"

# Получаем архив: вручную или самый свежий
if [ -n "$1" ]; then
  BACKUP_FILE="$MEDIA_BACKUP_PATH/media_backup_$1.tar.gz"
else
  BACKUP_FILE=$(ls -1 "$MEDIA_BACKUP_PATH"/media_backup_*.tar.gz 2>/dev/null | sort -V | tail -n 1)
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ Нет доступного медиа-бэкапа для восстановления: $BACKUP_FILE" | tee -a "$LOG_FILE"
  exit 1
fi

echo "Используем бэкап: $BACKUP_FILE" | tee -a "$LOG_FILE"

docker cp "$BACKUP_FILE" "$MEDIA_CONTAINER:/backup.tar.gz" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при копировании медиа-бэкапа в контейнер" | tee -a "$LOG_FILE"
  exit 1
fi

docker exec "$MEDIA_CONTAINER" tar xzvf /backup.tar.gz -C "$MEDIA_VOLUME_PATH" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при распаковке медиафайлов" | tee -a "$LOG_FILE"
  exit 1
fi

echo "✅ Восстановление медиафайлов завершено." | tee -a "$LOG_FILE"
