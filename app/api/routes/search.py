"""Роутер для управления поисковыми запросами."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_search_service
from app.database import get_db_session
from app.models.search import Search
from app.schemas.search import SearchCreate, SearchRead
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def create_search(
        payload: SearchCreate,
        background_tasks: BackgroundTasks,
        service: Annotated[SearchService, Depends(get_search_service)],
) -> dict[str, str]:
    """
    Запускает поиск в фоновом режиме.
    Возвращает сообщение о том, что поиск начат.
    """
    # Запускаем долгий процесс в фоне, чтобы не блокировать HTTP-ответ
    # В реальном проекте здесь лучше использовать Celery или ARQ, но FastAPI BackgroundTasks
    # отлично подходит для MVP.
    background_tasks.add_task(service.execute_search, payload.query)

    return {"message": "Search started in background"}


@router.get("/{search_id}", response_model=SearchRead)
async def get_search_results(
        search_id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Search:
    """Возвращает информацию о поиске и список оцененных кандидатов."""
    stmt = select(Search).where(Search.id == search_id)
    search = (await db.execute(stmt)).scalar_one_or_none()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found"
        )

    return search
