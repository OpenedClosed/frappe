# 0) выйти из внешней venv, чтобы не мешала (если активна)
deactivate 2>/dev/null || true

cd /Users/Dmitrii/Desktop/Dev_BMSTU/Dantist/frappe_gui

# 1) снести битую локальную venv бенча и создать заново
rm -rf env
python3 -V 
python3 -m venv env
source env/bin/activate

# 2) базовые инструменты
python -m pip install -U pip wheel setuptools

# 3) поставить сам bench ВНУТРИ этой venv
pip install -U frappe-bench

# 4) накатить python-зависимости из твоих apps
bench setup requirements --python

# 5) node/yarn для сборки фронта (если не стоят глобально)
# macOS: либо
#   brew install node
#   corepack enable    # включает yarn classic
# либо (если уже есть node>=18) — просто:
bench setup requirements --node

# 6) собрать ассеты (если менял фронт/темы/иконки)
bench build

# 7) старт
bench start
