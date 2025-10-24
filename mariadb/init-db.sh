#!/usr/bin/env bash
set -euo pipefail
# Однократно при первичном старте пустого volume.
# Разрешаем root@'%' с паролем из MARIADB_ROOT_PASSWORD.

echo "[init] enabling root@'%' for remote containers..."

if [ -z "${MARIADB_ROOT_PASSWORD:-}" ]; then
  echo "[init] MARIADB_ROOT_PASSWORD is empty, skip."
  exit 0
fi

cat >/tmp/init_remote_root.sql <<SQL
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '${MARIADB_ROOT_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SQL

# Во время первичной инициализации доступ по socket уже есть
if mysql --protocol=socket -uroot -p"${MARIADB_ROOT_PASSWORD}" < /tmp/init_remote_root.sql; then
  echo "[init] root@'%' is ready."
else
  echo "[init] WARN: couldn't apply remote root grants (maybe not first run)."
fi

rm -f /tmp/init_remote_root.sql || true