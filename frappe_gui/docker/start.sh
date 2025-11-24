#!/usr/bin/env bash
# Lean bootstrap for Frappe 15 + ERPNext + dantist_app в Docker
# Продовый сценарий, с авто-созданием/пересозданием сайта при проблемах с БД

set -Eeuo pipefail

# ===== pretty logs =====
ts() { date +'%F %T'; }
say(){ echo -e "[$(ts)] $*"; }
ok(){  say "✅ $*"; }
warn(){ say "⚠️  $*" >&2; }
err(){  say "❌ $*" >&2; }
step(){ echo -e "\n[$(ts)] ── $*"; }
fatal(){ err "$*"; exit 1; }
mask(){
  local s="${1:-}"; local n=${#s}
  if ((n==0)); then echo ""
  elif ((n<=6)); then echo "***"
  else echo "${s:0:2}***${s: -2}"
  fi
}

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

# Явное имя/пароль БД сайта (опционально, bench сам может придумать)
SITE_DB_NAME="${SITE_DB_NAME:-}"
SITE_DB_PASSWORD="${SITE_DB_PASSWORD:-}"

# По умолчанию ставим ERPNext и твой dantist_app
APP_LIST="${FRAPPE_INSTALL_APPS:-"erpnext dantist_app"}"
APP_ENV="${APP_ENV:-prod}"
PROCFILE_MODE="${PROCFILE_MODE:-container}"
WEB_PORT="${WEB_PORT:-8001}"
SOCKETIO_NODE_BIN="${SOCKETIO_NODE_BIN:-/usr/bin/node}"
BENCH_BIN="${BENCH_BIN:-bench}"

# ===== тумблер тяжёлых шагов =====
# HEAVY=1 (по умолчанию) — migrate + install-app + full bench build
# HEAVY=0 — только конфиги + fixtures + умная сборка ассетов при необходимости
HEAVY="${HEAVY:-1}"

# mysql client без SSL (устраняет HY000/2026)
printf "[client]\nssl=0\nprotocol=tcp\n" > /root/.my.cnf

bench(){ (cd "$BENCH_DIR" && command bench "$@"); }

ensure_site_logs(){
  mkdir -p "$SITE_DIR/logs" || true
  touch "$SITE_DIR/logs/frappe.log" "$SITE_DIR/logs/database.log" || true
}

site_cmd(){
  ensure_site_logs
  (cd "$BENCH_DIR" && command bench --site "$SITE" "$@")
}

# ===== helpers =====
has_app(){ [[ -d "$BENCH_DIR/apps/$1" ]]; }

read_db_creds(){
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

core_tables_ok(){
  [[ -f "$SITE_CFG" ]] || return 0
  local DB_NAME
  DB_NAME="$(python3 - "$SITE_CFG" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1])) or {}
except Exception: d={}
print(d.get("db_name",""))
PY
)"
  [[ -z "$DB_NAME" ]] && return 0
  mysql -h "$DB_HOST" -P "$DB_PORT" -uroot -p"$FRAPPE_DB_ROOT_PASSWORD" \
    -Nse "SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='${DB_NAME}' AND TABLE_NAME='tabDefaultValue' LIMIT 1;" 2>/dev/null | grep -q 1
}

db_tables_count(){
  [[ -f "$SITE_CFG" ]] || { echo 0; return 0; }
  local DB_NAME
  DB_NAME="$(python3 - "$SITE_CFG" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1])) or {}
except Exception: d={}
print(d.get("db_name",""))
PY
)"
  [[ -z "$DB_NAME" ]] && { echo 0; return 0; }
  local cnt
  cnt="$(mysql -h "$DB_HOST" -P "$DB_PORT" -uroot -p"$FRAPPE_DB_ROOT_PASSWORD" \
           -Nse "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='${DB_NAME}';" 2>/dev/null || echo 0)"
  echo "${cnt:-0}"
}

dump_config_masked(){
  local P="$1"
  if [[ ! -f "$P" ]]; then
    warn "конфиг ${P} отсутствует"
    return 0
  fi
  python3 - "$P" <<'PY'
import json,sys
P=sys.argv[1]
S=json.loads(open(P).read() or "{}")
MASK_KEYS={"db_password","encryption_key","admin_password","smtp_server_password","password","token","secret"}
def m(v):
    if not isinstance(v,str): return v
    if len(v)<=6: return "***"
    return v[:2]+"***"+v[-2:]
def walk(d):
    if isinstance(d,dict):
        return {k:(m(v) if k in MASK_KEYS else walk(v)) for k,v in d.items()}
    if isinstance(d,list):
        return [walk(x) for x in d]
    return d
print(json.dumps(walk(S), ensure_ascii=False, indent=2))
PY
}

