"""Тесты для источников данных."""

import httpx
import pytest

from app.sources.arxiv import ArxivSource
from app.sources.github import GitHubSource
from app.sources.openalex import OpenAlexSource

# ==================== Тесты для GitHub ====================

@pytest.mark.asyncio
async def test_github_source_search() -> None:
    """Тест успешного поиска в GitHub с использованием MockTransport."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/users":
            return httpx.Response(
                status_code=200,
                json={
                    "total_count": 1,
                    "items": [{"login": "test_user", "id": 12345}]
                }
            )
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
        return httpx.Response(status_code=404)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(base_url="https://api.github.com", transport=transport) as client:
        source = GitHubSource(client=client)
        results = await source.search("python developer")

        assert len(results) == 1
        candidate = results[0]
        assert candidate.source == "github"
        assert candidate.external_id == "12345"
        assert candidate.name == "Test User"
        assert candidate.url == "https://github.com/test_user"
        assert candidate.description == "Python Developer"


@pytest.mark.asyncio
async def test_github_source_search_error() -> None:
    """Тест обработки ошибки API (403)."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=403)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(base_url="https://api.github.com", transport=transport) as client:
        source = GitHubSource(client=client)
        results = await source.search("python")
        assert results == []


# ==================== Тесты для arXiv ====================

@pytest.mark.asyncio
async def test_arxiv_source_search() -> None:
    """Тест успешного поиска в arXiv (парсинг XML)."""
    # Пример реального XML-ответа от arXiv (упрощённый)
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>http://arxiv.org/abs/2401.12345v1</id>
            <title>Test Paper Title</title>
            <author>
                <name>John Doe</name>
            </author>
        </entry>
    </feed>"""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            text=mock_xml,
            headers={"Content-Type": "application/atom+xml"}
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(base_url="http://export.arxiv.org", transport=transport) as client:
        source = ArxivSource(client=client)
        results = await source.search("python")

        assert len(results) == 1
        candidate = results[0]
        assert candidate.source == "arxiv"
        assert candidate.external_id == "2401.12345v1"
        assert candidate.name == "John Doe"
        assert "Test Paper Title" in candidate.description
        assert candidate.url == "http://arxiv.org/abs/2401.12345v1"


@pytest.mark.asyncio
async def test_arxiv_source_search_error() -> None:
    """Тест обработки ошибки API arXiv."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=500)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(base_url="http://export.arxiv.org", transport=transport) as client:
        source = ArxivSource(client=client)
        results = await source.search("python")
        assert results == []


# ==================== Тесты для OpenAlex ====================

@pytest.mark.asyncio
async def test_openalex_source_search() -> None:
    """Тест успешного поиска в OpenAlex (парсинг JSON)."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "results": [
                    {
                        "id": "https://openalex.org/A1234567890",
                        "display_name": "Jane Smith",
                        "works_count": 42,
                        "last_known_institutions": [
                            {"display_name": "MIT"}
                        ]
                    }
                ]
            }
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(base_url="https://api.openalex.org", transport=transport) as client:
        source = OpenAlexSource(client=client)
        results = await source.search("machine learning")

        assert len(results) == 1
        candidate = results[0]
        assert candidate.source == "openalex"
        assert candidate.external_id == "A1234567890"
        assert candidate.name == "Jane Smith"
        assert "42" in candidate.description
        assert "MIT" in candidate.description


@pytest.mark.asyncio
async def test_openalex_source_search_error() -> None:
    """Тест обработки ошибки API OpenAlex."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=400)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(base_url="https://api.openalex.org", transport=transport) as client:
        source = OpenAlexSource(client=client)
        results = await source.search("test")
        assert results == []
