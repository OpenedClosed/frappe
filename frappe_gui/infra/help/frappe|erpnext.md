# 0) ПРЕФЛАЙТ (для ОБОИХ сабмодулей)

```bash
# ты в корне главного репо
git rev-parse --show-toplevel

# (опц.) удобнее жить:
git config --global pull.rebase false
git config --global submodule.recurse true
```

---

# 1) ЕДИНОРАЗОВАЯ НАСТРОЙКА: форки @ ветка `dantist` (для ОБОИХ)

```bash
# ERPNext → твой форк; upstream = официал; push в upstream запрещён
git -C frappe_gui/apps/erpnext remote set-url origin https://github.com/OpenedClosed/erpnext.git
if ! git -C frappe_gui/apps/erpnext remote | grep -qx upstream; then
  git -C frappe_gui/apps/erpnext remote add upstream https://github.com/frappe/erpnext.git
else
  git -C frappe_gui/apps/erpnext remote set-url upstream https://github.com/frappe/erpnext.git
fi
git -C frappe_gui/apps/erpnext remote set-url --push upstream DISABLED
git -C frappe_gui/apps/erpnext checkout -B dantist
git -C frappe_gui/apps/erpnext push -u origin dantist

# Frappe → твой форк; upstream = официал; push в upstream запрещён
git -C frappe_gui/apps/frappe remote set-url origin https://github.com/OpenedClosed/frappe.git
if ! git -C frappe_gui/apps/frappe remote | grep -qx upstream; then
  git -C frappe_gui/apps/frappe remote add upstream https://github.com/frappe/frappe.git
else
  git -C frappe_gui/apps/frappe remote set-url upstream https://github.com/frappe/frappe.git
fi
git -C frappe_gui/apps/frappe remote set-url --push upstream DISABLED
git -C frappe_gui/apps/frappe checkout -B dantist
git -C frappe_gui/apps/frappe push -u origin dantist
```

**Прописать `.gitmodules` в ГЛАВНОМ репо → форки @ `dantist`:**

```bash
git config -f .gitmodules submodule.frappe_gui/apps/erpnext.path   frappe_gui/apps/erpnext
git config -f .gitmodules submodule.frappe_gui/apps/erpnext.url    https://github.com/OpenedClosed/erpnext.git
git config -f .gitmodules submodule.frappe_gui/apps/erpnext.branch dantist

git config -f .gitmodules submodule.frappe_gui/apps/frappe.path    frappe_gui/apps/frappe
git config -f .gitmodules submodule.frappe_gui/apps/frappe.url     https://github.com/OpenedClosed/frappe.git
git config -f .gitmodules submodule.frappe_gui/apps/frappe.branch  dantist

git submodule sync -- frappe_gui/apps/erpnext frappe_gui/apps/frappe
git -C frappe_gui/apps/erpnext pull
git -C frappe_gui/apps/frappe  pull

git add .gitmodules frappe_gui/apps/erpnext frappe_gui/apps/frappe
git commit -m "Point submodules to OpenedClosed/{erpnext,frappe}@dantist"
git push
```

**Быстрая проверка:**

```bash
cat .gitmodules
git -C frappe_gui/apps/erpnext rev-parse --abbrev-ref --symbolic-full-name @{u}   # origin/dantist
git -C frappe_gui/apps/frappe  rev-parse --abbrev-ref --symbolic-full-name @{u}   # origin/dantist
git -C frappe_gui/apps/erpnext remote -v
git -C frappe_gui/apps/frappe  remote -v
```

---

# 2) РАБОЧИЙ ЦИКЛ

## A) Меняю core и «поднимаю пины» в главном

```bash
# ERPNext
git -C frappe_gui/apps/erpnext add -A
git -C frappe_gui/apps/erpnext commit -m "Change"
git -C frappe_gui/apps/erpnext push

# Frappe
git -C frappe_gui/apps/frappe add -A
git -C frappe_gui/apps/frappe commit -m "Change"
git -C frappe_gui/apps/frappe push

# Обновляю пины (SHA сабмодулей) в Dantist
git add frappe_gui/apps/erpnext frappe_gui/apps/frappe
git commit -m "Bump submodules"
git push
```

## B) Подтянуть **последние коммиты моих веток `dantist`** (если нужно)

```bash
git submodule update --remote --recursive
git add frappe_gui/apps/erpnext frappe_gui/apps/frappe
git commit -m "Bump submodules to latest dantist"
git push
```

## C) Взять **официальные апдейты** (только вручную)

