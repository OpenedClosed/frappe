"""Создание и настройка бота Aiogram."""
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from fastapi import FastAPI

from telegram_bot.db.redis.init_db import redis
from telegram_bot.infra import settings as bot_settings

# Настройка хранилища Redis для FSM
redis_storage = RedisStorage(
    redis=redis,
    key_builder=DefaultKeyBuilder(with_destiny=True),
    state_ttl=timedelta(days=30),
    data_ttl=timedelta(days=30),
)

# Создание экземпляров бота и диспетчера
bot = Bot(
    token=bot_settings.TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=redis_storage)

# Создание FastAPI-приложения
fastapi_app = FastAPI()
