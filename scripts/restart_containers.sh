#!/bin/bash

# Определяем путь для логов
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"  # Создаём папку, если её нет
LOG_FILE="$LOG_DIR/$(date +'%Y-%m-%d_%H-%M-%S').log"

echo "Starting monitoring..." | tee -a "$LOG_FILE"

# Находим упавшие контейнеры (exited, dead, removing, created, restarting)
STOPPED_CONTAINERS=$(docker ps -a --filter "status=exited" --filter "status=dead" --filter "status=removing" --filter "status=created" --filter "status=restarting" --format "{{.ID}} {{.Names}}")

if [ -n "$STOPPED_CONTAINERS" ]; then
    echo "Found stopped containers. Saving logs..." | tee -a "$LOG_FILE"

    # Записываем логи только упавших контейнеров (ID + Имя)
    while read -r CONTAINER_ID CONTAINER_NAME; do
        echo "==== Logs for container $CONTAINER_NAME ($CONTAINER_ID) ====" >> "$LOG_FILE"
        docker logs --tail 50 "$CONTAINER_ID" >> "$LOG_FILE" 2>&1
        echo -e "\n==============================\n" >> "$LOG_FILE"
    done <<< "$STOPPED_CONTAINERS"

    echo "Restarting failed containers..." | tee -a "$LOG_FILE"
    
    # Полный перезапуск
    docker-compose down
    docker system prune -af
    docker-compose up -d --force-recreate

    echo "Restart completed." | tee -a "$LOG_FILE"
else
    echo "All containers are running fine!" | tee -a "$LOG_FILE"
fi

# Проверяем, если вообще нет активных контейнеров, то поднимаем всё
RUNNING_CONTAINERS=$(docker ps --format "{{.ID}}")

if [ -z "$RUNNING_CONTAINERS" ]; then
    echo "No running containers found. Restarting docker-compose..." | tee -a "$LOG_FILE"
    docker-compose down
    docker system prune -af
    docker-compose up -d --force-recreate
fi

# Очистка логов старше 14 дней
echo "Cleaning up old logs..." | tee -a "$LOG_FILE"
find "$LOG_DIR" -type f -name "*.log" -mtime +14 -exec rm {} \;
echo "Old logs deleted." | tee -a "$LOG_FILE"
