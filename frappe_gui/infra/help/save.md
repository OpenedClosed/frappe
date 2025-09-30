# Что нужно сохранить

* **Код apps** (все репозитории + ветки/коммиты) и **fixtures**.
* **БД** сайта (dump).
* **Файлы**: `public/files` и `private/files`.
* **Конфиги**: `sites/<site>/site_config.json` (обязательно `encryption_key`) и `sites/common_site_config.json`.
* Снимок версий: `bench version`.

---

# Перед бэкапом (заморозить состояние)

```bash
SITE=dantist.localhost

bench --site $SITE migrate
bench version
```

**Экспорт кастомизаций в fixtures** (чтобы всё было в гите):

* В `apps/<app>/<app>/hooks.py` добавь (один раз и навсегда):

  ```python
  fixtures = [
      "Custom Field", "Property Setter",
      "Client Script", "Server Script",
      "Workspace", "Role", "Role Permission",
      "Website Settings"
  ]
  ```
* Затем:

  ```bash
  bench --site $SITE export-fixtures
  git add apps/*/fixtures/*.json
  git commit -m "fixtures: snapshot"
  ```

---

# Полный бэкап (БД + файлы + конфиги)

```bash
SITE=dantist.localhost
BACKUP_DIR=/tmp/frappe_backups/$(date +%F_%H-%M)
mkdir -p "$BACKUP_DIR"

bench --site $SITE backup --with-files --backup-path "$BACKUP_DIR"
cp "sites/$SITE/site_config.json"        "$BACKUP_DIR/"
cp "sites/common_site_config.json"       "$BACKUP_DIR/"
bench version > "$BACKUP_DIR/versions.txt"
```

В папке появятся:

* `…-database.sql.gz`
* `…-files.tar` (public)
* `…-private-files.tar` (private)
* `site_config.json`, `common_site_config.json`, `versions.txt`

> `encryption_key` берём из `site_config.json` — без него пароли/токены не расшифруются.

(Опционально — архив дерева сайта без мусора)

```bash
tar --exclude='locks' --exclude='logs' --exclude='assets' \
    -czf "$BACKUP_DIR/site_tree.tgz" "sites/$SITE"
```

---

# Восстановление «как на проде»

## 1) Поднять bench с теми же версиями

```bash
bench init frappe-bench --frappe-branch version-15
cd frappe-bench
bench get-app --branch version-15 frappe
# bench get-app --branch version-15 erpnext     # если нужен
bench get-app https://your.git/task_tracker.git # твой app с fixtures
```

## 2) Создать сайт и вернуть старый ключ шифрования

```bash
SITE=dantist.localhost
BACKUP_DIR=/path/to/backup_folder

bench new-site $SITE            # задай пароли
bench --site $SITE set-config encryption_key "<значение из $BACKUP_DIR/site_config.json>"
```

## 3) Восстановить БД и файлы

```bash
bench --site $SITE restore \
  "$BACKUP_DIR/XXXX-database.sql.gz" \
  --with-public-files  "$BACKUP_DIR/XXXX-files.tar" \
  --with-private-files "$BACKUP_DIR/XXXX-private-files.tar"
```

> Если ругается на отсутствующие приложения — сначала `bench get-app …` для всех apps из твоего проекта.

## 4) Доустановить app на сайт (если потребуется) и собрать ассеты

```bash
bench --site $SITE install-app task_tracker   # и остальные при необходимости
bench --site $SITE migrate
bench build
bench clear-cache && bench clear-website-cache
```

(Прод) включить прод-режим:

```bash
sudo bench setup production $(whoami)
bench restart
```

---

# Быстрая самопроверка после restore

```bash
bench --site $SITE doctor
bench version
# Зайти админом: проверить Workspaces, Custom Fields, страницы /about и /pricing,
# загрузки в /files/, Telegram-настройки, планировщик (Scheduled Jobs).
```

---

## Мини-скрипты (по желанию)

**backup\_full.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail
SITE=${1:-dantist.localhost}
STAMP=$(date +%F_%H-%M)
OUT=/tmp/frappe_backups/$STAMP
mkdir -p "$OUT"

bench --site $SITE migrate
bench --site $SITE export-fixtures || true
bench --site $SITE backup --with-files --backup-path "$OUT"
cp "sites/$SITE/site_config.json"  "$OUT/"
cp "sites/common_site_config.json" "$OUT/"
bench version > "$OUT/versions.txt"
echo "Backup done: $OUT"
```

**restore\_full.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail
SITE=${1:-dantist.localhost}
DIR=${2:?Backup folder required}

bench new-site $SITE
ENC=$(python - <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))["encryption_key"])
PY
"$DIR/site_config.json")
bench --site $SITE set-config encryption_key "$ENC"

DB=$(ls "$DIR"/*-database.sql.gz)
PUB=$(ls "$DIR"/*-files.tar)
PRI=$(ls "$DIR"/*-private-files.tar)

bench --site $SITE restore "$DB" --with-public-files "$PUB" --with-private-files "$PRI"
bench --site $SITE migrate
bench build
bench clear-cache && bench clear-website-cache
echo "Restore done for $SITE"
```
