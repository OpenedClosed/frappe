#!/bin/bash

POSTGRES_CONTAINER="root_db_1"
DB_NAME="NaN"
DB_USER="NaN"
DB_PASSWORD="NaN"
BACKUP_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../backups"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/recovery_postgres_$(date +'%Y-%m-%d_%H-%M').log"
echo "=== Восстановление PostgreSQL ===" | tee -a "$LOG_FILE"

LATEST_DB_BACKUP=$(ls -Art "$BACKUP_PATH"/*.sql 2>/dev/null | tail -n 1)
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
