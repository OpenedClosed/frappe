#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/bench-env/bin:$PATH"
cd /workspace

SITE="${SITE_NAME:-dantist.localhost}"
SITE_PATH="/workspace/sites/${SITE}"
COMMON_PATH="/workspace/sites/common_site_config.json"
SITE_CONFIG="${SITE_PATH}/site_config.json"

DB_HOST="${DB_HOST:-mariadb}"
DB_WAIT_SECONDS="${DB_WAIT_SECONDS:-60}"

# ---- HOST -> PUBLIC URLs (для браузера) ----
HOST="${HOST:-localhost}"
if [[ "$HOST" == "localhost" || "$HOST" == "127.0.0.1" ]]; then
  PROTOCOL="http"
else
  PROTOCOL="https"
fi

# Порты: внешне за Nginx, но публичные адреса нужны для iFrame
FRAPPE_PORT="${FRAPPE_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# Публичные (через Nginx / для браузера)
FRAPPE_PUBLIC_BASE="${FRAPPE_PUBLIC_BASE:-${PROTOCOL}://${HOST}/admin/api}"
FRONTEND_PUBLIC_ORIGIN_DEFAULT="${PROTOCOL}://${HOST}"
FRONTEND_PUBLIC_ORIGIN="${FRONTEND_PUBLIC_ORIGIN:-$FRONTEND_PUBLIC_ORIGIN_DEFAULT}"
FRONTEND_IFRAME_URL_DEFAULT="${PROTOCOL}://${HOST}/legacy-admin"
FRONTEND_IFRAME_URL="${FRONTEND_IFRAME_URL:-$FRONTEND_IFRAME_URL_DEFAULT}"

# Внутренние (межконтейнерные)
FRAPPE_API_BASE_INTERNAL="${FRAPPE_API_BASE_INTERNAL:-http://frappe:8001/api}"
DANTIST_BASE_URL_INTERNAL="${DANTIST_BASE_URL_INTERNAL:-http://backend:8000/api}"

mkdir -p "${SITE_PATH}" || true

