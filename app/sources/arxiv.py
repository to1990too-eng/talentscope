"""Источник данных: arXiv API."""

import logging
import xml.etree.ElementTree as ET

import httpx

from app.config import get_settings
from app.sources.base import BaseSource, RawCandidate

logger = logging.getLogger(__name__)

# Пространства имён для парсинга Atom XML
ATOM_NS = "{http://www.w3.org/2005/Atom}"


class ArxivSource(BaseSource):
    """Поиск научных статей и их авторов через arXiv API."""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.settings = get_settings()
        self._client = client
        self._headers = {"Accept": "application/atom+xml"}

    async def _get_client(self) -> httpx.AsyncClient:
        """Ленивое создание клиента."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=self._headers,
                timeout=15.0,
            )
        return self._client

    async def search(self, query: str, limit: int = 10) -> list[RawCandidate]:
        """Ищет статьи по запросу и извлекает информацию об авторах."""
        client = await self._get_client()
        candidates: list[RawCandidate] = []

        try:
            # Формируем запрос к arXiv API
            response = await client.get(
                "",  # Базовый URL уже содержит путь
                params={
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": limit,
                },
            )
            response.raise_for_status()

            # Парсим XML
            root = ET.fromstring(response.text)

            # Ищем все элементы <entry> (каждая статья)
            for entry in root.findall(f"{ATOM_NS}entry"):
                title_elem = entry.find(f"{ATOM_NS}title")
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Без названия"

                link_elem = entry.find(f"{ATOM_NS}id")
                url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

                # В arXiv авторы перечислены в тегах <author><name>
                # Для простоты мы возьмём первого автора как "кандидата"
                author_elem = entry.find(f"{ATOM_NS}author/{ATOM_NS}name")
                author_name = author_elem.text.strip() if author_elem is not None and author_elem.text else "Unknown Author"

                if not url:
                    continue

                candidates.append(
                    RawCandidate(
                        source="arxiv",
                        external_id=url.split("/")[-1],  # ID статьи из URL
                        name=author_name,
                        url=url,
                        description=title,
                    )
                )

        except (httpx.HTTPError, ET.ParseError) as e:
            logger.error(f"Ошибка при работе с arXiv: {e}")
            return []

        return candidates
