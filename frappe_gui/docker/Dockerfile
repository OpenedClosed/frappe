# Python 3.10 slim (Debian)
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    VENV=/opt/bench-env \
    PATH="/opt/bench-env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# --- Base packages + node/yarn + mysqlclient deps ---
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

# --- wkhtmltopdf 0.12.6-1 ---
RUN set -eux; \
    apt-get update; \
    for url in \
      "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.bookworm_amd64.deb" \
      "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.bullseye_amd64.deb" \
    ; do \
      if curl -fsSL -o /tmp/wkhtml.deb "$url"; then break; fi; \
    done; \
    dpkg -i /tmp/wkhtml.deb || apt-get -y -f install; \
    rm -rf /var/lib/apt/lists/* /tmp/wkhtml.deb

# --- Workspace ---
RUN mkdir -p /workspace
WORKDIR /workspace
COPY . /workspace/

# --- venv + bench ---
RUN python3 -m venv "$VENV" \
 && "$VENV/bin/pip" install -U pip setuptools wheel \
 && "$VENV/bin/pip" install "frappe-bench==5.25.9"

# bench ожидает env-ссылку
RUN ln -s "$VENV" /workspace/env

# --- yarn ---
RUN npm i -g yarn

# --- базовый common_site_config патч на билде ---
RUN python3 - <<'PY'
import json, pathlib
p = pathlib.Path("/workspace/sites/common_site_config.json")
cfg = {}
if p.exists():
    try: cfg = json.loads(p.read_text() or "{}")
    except Exception: cfg = {}
cfg.update({"frappe_user": "root", "live_reload": False})
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
PY

# --- инициализация git в apps/* (bench reqs) ---
RUN git config --global user.email "build@local" && git config --global user.name "Build User" \
 && for d in /workspace/apps/*; do \
      if [ -d "$d" ]; then \
        rm -rf "$d/.git"; \
        git -C "$d" init; \
        git -C "$d" add -A || true; \
        git -C "$d" commit -m "init for bench" --allow-empty; \
      fi; \
    done

# --- зависимости всех приложений (python+node) ---
RUN bench setup requirements

# --- editable install приложений ---
RUN set -eux; \
  for app in frappe erpnext dantist_app; do \
    if [ -d "apps/$app" ]; then "$VENV/bin/pip" install -e "apps/$app"; fi; \
  done

# --- предсборка ассетов на билде (best-effort) ---
RUN bench build || bench build || true

# --- start script ---
COPY docker/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

EXPOSE 8001 9000
ENTRYPOINT ["/usr/local/bin/start.sh"]