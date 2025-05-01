#!/bin/bash
# restart_containers.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/restart_containers_$(date +'%Y-%m-%d_%H-%M').log"

## ----------  НОВОЕ: глобальный замок деплоя  ----------
LOCK_FILE="/var/lock/dentist_deploy.lock"
if [ -e "$LOCK_FILE" ]; then
  echo "🚧 Найден файл $LOCK_FILE — идёт деплой. Завершаю работу." | tee -a "$LOG_FILE"
  exit 0
fi

## ----------  НОВОЕ: защита от повторного запуска самого скрипта  ----------
exec 9>/var/lock/restart_containers.runlock
flock -n 9 || {
  echo "⚠️  Скрипт уже запущен, выхожу." | tee -a "$LOG_FILE"
  exit 0
}

# ======= старая логика без изменений =======
IGNORED_CONTAINERS=("root_bot_1")

echo "=== Проверка контейнеров ===" | tee -a "$LOG_FILE"

STOPPED_CONTAINERS=$(docker ps -a \
  --filter "status=exited" \
  --filter "status=dead" \
  --filter "status=removing" \
  --filter "status=created" \
  --filter "status=restarting" \
  --format "{{.ID}} {{.Names}}")

AFFECTING_CONTAINERS=()

if [ -n "$STOPPED_CONTAINERS" ]; then
  echo "🔍 Найдены остановленные контейнеры:" | tee -a "$LOG_FILE"
  while read -r CONTAINER_ID CONTAINER_NAME; do
    echo " - $CONTAINER_NAME ($CONTAINER_ID)" | tee -a "$LOG_FILE"

    if [[ " ${IGNORED_CONTAINERS[*]} " =~ " ${CONTAINER_NAME} " ]]; then
      echo "   ⏭️  Контейнер $CONTAINER_NAME входит в список игнорируемых. Пропускаем." | tee -a "$LOG_FILE"
      continue
    fi

    AFFECTING_CONTAINERS+=("$CONTAINER_ID $CONTAINER_NAME")

    echo "=== Logs: $CONTAINER_NAME ($CONTAINER_ID) ===" >> "$LOG_FILE"
    docker logs --tail 50 "$CONTAINER_ID" >> "$LOG_FILE" 2>&1
    echo -e "\n==============================\n" >> "$LOG_FILE"
  done <<< "$STOPPED_CONTAINERS"
fi

if [ ${#AFFECTING_CONTAINERS[@]} -gt 0 ]; then
  echo "🔁 Перезапуск всех контейнеров..." | tee -a "$LOG_FILE"
  docker-compose down >> "$LOG_FILE" 2>&1
  docker system prune -af >> "$LOG_FILE" 2>&1
  docker-compose up -d --force-recreate >> "$LOG_FILE" 2>&1
  echo "✅ Перезапуск завершён." | tee -a "$LOG_FILE"
else
  RUNNING_CONTAINERS=$(docker ps -q)
  if [ -z "$RUNNING_CONTAINERS" ]; then
    echo "⚠️  Нет запущенных контейнеров. Перезапускаем..." | tee -a "$LOG_FILE"
    docker-compose down >> "$LOG_FILE" 2>&1
    docker system prune -af >> "$LOG_FILE" 2>&1
    docker-compose up -d --force-recreate >> "$LOG_FILE" 2>&1
    echo "✅ Перезапуск завершён." | tee -a "$LOG_FILE"
  else
    echo "✅ Все контейнеры работают нормально (или упали только игнорируемые)." | tee -a "$LOG_FILE"
  fi
fi

echo "🧹 Очистка логов старше 14 дней..." | tee -a "$LOG_FILE"
find "$LOG_DIR" -type f -name "*.log" -mtime +14 -exec rm {} \; >> "$LOG_FILE" 2>&1

echo "🏁 Скрипт restart_containers завершён." | tee -a "$LOG_FILE"
