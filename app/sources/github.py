"""Источник данных: GitHub API."""

import logging

import httpx

from app.config import get_settings
from app.sources.base import BaseSource, RawCandidate

logger = logging.getLogger(__name__)


class GitHubSource(BaseSource):
    """Поиск специалистов через официальный GitHub API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        """
        Инициализация источника.
        Мы разрешаем передать готовый httpx.AsyncClient.
        В продакшене он создастся автоматически, а в тестах мы подсунем ему фейковый клиент.
        """
        self.settings = get_settings()
        self._client = client

        # Заголовки для GitHub API
        self._headers = {"Accept": "application/vnd.github+json"}

        # Если в .env есть токен, добавляем его (это спасает от блокировок по Rate Limit)
        if self.settings.github_token:
            self._headers["Authorization"] = f"Bearer {self.settings.github_token}"

    async def _get_client(self) -> httpx.AsyncClient:
        """Ленивое создание клиента (только когда он реально понадобится)."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=self._headers,
                timeout=10.0,
            )
        return self._client

    async def search(self, query: str, limit: int = 10) -> list[RawCandidate]:
        """Ищет пользователей GitHub по запросу и собирает их профили."""
        client = await self._get_client()
        candidates: list[RawCandidate] = []

        # 1. Поиск пользователей по ключевым словам
        try:
            response = await client.get(
                "/search/users",
                params={"q": query, "per_page": limit}
            )
            response.raise_for_status()  # Вызовет исключение, если статус 4xx или 5xx
            data = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Ошибка при поиске на GitHub: {e}")
            return []  # Если поиск упал, возвращаем пустой список, не роняем всё приложение

        items = data.get("items", [])

        # 2. Для каждого найденного пользователя забираем детали профиля (био)
        # GitHub Search API не отдает bio, только логин. Поэтому делаем доп. запросы.
        for item in items:
            login = item.get("login")
            if not login:
                continue

            try:
                user_resp = await client.get(f"/users/{login}")
                user_resp.raise_for_status()
                user_data = user_resp.json()

                candidates.append(
                    RawCandidate(
                        source="github",
                        external_id=str(user_data["id"]),
                        name=user_data.get("name") or login,  # Если имя скрыто, берем логин
                        url=user_data.get("html_url", f"https://github.com/{login}"),
                        description=user_data.get("bio"),
                    )
                )
            except httpx.HTTPError as e:
                # Если не удалось достать профиль одного пользователя, просто логируем и идем дальше
                logger.warning(f"Не удалось получить профиль {login}: {e}")
                continue

        return candidates
