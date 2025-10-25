#!/usr/bin/env bash
# Idempotent bootstrap for Frappe in Docker (prod-first; no loops)

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

APP_LIST="${FRAPPE_INSTALL_APPS:-dantist_app}"   # через пробел
PRUNE_SEEDED_SITE="${PRUNE_SEEDED_SITE:-1}"      # 1 — чистить только реально битый локальный сайт
APP_ENV="${APP_ENV:-prod}"                       # prod|dev
DISABLE_FIXTURE_HAS_ROLE="${DISABLE_FIXTURE_HAS_ROLE:-0}"  # подстраховка, если вернёшь фикстуру

# Procfile / bench / node настройки
PROCFILE_MODE="${PROCFILE_MODE:-container}"      # container|local
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
try: d=json.load(open(sys.argv[1]))
except Exception: d={}
print(d.get("db_name","")); print(d.get("db_password","")); print(d.get("db_host","")); print(d.get("dantist_env",""))
PY
}

db_exists() {
  local name="$1"
  mysql -h "$DB_HOST" -P "$DB_PORT" -uroot -p"$FRAPPE_DB_ROOT_PASSWORD" \
    -Nse "SELECT 1 FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='${name}' LIMIT 1;" 2>/dev/null | grep -q 1
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
  if ! grep -Fqx "$app" "$APPS_TXT"; then
    echo "$app" >> "$APPS_TXT"
    ok "добавил '$app' в sites/apps.txt"
  fi
}

ensure_app_present_and_registered() {
  local app="$1"
  if [[ ! -d "$BENCH_DIR/apps/$app" ]]; then
    fatal "Не найдено приложение $app в /workspace/apps/$app. Проверь сборку/копирование."
  fi
  ensure_apps_txt_has "$app"
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
  || warn "root-доступ не проверился (new-site/reinstall потребуют root пароль в ENV)"

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
    "node": "/usr/bin/node",  # не брать путь из host nvm
})
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print(f"OK {p}")
PY
ok "common_site_config.json записан"

mkdir -p "$SITE_DIR" || true

# ===== 2) мягкая чистка только реально битого «зашитого» сайта =====
step "🧹 Проверка на «локальный/зашитый» сайт и конфликты"
if [[ -f "$SITE_CFG" && "$PRUNE_SEEDED_SITE" == "1" ]]; then
  read -r CUR_DB CUR_PASS CUR_DBHOST CUR_ENV < <(read_db_creds || echo "    ")
  if [[ "${CUR_ENV:-}" == "prod" ]]; then
    ok "Маркер dantist_env=prod найден → существующий сайт считаем продовым, НЕ удаляю"
  else
    if { [[ -n "${CUR_DB:-}" ]] && ! db_exists "${CUR_DB}"; } || ! core_tables_ok; then
      warn "Сайт выглядит битым (нет схемы БД или табличек ядра) → удаляю"
      if [[ -n "${CUR_DB:-}" ]] && db_exists "${CUR_DB}"; then
        say "• drop-site --force (non-interactive)"
        bench drop-site "$SITE" --force \
          --mariadb-root-username root \
          --mariadb-root-password "${FRAPPE_DB_ROOT_PASSWORD}" || true
      fi
      rm -rf "$SITE_DIR"
      ok "Локальный остаток удалён"
    else
      ok "Сайт валиден (ядро/схема на месте) — не трогаю"
    fi
  fi
else
  say "site_config.json отсутствует или PRUNE_SEEDED_SITE=0 — чистка пропущена"
fi

# ===== 3) создаём сайт, если нет =====
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
else
  step "♻️  Сайт уже существует — пропускаю создание"
fi

# ===== 4) патчим site_config из ENV (каждый старт) + маркер окружения =====
step "🧩 Актуализация site_config.json из ENV"
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
p = pathlib.Path(f"/workspace/sites/{site}/site_config.json")
cfg = read(p)

cfg["db_host"] = os.getenv("DB_HOST","mariadb")
cfg["host_name"] = os.getenv("HOST_NAME", f"{proto}://{host}")
cfg["dantist_base_url"] = os.getenv("DANTIST_BASE_URL_INTERNAL", "http://backend:8000/api")
cfg["dantist_iframe_origin"] = os.getenv("FRONTEND_PUBLIC_ORIGIN") or f"{proto}://{host}"
cfg["server_script_enabled"] = True
cfg["dantist_env"] = os.getenv("APP_ENV","prod")  # маркер окружения

devmode = os.getenv("DEVELOPER_MODE")
if devmode is not None:
    cfg["developer_mode"] = 1 if str(devmode).strip().lower() in {"1","true","yes","on"} else 0

log_level = os.getenv("LOG_LEVEL")
if log_level: cfg["log_level"] = log_level

enc = os.getenv("ENCRYPTION_KEY")
if enc and cfg.get("encryption_key") != enc:
    cfg["encryption_key"] = enc

write(p, cfg)
print(f"OK {p}")
PY
ok "site_config.json обновлён"
quick_diag

