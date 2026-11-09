"""Модели поискового запроса и оценки кандидата."""

import enum
from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.candidate import Candidate


class SearchStatus(enum.StrEnum):
    """Статусы выполнения поискового запроса."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Search(UUIDMixin, TimestampMixin, Base):
    """Запрос на поиск специалистов."""

    __tablename__ = "searches"

    # Текстовый запрос (например, "Python разработчик с опытом в ML")
    query: Mapped[str] = mapped_column(String(500), nullable=False)

    # Статус выполнения
    status: Mapped[SearchStatus] = mapped_column(
        SQLEnum(SearchStatus, name="search_status_enum"),
        default=SearchStatus.PENDING,
        nullable=False
    )

    # Связь 1-ко-многим: у одного поиска много оценок
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )


class Evaluation(UUIDMixin, TimestampMixin, Base):
    """Оценка конкретного кандидата в рамках конкретного поиска."""

    __tablename__ = "evaluations"
    __table_args__ = (
        # В рамках одного поиска кандидат оценивается только один раз
        UniqueConstraint("search_id", "candidate_id", name="uq_evaluation_search_candidate"),
    )

    search_id: Mapped[UUID] = mapped_column(
        ForeignKey("searches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Оценка от 1.0 до 10.0
    score: Mapped[float] = mapped_column(Float, nullable=False)

    # Текстовое обоснование от AI (почему такая оценка)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    # Обратные связи
    search: Mapped["Search"] = relationship(back_populates="evaluations")
    candidate: Mapped["Candidate"] = relationship()
