# Используем Python как базовый образ
FROM python:3.10

# Устанавливаем Supervisor
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY . .
RUN pip install --upgrade pip
RUN pip3 install -r infra/requirements.txt --no-cache-dir

# Копируем конфигурацию Supervisor
COPY infra/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Запускаем Supervisor
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