# ===== 5) самолечение ядра при необходимости =====
if ! core_tables_ok; then
  step "🩺 Самолечение ядра (reinstall)"
  [[ -n "${FRAPPE_DB_ROOT_PASSWORD:-}" ]] || fatal "Нужен FRAPPE_DB_ROOT_PASSWORD для reinstall"
  site_cmd reinstall --yes \
    --mariadb-root-username root \
    --mariadb-root-password "${FRAPPE_DB_ROOT_PASSWORD}"
fi
core_tables_ok && ok "Ядро сайта валидно (tabDefaultValue найдено)" || fatal "После reinstall базовые таблицы отсутствуют"

# ===== 6) регистрация приложений в apps.txt =====
step "🗂️ Регистрация приложений в sites/apps.txt"
ensure_apps_txt_has frappe
for app in ${APP_LIST}; do ensure_app_present_and_registered "$app"; done

# ===== 7) migrate ядра =====
step "📦 Migrate ядра"
site_cmd migrate || true

# ===== 8) (опционально) отключаем проблемную фикстуру has_role.json =====
if [[ "$DISABLE_FIXTURE_HAS_ROLE" == "1" && -f "apps/dantist_app/dantist_app/fixtures/has_role.json" ]]; then
  step "🩹 Временно отключаю fixtures/has_role.json (DISABLE_FIXTURE_HAS_ROLE=1)"
  mv apps/dantist_app/dantist_app/fixtures/has_role.json apps/dantist_app/dantist_app/fixtures/has_role.json.disabled || true
fi

# ===== 9) установка приложений (без падения скрипта) =====
step "🧩 Установка приложений: ${APP_LIST}"
for app in ${APP_LIST}; do
  if ! site_cmd list-apps 2>/dev/null | grep -Fqx "$app"; then
    say "• install-app $app"
    site_cmd install-app "$app" \
      && ok "установлен $app" \
      || { warn "install-app $app не прошёл (смотри стек выше). Продолжаю bootstrap, сайт не трогаю."; }
  else
    say "• $app уже установлен"
  fi
done

# ===== 10) финальная migrate + sync fixtures корректным способом =====
step "🔁 Финальная migrate"
site_cmd migrate || true

step "📥 Синхронизация фикстур через frappe.utils.fixtures.sync_fixtures"
site_cmd execute "frappe.utils.fixtures.sync_fixtures" \
  && ok "фикстуры синхронизированы" \
  || warn "sync_fixtures вернул ненулевой код (см. лог выше)"

# ===== 11) build ассетов (ОБЯЗАТЕЛЬНО сборка frappe) =====
step "🧱 Сборка ассетов"
if ! bench build --apps "frappe ${APP_LIST}"; then
  warn "scoped build вернул ошибку — пробую полную сборку"
  bench build || warn "bench build с предупреждением"
fi

# sanity-check ключевого бандла → форсированный rebuild при необходимости
if ! ls /workspace/sites/assets/frappe/dist/js/frappe-web.bundle*.js >/dev/null 2>&1; then
  warn "frappe-web.bundle не найден, форсирую rebuild"
  bench build --force || true
fi

chmod -R a+rX /workspace/sites/assets || true

# ===== 12) проверка Administrator через SQL =====
step "🔐 Проверка пользователя Administrator"
read -r DB_NAME DB_PASS _junk _envmark < <(read_db_creds || echo "    ")
if [[ -n "${DB_NAME:-}" && -n "${DB_PASS:-}" ]]; then
  if mysql -h "$DB_HOST" -P "$DB_PORT" -u"$DB_NAME" -p"$DB_PASS" "$DB_NAME" -Nse "SELECT 1 FROM tabUser WHERE name='Administrator' LIMIT 1;" 2>/dev/null | grep -q 1; then
    ok "Администратор найден"
  else
    warn "Administrator не найден"
  fi
else
  warn "Не удалось прочитать креды БД сайта для проверки Administrator"
fi

# ===== 13) Procfile (динамически, без redis_*) =====
step "🗂️  Procfile генерация"
PROCFILE_PATH="/workspace/Procfile"

write_procfile_container() {
cat > "$PROCFILE_PATH" <<PROC
web: cd /workspace && $BENCH_BIN serve --port $WEB_PORT
socketio: cd /workspace && $SOCKETIO_NODE_BIN apps/frappe/socketio.js
schedule: cd /workspace && $BENCH_BIN schedule
worker: cd /workspace && $BENCH_BIN worker
PROC
}

write_procfile_local() {
cat > "$PROCFILE_PATH" <<PROC
web: $BENCH_BIN serve --port $WEB_PORT
socketio: $SOCKETIO_NODE_BIN apps/frappe/socketio.js
watch: $BENCH_BIN watch
schedule: $BENCH_BIN schedule
worker: OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES NO_PROXY=* $BENCH_BIN worker 1>> logs/worker.log 2>> logs/worker.error.log
PROC
}

if [[ "$PROCFILE_MODE" == "local" ]]; then
  write_procfile_local
else
  write_procfile_container
fi
ok "Procfile готов ($PROCFILE_MODE)"

# ===== 14) сводка и запуск =====
step "📋 Финальная сводка"
site_cmd list-apps | sed 's/^/• /' || true
say "assets: $(du -sh /workspace/sites/assets 2>/dev/null | awk '{print $1}')"
ok "Bootstrap завершён. Запускаю процессы…"

exec bench start