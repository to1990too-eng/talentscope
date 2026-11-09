"""Тесты для фонового воркера."""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.worker import process_task


@pytest.mark.asyncio
async def test_process_task_success() -> None:
    """Тест: воркер корректно обрабатывает задачу из Redis."""
    search_id = uuid4()
    payload = json.dumps({"search_id": str(search_id), "query": "python"})

    # Мокаем сессию БД
    mock_db = AsyncMock()

    # Мокаем фабрику сессий, чтобы она возвращала наш mock_db
    # Используем patch, так как async_session_factory вызывается внутри воркера
    with patch("app.worker.async_session_factory") as mock_factory:
        # Настраиваем контекстный менеджер (async with)
        mock_factory.return_value.__aenter__.return_value = mock_db

        # Мокаем SearchService
        with patch("app.worker.SearchService") as mock_service_class:
            mock_service_instance = AsyncMock()
            mock_service_class.return_value = mock_service_instance

            # Вызываем функцию
            await process_task(payload)

            # Проверяем, что сервис был инициализирован
            mock_service_class.assert_called_once()

            # Проверяем, что execute_search был вызван с правильными аргументами
            mock_service_instance.execute_search.assert_called_once_with(
                query="python",
                search_id=search_id
            )
