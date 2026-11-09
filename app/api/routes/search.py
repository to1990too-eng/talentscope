"""Роутер для управления поисковыми запросами."""

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.search import Search, SearchStatus
from app.redis_client import redis_client
from app.schemas.search import SearchCreate, SearchRead

router = APIRouter(prefix="/search", tags=["Search"])

QUEUE_NAME = "search_queue"


@router.post("", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def create_search(
        payload: SearchCreate,
        db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """
    Создает запись о поиске и отправляет задачу в очередь Redis.
    """
    # 1. Создаем запись в БД со статусом PENDING
    search = Search(query=payload.query, status=SearchStatus.PENDING)
    db.add(search)
    await db.commit()
    await db.refresh(search)

    # 2. Отправляем задачу в очередь Redis (LPUSH кладет элемент в начало списка)
    task_payload = json.dumps({"search_id": str(search.id), "query": search.query})
    await redis_client.lpush(QUEUE_NAME, task_payload)

    return {
        "message": "Search started in background",
        "search_id": str(search.id)
    }


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
