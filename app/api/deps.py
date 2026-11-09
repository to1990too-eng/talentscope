"""Зависимости (Dependencies) для внедрения в роутеры FastAPI."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.evaluator import Evaluator
from app.services.search_service import SearchService
from app.sources.arxiv import ArxivSource
from app.sources.github import GitHubSource
from app.sources.openalex import OpenAlexSource


async def get_search_service(
        db: Annotated[AsyncSession, Depends(get_db_session)]
) -> AsyncGenerator[SearchService, None]:
    """
    Собирает все источники и сервис оценки, создавая SearchService.
    Использует зависимость get_db_session для получения сессии БД.
    """
    # Инициализируем источники
    sources = [
        GitHubSource(),
        ArxivSource(),
        OpenAlexSource(),
    ]

    # Инициализируем оценщик
    evaluator = Evaluator()

    # Создаем сервис оркестрации
    service = SearchService(db=db, sources=sources, evaluator=evaluator)
    yield service
