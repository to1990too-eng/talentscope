"""Роутер для работы с кандидатами."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db_session
from app.models.candidate import Candidate
from app.models.search import Evaluation
from app.schemas.candidate import CandidateRead
from app.services.exporter import ExcelExporter

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
async def export_candidates_to_excel(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        # ИСПРАВЛЕНИЕ: используем Annotated для Query и ставим = None в конце
        search_id: Annotated[UUID | None, Query(description="ID поиска для выгрузки")] = None,
) -> Response:
    """
    Экспортирует результаты поиска в Excel.
    Если передан search_id, выгружает только результаты этого поиска.
    Если нет — выгружает все оценки.
    """
    # Запрашиваем оценки вместе с данными кандидатов (selectinload предотвращает проблему N+1)
    stmt = select(Evaluation).options(selectinload(Evaluation.candidate))

    if search_id:
        stmt = stmt.where(Evaluation.search_id == search_id)

    result = await db.execute(stmt)
    evaluations = list(result.scalars().all())

    # Генерируем Excel
    excel_bytes = ExcelExporter.export_to_excel(evaluations)

    # Возвращаем как файл для скачивания
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=talentscope_export.xlsx"}
    )
