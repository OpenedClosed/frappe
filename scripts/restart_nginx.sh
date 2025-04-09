#!/bin/bash

LOG_DIR="./logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/restart_nginx_$(date +'%Y-%m-%d_%H-%M').log"

echo "=== Проверка Nginx ===" | tee -a "$LOG_FILE"

NGINX_SERVICE_NAME="nginx"

STOPPED_NGINX=$(docker ps -a \
  --filter "name=${NGINX_SERVICE_NAME}" \
  --filter "status=exited" \
  --filter "status=dead" \
  --filter "status=removing" \
  --filter "status=created" \
  --filter "status=restarting" \
  --format "{{.ID}} {{.Names}}")

if [ -n "$STOPPED_NGINX" ]; then
  echo "Nginx не запущен. Сохраняем логи..." | tee -a "$LOG_FILE"
  while read -r CONTAINER_ID CONTAINER_NAME; do
    echo "=== Logs: $CONTAINER_NAME ($CONTAINER_ID) ===" >> "$LOG_FILE"
    docker logs --tail 50 "$CONTAINER_ID" >> "$LOG_FILE" 2>&1
    echo -e "\n==============================\n" >> "$LOG_FILE"
  done <<< "$STOPPED_NGINX"

  echo "Перезапуск всех контейнеров..." | tee -a "$LOG_FILE"
  docker-compose down >> "$LOG_FILE" 2>&1
  docker system prune -af >> "$LOG_FILE" 2>&1
  docker-compose up -d --force-recreate >> "$LOG_FILE" 2>&1
  echo "Перезапуск завершён." | tee -a "$LOG_FILE"
else
  echo "Nginx работает нормально." | tee -a "$LOG_FILE"
fi

echo "Очистка логов старше 14 дней..." | tee -a "$LOG_FILE"
find "$LOG_DIR" -type f -name "*.log" -mtime +14 -exec rm {} \; >> "$LOG_FILE" 2>&1

echo "✅ Скрипт restart_nginx завершён." | tee -a "$LOG_FILE"
