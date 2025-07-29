"""Настройки проекта."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv(dotenv_path=Path("../infra/.env"))

# Базовые настройки
APP_NAME = "main"
MODEL_DEFAULT = "gemini-2.0-flash"

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / "media/images"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

CONTEXT_PATH = BASE_DIR / "files/context"
CONTEXT_PATH.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")

# Хост и протокол
HOST = os.getenv("HOST", "localhost")
PROTOCOL = "https" if HOST != "localhost" else "http"
HOST_URL = f"{PROTOCOL}://{HOST}"
if HOST == "localhost":
    FRONTEND_URL = f"{HOST_URL}:3000"
    BACKEND_URL = f"{HOST_URL}:8000"
else:
    FRONTEND_URL = f"{HOST_URL}"
    BACKEND_URL = f"{HOST_URL}"

# Подключения
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "mydatabase")

# ИИ API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "change_me")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "change_me")

# CORS
ALLOWED_ORIGINS = [
    HOST_URL,
    FRONTEND_URL,
    BACKEND_URL,
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:4000",
    "http://localhost:3001",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:8000",
]

# Остальные
CHAT_TIMEOUT = timedelta(days=1)
FLOOD_TIMEOUTS = {
    "manual": timedelta(seconds=3),
    "automatic": timedelta(seconds=3),
}
CONTEXT_TTL = timedelta(days=1)

SUPPORTED_LANGUAGES = {"en", "pl", "uk", "ru", "ka"}
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "change_me")
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"
WEATHER_CACHE_LIFETIME = timedelta(hours=1)
LOCATION_INFO = [
    {
        "name": "AnyLocation",
        "address": "Chanchkhalo, Adjara, Georgia",
    },
]

# Instagram API настройки
APPLICATION_ACCESS_TOKEN = os.getenv("APPLICATION_ACCESS_TOKEN", "change_me")
APPLICATION_PAGE_ID = os.getenv("APPLICATION_PAGE_ID", "change_me")

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "change_me")
INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID", "change_me")
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "change_me")
INSTAGRAM_VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "change_me")
INSTAGRAM_BOT_NAME = os.getenv("INSTAGRAM_BOT_NAME", "change_me")
INSTAGRAM_BOT_ID = os.getenv("INSTAGRAM_BOT_ID", "change_me")

# WhatsApp API настройки
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "change_me")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv(
    "WHATSAPP_BUSINESS_ACCOUNT_ID", "change_me")
WHATSAPP_BOT_NUMBER_ID = os.getenv("WHATSAPP_BOT_NUMBER_ID", "change_me")
WHATSAPP_BOT_NUMBER = os.getenv("WHATSAPP_BOT_NUMBER", "change_me")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "change_me")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "change_me")

# Facebook Messenger API настройки
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "change_me")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "change_me")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "change_me")
FACEBOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN", "change_me")
FACEBOOK_BUSINESS_ACCOUNT_ID = os.getenv(
    "FACEBOOK_BUSINESS_ACCOUNT_ID", "change_me")

# Telegram настройки
TELEGRAM_BOT_TOKEN = os.getenv("TOKEN", "change_me")
TELEGRAM_BOT_ID = os.getenv("TELEGRAM_BOT_ID", "change_me")

# Constructor.chat настройки
CONSTRUCTOR_URL = "https://ai-chat-bbho.onrender.com/graphql"
CONSTRUCTOR_TOKEN = os.getenv("CONSTRUCTOR_TOKEN", "change_me")
CONSTRUCTOR_ASSISTANT_ID = os.getenv("CONSTRUCTOR_ASSISTANT_ID", "change_me")

# SMTP
SMS_API_URL = os.getenv("SMS_API_URL", "change_me")
SMS_API_KEY = os.getenv("SMS_API_KEY", "change_me")
SMS_API_SENDER = os.getenv("SMS_API_SENDER", "change_me")

SMTP_HOST = "smtp.emaillabs.net.pl" # EmailLabs
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASS")
SMTP_FROM = "[email protected]"
SMTP_USE_TLS = True
SMTP_TIMEOUT = 10.0

# PaNa Medica CRM
CRM_API_URL = os.getenv("CRM_API_URL", "change_me")
CRM_CLIENT_ID = os.getenv("CRM_CLIENT_ID", "change_me")
CRM_CLIENT_SECRET = os.getenv("CRM_CLIENT_SECRET", "change_me")
