"""Роутер для работы с кандидатами."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateRead

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get("", response_model=list[CandidateRead])
async def get_candidates(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    skip: int = 0,
    limit: int = 100,
) -> list[Candidate]:
    """Возвращает список всех найденных кандидатов с пагинацией."""
    stmt = select(Candidate).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/export")
async def export_candidates_to_excel() -> dict[str, str]:
    """
    Эндпоинт для экспорта кандидатов в Excel.
    Полноценная реализация появится на Шаге 9.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Export to Excel will be implemented in Step 9"
    )
