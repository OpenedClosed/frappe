#!/usr/bin/env bash
set -euo pipefail

log() { echo -e "[$(date +'%F %T')] $*"; }
fatal() { echo -e "[$(date +'%F %T')] ERROR: $*" >&2; exit 1; }

export PATH="/opt/bench-env/bin:$PATH"
cd /workspace

SITE="${SITE_NAME:-dantist.localhost}"
SITE_PATH="/workspace/sites/${SITE}"
COMMON_PATH="/workspace/sites/common_site_config.json"
SITE_CONFIG="${SITE_PATH}/site_config.json"

DB_HOST="${DB_HOST:-mariadb}"
DB_WAIT_SECONDS="${DB_WAIT_SECONDS:-60}"

# ---- PUBLIC HOST/PROTO (для формирования ссылок) ----
HOST="${HOST:-localhost}"
if [[ "$HOST" == "localhost" || "$HOST" == "127.0.0.1" ]]; then
  PROTOCOL="http"
else
  PROTOCOL="https"
fi

FRAPPE_PORT="${FRAPPE_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# Публичные
FRAPPE_PUBLIC_BASE="${FRAPPE_PUBLIC_BASE:-${PROTOCOL}://${HOST}/admin/api}"
FRONTEND_PUBLIC_ORIGIN_DEFAULT="${PROTOCOL}://${HOST}"
FRONTEND_PUBLIC_ORIGIN="${FRONTEND_PUBLIC_ORIGIN:-$FRONTEND_PUBLIC_ORIGIN_DEFAULT}"
FRONTEND_IFRAME_URL_DEFAULT="${PROTOCOL}://${HOST}/legacy-admin"
FRONTEND_IFRAME_URL="${FRONTEND_IFRAME_URL:-$FRONTEND_IFRAME_URL_DEFAULT}"

# Внутренние (service-to-service)
FRAPPE_API_BASE_INTERNAL="${FRAPPE_API_BASE_INTERNAL:-http://frappe:8001/api}"
DANTIST_BASE_URL_INTERNAL="${DANTIST_BASE_URL_INTERNAL:-http://backend:8000/api}"

mkdir -p "${SITE_PATH}" || true

# ===== 0) Клиентский my.cnf: глобально отключаем SSL для mysql-клиента =====
printf "[client]\nssl=0\nprotocol=tcp\n" > /root/.my.cnf

# Алиасы паролей (совместимость)
FRAPPE_DB_ROOT_PASSWORD="${FRAPPE_DB_ROOT_PASSWORD:-${DB_ROOT_PASSWORD:-}}"
FRAPPE_ADMIN_PASSWORD="${FRAPPE_ADMIN_PASSWORD:-${ADMIN_PASSWORD:-}}"

# ===== 1) Ждём MariaDB =====
log "[frappe] waiting for MariaDB at ${DB_HOST}:3306 (timeout ${DB_WAIT_SECONDS}s)"
for i in $(seq 1 "${DB_WAIT_SECONDS}"); do
  (echo > /dev/tcp/${DB_HOST}/3306) >/dev/null 2>&1 && break || true
  sleep 1
  [[ "$i" = "${DB_WAIT_SECONDS}" ]] && fatal "MariaDB is not reachable"
done

# ===== 2) Базовый common_site_config до любых bench-команд =====
python3 - <<'PY'
import os, json, pathlib
p = pathlib.Path("/workspace/sites/common_site_config.json")
p.parent.mkdir(parents=True, exist_ok=True)
cfg = {}
if p.exists():
    try: cfg = json.loads(p.read_text() or "{}")
    except Exception: cfg = {}
redis_base = os.getenv("REDIS_URL","redis://redis:6379").split("/",3)
redis_base = f"{redis_base[0]}//{redis_base[2]}"
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
})
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print("[common] written", p)
PY

bench() { command bench "$@"; }
site_cmd() { bench --site "$SITE" "$@"; }

# ===== helper: проверка, установлено ли приложение =====
is_app_installed() { site_cmd list-apps 2>/dev/null | grep -Fqx "$1"; }

# ===== 3) Если сайт ещё не создан — создаём =====
if [ ! -f "${SITE_CONFIG}" ]; then
  [[ -z "${FRAPPE_DB_ROOT_PASSWORD:-}" ]] && fatal "FRAPPE_DB_ROOT_PASSWORD/DB_ROOT_PASSWORD is required"
  [[ -z "${FRAPPE_ADMIN_PASSWORD:-}" ]] && fatal "FRAPPE_ADMIN_PASSWORD/ADMIN_PASSWORD is required"

  log "[site] creating new site ${SITE} ..."
  bench new-site "${SITE}" \
    --mariadb-root-username root \
    --mariadb-root-password "${FRAPPE_DB_ROOT_PASSWORD}" \
    --admin-password "${FRAPPE_ADMIN_PASSWORD}" \
    --db-host "${DB_HOST}" \
    --mariadb-user-host-login-scope='%' \
    --install-app frappe \
    --force

  # Включаем DEV MODE сразу (для фикстур DocType)
  site_cmd set-config developer_mode 1
fi

# ===== 3.5) Self-heal БД-пользователя/пароля/прав =====
python3 - "$SITE_CONFIG" <<'PY'
import sys, json, pathlib, os, subprocess
p = pathlib.Path(sys.argv[1])
if not p.exists():
    sys.exit(0)
