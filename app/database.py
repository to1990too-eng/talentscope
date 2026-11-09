"""Настройка асинхронного подключения к базе данных и сессий."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Создаем асинхронный движок.
# echo=settings.debug позволяет видеть SQL-запросы в консоли при DEBUG=true.
engine = create_async_engine(
    str(settings.database_url),
    echo=settings.debug,
    future=True,
)

# Фабрика асинхронных сессий.
# expire_on_commit=False необходим, чтобы после коммита мы могли обращаться
# к атрибутам объектов (иначе в async-режиме они станут недоступны).
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""
    pass

async def get_db_session() -> AsyncGenerator[AsyncSession, Any]:
    """
    Зависимость (dependency) для FastAPI.
    Открывает сессию на время запроса и автоматически закрывает её.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
