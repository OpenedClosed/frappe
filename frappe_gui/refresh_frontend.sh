#!/usr/bin/env bash
set -euo pipefail

# ==== НАСТРОЙКИ ====
# Корневая папка bench'а (если скрипт лежит в корне frappe_gui — менять не нужно)
BENCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Версия Node для nvm (если не используешь nvm — просто игнорируется)
NODE_VERSION="v20.18.2"

# Сайт по умолчанию (если захочешь добавлять migrate)
DEFAULT_SITE="dantist.localhost"

# ==== ХЕЛПЕРЫ ====

log() {
  echo -e "\n\033[1;32m>>> $*\033[0m"
}

reinstall_node_modules() {
  local app_dir="$1"

  if [[ ! -d "$app_dir" ]]; then
    log "Пропускаю ${app_dir} — директории нет"
    return 0
  fi

  log "Переустанавливаю node_modules в ${app_dir}"
  pushd "$app_dir" >/dev/null

  rm -rf node_modules
  yarn install

  popd >/dev/null
}

# ==== ОСНОВНАЯ ЛОГИКА ====

cd "$BENCH_ROOT"
log "Рабочая директория: $BENCH_ROOT"

# 1. Git submodules (frappe, erpnext и прочие как сабмодули)
if command -v git >/dev/null 2>&1; then
  log "Обновляю git submodules"
  git submodule update --init --recursive
else
  log "git не найден, пропускаю обновление submodules"
fi

# 2. Python venv
if [[ -d "env" ]]; then
  log "Активирую Python venv (env)"
  # shellcheck disable=SC1091
  source env/bin/activate
else
  log "Виртуальное окружение env не найдено. Останов."
  exit 1
fi

# 3. Node через nvm (если установлен)
if command -v nvm >/dev/null 2>&1; then
  log "Переключаюсь на Node ${NODE_VERSION} через nvm"
  nvm use "${NODE_VERSION}" || log "Не удалось nvm use ${NODE_VERSION}, продолжаю с текущим node"
else
  log "nvm не найден, использую текущую версию node: $(node -v 2>/dev/null || echo 'node не установлен')"
fi

# 4. Логи (на будущее, чтобы не было ошибок про logs/worker.log и site logs)
log "Создаю общую папку logs и логи для сайтов"
mkdir -p logs

if [[ -d "sites" ]]; then
  for site_dir in sites/*; do
    if [[ -d "$site_dir" ]]; then
      mkdir -p "$site_dir/logs"
    fi
  done
fi

# 5. Переустановить node_modules в apps/frappe и apps/erpnext
reinstall_node_modules "apps/frappe"
reinstall_node_modules "apps/erpnext"

# 6. Сборка ассетов
log "Собираю ассеты (bench build)"
bench build

# 7. (ОПЦИОНАЛЬНО) миграция сайта — можешь раскомментировать, если хочешь запускать всегда
# log "Выполняю migrate для ${DEFAULT_SITE}"
# bench --site "${DEFAULT_SITE}" migrate

log "Готово. Можно запускать: bench start"