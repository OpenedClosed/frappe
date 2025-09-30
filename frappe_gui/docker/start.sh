#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/bench-env/bin:$PATH"
cd /workspace

# --- Инициализация тома sites при первом старте ---
if [ ! -f "/workspace/sites/apps.json" ]; then
  cp -a /opt/seed-sites/. /workspace/sites/ || true
fi

# --- Патч конфигов под Docker + Procfile(prod) ---
python3 - <<'PY'
import json, os, pathlib

def read_json(path):
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text() or "{}")
    except Exception:
        return {}

def write_json(path, data):
    pathlib.Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))

site = os.getenv("SITE_NAME", "dantist.localhost")
common_path = "/workspace/sites/common_site_config.json"
site_path = f"/workspace/sites/{site}/site_config.json"

# путь к локальному (seed) конфигу, который приехал в образ при билде
seed_path = f"/opt/seed-sites/{site}/site_config.json"

common = read_json(common_path)
common.update({
    "default_site": site,
    "webserver_port": 8001,
    "socketio_port": 9000,
    "redis_cache": "redis://redis:6379/0",
    "redis_queue": "redis://redis:6379/1",
    "redis_socketio": "redis://redis:6379/2",
    "use_redis_auth": False,
    "serve_default_site": True,
    "live_reload": False,
    "frappe_user": "root"
})
write_json(common_path, common)

site_cfg = read_json(site_path)

# принудительно выставляем encryption_key из локального seed-конфига (если он там есть)
seed_cfg = read_json(seed_path)
seed_key = seed_cfg.get("encryption_key")
if seed_key and site_cfg.get("encryption_key") != seed_key:
    site_cfg["encryption_key"] = seed_key

# остальная логика как была
site_cfg["db_host"] = "mariadb"
write_json(site_path, site_cfg)

# Всегда запускать процессы из /workspace
proc = (
    "web: cd /workspace && bench serve --port 8001\n"
    "socketio: cd /workspace && node apps/frappe/socketio.js\n"
    "schedule: cd /workspace && bench schedule\n"
    "worker: cd /workspace && bench worker\n"
)
pathlib.Path("/workspace/Procfile").write_text(proc)
PY

# --- Сборка ассетов ---
mkdir -p /workspace/logs

# гарантируем наличие папки логов сайта и файлов, чтобы избежать FileNotFoundError
SITE="${SITE_NAME:-dantist.localhost}"
mkdir -p "/workspace/sites/$SITE/logs" && touch "/workspace/sites/$SITE/logs"/{frappe.log,database.log,web.log,worker.log,scheduler.log} || true

bench build || true
 
# --- Материализация ассетов (убираем симлинки, копируем реальные файлы) ---
for app in frappe erpnext task_tracker; do
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

# --- Старт процессов ---
exec bench start
