# Python 3.10 slim (Debian trixie)
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    VENV=/opt/bench-env \
    PATH="/opt/bench-env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# --- Базовые пакеты и фронт ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates \
    build-essential pkg-config \
    default-libmysqlclient-dev \
    libffi-dev libssl-dev zlib1g-dev \
    libjpeg62-turbo-dev libwebp-dev libpng-dev libtiff5-dev liblcms2-dev \
    libxml2-dev libxslt1-dev \
    ghostscript \
    fontconfig libxrender1 libxext6 libx11-6 libxcb1 xfonts-base xfonts-75dpi \
    nodejs npm \
    file \
    mariadb-client \
 && rm -rf /var/lib/apt/lists/*


# --- wkhtmltopdf 0.12.6-1 (.deb с fallback) ---
RUN set -eux; \
    apt-get update; \
    for url in \
      "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.bookworm_amd64.deb" \
      "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.bullseye_amd64.deb" \
    ; do \
      echo "Downloading: $url"; \
      if curl -fsSL -o /tmp/wkhtml.deb "$url"; then break; fi; \
    done; \
    dpkg -i /tmp/wkhtml.deb || apt-get -y -f install; \
    rm -rf /var/lib/apt/lists/* /tmp/wkhtml.deb

# --- Bench дерево ---
RUN mkdir -p /workspace /opt/seed-sites
WORKDIR /workspace
# Контекст билда — ./frappe_gui
COPY . /workspace/

# --- Venv + bench CLI (совместимо с bench 5.25.x) ---
RUN python3 -m venv "$VENV" \
 && "$VENV/bin/pip" install -U pip setuptools wheel \
 && "$VENV/bin/pip" install "frappe-bench==5.25.9"

# --- Ссылка на venv туда, где bench его ожидает (/workspace/env) ---
RUN ln -s "$VENV" /workspace/env

# --- Yarn для node-зависимостей ---
RUN npm i -g yarn

# --- Патч common_site_config: не дропаем права на локального macOS-пользователя ---
RUN python3 - <<'PY'
import json, pathlib
p = pathlib.Path("/workspace/sites/common_site_config.json")
cfg = {}
if p.exists():
    try:
        cfg = json.loads(p.read_text() or "{}")
    except Exception:
        cfg = {}
cfg.update({"frappe_user": "root", "live_reload": False})
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
PY

# --- Инициализация git в apps/* (Bench/GitPython требуют валидный репозиторий) ---
RUN git config --global user.email "build@local" && git config --global user.name "Build User" \
 && for d in /workspace/apps/*; do \
      if [ -d "$d" ]; then \
        rm -rf "$d/.git"; \
        git -C "$d" init; \
        git -C "$d" add -A || true; \
        git -C "$d" commit -m "init for bench" --allow-empty; \
      fi; \
    done

# --- Установка зависимостей всех приложений (Python + Node) ---
RUN bench setup requirements

# --- Устанавливаем сами приложения (editable), чтобы появились команды serve/worker/... ---
RUN set -eux; \
  for app in frappe erpnext task_tracker; do \
    if [ -d "apps/$app" ]; then "$VENV/bin/pip" install -e "apps/$app"; fi; \
  done

# --- Предсборка ассетов (на этапе билда) ---
RUN bench build || bench build || true

# --- Seed для пустого тома sites/ ---
RUN cp -a /workspace/sites/. /opt/seed-sites/ || true

# --- Стартовый скрипт ---
COPY docker/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

EXPOSE 8001 9000
ENTRYPOINT ["/usr/local/bin/start.sh"]
