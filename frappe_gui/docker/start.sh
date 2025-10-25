#!/usr/bin/env bash
# Lean bootstrap for Frappe in Docker (prod-first)

set -Eeuo pipefail

# ===== pretty logs =====
ts() { date +'%F %T'; }
say()   { echo -e "[$(ts)] $*"; }
ok()    { say "✅ $*"; }
warn()  { say "⚠️  $*" >&2; }
err()   { say "❌ $*" >&2; }
step()  { echo -e "\n[$(ts)] ── $*"; }
fatal() { err "$*"; exit 1; }
mask() { local s="${1:-}"; local n=${#s}; if ((n==0)); then echo ""; elif ((n<=6)); then echo "***"; else echo "${s:0:2}***${s: -2}"; fi; }

# ===== env & paths =====
export PATH="/opt/bench-env/bin:/usr/bin:/usr/local/bin:$PATH"
export BENCH_DIR="/workspace"
cd "$BENCH_DIR"

mkdir -p "$BENCH_DIR/apps" "$BENCH_DIR/sites" "$BENCH_DIR/logs"

SITE="${SITE_NAME:-dantist.localhost}"
SITE_DIR="$BENCH_DIR/sites/${SITE}"
SITE_CFG="${SITE_DIR}/site_config.json"
COMMON_CFG="$BENCH_DIR/sites/common_site_config.json"
APPS_TXT="$BENCH_DIR/sites/apps.txt"

DB_HOST="${DB_HOST:-mariadb}"
DB_PORT="${DB_PORT:-3306}"
DB_WAIT="${DB_WAIT_SECONDS:-90}"

HOST="${HOST:-localhost}"
PROTO=$([[ "$HOST" == "localhost" || "$HOST" == "127.0.0.1" ]] && echo http || echo https)

FRAPPE_DB_ROOT_PASSWORD="${FRAPPE_DB_ROOT_PASSWORD:-${DB_ROOT_PASSWORD:-}}"
FRAPPE_ADMIN_PASSWORD="${FRAPPE_ADMIN_PASSWORD:-${ADMIN_PASSWORD:-}}"

APP_LIST="${FRAPPE_INSTALL_APPS:-dantist_app}"     # через пробел
APP_ENV="${APP_ENV:-prod}"                          # prod|dev
PROCFILE_MODE="${PROCFILE_MODE:-container}"         # container|local
WEB_PORT="${WEB_PORT:-8001}"
SOCKETIO_NODE_BIN="${SOCKETIO_NODE_BIN:-/usr/bin/node}"
BENCH_BIN="${BENCH_BIN:-bench}"

# mysql client без SSL (устраняет sporadic HY000/2026)
printf "[client]\nssl=0\nprotocol=tcp\n" > /root/.my.cnf

bench()    { (cd "$BENCH_DIR" && command bench "$@"); }
site_cmd() { (cd "$BENCH_DIR" && command bench --site "$SITE" "$@"); }

# ------ helpers ------
read_db_creds() {
  python3 - "$SITE_CFG" <<'PY'
import json,sys
p = sys.argv[1]
try:
    with open(p,'r') as f:
        d = json.load(f) or {}
except Exception:
    d = {}
print(d.get("db_name",""))
print(d.get("db_password",""))
print(d.get("db_host",""))
print(d.get("dantist_env",""))
PY
}

core_tables_ok() {
  [[ -f "$SITE_CFG" ]] || return 1
  local DB_NAME
  DB_NAME="$(python3 - "$SITE_CFG" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1])) or {}
except: d={}
print(d.get("db_name",""))
PY
)"
  [[ -z "$DB_NAME" ]] && return 1
  mysql -h "$DB_HOST" -P "$DB_PORT" -uroot -p"$FRAPPE_DB_ROOT_PASSWORD" \
    -Nse "SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='${DB_NAME}' AND TABLE_NAME='tabDefaultValue' LIMIT 1;" 2>/dev/null | grep -q 1
}

quick_diag() {
  step "🧪 Диагностика"
  if [[ -f "$SITE_CFG" ]]; then
    read -r DB_NAME DB_PASS DBH DENV < <(read_db_creds || echo "    ")
    say "• site: $SITE"
    say "• dantist_env: ${DENV:-<none>}"
    say "• db_name: ${DB_NAME:-<none>}  db_pass: $(mask "${DB_PASS:-}")  db_host: ${DBH:-<unset>}"
    say "• MariaDB ping (${DB_HOST}:${DB_PORT})…"
    (echo > /dev/tcp/${DB_HOST}/${DB_PORT}) >/dev/null 2>&1 && ok "ping ok" || warn "нет TCP-подключения"
    if [[ -n "${DB_NAME:-}" ]]; then
      core_tables_ok && ok "таблицы ядра на месте (tabDefaultValue)" || warn "таблицы ядра не найдены root-проверкой"
    fi
  else
    warn "site_config.json отсутствует"
  fi
}

ensure_apps_txt_has() {
  local app="$1"
  touch "$APPS_TXT"
  grep -Fqx "$app" "$APPS_TXT" || { echo "$app" >> "$APPS_TXT"; ok "добавил '$app' в sites/apps.txt"; }
}

ensure_app_present_and_registered() {
  local app="$1"
  if [[ ! -d "$BENCH_DIR/apps/$app" ]]; then
    warn "Приложение $app не найдено в /workspace/apps/$app — пропускаю установку (проверь образ)."
  else
    ensure_apps_txt_has "$app"
  fi
}

# ===== 0) ждём MariaDB =====
step "⏳ Ожидание MariaDB ${DB_HOST}:${DB_PORT} (до ${DB_WAIT}s)"
for i in $(seq 1 "$DB_WAIT"); do
  (echo > /dev/tcp/${DB_HOST}/${DB_PORT}) >/dev/null 2>&1 && { ok "MariaDB reachable"; break; }
  sleep 1
  [[ "$i" == "$DB_WAIT" ]] && fatal "MariaDB не доступна за ${DB_WAIT}s"
done
mysql -h "$DB_HOST" -P "$DB_PORT" -uroot -p"$FRAPPE_DB_ROOT_PASSWORD" -e "SELECT VERSION();" >/dev/null 2>&1 \
  && ok "root-доступ к MariaDB подтверждён" \
  || warn "root-доступ не проверился (new-site потребует root пароль в ENV)"

# ===== 1) common_site_config.json (+ правильный путь к node) =====
step "🛠️  Общий конфиг: $COMMON_CFG"
python3 - <<'PY'
import os, json, pathlib
p = pathlib.Path("/workspace/sites/common_site_config.json")
p.parent.mkdir(parents=True, exist_ok=True)
cfg = {}
if p.exists():
    try: cfg = json.loads(p.read_text() or "{}")
    except Exception: cfg = {}
redis = os.getenv("REDIS_URL","redis://redis:6379")
redis_base = f"{redis.split('/',3)[0]}//{redis.split('/',3)[2]}"
cfg.update({
    "default_site": os.getenv("SITE_NAME","dantist.localhost"),
    "webserver_port": 8001,
    "socketio_port": 9000,
    "redis_cache":    f"{redis_base}/0",
    "redis_queue":    f"{redis_base}/1",
    "redis_socketio": f"{redis_base}/2",
    "serve_default_site": True,
    "use_redis_auth": False,
    "live_reload": os.getenv("APP_ENV","dev")=="dev",
    "frappe_user": "root",
    "node": "/usr/bin/node",
})
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print(f"OK {p}")
PY
ok "common_site_config.json записан"

mkdir -p "$SITE_DIR" || true

# ===== 2) существующий сайт (без разрушений) / создание если нет =====
if [[ ! -f "$SITE_CFG" ]]; then
  step "🏗️  Создание сайта: ${SITE}"
  [[ -n "${FRAPPE_DB_ROOT_PASSWORD:-}" ]] || fatal "Нужен FRAPPE_DB_ROOT_PASSWORD/DB_ROOT_PASSWORD"
  [[ -n "${FRAPPE_ADMIN_PASSWORD:-}"   ]] || fatal "Нужен FRAPPE_ADMIN_PASSWORD/ADMIN_PASSWORD"
  bench new-site "${SITE}" \
    --mariadb-root-username root \
    --mariadb-root-password "${FRAPPE_DB_ROOT_PASSWORD}" \
    --admin-password "${FRAPPE_ADMIN_PASSWORD}" \
    --db-host "${DB_HOST}" \
    --db-port "${DB_PORT}" \
    --mariadb-user-host-login-scope='%' \
    --install-app frappe \
    --force
  ok "Сайт создан"
else
  step "♻️  Сайт уже существует — пропускаю создание"
fi

# ===== 3) патчим site_config из ENV (каждый старт) + фиксим origin =====
step "🧩 Актуализация site_config.json из ENV"
python3 - <<PY
import os, json, pathlib
from urllib.parse import urlparse

def good_origin(v: str) -> bool:
    try:
        u = urlparse(v or "")
        return bool(u.scheme and u.netloc)
    except Exception:
        return False

site = os.getenv("SITE_NAME","dantist.localhost")
host = os.getenv("HOST","localhost")
proto = "http" if host in {"localhost","127.0.0.1"} else "https"
p = pathlib.Path(f"/workspace/sites/{site}/site_config.json")
cfg = json.loads(p.read_text() or "{}") if p.exists() else {}

cfg["db_host"] = os.getenv("DB_HOST","mariadb")
cfg["host_name"] = os.getenv("HOST_NAME", f"{proto}://{host}")
cfg["dantist_base_url"] = os.getenv("DANTIST_BASE_URL_INTERNAL", "http://backend:8000/api")

cur = cfg.get("dantist_iframe_origin")
desired = os.getenv("FRONTEND_PUBLIC_ORIGIN")
default = f"{proto}://{host}"
cfg["dantist_iframe_origin"] = (desired if good_origin(desired or "") else (cur if good_origin(cur or "") else default))

cfg["server_script_enabled"] = True
cfg["dantist_env"] = os.getenv("APP_ENV","prod")

devmode = os.getenv("DEVELOPER_MODE")
if devmode is not None:
    cfg["developer_mode"] = 1 if str(devmode).strip().lower() in {"1","true","yes","on"} else 0

log_level = os.getenv("LOG_LEVEL")
if log_level: cfg["log_level"] = log_level

enc = os.getenv("ENCRYPTION_KEY")
if enc: cfg["encryption_key"] = enc

p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print(f"OK {p}")
PY
ok "site_config.json обновлён"

quick_diag
core_tables_ok || fatal "База сайта неконсистентна (нет tabDefaultValue)"

# ===== 4) регистрация приложений (без лишних install) =====
step "🗂️ Регистрация приложений в sites/apps.txt"
ensure_apps_txt_has frappe
for app in ${APP_LIST}; do ensure_app_present_and_registered "$app"; done

# Установка только если реально не установлено
for app in ${APP_LIST}; do
  if ! site_cmd list-apps 2>/dev/null | grep -Fqx "$app"; then
    say "• install-app $app"
    site_cmd install-app "$app" && ok "установлен $app" || warn "install-app $app не прошёл (см. стек выше)"
  else
    say "• $app уже установлен — пропускаю install-app"
  fi
done

# ===== 5) миграция (один раз) =====
step "🔁 Финальная migrate"
site_cmd migrate || warn "migrate завершилась с предупреждением"

# ===== 6) фикстуры =====
step "📥 Синхронизация фикстур"
site_cmd execute "frappe.utils.fixtures.sync_fixtures" \
  && ok "фикстуры синхронизированы" \
  || warn "sync_fixtures вернул ненулевой код"

# ===== 7) build ассетов (один общий) =====
step "🧱 Сборка ассетов"
if ! bench build; then
  warn "bench build вернул ошибку — пробую форсированный rebuild"
  bench build --force || warn "bench build с предупреждением"
fi
chmod -R a+rX /workspace/sites/assets || true

# ===== 8) Administrator — проставить пароль, если задан в ENV =====
step "🔐 Проверка/установка пароля Administrator"
if [[ -n "${FRAPPE_ADMIN_PASSWORD:-}" ]]; then
  # Если пользователя нет — bench всё равно проставит пароль, но сначала проверим наличия БД-кредов
  read -r DB_NAME DB_PASS DBH _ < <(read_db_creds || echo "    ")
  if [[ -n "${DB_NAME:-}" && -n "${DB_PASS:-}" ]]; then
    if ! mysql -h "$DB_HOST" -P "$DB_PORT" -u"$DB_NAME" -p"$DB_PASS" "$DB_NAME" -Nse "SELECT 1 FROM tabUser WHERE name='Administrator' LIMIT 1;" 2>/dev/null | grep -q 1; then
      warn "Administrator не найден — попытаюсь создать/починить через bench"
    fi
  else
    warn "Не удалось прочитать db_name/db_password — всё равно проставлю пароль через bench"
  fi
  if site_cmd set-admin-password "$FRAPPE_ADMIN_PASSWORD"; then
    ok "Пароль Administrator установлен"
  else
    warn "Не удалось установить пароль Administrator (см. лог bench)"
  fi
else
  say "FRAPPE_ADMIN_PASSWORD не задан — пропускаю установку пароля Administrator"
fi

# ===== 9) Procfile =====
step "🗂️  Procfile генерация"
PROCFILE_PATH="/workspace/Procfile"
if [[ "${PROCFILE_MODE}" == "local" ]]; then
  cat > "$PROCFILE_PATH" <<PROC
web: $BENCH_BIN serve --port $WEB_PORT
socketio: $SOCKETIO_NODE_BIN apps/frappe/socketio.js
watch: $BENCH_BIN watch
schedule: $BENCH_BIN schedule
worker: OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES NO_PROXY=* $BENCH_BIN worker 1>> logs/worker.log 2>> logs/worker.error.log
PROC
else
  cat > "$PROCFILE_PATH" <<PROC
web: cd /workspace && $BENCH_BIN serve --port $WEB_PORT
socketio: cd /workspace && $SOCKETIO_NODE_BIN apps/frappe/socketio.js
schedule: cd /workspace && $BENCH_BIN schedule
worker: cd /workspace && $BENCH_BIN worker
PROC
fi
ok "Procfile готов ($PROCFILE_MODE)"

# ===== 10) сводка и старт =====
step "📋 Финальная сводка"
(site_cmd list-apps || true) | sed 's/^/• /'
say "assets: $(du -sh /workspace/sites/assets 2>/dev/null | awk '{print $1}')"
ok "Bootstrap завершён. Запускаю процессы…"

exec bench start