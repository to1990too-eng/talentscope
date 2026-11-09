"""Настройка окружения Alembic для асинхронного SQLAlchemy."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.config import get_settings
from app.database import Base

# Импортируем все модели (на шаге 3 добавим их сюда,
# чтобы Alembic видел таблицы при автогенерации)
# from app.models import *  # noqa

config = context.config

# Настраиваем логирование из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Получаем URL базы данных из нашего конфига и подставляем в Alembic
settings = get_settings()
config.set_main_option("sqlalchemy.url", str(settings.database_url))

# Указываем Alembic метаданные наших моделей
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в 'offline' режиме (генерация SQL скриптов)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Синхронная обертка для запуска миграций внутри асинхронного соединения."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Запуск миграций в 'online' режиме (асинхронно)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Точка входа для online-миграций."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