quick_diag(){
  step "🧪 Диагностика"
  say "• SITE=${SITE}  HOST=${HOST}  PROTO=${PROTO}  APP_ENV=${APP_ENV}  HEAVY=${HEAVY}"
  say "• MariaDB ping (${DB_HOST}:${DB_PORT})…"
  (echo > /dev/tcp/${DB_HOST}/${DB_PORT}) >/dev/null 2>&1 && ok "ping ok" || warn "нет TCP-подключения"
  if [[ -f "$SITE_CFG" ]]; then
    read -r DB_NAME DB_PASS DBH DENV < <(read_db_creds || echo "    ")
    say "• db_name: ${DB_NAME:-<none>}  db_pass: $(mask "${DB_PASS:-}")  db_host: ${DBH:-<unset>}  dantist_env: ${DENV:-<none>}"
    if core_tables_ok; then
      ok "таблицы ядра на месте (tabDefaultValue)"
    else
      warn "таблицы ядра не найдены root-проверкой"
    fi
  else
    warn "site_config.json отсутствует"
  fi
}

ensure_apps_txt_has(){
  local app="$1"
  touch "$APPS_TXT"
  if ! grep -Fqx "$app" "$APPS_TXT"; then
    echo "$app" >> "$APPS_TXT"
    ok "добавил '$app' в sites/apps.txt"
  fi
}

ensure_app_present_and_registered(){
  local app="$1"
  if has_app "$app"; then
    ensure_apps_txt_has "$app"
  else
    warn "Приложение $app не найдено в /workspace/apps/$app — пропускаю регистрацию."
  fi
}

