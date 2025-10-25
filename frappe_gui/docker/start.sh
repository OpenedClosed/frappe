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

FRAPPE_DB_ROOT_PASSWORD="${FRAPPE_DB_ROOT_PASSWORD:-${DB_ROOT_PASSWORD:-}}"
FRAPPE_ADMIN_PASSWORD="${FRAPPE_ADMIN_PASSWORD:-${ADMIN_PASSWORD:-}}"
APP_LIST="${FRAPPE_INSTALL_APPS:-dantist_app}"   # через пробел
APP_ENV="${APP_ENV:-prod}"                       # prod|dev
PROCFILE_MODE="${PROCFILE_MODE:-container}"
WEB_PORT="${WEB_PORT:-8001}"
SOCKETIO_NODE_BIN="${SOCKETIO_NODE_BIN:-/usr/bin/node}"
BENCH_BIN="${BENCH_BIN:-bench}"

# wrappers
bench()    { (cd "$BENCH_DIR" && command bench "$@"); }
site_cmd() { (cd "$BENCH_DIR" && command bench --site "$SITE" "$@"); }

# mysql client без SSL (устраняет sporadic HY000/2026)
printf "[client]\nssl=0\nprotocol=tcp\n" > /root/.my.cnf

# ------ helpers ------
read_db_creds() {
  python3 - "$SITE_CFG" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: d={}
print(d.get("db_name","")); print(d.get("db_password","")); print(d.get("db_host","")); print(d.get("dantist_env",""))
PY
}

core_tables_ok() {
  [[ -f "$SITE_CFG" ]] || return 1
  local DB_NAME
  DB_NAME="$(python3 - "$SITE_CFG" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
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
    [[ -n "${DB_NAME:-}" ]] && { core_tables_ok && ok "таблицы ядра на месте (tabDefaultValue)"; }
  else
    warn "site_config.json отсутствует"
  fi
}

# ===== 0) ждём MariaDB =====
step "⏳ Ожидание MariaDB ${DB_HOST}:${DB_PORT} (до ${DB_WAIT}s)"
for i in $(seq 1 "$DB_WAIT"); do
  (echo > /dev/tcp/${DB_HOST}/${DB_PORT}) >/dev/null 2>&1 && { ok "MariaDB reachable"; break; }
  sleep 1
  [[ "$i" == "$DB_WAIT" ]] && fatal "MariaDB не доступна за ${DB_WAIT}s"
done
mysql -h "$DB_HOST" -P "$DB_PORT" -uroot -p"$FRAPPE_DB_ROOT_PASSWORD" -e "SELECT 1" >/dev/null 2>&1 \
  && ok "root-доступ к MariaDB подтверждён" || warn "root-доступ не подтвердился"

# ===== 1) common_site_config.json =====
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

# ===== 2) если сайта нет — создать (один раз) =====
if [[ ! -f "$SITE_CFG" ]]; then
  step "🏗️  Создание нового сайта: ${SITE}"
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
fi

# ===== 3) бережная актуализация site_config.json =====
step "🧩 Актуализация site_config.json из ENV (без трогания db_name/db_password)"
python3 - <<PY
import os, json, pathlib 
site = os.getenv("SITE_NAME","dantist.localhost")
host = os.getenv("HOST","localhost")
proto = "http" if host in {"localhost","127.0.0.1"} else "https"
p = pathlib.Path(f"/workspace/sites/{site}/site_config.json")
cfg = json.loads(p.read_text() or "{}") if p.exists() else {}
cfg.setdefault("db_host", os.getenv("DB_HOST","mariadb"))
cfg["host_name"] = os.getenv("HOST_NAME", f"{proto}://{host}")
cfg["dantist_base_url"] = os.getenv("DANTIST_BASE_URL_INTERNAL", "http://backend:8000/api")
cfg["dantist_iframe_origin"] = os.getenv("FRONTEND_PUBLIC_ORIGIN") or f"{proto}://{host}"
cfg["server_script_enabled"] = True
cfg["dantist_env"] = os.getenv("APP_ENV","prod")
devmode = os.getenv("DEVELOPER_MODE")
if devmode is not None:
    cfg["developer_mode"] = 1 if str(devmode).strip().lower() in {"1","true","yes","on"} else 0
log_level = os.getenv("LOG_LEVEL")
if log_level: cfg["log_level"] = log_level
enc = os.getenv("ENCRYPTION_KEY")
if enc and cfg.get("encryption_key") != enc:
    cfg["encryption_key"] = enc
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print(f"OK {p}")
PY
ok "site_config.json обновлён"
quick_diag

