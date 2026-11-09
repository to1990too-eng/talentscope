"""Источник данных: OpenAlex API."""

import logging

import httpx

from app.config import get_settings
from app.sources.base import BaseSource, RawCandidate

logger = logging.getLogger(__name__)


class OpenAlexSource(BaseSource):
    """Поиск исследователей через OpenAlex API."""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.settings = get_settings()
        self._client = client
        self._headers = {"Accept": "application/json"}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=self._headers,
                timeout=10.0,
            )
        return self._client

    async def search(self, query: str, limit: int = 10) -> list[RawCandidate]:
        """Ищет авторов (исследователей) по запросу."""
        client = await self._get_client()
        candidates: list[RawCandidate] = []

        try:
            # Ищем авторов по имени/ключевым словам
            response = await client.get(
                "/authors",
                params={
                    "search": query,
                    "per_page": limit,
                },
            )
            response.raise_for_status()
            data = response.json()

            # OpenAlex возвращает результаты в поле "results"
            for item in data.get("results", []):
                author_id = item.get("id", "")
                if not author_id:
                    continue

                # Извлекаем ID из URL (например, https://openalex.org/A1234567890)
                external_id = author_id.split("/")[-1]

                # OpenAlex может возвращать разные варианты имени
                display_name = item.get("display_name", "Unknown")

                # Ссылка на профиль
                url = author_id

                # Описание может содержать количество работ или аффилиацию
                works_count = item.get("works_count", 0)
                description = f"Works count: {works_count}"

                # Если есть информация об учреждении, добавляем
                last_known_institutions = item.get("last_known_institutions", [])
                if last_known_institutions and isinstance(last_known_institutions, list):
                    inst_name = last_known_institutions[0].get("display_name")
                    if inst_name:
                        description += f", Institution: {inst_name}"

                candidates.append(
                    RawCandidate(
                        source="openalex",
                        external_id=external_id,
                        name=display_name,
                        url=url,
                        description=description,
                    )
                )

        except httpx.HTTPError as e:
            logger.error(f"Ошибка при работе с OpenAlex: {e}")
            return []

        return candidates
