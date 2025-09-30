#!/usr/bin/env bash
set -euo pipefail

# ========== CONFIG (правь тут, либо через ENV/флаги) ==========
PROJECT_NAME="${PROJECT_NAME:-Dantist}"
BRANCH="${BRANCH:-dantist}"

FORK_FRAPPE_URL="${FORK_FRAPPE_URL:-https://github.com/OpenedClosed/frappe.git}"
FORK_ERP_URL="${FORK_ERP_URL:-https://github.com/OpenedClosed/erpnext.git}"
UPSTREAM_FRAPPE_URL="${UPSTREAM_FRAPPE_URL:-https://github.com/frappe/frappe.git}"
UPSTREAM_ERP_URL="${UPSTREAM_ERP_URL:-https://github.com/frappe/erpnext.git}"

SUB_FRAPPE_PATH="${SUB_FRAPPE_PATH:-frappe_gui/apps/frappe}"
SUB_ERP_PATH="${SUB_ERP_PATH:-frappe_gui/apps/erpnext}"

# bench по умолчанию внутри репо
BENCH_DIR_REL_DEFAULT="${BENCH_DIR_REL:-frappe_gui}"

SITE_NAME="${SITE_NAME:-dantist.localhost}"
DB_NAME="${DB_NAME:-dantist_db}"
APP_NAME="${APP_NAME:-dantist_app}"

ROOT_USER="${ROOT_USER:-root}"
ROOT_PWD="${MARIADB_ROOT_PWD:-}"     # передай через ENV, чтобы не спрашивало

# ========== LOG/UTIL ==========
log()  { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m[DONE]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[ERR ]\033[0m %s\n" "$*" >&2; }

run() { log "run: $*"; bash -lc "$*"; }
need(){ command -v "$1" >/dev/null 2>&1 || { err "missing dependency: $1"; exit 1; }; }
changed(){ git -C "$REPO_ROOT" status --porcelain | grep -q . || return 1; }

usage(){
cat <<EOF
Usage: $(basename "$0") [MODE] [OPTIONS]

MODES (одно; по умолчанию --both)
  --only-submodules           только настройка сабмодулей (frappe/erpnext)
  --only-bench                только bench/site/app (без сабмодулей)
  --both                      и сабмодули, и bench (ПО УМОЛЧАНИЮ)
  --init-bench                создать НОВЫЙ bench в --bench-dir и всё настроить

BENCH OPTIONS
  --bench-dir PATH            путь к bench (существующему или новому), default: ./frappe_gui
  --clean-site                drop-site + new-site (нужен пароль root MariaDB)
  --create-site               создать сайт, если его нет (по умолчанию ВКЛ)
  --no-create-site            не создавать сайт
  --site NAME                 имя сайта (default: $SITE_NAME)
  --db-name NAME              имя БД (default: $DB_NAME)
  --app NAME                  имя кастом-приложения (default: $APP_NAME)

SUBMODULES OPTIONS
  --frappe-url URL            URL форка frappe
  --erpnext-url URL           URL форка erpnext
  --branch NAME               ветка форков (default: $BRANCH)

AUTH (ENV)
  MARIADB_ROOT_PWD            пароль root для MariaDB (или спросим интерактивно)

Примеры:
  # Настроить сабмодули и существующий bench в ./frappe_gui (обычно то, что нужно)
  MARIADB_ROOT_PWD=pass ./start.sh --both

  # Только сабмодули
  ./start.sh --only-submodules

  # Только bench (если сабмодули уже ок)
  MARIADB_ROOT_PWD=pass ./start.sh --only-bench --bench-dir ./frappe_gui

  # Полностью новый bench
  MARIADB_ROOT_PWD=pass ./start.sh --init-bench --bench-dir ./new-bench
EOF
}

# ========== parse args ==========
MODE="both"           # subs / bench / both / init-bench
CLEAN_SITE=0
CREATE_SITE=1
BENCH_DIR_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --only-submodules) MODE="subs" ;;
    --only-bench)      MODE="bench" ;;
    --both)            MODE="both" ;;
    --init-bench)      MODE="init-bench" ;;
    --bench-dir)       BENCH_DIR_ARG="$2"; shift ;;
    --clean-site)      CLEAN_SITE=1 ;;
    --create-site)     CREATE_SITE=1 ;;
    --no-create-site)  CREATE_SITE=0 ;;
    --site)            SITE_NAME="$2"; shift ;;
    --db-name)         DB_NAME="$2"; shift ;;
    --app)             APP_NAME="$2"; shift ;;
    --frappe-url)      FORK_FRAPPE_URL="$2"; shift ;;
    --erpnext-url)     FORK_ERP_URL="$2"; shift ;;
    --branch)          BRANCH="$2"; shift ;;
    -h|--help)         usage; exit 0 ;;
    *) err "Unknown arg: $1"; usage; exit 1 ;;
  esac
  shift
