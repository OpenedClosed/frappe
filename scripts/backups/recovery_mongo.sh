#!/bin/bash

MONGO_CONTAINER="root-mongo-1"
MONGO_DB_NAME="Nan"
BACKUP_PATH="./mongo_backups"

LOG_DIR="./logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/recovery_mongo_$(date +'%Y-%m-%d_%H-%M').log"

echo "=== Восстановление MongoDB ===" | tee -a "$LOG_FILE"

LATEST_MONGO_BACKUP=$(ls -Art "$BACKUP_PATH" | tail -n 1)
if [ -z "$LATEST_MONGO_BACKUP" ]; then
  echo "❌ Нет доступных Mongo-бэкапов для восстановления" | tee -a "$LOG_FILE"
  exit 1
fi

echo "Используем бэкап: $LATEST_MONGO_BACKUP" | tee -a "$LOG_FILE"

docker cp "$BACKUP_PATH/$LATEST_MONGO_BACKUP" "$MONGO_CONTAINER:/tmp/mongo_backup" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при копировании бэкапа в контейнер" | tee -a "$LOG_FILE"
  exit 1
fi

docker exec "$MONGO_CONTAINER" mongorestore --db "$MONGO_DB_NAME" "/tmp/mongo_backup/$MONGO_DB_NAME" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при восстановлении MongoDB" | tee -a "$LOG_FILE"
  exit 1
fi

echo "✅ Восстановление MongoDB завершено." | tee -a "$LOG_FILE"