```bash
# ERPNext
git -C frappe_gui/apps/erpnext fetch upstream
git -C frappe_gui/apps/erpnext merge upstream/version-15    # или rebase
git -C frappe_gui/apps/erpnext push origin dantist
git add frappe_gui/apps/erpnext && git commit -m "Merge upstream into ERPNext@dantist" && git push

# Frappe
git -C frappe_gui/apps/frappe fetch upstream
git -C frappe_gui/apps/frappe merge upstream/version-15
git -C frappe_gui/apps/frappe push origin dantist
git add frappe_gui/apps/frappe && git commit -m "Merge upstream into Frappe@dantist" && git push
```

> Апстрим **сам по себе ничего не перезапишет**. Только когда ты явно делаешь merge/rebase из `upstream`.

---

# 3) ПРОД (сервер)

**Первый деплой**

```bash
git clone https://github.com/OpenedClosed/Dantist.git
cd Dantist
git submodule update --init --recursive   # подтянет пиннутые SHA из форков
```

**Обычное обновление (стабильно по пинам)**

```bash
git pull
git submodule update --init --recursive
```

**Осознанно взять последние коммиты `dantist` на проде (редко)**

```bash
git submodule update --remote --recursive
# лучше так делать локально → запинить в Dantist → обычное обновление на проде
```

---

# 4) КНОПКА СБРОСА (чистка «лишних настроек» и переинициализация)

Полностью удалить текущие сабмодули и завести заново на свои форки/ветки. Запускай из корня `Dantist`.

```bash
# === Удалить старые сабмодули И следы в .git ===
git submodule deinit -f frappe_gui/apps/erpnext 2>/dev/null || true
git rm -f frappe_gui/apps/erpnext                2>/dev/null || true
rm -rf .git/modules/frappe_gui/apps/erpnext      2>/dev/null || true
git config -f .gitmodules --remove-section submodule.frappe_gui/apps/erpnext 2>/dev/null || true

git submodule deinit -f frappe_gui/apps/frappe   2>/dev/null || true
git rm -f frappe_gui/apps/frappe                 2>/dev/null || true
rm -rf .git/modules/frappe_gui/apps/frappe       2>/dev/null || true
git config -f .gitmodules --remove-section submodule.frappe_gui/apps/frappe  2>/dev/null || true

git add -A
git commit -m "Remove submodules (cleanup)" || true

# === Добавить заново как сабмодули на свои форки/ветки ===
git submodule add -b dantist https://github.com/OpenedClosed/erpnext.git frappe_gui/apps/erpnext
git submodule add -b dantist https://github.com/OpenedClosed/frappe.git  frappe_gui/apps/frappe
git commit -m "Add submodules to forks @ dantist"

# === Внутри сабмодулей добавить upstream и запретить push в него ===
git -C frappe_gui/apps/erpnext remote add upstream https://github.com/frappe/erpnext.git 2>/dev/null || true
git -C frappe_gui/apps/erpnext remote set-url --push upstream DISABLED

git -C frappe_gui/apps/frappe  remote add upstream https://github.com/frappe/frappe.git  2>/dev/null || true
git -C frappe_gui/apps/frappe  remote set-url --push upstream DISABLED

git push
```

---

# 5) ШАБЛОН ДЛЯ ДРУГИХ ПРОЕКТОВ (своё имя ветки/форка)

Подставь:

* `<PATH>`: путь сабмодуля (напр. `apps/erpnext`)
* `<FORK_URL>`: URL твоего форка
* `<UPSTREAM_URL>`: URL оригинала
* `<BRANCH>`: твоя ветка (напр. `myproj-branch`)

```bash
# remotes + ветка
git -C <PATH> remote set-url origin   <FORK_URL>
if ! git -C <PATH> remote | grep -qx upstream; then
  git -C <PATH> remote add upstream <UPSTREAM_URL>
else
  git -C <PATH> remote set-url upstream <UPSTREAM_URL>
fi
git -C <PATH> remote set-url --push upstream DISABLED
git -C <PATH> checkout -B <BRANCH>
git -C <PATH> push -u origin <BRANCH>

# .gitmodules в корне
git config -f .gitmodules submodule.<PATH>.path   <PATH>
git config -f .gitmodules submodule.<PATH>.url    <FORK_URL>
git config -f .gitmodules submodule.<PATH>.branch <BRANCH>
git submodule sync -- <PATH>
git -C <PATH> pull
git add .gitmodules <PATH>
git commit -m "Point <PATH> to fork @ <BRANCH>"
git push
```

---

## Короткий ответ на «из какой ветки тянет pull?»

* Внутри сабмодуля `git pull` тянет **из твоего форка** (`origin`) и **той ветки, которую трекает HEAD** — у нас это `dantist`.
* Оф. апдейты попадут к тебе **только** после явного `fetch upstream` + `merge/rebase`.
* Главный репо видит сабмодули как **пины** (SHA). Ты сам решаешь, когда «поднимать пины» коммитом в `Dantist`.
