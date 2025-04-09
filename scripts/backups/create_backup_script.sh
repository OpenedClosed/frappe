#!/bin/bash

POSTGRES_CONTAINER="root-db-1"
DB_NAME="NaN"
DB_USER="NaN"
DB_PASSWORD="NaN"
BACKUP_PATH="./backups"

# Папка и файл логов
LOG_DIR="./logs"
mkdir -p "$BACKUP_PATH" "$LOG_DIR"
LOG_FILE="$LOG_DIR/backup_postgres_$(date +'%Y-%m-%d_%H-%M').log"

echo "=== Создание бэкапа PostgreSQL ===" | tee -a "$LOG_FILE"

# Выполняем pg_dump
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" -f /tmp/backup.sql 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при pg_dump" | tee -a "$LOG_FILE"
  exit 1
fi

# Копируем бэкап из контейнера
docker cp "$POSTGRES_CONTAINER:/tmp/backup.sql" "$BACKUP_PATH/backup_$(TZ=Europe/Moscow date +%d-%m-%Y_%H-%M).sql" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при копировании backup.sql" | tee -a "$LOG_FILE"
  exit 1
fi

# Удаление старых бэкапов
find "$BACKUP_PATH" -type f -name '*.sql' -mtime +14 -exec rm {} \; 2>&1 | tee -a "$LOG_FILE"