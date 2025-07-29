"""Настройки бота."""
import os

from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv(dotenv_path="infra/.env")

# Основные настройки бота
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "good_service")
SERVICE_NAME = os.getenv("SERVICE_NAME", "good_channel")
BOT_LINK = os.getenv("BOT_LINK", "https://t.me/your_bot_link")
TOKEN = os.getenv("TOKEN", "yourbottoken123456789")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "yourbottoken123456789")
WEBHOOK_ALLOWED_IPS = {}
TELEGRAM_BOT_TOKEN = os.getenv("TOKEN", "super-secret-token")

# Настройки Redis
REDIS_STORAGE_URL = os.getenv("REDIS_STORAGE_URL", "redis://localhost:6379/0")

# Настройки Telegram API
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@your_channel")
