"""Интеграционные тесты для API."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db_session
from app.main import app
from app.models.search import Search


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
    mock_db = AsyncMock()

    # ИСПРАВЛЕНИЕ: db.add() — синхронный метод, делаем его MagicMock
    mock_db.add = MagicMock()

    # Имитируем присвоение ID при refresh
    async def refresh_side_effect(instance: Search) -> None:
        if instance.id is None:
            instance.id = uuid4()

    mock_db.refresh.side_effect = refresh_side_effect

    # Мокаем redis lpush, чтобы не стучаться в реальный Redis
    with patch("app.api.routes.search.redis_client.lpush", new_callable=AsyncMock) as mock_lpush:
        app.dependency_overrides[get_db_session] = lambda: mock_db
        try:
            response = await async_client.post("/search", json={"query": "python developer"})
            assert response.status_code == 202
            assert "search_id" in response.json()
            mock_lpush.assert_called_once()
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_search_results_not_found(async_client: AsyncClient) -> None:
    """Тест: если поиск не найден, возвращается 404."""
    mock_db = AsyncMock()

    # ИСПРАВЛЕНИЕ: scalar_one_or_none() — синхронный, используем MagicMock
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session] = lambda: mock_db
    try:
        search_id = uuid4()
        response = await async_client.get(f"/search/{search_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Search not found"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_export_candidates(async_client: AsyncClient) -> None:
    """Тест экспорта кандидатов в Excel."""
    mock_db = AsyncMock()

    # ИСПРАВЛЕНИЕ: scalars().all() — синхронные, используем MagicMock
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session] = lambda: mock_db
    try:
        response = await async_client.get("/candidates/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    finally:
        app.dependency_overrides.clear()
