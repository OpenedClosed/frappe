#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
[ -f "$ENV_FILE" ] && export $(grep -v '^#' "$ENV_FILE" | xargs)

LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/cert_check_restart_$(date +'%Y-%m-%d_%H-%M').log"

DOMAIN="${HOST}"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
THRESHOLD_SEC="${THRESHOLD_SEC:-86400}"  # 1 день
LOCK_FILE="/var/lock/dentist_deploy.lock"
CONTAINER_NAME="${CONTAINER_NAME:-nginx}"
RESTART_MODE="${RESTART_MODE:-restart}"  # restart или full
COMPOSE_FILE="${COMPOSE_FILE:-$SCRIPT_DIR/../docker-compose.yml}"

log() {
  echo "$(date '+%F %T') $1" | tee -a "$LOG_FILE"
}

# ---------- Защита от деплоя ----------
if [ -e "$LOCK_FILE" ]; then
  log "🚧 Найден файл $LOCK_FILE — идёт деплой. Завершаю работу."
  exit 0
fi

# ---------- Блокировка от параллельного запуска ----------
exec 9>/var/lock/check_cert_restart.runlock
flock -n 9 || {
  log "⚠️  Скрипт уже запущен, выхожу."
  exit 0
}

# ---------- Получение даты окончания ----------
if [[ -n "$FAKE_END_DATE" ]]; then
  log "🧪 Используем фейковую дату окончания: $FAKE_END_DATE"
  END_DATE="$FAKE_END_DATE"
else
  if [ ! -f "$CERT_PATH" ]; then
    log "❌ Сертификат не найден: $CERT_PATH"
    exit 1
  fi
  END_DATE=$(openssl x509 -in "$CERT_PATH" -noout -enddate 2>/dev/null | cut -d= -f2)
  if [ -z "$END_DATE" ]; then
    log "❌ Не удалось прочитать дату окончания сертификата"
    exit 1
  fi
fi

END_TS=$(date -d "$END_DATE" +%s)
NOW_TS=$(date +%s)
LEFT_SEC=$(( END_TS - NOW_TS ))

# ---------- Проверка и возможный перезапуск ----------
if [ "$LEFT_SEC" -le "$THRESHOLD_SEC" ]; then
  log "⚠️  До окончания сертификата осталось $LEFT_SEC сек (≤ $THRESHOLD_SEC). Перезапускаю контейнер $CONTAINER_NAME через docker-compose ($RESTART_MODE)..."

  if [ "$RESTART_MODE" = "full" ]; then
    docker-compose -f "$COMPOSE_FILE" down >> "$LOG_FILE" 2>&1
    docker system prune -af >> "$LOG_FILE" 2>&1
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate "$CONTAINER_NAME" >> "$LOG_FILE" 2>&1
  else
    docker-compose -f "$COMPOSE_FILE" restart "$CONTAINER_NAME" >> "$LOG_FILE" 2>&1
  fi

  if [ $? -eq 0 ]; then
    log "✅ Контейнер $CONTAINER_NAME перезапущен через docker-compose."
  else
    log "❌ Ошибка при перезапуске контейнера $CONTAINER_NAME через docker-compose"
    exit 1
  fi
else
  DAYS_LEFT=$(( LEFT_SEC / 86400 ))
  log "✅ Сертификат ещё жив ~${DAYS_LEFT} дн. Перезапуск не требуется."
fi

# ---------- Очистка старых логов ----------
log "🧹 Удаляем логи старше 1 дня..."
find "$LOG_DIR" -type f -name "*.log" -mtime +1 -exec rm {} \; >> "$LOG_FILE" 2>&1

log "✅ Скрипт check_cert_and_renew завершён."
