"""Тесты для источников данных."""

import httpx
import pytest

from app.sources.github import GitHubSource


@pytest.mark.asyncio
async def test_github_source_search() -> None:
    """Тест успешного поиска в GitHub с использованием MockTransport."""

    # 1. Создаем фейковый обработчик (симулятор GitHub API)
    def mock_handler(request: httpx.Request) -> httpx.Response:
        # Если приложение стучится на /search/users
        if request.url.path == "/search/users":
            return httpx.Response(
                status_code=200,
                json={
                    "total_count": 1,
                    "items": [{"login": "test_user", "id": 12345}]
                }
            )
        # Если приложение стучится за профилем пользователя
        if request.url.path == "/users/test_user":
            return httpx.Response(
                status_code=200,
                json={
                    "id": 12345,
                    "name": "Test User",
                    "bio": "Python Developer",
                    "html_url": "https://github.com/test_user"
                }
            )
        # На всё остальное отвечаем 404
        return httpx.Response(status_code=404)

    # 2. Создаем "транспорт", который использует наш фейковый обработчик
    transport = httpx.MockTransport(mock_handler)

    # 3. Создаем реальный httpx.AsyncClient, но с фейковым транспортом.
    # ВАЖНО: добавлен base_url, чтобы httpx понимал, куда слать относительные пути.
    async with httpx.AsyncClient(base_url="https://api.github.com", transport=transport) as client:

        # 4. Передаем этот клиент в наш источник
        source = GitHubSource(client=client)

        # 5. Вызываем поиск (он пойдет не в интернет, а в mock_handler)
        results = await source.search("python developer")

        # 6. Проверяем результаты
        assert len(results) == 1
        candidate = results[0]

        assert candidate.source == "github"
        assert candidate.external_id == "12345"
        assert candidate.name == "Test User"
        assert candidate.url == "https://github.com/test_user"
        assert candidate.description == "Python Developer"


@pytest.mark.asyncio
async def test_github_source_search_error() -> None:
    """Тест обработки ошибки API (например, 403 Rate Limit)."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        # Симулируем ошибку "Слишком много запросов"
        return httpx.Response(status_code=403)

    transport = httpx.MockTransport(mock_handler)

    # ВАЖНО: добавлен base_url
    async with httpx.AsyncClient(base_url="https://api.github.com", transport=transport) as client:
        source = GitHubSource(client=client)

        # Поиск должен вернуть пустой список, а не упасть с необработанным исключением
        results = await source.search("python")
        assert results == []
