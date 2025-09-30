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

# Получаем путь к нужному файлу: вручную или последний
if [ -n "$1" ]; then
  BACKUP_FILE="$BACKUP_PATH/backup_$1.sql"
else
  BACKUP_FILE=$(ls -1 "$BACKUP_PATH"/backup_*.sql 2>/dev/null | sort -V | tail -n 1)
fi

# Проверка
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ Нет доступного .sql-файла для восстановления: $BACKUP_FILE" | tee -a "$LOG_FILE"
  exit 1
fi

echo "Используем бэкап: $BACKUP_FILE" | tee -a "$LOG_FILE"

docker cp "$BACKUP_FILE" "$POSTGRES_CONTAINER:/tmp/backup.sql" 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при копировании в контейнер" | tee -a "$LOG_FILE"
  exit 1
fi

docker exec "$POSTGRES_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f /tmp/backup.sql 2>&1 | tee -a "$LOG_FILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
  echo "❌ Ошибка при восстановлении PostgreSQL" | tee -a "$LOG_FILE"
  exit 1
fi

echo "✅ Восстановление PostgreSQL завершено." | tee -a "$LOG_FILE"
