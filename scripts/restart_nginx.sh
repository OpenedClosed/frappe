#!/bin/bash

# Папка для логов
LOG_DIR="./logs_nginx"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +'%Y-%m-%d_%H-%M-%S').log"

echo "Starting Nginx container monitoring..." | tee -a "$LOG_FILE"

# Имя сервиса Nginx в docker-compose
NGINX_SERVICE_NAME="nginx"

# Проверяем статус Nginx-контейнера
STOPPED_NGINX=$(docker ps -a \
  --filter "name=${NGINX_SERVICE_NAME}" \
  --filter "status=exited" \
  --filter "status=dead" \
  --filter "status=removing" \
  --filter "status=created" \
  --filter "status=restarting" \
  --format "{{.ID}} {{.Names}}")

if [ -n "$STOPPED_NGINX" ]; then
    echo "Nginx is not running. Saving logs..." | tee -a "$LOG_FILE"

    while read -r CONTAINER_ID CONTAINER_NAME; do
        echo "==== Logs for container: $CONTAINER_NAME ($CONTAINER_ID) ====" >> "$LOG_FILE"
        docker logs --tail 50 "$CONTAINER_ID" >> "$LOG_FILE" 2>&1
        echo -e "\n==============================\n" >> "$LOG_FILE"
    done <<< "$STOPPED_NGINX"

    echo "Restarting all containers..." | tee -a "$LOG_FILE"
    docker-compose down
    docker system prune -af
    docker-compose up -d --force-recreate

    echo "All containers restarted." | tee -a "$LOG_FILE"
else
    echo "Nginx container is running fine." | tee -a "$LOG_FILE"
fi

# Очистка логов старше 14 дней
echo "Cleaning up old logs..." | tee -a "$LOG_FILE"
find "$LOG_DIR" -type f -name "*.log" -mtime +14 -exec rm {} \;
echo "Old logs deleted." | tee -a "$LOG_FILE"
