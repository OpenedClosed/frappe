#!/bin/bash

MONGO_CONTAINER="root_mongo_1"
MONGO_DB_NAME="dentist_db"
BACKUP_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../mongo_backups"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/recovery_mongo_$(date +'%Y-%m-%d_%H-%M').log"

echo "=== Восстановление MongoDB ===" | tee -a "$LOG_FILE"

# Если аргумент передан — используем его
if [ -n "$1" ]; then
  BACKUP_FOLDER="mongo_backup_$1"
else
  BACKUP_FOLDER=$(ls -1 "$BACKUP_PATH" | grep '^mongo_backup_' | sort -V | tail -n 1)
fi

# Проверка
if [ -z "$BACKUP_FOLDER" ] || [ ! -d "$BACKUP_PATH/$BACKUP_FOLDER" ]; then
  echo "❌ Нет доступного бэкапа: $BACKUP_FOLDER" | tee -a "$LOG_FILE"
  exit 1
fi

echo "Используем бэкап: $BACKUP_FOLDER" | tee -a "$LOG_FILE"

docker cp "$BACKUP_PATH/$BACKUP_FOLDER" "$MONGO_CONTAINER:/tmp/mongo_backup" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при копировании" | tee -a "$LOG_FILE"
  exit 1
fi

docker exec "$MONGO_CONTAINER" mongorestore --drop --db "$MONGO_DB_NAME" "/tmp/mongo_backup/$MONGO_DB_NAME" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при восстановлении" | tee -a "$LOG_FILE"
  exit 1
fi

echo "✅ Восстановление MongoDB завершено." | tee -a "$LOG_FILE"