done

# ========== env checks ==========
need git
need bench
need mysql
need jq
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$REPO_ROOT" ] || { err "Run inside a git repository ($PROJECT_NAME root)."; exit 1; }
run "git config --global pull.rebase false"
run "git config --global submodule.recurse true"

# ========== SUBMODULE HELPERS ==========
is_registered_submodule(){
  local path="$1"
  if git -C "$REPO_ROOT" config -f .gitmodules --get-regexp "^submodule\..*\.path$" 2>/dev/null | awk '{print $2}' | grep -Fxq "$path"; then
    return 0
  fi
  if git -C "$REPO_ROOT" rev-parse -q --verify HEAD >/dev/null 2>&1; then
    git -C "$REPO_ROOT" ls-tree -d HEAD -- "$path" 2>/dev/null | grep -q '160000' && return 0
  fi
  return 1
}

register_submodule_if_needed(){
  local path="$1" url="$2" branch="$3"
  if ! is_registered_submodule "$path"; then
    log "Registering $path as submodule @ $url#$branch"
    run "git -C \"$REPO_ROOT\" submodule add -f -b \"$branch\" \"$url\" \"$path\""
  else
    log "$path already registered as submodule."
  fi
}

ensure_submodule(){
  local path="$1" url="$2" branch="$3"
  register_submodule_if_needed "$path" "$url" "$branch"
  [ -d "$REPO_ROOT/$path" ] || { err "Submodule dir missing: $path"; exit 1; }

  run "git -C \"$REPO_ROOT/$path\" remote set-url origin \"$url\""
  run "git -C \"$REPO_ROOT/$path\" fetch origin --prune"

  if run "git -C \"$REPO_ROOT/$path\" rev-parse --verify \"$branch\" >/dev/null 2>&1"; then
    run "git -C \"$REPO_ROOT/$path\" checkout \"$branch\""
  else
    if run "git -C \"$REPO_ROOT/$path\" ls-remote --exit-code --heads origin \"$branch\" >/dev/null 2>&1"; then
      run "git -C \"$REPO_ROOT/$path\" checkout -b \"$branch\" origin/$branch"
    else
      warn "Remote branch '$branch' not found on origin. Creating it."
      run "git -C \"$REPO_ROOT/$path\" checkout -b \"$branch\""
      run "git -C \"$REPO_ROOT/$path\" push -u origin \"$branch\""
    fi
  fi
}

configure_upstream(){
  local path="$1" upstream_url="$2"
  if ! run "git -C \"$REPO_ROOT/$path\" remote | grep -qx upstream"; then
    run "git -C \"$REPO_ROOT/$path\" remote add upstream \"$upstream_url\""
  else
    run "git -C \"$REPO_ROOT/$path\" remote set-url upstream \"$upstream_url\""
  fi
  run "git -C \"$REPO_ROOT/$path\" remote set-url --push upstream DISABLED"
}

pin_gitmodules(){
  local path="$1" url="$2" branch="$3"
  run "git -C \"$REPO_ROOT\" config -f .gitmodules submodule.$path.path   \"$path\""
  run "git -C \"$REPO_ROOT\" config -f .gitmodules submodule.$path.url    \"$url\""
  run "git -C \"$REPO_ROOT\" config -f .gitmodules submodule.$path.branch \"$branch\""
}

