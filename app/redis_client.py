"""Настройка асинхронного клиента Redis."""

import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

# Создаем глобальный асинхронный клиент Redis.
redis_client = redis.Redis.from_url(
    str(settings.redis_url),
    encoding="utf-8",
    decode_responses=True,
    # 👇 Явно отключаем таймаут сокета для поддержки бесконечного BRPOP
    socket_timeout=None,
    # 👇 Принудительно используем старый протокол RESP2 для стабильности
    protocol=2,
)