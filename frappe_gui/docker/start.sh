#!/usr/bin/env bash
# Ultra-verbose bootstrap for Frappe in Docker (prod-first, idempotent)
# Создаёт сайт на проде, лечит ядро, ставит app, тянет фикстуры, билдит ассеты.
# Пишет подробные логи с эмодзи на каждом шаге.

set -Eeuo pipefail

# ===== pretty logs =====
ts() { date +'%F %T'; }
say()   { echo -e "[$(ts)] $*"; }
ok()    { say "✅ $*"; }
warn()  { say "⚠️  $*" >&2; }
err()   { say "❌ $*" >&2; }
step()  { echo -e "\n[$(ts)] ── $*"; }
fatal() { err "$*"; exit 1; }

mask() {
  local s="${1:-}"; local n=${#s}
  if (( n == 0 )); then echo ""; elif (( n <= 6 )); then echo "***"; else echo "${s:0:2}***${s: -2}"; fi
}

# ===== env & paths =====
export PATH="/opt/bench-env/bin:$PATH"
export BENCH_DIR="/workspace"
cd "$BENCH_DIR"

mkdir -p "$BENCH_DIR/apps" "$BENCH_DIR/sites" "$BENCH_DIR/logs"

SITE="${SITE_NAME:-dantist.localhost}"
SITE_DIR="$BENCH_DIR/sites/${SITE}"
SITE_CFG="${SITE_DIR}/site_config.json"
COMMON_CFG="$BENCH_DIR/sites/common_site_config.json"

DB_HOST="${DB_HOST:-mariadb}"
DB_PORT="${DB_PORT:-3306}"
DB_WAIT="${DB_WAIT_SECONDS:-90}"

HOST="${HOST:-localhost}"
PROTO=$([[ "$HOST" == "localhost" || "$HOST" == "127.0.0.1" ]] && echo http || echo https)

FRAPPE_DB_ROOT_PASSWORD="${FRAPPE_DB_ROOT_PASSWORD:-${DB_ROOT_PASSWORD:-}}"
FRAPPE_ADMIN_PASSWORD="${FRAPPE_ADMIN_PASSWORD:-${ADMIN_PASSWORD:-}}"

APP_LIST="${FRAPPE_INSTALL_APPS:-dantist_app}"   # можно через ENV перечислить через пробел

PRUNE_SEEDED_SITE="${PRUNE_SEEDED_SITE:-1}"      # 1 = агрессивно лечим/вырезаем локальный «зашитый» сайт
APP_ENV="${APP_ENV:-prod}"

# mysql client w/o SSL (бывает HY000/2026 в докере)
printf "[client]\nssl=0\nprotocol=tcp\n" > /root/.my.cnf

bench()    { (cd "$BENCH_DIR" && command bench "$@"); }
site_cmd() { (cd "$BENCH_DIR" && command bench --site "$SITE" "$@"); }

read_db_creds() {
  python3 - "$SITE_CFG" <<'PY'
import json,sys
p=sys.argv[1]
try:
  d=json.loads(open(p).read())
except:
  d={}
print(d.get("db_name","")); print(d.get("db_password","")); print(d.get("db_host",""))
PY
}

core_tables_ok() {
  [[ -f "$SITE_CFG" ]] || return 1
  read -r DB_NAME DB_PASS DBH < <(read_db_creds || echo "  ")
  [[ -z "${DB_NAME:-}" || -z "${DB_PASS:-}" ]] && return 1
  mysql -h "${DBH:-$DB_HOST}" -P "$DB_PORT" -u"$DB_NAME" -p"$DB_PASS" "$DB_NAME" \
    -Nse "SHOW TABLES LIKE 'tabDefaultValue';" >/dev/null 2>&1
}

db_exists() {
  local name="$1"
  mysql -h "$DB_HOST" -P "$DB_PORT" -uroot -p"$FRAPPE_DB_ROOT_PASSWORD" \
    -Nse "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='${name}';" 2>/dev/null | grep -Fxq "$name"
}

quick_diag() {
  step "🧪 Диагностика"
  if [[ -f "$SITE_CFG" ]]; then
    read -r DB_NAME DB_PASS DBH < <(read_db_creds || echo "  ")
    say "• site: $SITE"
    say "• db_name: ${DB_NAME:-<none>}  db_pass: $(mask "${DB_PASS:-}")  db_host: ${DBH:-<unset>}"
    say "• MariaDB ping (${DB_HOST}:${DB_PORT})…"
    (echo > /dev/tcp/${DB_HOST}/${DB_PORT}) >/dev/null 2>&1 && ok "ping ok" || warn "нет TCP-подключения"
    if [[ -n "${DB_NAME:-}" ]]; then
      local any=$(mysql -h "${DBH:-$DB_HOST}" -P "$DB_PORT" -u"$DB_NAME" -p"$DB_PASS" "$DB_NAME" -Nse "SHOW TABLES LIMIT 1;" 2>/dev/null || true)
      if [[ -n "$any" ]]; then ok "таблицы доступны (показана 1-я есть)"; else warn "таблицы не прочитались этим пользователем"; fi
    fi
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

# пробуем root доступ (не фатально — просто лог)
mysql -h "$DB_HOST" -P "$DB_PORT" -uroot -p"$FRAPPE_DB_ROOT_PASSWORD" -e "SELECT VERSION() AS version;" >/dev/null 2>&1 \
  && ok "root-доступ к MariaDB подтверждён" \
  || warn "root-доступ не проверился (продолжим, но new-site потребует root пароль)"

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
})
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print(f"OK {p}")
PY
ok "common_site_config.json записан"