try:
    cfg = json.loads(p.read_text() or "{}")
except Exception:
    cfg = {}
db_host = os.getenv("DB_HOST","mariadb")
db_root_pwd = os.getenv("FRAPPE_DB_ROOT_PASSWORD","")
db_name = cfg.get("db_name")
db_pwd  = cfg.get("db_password")
db_user = db_name  # frappe: имя БД == имя пользователя
if db_name and db_pwd and db_root_pwd:
    sql = f"""
    CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4;
    CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_pwd}';
    ALTER USER '{db_user}'@'%' IDENTIFIED BY '{db_pwd}';
    GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'%';
    FLUSH PRIVILEGES;
    """
    cmd = ["mysql","-h",db_host,"-uroot",f"-p{db_root_pwd}","-e",sql]
    try:
        subprocess.run(cmd, check=True)
        print("[self-heal] ensured db/user/grants for", db_name, file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print("[self-heal] skip / not first run:", e, file=sys.stderr)
PY

# ===== 4) Патчим site_config.json из ENV на КАЖДОМ старте (идемпотентно) =====
python3 - <<PY
import os, json, pathlib
def read(p):
    p=pathlib.Path(p)
    return json.loads(p.read_text() or "{}") if p.exists() else {}
def write(p,d):
    pathlib.Path(p).write_text(json.dumps(d, indent=2, ensure_ascii=False))

site = os.getenv("SITE_NAME","dantist.localhost")
host = os.getenv("HOST","localhost")
proto = "http" if host in {"localhost","127.0.0.1"} else "https"
site_path = f"/workspace/sites/{site}/site_config.json"
cfg = read(site_path)

cfg["db_host"] = os.getenv("DB_HOST","mariadb")
cfg["host_name"] = os.getenv("HOST_NAME", f"{proto}://{host}")
cfg["dantist_base_url"] = os.getenv("DANTIST_BASE_URL_INTERNAL", "http://backend:8000/api")

iframe_url = os.getenv("FRONTEND_IFRAME_URL") or f"{proto}://{host}/legacy-admin"
cfg["dantist_iframe_url"] = iframe_url
cfg["dantist_iframe_origin"] = os.getenv("FRONTEND_PUBLIC_ORIGIN") or f"{proto}://{host}"

cfg["dantist_integration_aud"] = os.getenv("DANTIST_INTEGRATION_AUD","frappe")
shared = os.getenv("FRAPPE_SHARED_SECRET") or os.getenv("DANTIST_SHARED_SECRET")
if shared: cfg["dantist_shared_secret"] = shared

# Dev mode: если DEVELOPER_MODE=1 в .env — форсим в site_config.json
devmode = os.getenv("DEVELOPER_MODE")
if devmode is not None:
    cfg["developer_mode"] = 1 if str(devmode).strip().lower() in {"1","true","yes","on"} else 0

log_level = os.getenv("LOG_LEVEL")
if log_level: cfg["log_level"] = log_level

cfg["server_script_enabled"] = True

env_key = os.getenv("ENCRYPTION_KEY")
if env_key and cfg.get("encryption_key") != env_key:
    cfg["encryption_key"] = env_key

write(site_path, cfg)
print("[site-config] patched", site_path)
PY

# ===== 5) Установка dantist_app (идемпотентно) =====
if ! is_app_installed "dantist_app"; then
  site_cmd set-config developer_mode 1
  log "[apps] installing dantist_app ..."
  site_cmd install-app dantist_app || {
    log "[apps] install-app failed (retry after core migrate)..."
    site_cmd migrate
    site_cmd install-app dantist_app
  }
fi

# ===== 6) Миграции + авто-ремеди на известные коллизии фикстур =====
set +e
site_cmd migrate
MIGRC=$?
set -e
if [[ $MIGRC -ne 0 ]]; then
  log "[migrate] failed, healing known 'Has Role' duplicate..."
  site_cmd execute frappe.database.query \
    --args "DELETE FROM \`tabHas Role\` WHERE parent='permission-manager' AND role='System Manager'" || true
  site_cmd migrate
fi

# ===== 7) Procfile =====
cat > /workspace/Procfile <<'PROC'
web: cd /workspace && bench serve --port 8001
socketio: cd /workspace && node apps/frappe/socketio.js
schedule: cd /workspace && bench schedule
worker: cd /workspace && bench worker
PROC

# ===== 8) Логи =====
mkdir -p /workspace/logs "/workspace/sites/${SITE}/logs"
touch "/workspace/sites/${SITE}/logs"/{frappe.log,database.log,web.log,worker.log,scheduler.log} || true

# ===== 9) Сборка и материализация ассетов =====
bench build || true
for app in frappe erpnext dantist_app; do
  src="/workspace/apps/$app/$app/public"
  dst="/workspace/sites/assets/$app"
  if [ -L "$dst" ] && [ -d "$src" ]; then
    log "[start] materialize assets for $app -> $dst"
    rm -f "$dst"
    mkdir -p "$dst"
    cp -aL "$src/." "$dst/"
  fi
done
chmod -R a+rX /workspace/sites/assets || true

log "[ok] starting bench processes..."
exec bench start