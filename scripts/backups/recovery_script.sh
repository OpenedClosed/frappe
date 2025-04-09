#!/bin/bash

# Параметры PostgreSQL
POSTGRES_CONTAINER="root-db-1"
DB_NAME="Nan"
DB_USER="Nan"
DB_PASSWORD="Nan"
BACKUP_PATH="./backups"

LOG_DIR="./logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/recovery_postgres_$(date +'%Y-%m-%d_%H-%M').log"

echo "=== Восстановление PostgreSQL ===" | tee -a "$LOG_FILE"

LATEST_DB_BACKUP=$(ls -Art "$BACKUP_PATH"/*.sql | tail -n 1)
if [ -z "$LATEST_DB_BACKUP" ]; then
  echo "❌ Нет доступных .sql-файлов для восстановления" | tee -a "$LOG_FILE"
  exit 1
fi

echo "Используем бэкап: $LATEST_DB_BACKUP" | tee -a "$LOG_FILE"

docker cp "$LATEST_DB_BACKUP" "$POSTGRES_CONTAINER:/tmp/backup.sql" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при копировании бэкапа в контейнер" | tee -a "$LOG_FILE"
  exit 1
fi

docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f /tmp/backup.sql 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при восстановлении PostgreSQL" | tee -a "$LOG_FILE"
  exit 1
fi

echo "✅ Восстановление PostgreSQL завершено." | tee -a "$LOG_FILE"
