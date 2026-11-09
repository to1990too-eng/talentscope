"""Pydantic-схемы для кандидатов."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CandidateBase(BaseModel):
    """Базовые поля кандидата."""
    source: str = Field(..., description="Источник (github, arxiv, openalex)")
    external_id: str = Field(..., description="ID внутри источника")
    name: str = Field(..., description="Имя или никнейм")
    url: str = Field(..., description="Ссылка на профиль")
    description: str | None = Field(None, description="Описание профиля")


class CandidateCreate(CandidateBase):
    """Схема для создания кандидата."""
    pass


class CandidateRead(CandidateBase):
    """Схема для чтения кандидата из БД."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    # Позволяет Pydantic читать данные напрямую из объектов SQLAlchemy
    model_config = ConfigDict(from_attributes=True)
