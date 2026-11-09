"""Интеграционные тесты для API."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_search_service
from app.database import get_db_session
from app.main import app


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Фикстура для создания тестового клиента."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    """Тест проверки здоровья."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_search(async_client: AsyncClient) -> None:
    """Тест запуска поиска (проверяем, что возвращается 202)."""

    # Мокаем SearchService
    mock_service = AsyncMock()

    # Переопределяем зависимость get_search_service, чтобы FastAPI использовал мок
    app.dependency_overrides[get_search_service] = lambda: mock_service

    response = await async_client.post("/search", json={"query": "python developer"})

    assert response.status_code == 202
    assert response.json() == {"message": "Search started in background"}

    # Очищаем переопределения после теста
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_search_results_not_found(async_client: AsyncClient) -> None:
    """Тест: если поиск не найден, возвращается 404."""

    mock_db = AsyncMock()

    # ИСПРАВЛЕНИЕ: scalar_one_or_none() — синхронный метод, поэтому используем MagicMock!
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    # execute() — асинхронный, поэтому db.execute возвращает AsyncMock (но await отдаст mock_result)
    mock_db.execute.return_value = mock_result

    # Переопределяем зависимость получения БД
    app.dependency_overrides[get_db_session] = lambda: mock_db

    search_id = uuid4()
    response = await async_client.get(f"/search/{search_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Search not found"

    # Очищаем переопределения
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_export_not_implemented(async_client: AsyncClient) -> None:
    """Тест заглушки экспорта."""
    response = await async_client.get("/candidates/export")
    assert response.status_code == 501