gitignore_harden(){
  local add='
*.log
*.log.*
# Любая папка logs/ на любом уровне
**/logs/**
'
  if ! grep -q 'bench & runtime artifacts' "$REPO_ROOT/.gitignore" 2>/dev/null; then
    log "Update .gitignore with bench/logs/files patterns"
    printf "%s\n" "$add" >> "$REPO_ROOT/.gitignore"
  fi

  run "git -C \"$REPO_ROOT\" rm -r --cached dantist-bench 2>/dev/null || true"
  run "git -C \"$REPO_ROOT\" rm -r --cached frappe_gui/logs 2>/dev/null || true"
  run "git -C \"$REPO_ROOT\" rm -r --cached frappe_gui/assets 2>/dev/null || true"

  for p in "$REPO_ROOT"/frappe_gui/sites/*; do
    [ -d "$p" ] || continue
    run "git -C \"$REPO_ROOT\" rm -r --cached \"${p#$REPO_ROOT/}/logs\" 2>/dev/null || true"
    run "git -C \"$REPO_ROOT\" rm -r --cached \"${p#$REPO_ROOT/}/private/backups\" 2>/dev/null || true"
    run "git -C \"$REPO_ROOT\" rm -r --cached \"${p#$REPO_ROOT/}/private/files\" 2>/dev/null || true"
    run "git -C \"$REPO_ROOT\" rm -r --cached \"${p#$REPO_ROOT/}/public/files\" 2>/dev/null || true"
    run "git -C \"$REPO_ROOT\" rm -f --cached \"${p#$REPO_ROOT/}/site_config.json\" 2>/dev/null || true"
  done

  run "git -C \"$REPO_ROOT\" add .gitignore || true"
}

finalize_root_commit(){
  run "git -C \"$REPO_ROOT\" submodule sync --recursive"
  run "git -C \"$REPO_ROOT/$SUB_FRAPPE_PATH\" pull || true"
  run "git -C \"$REPO_ROOT/$SUB_ERP_PATH\" pull || true"
  run "git -C \"$REPO_ROOT\" add .gitmodules \"$SUB_FRAPPE_PATH\" \"$SUB_ERP_PATH\" || true"
  if changed; then
    run "git -C \"$REPO_ROOT\" commit -m \"pin: submodules to forks @ $BRANCH + gitignore hardened\" || true"
    run "git -C \"$REPO_ROOT\" push || true"
  fi
  ok "Submodules pinned and .gitignore hardened."
}

# ========== bench directory resolution ==========
resolve_bench_dir(){
  local dir=""
  if [ -n "${BENCH_DIR_ARG:-}" ]; then
    dir="$BENCH_DIR_ARG"
  else
    if [ -f "Procfile" ] && [ -d "sites" ]; then
      dir="$(pwd)"
    else
      dir="$REPO_ROOT/$BENCH_DIR_REL_DEFAULT"
    fi
  fi
  echo "$dir"
}

# ========== BENCH/SITE/APPS ==========
prompt_root_pwd(){
  [ -n "$ROOT_PWD" ] || { read -s -p "Enter MariaDB root password: " ROOT_PWD; echo; }
}

# После создания/наличия сайта — создаём дополнительного DB-пользователя '@%' с тем же паролем
ensure_wildcard_db_user(){
  local site="$1"
  local site_cfg="sites/$site/site_config.json"
  if [ ! -f "$site_cfg" ]; then
    warn "site_config.json not found at $site_cfg — skip wildcard db user."
    return 0
  fi
  local db_user db_pass
  db_user="$(jq -r .db_name "$site_cfg")"
  db_pass="$(jq -r .db_password "$site_cfg")"
  if [ -z "$db_user" ] || [ -z "$db_pass" ] || [ "$db_user" = "null" ] || [ "$db_pass" = "null" ]; then
    warn "Cannot read db_name/db_password from $site_cfg"
    return 0
  fi

  prompt_root_pwd
  log "Ensuring '${db_user}'@'%' with same password as '@localhost'..."
  run "mysql -u \"$ROOT_USER\" -p\"$ROOT_PWD\" -e \"
    CREATE USER IF NOT EXISTS '${db_user}'@'%' IDENTIFIED BY '${db_pass}';
    GRANT ALL PRIVILEGES ON \\\`${db_user}\\\`.* TO '${db_user}'@'%';
    FLUSH PRIVILEGES;
  \""
}

do_bench_existing(){
  local bench_dir="$1"
  log "=== STEP: Use existing bench at $bench_dir ==="
  [ -d "$bench_dir" ] || { err "Bench dir not found: $bench_dir"; exit 1; }
  cd "$bench_dir"

  [ -d "apps/frappe" ]  || { err "bench apps/frappe not found."; exit 1; }
  [ -d "apps/erpnext" ] || { err "bench apps/erpnext not found."; exit 1; }

  if [ "$CLEAN_SITE" -eq 1 ] && [ -d "sites/$SITE_NAME" ]; then
    warn "Dropping site $SITE_NAME"
    prompt_root_pwd
    run "bench drop-site \"$SITE_NAME\" --root-login \"$ROOT_USER\" --root-password \"$ROOT_PWD\" --force"
  fi

  if [ "$CREATE_SITE" -eq 1 ] && [ ! -d "sites/$SITE_NAME" ]; then
    prompt_root_pwd
    # ВАЖНО: создаём db_user как '@localhost' чтобы bootstrap прошёл по unix-socket
    run "bench new-site \"$SITE_NAME\" \
          --admin-password admin \
          --db-name \"$DB_NAME\" \
          --mariadb-root-username \"$ROOT_USER\" \
          --mariadb-root-password \"$ROOT_PWD\" \
          --mariadb-user-host-login-scope='localhost'"

    # После успешного создания — добавляем того же пользователя ещё и как '@%'
    ensure_wildcard_db_user "$SITE_NAME"
  else
    log "Site create step skipped (exists or --no-create-site)."
    # На всякий случай добавим/синхронизируем '@%' под текущий пароль из site_config.json
    ensure_wildcard_db_user "$SITE_NAME"
  fi

  if ! bench --site "$SITE_NAME" list-apps | grep -qx erpnext; then
    run "bench --site \"$SITE_NAME\" install-app erpnext"
  else
    log "ERPNext already installed on $SITE_NAME"
  fi

  if [ ! -d "apps/$APP_NAME" ]; then
    run "bench new-app \"$APP_NAME\" --no-git"
  else
    log "App dir exists: apps/$APP_NAME"
  fi

  if ! bench --site "$SITE_NAME" list-apps | grep -qx "$APP_NAME"; then
    run "bench --site \"$SITE_NAME\" install-app \"$APP_NAME\""
  else
    log "App '$APP_NAME' already installed on $SITE_NAME"
  fi

  run "bench set-config -g default_site \"$SITE_NAME\""
  run "bench use \"$SITE_NAME\""

  ok "Site $SITE_NAME ready in: $bench_dir"
  echo
  echo "Next:"
  echo "  cd \"$bench_dir\" && bench start"
  echo "  open http://$SITE_NAME/desk"
}

do_bench_init(){
  local bench_dir="$1"
  log "=== STEP: Init NEW bench at $bench_dir ==="
  [ -d "$bench_dir" ] && { err "Target bench dir already exists: $bench_dir"; exit 1; }

  ABS_FRAPPE_PATH="$(cd \"$REPO_ROOT/$SUB_FRAPPE_PATH\" && pwd)"
  ABS_ERP_PATH="$(cd \"$REPO_ROOT/$SUB_ERP_PATH\" && pwd)"

  run "bench init \"$bench_dir\" --frappe-path \"$ABS_FRAPPE_PATH\" --frappe-branch \"$BRANCH\""
  cd "$bench_dir"

  if [ "$CREATE_SITE" -eq 1 ]; then
    prompt_root_pwd
    run "bench new-site \"$SITE_NAME\" \
          --admin-password admin \
          --db-name \"$DB_NAME\" \
          --mariadb-root-username \"$ROOT_USER\" \
          --mariadb-root-password \"$ROOT_PWD\" \
          --mariadb-user-host-login-scope='localhost'"
    ensure_wildcard_db_user "$SITE_NAME"
  fi

  run "bench get-app erpnext \"$ABS_ERP_PATH\" --branch \"$BRANCH\""
  [ "$CREATE_SITE" -eq 1 ] && run "bench --site \"$SITE_NAME\" install-app erpnext"

  run "bench new-app \"$APP_NAME\" --no-git"
  if [ "$CREATE_SITE" -eq 1 ]; then
    run "bench --site \"$SITE_NAME\" install-app \"$APP_NAME\""
    run "bench set-config -g default_site \"$SITE_NAME\""
    run "bench use \"$SITE_NAME\""
  fi

  ok "New bench ready: $bench_dir"
  echo
  echo "Next:"
  echo "  cd \"$bench_dir\" && bench start"
  [ "$CREATE_SITE" -eq 1 ] && echo "  open http://$SITE_NAME/desk"
}

# ========== DRIVER ==========
do_submodules(){
  log "=== STEP: Submodules setup ==="
  ensure_submodule "$SUB_FRAPPE_PATH" "$FORK_FRAPPE_URL" "$BRANCH"
  ensure_submodule "$SUB_ERP_PATH"    "$FORK_ERP_URL"    "$BRANCH"
  configure_upstream "$SUB_FRAPPE_PATH" "$UPSTREAM_FRAPPE_URL"
  configure_upstream "$SUB_ERP_PATH"    "$UPSTREAM_ERP_URL"
  pin_gitmodules "$SUB_FRAPPE_PATH" "$FORK_FRAPPE_URL" "$BRANCH"
  pin_gitmodules "$SUB_ERP_PATH"    "$FORK_ERP_URL"    "$BRANCH"
  gitignore_harden
  finalize_root_commit
}

case "$MODE" in
  subs)
    do_submodules
    ;;
  bench)
    BENCH_DIR="$(resolve_bench_dir)"
    do_bench_existing "$BENCH_DIR"
    ;;
  both)
    do_submodules
    BENCH_DIR="$(resolve_bench_dir)"
    do_bench_existing "$BENCH_DIR"
    ;;
  init-bench)
    do_submodules
    [ -n "${BENCH_DIR_ARG:-}" ] || { err "Provide --bench-dir PATH for --init-bench"; exit 1; }
    do_bench_init "$BENCH_DIR_ARG"
    ;;
  *)
    err "Unknown MODE"; usage; exit 1;;
esac