mkdir -p "$SITE_DIR" || true

# ===== 2) если «локальный» сайт зашит в образе — вырежем (один раз) =====
step "🧹 Проверка на «локальный/зашитый» сайт и конфликты"
LOCAL_WAS_REMOVED=0
if [[ -f "$SITE_CFG" ]]; then
  read -r CUR_DB CUR_PASS CUR_DBHOST < <(read_db_creds || echo "  ")
  if [[ "$PRUNE_SEEDED_SITE" == "1" ]]; then
    # критерии локального мусора: db_host пустой/localhost/127.*, или DB не существует на проде, или нет базовых таблиц
    BAD_DH=0
    [[ -z "${CUR_DBHOST:-}" || "$CUR_DBHOST" == "localhost" || "$CUR_DBHOST" == "127.0.0.1" ]] && BAD_DH=1
    if (( BAD_DH == 1 )) || ! db_exists "${CUR_DB:-_NO_}" || ! core_tables_ok; then
      warn "Обнаружен подозрительный сайт (${SITE}) → удаляю для чистого прод-развёртывания"
      # Чистое удаление: если база существует — прибьём её корректно
      if [[ -n "${CUR_DB:-}" ]] && db_exists "${CUR_DB}"; then
        say "• drop-site --force"
        bench drop-site "$SITE" --force || true
      fi
      rm -rf "$SITE_DIR"
      LOCAL_WAS_REMOVED=1
      ok "Локальный остаток удалён"
    else
      ok "Существующий сайт выглядит валидным"
    fi
  else
    say "PRUNE_SEEDED_SITE=0 → пропускаю агрессивную чистку"
  fi
else
  say "site_config.json не найден — ничего чистить"
fi

# ===== 3) создаём сайт, если нет =====
if [[ ! -f "$SITE_CFG" ]]; then
  step "🏗️  Создание нового сайта: ${SITE}"
  [[ -n "${FRAPPE_DB_ROOT_PASSWORD:-}" ]] || fatal "Нужен FRAPPE_DB_ROOT_PASSWORD/DB_ROOT_PASSWORD"
  [[ -n "${FRAPPE_ADMIN_PASSWORD:-}"   ]] || fatal "Нужен FRAPPE_ADMIN_PASSWORD/ADMIN_PASSWORD"
  bench new-site "${SITE}" \
    --no-mariadb-socket \
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

# ===== 4) патчим site_config из ENV (каждый старт) =====
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

# ===== 5) самолечение ядра, если нужно =====
if ! core_tables_ok; then
  step "🩺 Самолечение ядра (reinstall)"
  [[ -n "${FRAPPE_DB_ROOT_PASSWORD:-}" ]] || fatal "Нужен FRAPPE_DB_ROOT_PASSWORD для reinstall"
  site_cmd reinstall --yes
fi

# повторная проверка
core_tables_ok && ok "Ядро сайта валидно (tabDefaultValue найдено)" || fatal "После reinstall базовые таблицы отсутствуют"

# ===== 6) миграции ядра =====
step "📦 Migrate ядра"
site_cmd migrate || true

# ===== 7) установка твоих приложений (безопасно к повтору) =====
step "🧩 Установка приложений: ${APP_LIST}"
for app in ${APP_LIST}; do
  if ! site_cmd list-apps 2>/dev/null | grep -Fqx "$app"; then
    say "• install-app $app"
    if ! site_cmd install-app "$app"; then
      warn "install-app $app не прошёл → пробую migrate и повтор"
      site_cmd migrate || true
      site_cmd install-app "$app"
    fi
  else
    say "• $app уже установлен"
  fi
done

# ===== 8) финальные миграции + фикстуры =====
step "🔁 Финальная migrate"
site_cmd migrate

step "📥 Импорт фикстур"
site_cmd import-fixtures || warn "import-fixtures вернул ненулевой код (продолжаю)"

# ===== 9) build ассетов (prod) =====
step "🧱 Сборка ассетов"
bench build --apps ${APP_LIST} || bench build || warn "bench build с предупреждением"
chmod -R a+rX /workspace/sites/assets || true

# ===== 10) быстрая проверка входа администратора (не раскроем пароль) =====
step "🔐 Проверка, что пользователь Administrator существует"
site_cmd execute "frappe.db.exists" --kwargs "{'doctype':'User','name':'Administrator'}" \
  && ok "Администратор в БД найден" \
  || warn "Не обнаружен Administrator? Проверь миграции/логи"

# ===== 11) финальная сводка =====
step "📋 Финальная сводка"
site_cmd list-apps | sed 's/^/• /'
say "assets: $(du -sh /workspace/sites/assets 2>/dev/null | awk '{print $1}')"
ok "Bootstrap завершён. Передаю управление основному процессу…"

# ===== 12) запуск процессов =====
if [[ -f /workspace/Procfile ]]; then
  say "Procfile найден — оставляю как есть"
else
  cat > /workspace/Procfile <<'PROC'
web: cd /workspace && bench serve --port 8001
socketio: cd /workspace && node apps/frappe/socketio.js
schedule: cd /workspace && bench schedule
worker: cd /workspace && bench worker
PROC
fi

exec bench start