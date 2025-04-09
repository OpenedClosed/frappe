#!/bin/bash

# Параметры MongoDB
MONGO_CONTAINER="root-mongo-1"
MONGO_DB_NAME="Nan"
BACKUP_PATH="./mongo_backups"

LOG_DIR="./logs"
mkdir -p "$BACKUP_PATH" "$LOG_DIR"
LOG_FILE="$LOG_DIR/backup_mongo_$(date +'%Y-%m-%d_%H-%M').log"

echo "=== Создание бэкапа MongoDB ===" | tee -a "$LOG_FILE"

docker exec "$MONGO_CONTAINER" mongodump --out /tmp/mongo_backup 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при mongodump" | tee -a "$LOG_FILE"
  exit 1
fi

docker cp "$MONGO_CONTAINER:/tmp/mongo_backup" "$BACKUP_PATH/mongo_backup_$(TZ=Europe/Moscow date +%d-%m-%Y_%H-%M)" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при копировании резервной копии MongoDB" | tee -a "$LOG_FILE"
  exit 1
fi

# Удаление старых бэкапов
find "$BACKUP_PATH" -type d -name 'mongo_backup_*' -mtime +14 -exec rm -rf {} \; 2>&1 | tee -a "$LOG_FILE"

echo "✅ Бэкап MongoDB завершён." | tee -a "$LOG_FILE"
