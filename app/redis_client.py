"""Настройка асинхронного клиента Redis."""

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

# Создаем глобальный асинхронный клиент Redis.
# decode_responses=True автоматически декодирует байты в строки (utf-8).
redis_client = redis.Redis.from_url(
    str(settings.redis_url),
    encoding="utf-8",
    decode_responses=True,
)