need_assets_rebuild(){
  ls /workspace/sites/assets/frappe/dist/js/desk.bundle.*.js  >/dev/null 2>&1 || return 0
  ls /workspace/sites/assets/frappe/dist/css/desk.bundle.*.css >/dev/null 2>&1 || return 0
  if [[ -d /workspace/sites/assets/dantist_app/dist/css ]]; then
    ls /workspace/sites/assets/dantist_app/dist/css/*.css >/dev/null 2>&1 || return 0
  fi
  return 1
}

# ==== Socket.IO в site_config.json ====
ensure_socketio_settings(){
  step "🧷 Socket.IO настройки в site_config.json"
  python3 - <<'PY'
import os,json,pathlib
site=os.getenv("SITE_NAME","dantist.localhost")
host=os.getenv("HOST","localhost")
proto="http" if host in {"localhost","127.0.0.1"} else "https"
p=pathlib.Path(f"/workspace/sites/{site}/site_config.json")
cfg=json.loads(p.read_text() or "{}") if p.exists() else {}
cfg["host_name"]=cfg.get("host_name") or f"{proto}://{host}"
cfg["socketio_protocol"]="https" if proto=="https" else "http"
cfg["socketio_port"]=443 if proto=="https" else 80
cfg["socketio_path"]="/socket.io"
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print(f"OK {p}")
PY
}

do_install_apps(){
  if [[ "$HEAVY" != "1" ]]; then
    warn "HEAVY=0 → пропускаю install-app"
    return 0
  fi
  step "🧩 Установка приложений (HEAVY=1)"
  for app in ${APP_LIST}; do
    if ! has_app "$app"; then
      warn "• $app отсутствует в /workspace/apps — пропуск install-app"
      continue
    fi
    if site_cmd list-apps 2>/dev/null | grep -Fqx "$app"; then
      say "• $app уже установлен"
    else
      say "• install-app $app"
      if site_cmd install-app "$app"; then
        ok "установлен $app"
      else
        warn "install-app $app не прошёл"
      fi
    fi
  done
}

do_migrate(){
  if [[ "$HEAVY" != "1" ]]; then
    warn "HEAVY=0 → пропускаю migrate"
    return 0
  fi
  step "🔁 Migrate (HEAVY=1)"
  if site_cmd migrate; then
    ok "migrate завершился успешно"
  else
    warn "migrate завершился с предупреждением (см. лог bench)"
  fi
}

do_assets(){
  if [[ "$HEAVY" == "1" ]]; then
    step "🧱 Сборка ассетов (HEAVY=1)"
    if bench build; then
      ok "bench build завершился успешно"
    else
      warn "bench build завершился с ошибкой"
    fi
  else
    step "🧱 Сборка ассетов (умная проверка, HEAVY=0)"
    if need_assets_rebuild; then
      say "• ключевых бандлов нет → bench build"
      if bench build; then
        ok "bench build завершился успешно"
      else
        warn "bench build завершился с ошибкой"
      fi
    else
      say "• ассеты на месте — сборка не требуется"
    fi
  fi
  chmod -R a+rX /workspace/sites/assets || true
}

# ==== Публикация файлов dantist_app в /files ====
link_app_public_files(){
  step "🔗 Публикация файлов dantist_app в ${SITE}/public/files (symlink)"
  local APP="dantist_app"
  local APP_FILES_DIR="$BENCH_DIR/sites/assets/${APP}/files"
  local SITE_FILES_DIR="$SITE_DIR/public/files"

  mkdir -p "$SITE_FILES_DIR"

  if [[ ! -d "$APP_FILES_DIR" ]]; then
    warn "Каталог с файлами приложения не найден: $APP_FILES_DIR (возможно, ассеты ещё не собраны)"
    return 0
  fi

  for dir in source_avatars; do
    if [[ -d "${APP_FILES_DIR}/${dir}" ]]; then
      if [[ -e "${SITE_FILES_DIR}/${dir}" && ! -L "${SITE_FILES_DIR}/${dir}" ]]; then
        warn "Пропускаю каталог /files/${dir}: уже существует реальная директория"
      else
        ln -sfn "${APP_FILES_DIR}/${dir}" "${SITE_FILES_DIR}/${dir}"
        ok "symlink: /files/${dir} -> ${APP_FILES_DIR}/${dir}"
      fi
    fi
  done

  shopt -s nullglob dotglob
  for item in "${APP_FILES_DIR}/"*; do
    local name
    name="$(basename "$item")"
    local target="${SITE_FILES_DIR}/${name}"
    if [[ -e "$target" && ! -L "$target" ]]; then
      say "skip (exists real): /files/${name}"
      continue
    fi
    ln -sfn "$item" "$target"
    say "linked: /files/${name} -> $item"
  done

  chmod -R a+rX "$SITE_FILES_DIR" || true
}

# ==== sync fixtures ====
do_fixtures(){
  step "📥 Синхронизация фикстур"
  if site_cmd execute "frappe.utils.fixtures.sync_fixtures"; then
    ok "фикстуры синхронизированы"
  else
    warn "sync_fixtures завершился с ошибкой"
  fi
}

# ==== Проверка Administrator через root-SQL ====
admin_exists_mysql(){
  read -r DB_NAME _ _ < <(read_db_creds || echo "   ")
  [[ -z "${DB_NAME:-}" ]] && return 2
  mysql -h "${DB_HOST}" -P "${DB_PORT}" -uroot -p"${FRAPPE_DB_ROOT_PASSWORD}" "${DB_NAME}" \
    -Nse "SELECT 1 FROM tabUser WHERE name='Administrator' LIMIT 1;" 2>/dev/null | grep -q 1
}

do_admin_password(){
  local PASS="${FRAPPE_ADMIN_PASSWORD:-${ADMIN_PASSWORD:-}}"
  if [[ -z "$PASS" ]]; then
    say "FRAPPE_ADMIN_PASSWORD не задан — пропускаю установку пароля Administrator"
    return 0
  fi

  step "🔐 Проверка/установка пароля Administrator"
  if admin_exists_mysql; then
    ok "Administrator уже существует — смена пароля не требуется"
    return 0
  fi

  say "• Administrator не найден — выставляю пароль через bench"
  if site_cmd set-admin-password "$PASS"; then
    ok "Пароль Administrator установлен"
  else
    warn "Не удалось установить пароль Administrator (см. лог bench)"
  fi
}

print_env_summary(){
  step "🧾 ENV-summary (маскировано)"
  say "• SITE=${SITE}"
  say "• HOST=${HOST} (${PROTO})"
  say "• DB_HOST=${DB_HOST}:${DB_PORT}"
  say "• FRAPPE_DB_ROOT_PASSWORD=$(mask "${FRAPPE_DB_ROOT_PASSWORD:-}")"
  say "• FRAPPE_ADMIN_PASSWORD=$(mask "${FRAPPE_ADMIN_PASSWORD:-}")"
  say "• FRAPPE_SHARED_SECRET (для dantist_shared_secret) = $(mask "${FRAPPE_SHARED_SECRET:-}")"
  say "• DANTIST_INTEGRATION_AUD = $(mask "${DANTIST_INTEGRATION_AUD:-}")"
  say "• APP_LIST=${APP_LIST}"
  say "• APP_ENV=${APP_ENV}  HEAVY=${HEAVY}  PROCFILE_MODE=${PROCFILE_MODE}"
}

print_configs(){
  step "📚 common_site_config.json (masked)"
  dump_config_masked "$COMMON_CFG" || true
  step "📚 site_config.json (masked)"
  dump_config_masked "$SITE_CFG" || true
}

# ===== Создание/пересоздание сайта =====
create_site(){
  step "🏗️  Создание сайта: ${SITE}"
  [[ -n "${FRAPPE_DB_ROOT_PASSWORD:-}" ]] || fatal "Нужен FRAPPE_DB_ROOT_PASSWORD/DB_ROOT_PASSWORD"
  [[ -n "${FRAPPE_ADMIN_PASSWORD:-}"   ]] || fatal "Нужен FRAPPE_ADMIN_PASSWORD/ADMIN_PASSWORD"

  # Frappe ставится как основа, install-app frappe не делаем
  local install_apps=()
  if has_app erpnext; then
    install_apps+=("erpnext")
  fi
  # Остальные из APP_LIST (кроме erpnext, чтобы не дублировать)
  for app in ${APP_LIST}; do
    [[ "$app" == "erpnext" ]] && continue
    if has_app "$app"; then
      install_apps+=("$app")
    fi
  done
  say "• install on create apps: ${install_apps[*]:-<none>}"

  # Собираем bench new-site в массив, чтобы не получить пустых аргументов
  local cmd=(bench new-site "${SITE}"
    --mariadb-root-username root
    --mariadb-root-password "${FRAPPE_DB_ROOT_PASSWORD}"
    --admin-password "${FRAPPE_ADMIN_PASSWORD}"
    --db-host "${DB_HOST}"
    --db-port "${DB_PORT}"
    --mariadb-user-host-login-scope=%
  )

  if [[ -n "${SITE_DB_NAME:-}" ]]; then
    cmd+=(--db-name "${SITE_DB_NAME}")
  fi
  if [[ -n "${SITE_DB_PASSWORD:-}" ]]; then
    cmd+=(--db-password "${SITE_DB_PASSWORD}")
  fi

  if ((${#install_apps[@]})); then
    for a in "${install_apps[@]}"; do
      cmd+=(--install-app "$a")
    done
  fi

  cmd+=(--force)

  say "• bench new-site команда:"
  printf '    %q' "${cmd[@]}"
  echo

  "${cmd[@]}"

  ensure_site_logs
  ok "Сайт создан"
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
  || warn "root-доступ не подтвердился (new-site потребует корректный root-пароль в ENV)"

# ===== 1) common_site_config.json (+ redis/node/db_host) =====
step "🛠️  Общий конфиг: $COMMON_CFG"
python3 - <<'PY'
import os, json, pathlib
p = pathlib.Path("/workspace/sites/common_site_config.json")
p.parent.mkdir(parents=True, exist_ok=True)
cfg = {}
if p.exists():
    try:
        cfg = json.loads(p.read_text() or "{}")
    except Exception:
        cfg = {}
redis = os.getenv("REDIS_URL","redis://redis:6379")
redis_base = f"{redis.split('/',3)[0]}//{redis.split('/',3)[2]}"
cfg.update({
    "default_site": os.getenv("SITE_NAME","dantist.localhost"),
    "webserver_port": 443,
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
cfg["db_host"] = os.getenv("DB_HOST","mariadb")
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print(f"OK {p}")
PY
ok "common_site_config.json записан"

mkdir -p "$SITE_DIR" || true
ensure_site_logs

# ===== 2) создание / пересоздание сайта =====
if [[ ! -f "$SITE_CFG" ]]; then
  create_site
else
  step "♻️  Сайт уже существует — проверяю базу"
  if core_tables_ok; then
    ok "База сайта консистентна (таблицы ядра найдены)"
  else
    warn "База сайта неконсистентна (нет tabDefaultValue)"
    tables_cnt="$(db_tables_count || echo 0)"
    say "• db_tables_count=${tables_cnt}"
    if [[ "${tables_cnt:-0}" -eq 0 ]]; then
      warn "База пустая/отсутствует — пересоздаю сайт ${SITE}"
      create_site
    else
      warn "База содержит таблицы (${tables_cnt}) — считаю её битой, дропаю и пересоздаю"
      read -r DB_NAME _ _ _ < <(read_db_creds || echo "    ")
      if [[ -n "${DB_NAME:-}" ]]; then
        say "• DROP DATABASE \`${DB_NAME}\` и пользователя '${DB_NAME}'@'%'"
        mysql -h "$DB_HOST" -P "$DB_PORT" -uroot -p"$FRAPPE_DB_ROOT_PASSWORD" \
          -e "DROP DATABASE IF EXISTS \`${DB_NAME}\`; DROP USER IF EXISTS '${DB_NAME}'@'%';" \
          || warn "Не удалось дропнуть БД/пользователя — bench new-site сам попробует создать заново"
      fi
      if [[ -d "$SITE_DIR" && "$SITE_DIR" == /workspace/sites/* ]]; then
        rm -rf "$SITE_DIR"
        mkdir -p "$SITE_DIR"
      fi
      create_site
    fi
  fi
fi

# ===== 3) Актуализация site_config.json из ENV + socket.io =====
step "🧩 Актуализация site_config.json из ENV"
python3 - <<'PY'
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
public_origin = os.getenv("HOST_NAME", f"{proto}://{host}")

p = pathlib.Path(f"/workspace/sites/{site}/site_config.json")
cfg = json.loads(p.read_text() or "{}") if p.exists() else {}

cfg["db_host"] = os.getenv("DB_HOST","mariadb")

cfg["host_name"] = public_origin
cfg["use_ssl"] = (proto == "https")
cfg["preferred_url_protocol"] = proto

cfg["dantist_base_url"] = os.getenv("DANTIST_BASE_URL_INTERNAL", "http://backend:8000/api")

legacy = os.getenv("LEGACY_ADMIN_PUBLIC_ORIGIN", public_origin)
cfg["dantist_iframe_origin"] = legacy if good_origin(legacy) else public_origin

cfg["server_script_enabled"] = True
cfg["dantist_env"] = os.getenv("APP_ENV","prod")

cfg["socketio_protocol"] = "https" if proto=="https" else "http"
cfg["socketio_port"] = 443 if proto=="https" else 80
cfg["socketio_path"] = "/socket.io"

secret_env = os.getenv("FRAPPE_SHARED_SECRET")
if secret_env:
    cfg["dantist_shared_secret"] = secret_env

aud_env = os.getenv("DANTIST_INTEGRATION_AUD")
if aud_env:
    cfg["dantist_integration_aud"] = aud_env

devmode = os.getenv("DEVELOPER_MODE")
if devmode is not None:
    cfg["developer_mode"] = 1 if str(devmode).strip().lower() in {"1","true","yes","on"} else 0

log_level = os.getenv("LOG_LEVEL")
if log_level:
    cfg["log_level"] = log_level

enc = os.getenv("ENCRYPTION_KEY")
if enc:
    cfg["encryption_key"] = enc

pbx_token = os.getenv("PBX_WEBHOOK_TOKEN")
if pbx_token:
    cfg["pbx_webhook_token"] = pbx_token

p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print(f"OK {p}")
PY
ok "site_config.json обновлён"

ensure_socketio_settings
quick_diag

# ===== 4) регистрация приложений в sites/apps.txt =====
step "🗂️ Регистрация приложений в sites/apps.txt"
ensure_apps_txt_has frappe
has_app erpnext && ensure_apps_txt_has erpnext
for app in ${APP_LIST}; do
  ensure_app_present_and_registered "$app"
done

# ===== 5) миграции и установка приложений (по HEAVY) =====
do_migrate
do_install_apps
do_migrate

# ===== 6) фикстуры (всегда, чтобы HEAVY=0 работал для sync fixtures) =====
do_fixtures

# ===== 7) ассеты =====
do_assets

# ===== 8) файлы приложения в /files =====
link_app_public_files

# ===== 9) пароль Administrator (если задан) =====
do_admin_password

# ===== 10) Procfile =====
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
ok "Procfile готов (${PROCFILE_MODE})"

# ===== 11) Сводки =====
print_env_summary
print_configs
step "📄 Procfile (print)"
sed 's/^/    /' "$PROCFILE_PATH" || true

step "📋 Финальная сводка"
(site_cmd list-apps || true) | sed 's/^/• /'
say "assets: $(du -sh /workspace/sites/assets 2>/dev/null | awk '{print $1}')"
say "• get_url(): $(site_cmd execute 'frappe.utils.get_url' 2>/dev/null || echo '<error>')"

ensure_site_logs
ok "Bootstrap завершён. Запускаю процессы…"

exec bench start