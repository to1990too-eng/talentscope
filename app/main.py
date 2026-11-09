"""Точка входа в приложение FastAPI."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import candidates, health, search
from app.config import get_settings
from app.database import engine
from app.redis_client import redis_client

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Управление жизненным циклом приложения (запуск и остановка)."""
    logger.info("Запуск приложения TalentScope...")
    yield
    # Действия при остановке приложения
    logger.info("Остановка приложения. Закрытие соединений...")
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(
    title=settings.app_name,
    description="AI-агент для поиска и оценки специалистов",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# Подключаем роутеры
app.include_router(health.router)
app.include_router(search.router)
app.include_router(candidates.router)