# ===== 4) короткое-замыкание: вычисляем сигнатуру состояния =====
git_sha() { git -C "$1" rev-parse --short HEAD 2>/dev/null || echo none; }
hash_tree() {
  find "$1" -type f \( -path "*/fixtures/*" -o -path "*/public/*" -o -name "*.py" -o -name "*.json" -o -name "*.js" -o -name "*.css" \) \
    -printf '%P %T@\n' 2>/dev/null | sort | md5sum | awk '{print $1}'
}
FRAPPE_SHA="$(git_sha apps/frappe)"
APP_SHA="$(git_sha apps/dantist_app)"
FIX_SIG="$(hash_tree apps/dantist_app || true)"
STATE_SIG="frappe:${FRAPPE_SHA}|app:${APP_SHA}|fix:${FIX_SIG}"
SIG_FILE="/workspace/sites/.bootstrap_sig"
PREV_SIG="$(cat "$SIG_FILE" 2>/dev/null || echo)"
LIGHT_MODE=0
if [[ "${FORCE_FULL_BOOTSTRAP:-0}" != "1" && "$PREV_SIG" == "$STATE_SIG" ]]; then
  LIGHT_MODE=1
  ok "Изменений не обнаружено → лёгкий режим"
else
  say "Обнаружены изменения или форс → полный режим"
fi

# ===== 5) регистрация приложений в apps.txt =====
step "🗂️ Регистрация приложений"
touch "$APPS_TXT"
grep -Fxq "frappe" "$APPS_TXT" || echo "frappe" >> "$APPS_TXT"
for app in ${APP_LIST}; do
  [[ -d "$BENCH_DIR/apps/$app" ]] || fatal "Нет приложения: /workspace/apps/$app"
  grep -Fxq "$app" "$APPS_TXT" || echo "$app" >> "$APPS_TXT"
done
ok "apps.txt готов"

# ===== 6) install-app (только если отсутствует) =====
for app in ${APP_LIST}; do
  if ! site_cmd list-apps 2>/dev/null | grep -Fqx "$app"; then
    step "🧩 install-app $app"
    site_cmd install-app "$app" || warn "install-app $app не прошёл"
  fi
done

# ===== 7) migrate (один раз и только при изменениях) =====
if [[ "$LIGHT_MODE" -ne 1 ]]; then
  step "📦 Migrate (разово)"
  site_cmd migrate || warn "migrate завершился с предупреждением"
fi

# ===== 8) фикстуры — ВСЕГДА =====
step "📥 Синхронизация фикстур"
site_cmd execute "frappe.utils.fixtures.sync_fixtures" \
  && ok "фикстуры синхронизированы" \
  || warn "sync_fixtures вернул ненулевой код"

# ===== 9) сборка ассетов/переводов — только при изменениях =====
if [[ "$LIGHT_MODE" -ne 1 ]]; then
  step "🧱 Сборка ассетов/переводов"
  if ! bench build --apps "frappe ${APP_LIST}"; then
    warn "scoped build упал — пробую полную сборку"
    bench build || warn "bench build с предупреждением"
  fi
fi

# ===== 10) очистка кэша — ВСЕГДА =====
step "🧹 Очистка кэша"
bench clear-cache || true

# ===== 11) Проверка/создание Administrator =====
step "🔐 Проверка/создание Administrator"
read -r DB_NAME DB_PASS _junk _envmark < <(read_db_creds || echo "    ")
if [[ -n "${DB_NAME:-}" && -n "${DB_PASS:-}" ]]; then
  if mysql -h "$DB_HOST" -P "$DB_PORT" -u"$DB_NAME" -p"$DB_PASS" "$DB_NAME" -Nse "SELECT 1 FROM tabUser WHERE name='Administrator' LIMIT 1;" 2>/dev/null | grep -q 1; then
    ok "Administrator существует"
  else
    warn "Administrator не найден — создаю и назначаю пароль"
    python3 - <<PY
import os, frappe
site=os.getenv("SITE_NAME","${SITE}")
pwd=os.getenv("FRAPPE_ADMIN_PASSWORD","")
frappe.init(site=site)
frappe.connect()
try:
    if not frappe.db.exists("User","Administrator"):
        u=frappe.new_doc("User")
        u.name="Administrator"
        u.email="admin@localhost"
        u.first_name="Administrator"
        u.enabled=1
        u.user_type="System User"
        u.insert(ignore_permissions=True, ignore_if_duplicate=True)
        frappe.db.commit()
    from frappe.utils.password import update_password
    if pwd:
        update_password("Administrator", pwd)
        frappe.db.commit()
    print("OK Administrator ensured")
finally:
    frappe.destroy()
PY
  fi
else
  say "• пропускаю проверку/создание Administrator (нет db creds в site_config.json)"
fi

# ===== 12) Procfile =====
step "🗂️  Procfile"
PROCFILE_PATH="/workspace/Procfile"
if [[ "$PROCFILE_MODE" == "local" ]]; then
  cat > "$PROCFILE_PATH" <<PROC
web: bench serve --port $WEB_PORT
socketio: $SOCKETIO_NODE_BIN apps/frappe/socketio.js
watch: bench watch
schedule: bench schedule
worker: OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES NO_PROXY=* bench worker 1>> logs/worker.log 2>> logs/worker.error.log
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

# ===== 13) запись сигнатуры (если был полный режим) =====
if [[ "$LIGHT_MODE" -ne 1 ]]; then
  echo "$STATE_SIG" > "$SIG_FILE"
  ok "Сигнатура состояния обновлена"
fi

# ===== 14) старт процессов =====
step "🚀 Запуск процессов"
exec bench start