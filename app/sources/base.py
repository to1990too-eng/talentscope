"""Базовые классы и схемы для источников данных."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict


class RawCandidate(BaseModel):
    """
    Промежуточная схема кандидата.
    Она не привязана к БД. Это просто универсальный формат,
    в который все источники (GitHub, arXiv и др.) приводят свои данные.
    """
    source: str
    external_id: str
    name: str
    url: str
    description: str | None = None

    # frozen=True делает объект неизменяемым (как tuple), это хорошая практика для DTO
    model_config = ConfigDict(frozen=True)


class BaseSource(ABC):
    """Абстрактный базовый класс для всех источников данных."""

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[RawCandidate]:
        """
        Асинхронный метод для поиска кандидатов.

        :param query: Поисковый запрос (например, "python developer").
        :param limit: Сколько максимум результатов вернуть.
        :return: Список объектов RawCandidate.
        """
        pass