# ===== 0) Нормализуем REDIS_URL в базу + /0 /1 /2 =====
# Позволяет задавать REDIS_URL без DB-суффикса, например redis://redis:6379
REDIS_BASE="$(printf '%s' "${REDIS_URL:-redis://redis:6379}" | awk -F/ '{print $1"//"$3}')"
export REDIS_BASE

# ===== 1) Ждём MariaDB =====
echo "[frappe] waiting for MariaDB at ${DB_HOST}:3306 (timeout ${DB_WAIT_SECONDS}s)"
for i in $(seq 1 "${DB_WAIT_SECONDS}"); do
  (echo > /dev/tcp/${DB_HOST}/3306) >/dev/null 2>&1 && break || true
  sleep 1
  if [ "$i" = "${DB_WAIT_SECONDS}" ]; then
    echo "[frappe] ERROR: MariaDB is not reachable" >&2
    exit 1
  fi
done

# Алиасы паролей (совместимость)
FRAPPE_DB_ROOT_PASSWORD="${FRAPPE_DB_ROOT_PASSWORD:-${DB_ROOT_PASSWORD:-}}"
FRAPPE_ADMIN_PASSWORD="${FRAPPE_ADMIN_PASSWORD:-${ADMIN_PASSWORD:-}}"

# ===== 2) Базовый common_site_config до любых bench-команд =====
python3 - <<'PY'
import os, json, pathlib

p = pathlib.Path("/workspace/sites/common_site_config.json")
p.parent.mkdir(parents=True, exist_ok=True)
cfg = {}
if p.exists():
    try: cfg = json.loads(p.read_text() or "{}")
    except Exception: cfg = {}

redis_base = os.getenv("REDIS_BASE","redis://redis:6379")

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
PY

# ===== 3) Если сайт ещё не создан — создаём =====
if [ ! -f "${SITE_CONFIG}" ]; then
  if [ -z "${FRAPPE_DB_ROOT_PASSWORD:-}" ]; then
    echo "ERROR: FRAPPE_DB_ROOT_PASSWORD/DB_ROOT_PASSWORD is required." >&2; exit 1
  fi
  if [ -z "${FRAPPE_ADMIN_PASSWORD:-}" ]; then
    echo "ERROR: FRAPPE_ADMIN_PASSWORD/ADMIN_PASSWORD is required." >&2; exit 1
  fi

  echo "[frappe] creating new site ${SITE} ..."
  bench new-site "${SITE}" \
    --mariadb-root-username root \
    --mariadb-root-password "${FRAPPE_DB_ROOT_PASSWORD}" \
    --admin-password "${FRAPPE_ADMIN_PASSWORD}" \
    --db-host "${DB_HOST}" \
    --no-mariadb-socket \
    --install-app frappe \
    --force

  # (опционально) ERPNext
  if [ "${INSTALL_ERPNext:-0}" = "1" ]; then
    bench --site "${SITE}" install-app erpnext
  fi

  # Устанавливаем твоё приложение
  bench --site "${SITE}" install-app dantist_app

  # Первая миграция — подтянет фикстуры
  bench --site "${SITE}" migrate
fi

# ===== 3.5) Self-heal БД-пользователя/пароля/прав (если site_config есть) =====
if [ -f "${SITE_CONFIG}" ] && [ -n "${FRAPPE_DB_ROOT_PASSWORD:-}" ]; then
  python3 - "$SITE_CONFIG" <<'PY'
import sys, json, pathlib, os, subprocess, shlex
p = pathlib.Path(sys.argv[1])
try:
    cfg = json.loads(p.read_text())
except Exception:
    cfg = {}
db_host = os.getenv("DB_HOST","mariadb")
db_root_pwd = os.getenv("FRAPPE_DB_ROOT_PASSWORD","")
db_name = cfg.get("db_name")
db_pwd  = cfg.get("db_password")
db_user = db_name  # frappe использует имя БД как имя пользователя
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
fi

# ===== 4) Патч site_config.json из ENV на каждом старте =====
python3 - <<'PY'
import os, json, pathlib

def read_json(p):
    p = pathlib.Path(p)
    if not p.exists(): return {}
    try: return json.loads(p.read_text() or "{}")
    except Exception: return {}

def write_json(p, data):
    pathlib.Path(p).write_text(json.dumps(data, indent=2, ensure_ascii=False))

def parse_bool(v, default=False):
    if v is None: return default
    return str(v).strip().lower() in {"1","true","yes","on"}

def parse_list_csv(v):
    if not v: return None
    return [x.strip() for x in v.split(",") if x.strip()]

site = os.getenv("SITE_NAME","dantist.localhost")
host = os.getenv("HOST","localhost")
proto = "http" if host in {"localhost","127.0.0.1"} else "https"

common_path = "/workspace/sites/common_site_config.json"
site_path   = f"/workspace/sites/{site}/site_config.json"

site_cfg = read_json(site_path)

# DB хост
site_cfg["db_host"] = os.getenv("DB_HOST","mariadb")

# Полный публичный хост для формирования ссылок (без :8001 — работаем за Nginx)
site_cfg["host_name"] = os.getenv("HOST_NAME", f"{proto}://{host}")

# Внутренний URL для сервер-сайд интеграции Frappe -> FastAPI
site_cfg["dantist_base_url"] = os.getenv("DANTIST_BASE_URL_INTERNAL", "http://backend:8000/api")

# iFrame: полный публичный URL скрытой админки + её ORIGIN (домен без пути)
iframe_url = os.getenv("FRONTEND_IFRAME_URL")
if iframe_url:
    site_cfg["dantist_iframe_url"] = iframe_url
else:
    # дефолт собран из HOST
    site_cfg["dantist_iframe_url"] = f"{proto}://{host}/legacy-admin"

iframe_origin = os.getenv("FRONTEND_PUBLIC_ORIGIN")
if iframe_origin:
    site_cfg["dantist_iframe_origin"] = iframe_origin
else:
    site_cfg["dantist_iframe_origin"] = f"{proto}://{host}"

# Ауд
site_cfg["dantist_integration_aud"] = os.getenv("DANTIST_INTEGRATION_AUD","frappe")

# Shared secret (FastAPI ↔ Frappe)
shared = os.getenv("FRAPPE_SHARED_SECRET") or os.getenv("DANTIST_SHARED_SECRET")
if shared:
    site_cfg["dantist_shared_secret"] = shared

# Исключённые пользователи
excluded = parse_list_csv(os.getenv("DANTIST_EXCLUDED_USERS"))
if excluded is not None:
    site_cfg["dantist_excluded_users"] = excluded

# dev / логи
devmode = os.getenv("DEVELOPER_MODE")
if devmode is not None:
    site_cfg["developer_mode"] = 1 if parse_bool(devmode) else 0

log_level = os.getenv("LOG_LEVEL")
if log_level:
    site_cfg["log_level"] = log_level

site_cfg["server_script_enabled"] = True

# encryption_key — только если явно задан
env_key = os.getenv("ENCRYPTION_KEY")
if env_key and site_cfg.get("encryption_key") != env_key:
    site_cfg["encryption_key"] = env_key

write_json(site_path, site_cfg)
PY

# ===== 5) Наш Procfile: без внутренних redis-процессов и без локальных путей к node =====
cat > /workspace/Procfile <<'PROC'
web: cd /workspace && bench serve --port 8001
socketio: cd /workspace && node apps/frappe/socketio.js
schedule: cd /workspace && bench schedule
worker: cd /workspace && bench worker
PROC

# ===== 6) Логи: каталоги/пустые файлы, чтобы worker/schedule не падали =====
mkdir -p /workspace/logs
mkdir -p "/workspace/sites/${SITE}/logs"
touch "/workspace/sites/${SITE}/logs"/{frappe.log,database.log,web.log,worker.log,scheduler.log} || true

# ===== 7) Сборка ассетов (уже в валидной bench-директории) =====
bench build || true

# Материализация ассетов (если есть симлинки)
for app in frappe erpnext dantist_app; do
  src="/workspace/apps/$app/$app/public"
  dst="/workspace/sites/assets/$app"
  if [ -L "$dst" ] && [ -d "$src" ]; then
    echo "[start] materialize assets for $app -> $dst"
    rm -f "$dst"
    mkdir -p "$dst"
    cp -aL "$src/." "$dst/"
  fi
done
chmod -R a+rX /workspace/sites/assets || true

# ===== 8) Старт процессов =====
exec bench start