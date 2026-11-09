"""Модель найденного кандидата."""

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Candidate(UUIDMixin, TimestampMixin, Base):
    """Специалист, найденный в одном из внешних источников."""

    __tablename__ = "candidates"
    __table_args__ = (
        # Один и тот же профиль не должен дублироваться в рамках одного источника
        UniqueConstraint("source", "external_id", name="uq_candidate_source_ext_id"),
    )

    # Источник (github, arxiv, openalex)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Уникальный ID внутри источника (например, username в GitHub)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Имя / Никнейм
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Ссылка на профиль
    url: Mapped[str] = mapped_column(String(512), nullable=False)

    # Краткое описание (био, список технологий или название статьи)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
