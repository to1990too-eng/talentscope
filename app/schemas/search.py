"""Pydantic-схемы для поисковых запросов и оценок."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.search import SearchStatus
from app.schemas.candidate import CandidateRead


class SearchCreate(BaseModel):
    """Схема для создания поискового запроса."""
    query: str = Field(..., min_length=2, max_length=500, description="Поисковый запрос")


class EvaluationRead(BaseModel):
    """Схема для чтения оценки."""
    id: UUID
    score: float
    reasoning: str
    created_at: datetime

    # Вкладываем данные кандидата прямо в оценку (удобно для фронтенда)
    candidate: CandidateRead

    model_config = ConfigDict(from_attributes=True)


class SearchRead(BaseModel):
    """Схема для чтения поискового запроса с результатами."""
    id: UUID
    query: str
    status: SearchStatus
    created_at: datetime

    # Список оценок (кандидатов) для этого поиска
    evaluations: list[EvaluationRead] = []

    model_config = ConfigDict(from_attributes=True)
