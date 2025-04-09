#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/restart_containers_$(date +'%Y-%m-%d_%H-%M').log"

echo "=== Проверка контейнеров ===" | tee -a "$LOG_FILE"

STOPPED_CONTAINERS=$(docker ps -a \
  --filter "status=exited" \
  --filter "status=dead" \
  --filter "status=removing" \
  --filter "status=created" \
  --filter "status=restarting" \
  --format "{{.ID}} {{.Names}}")

if [ -n "$STOPPED_CONTAINERS" ]; then
  echo "Найдены остановленные контейнеры. Сохраняем логи..." | tee -a "$LOG_FILE"
  while read -r CONTAINER_ID CONTAINER_NAME; do
    echo "=== Logs: $CONTAINER_NAME ($CONTAINER_ID) ===" >> "$LOG_FILE"
    docker logs --tail 50 "$CONTAINER_ID" >> "$LOG_FILE" 2>&1
    echo -e "\n==============================\n" >> "$LOG_FILE"
  done <<< "$STOPPED_CONTAINERS"

  echo "Перезапуск всех контейнеров..." | tee -a "$LOG_FILE"
  docker-compose down >> "$LOG_FILE" 2>&1
  docker system prune -af >> "$LOG_FILE" 2>&1
  docker-compose up -d --force-recreate >> "$LOG_FILE" 2>&1
  echo "Перезапуск завершён." | tee -a "$LOG_FILE"
else
  echo "Все контейнеры работают нормально." | tee -a "$LOG_FILE"
fi

# Проверка: если совсем нет запущенных контейнеров
if [ -z "$(docker ps -q)" ]; then
  echo "Нет запущенных контейнеров. Перезапускаем..." | tee -a "$LOG_FILE"
  docker-compose down >> "$LOG_FILE" 2>&1
  docker system prune -af >> "$LOG_FILE" 2>&1
  docker-compose up -d --force-recreate >> "$LOG_FILE" 2>&1
fi

# Удаление старых логов (каждый запуск)
echo "Очистка логов старше 14 дней..." | tee -a "$LOG_FILE"
find "$LOG_DIR" -type f -name "*.log" -mtime +14 -exec rm {} \; >> "$LOG_FILE" 2>&1

echo "✅ Скрипт restart_containers завершён." | tee -a "$LOG_FILE"
