"""Модели базы данных."""

from app.models.candidate import Candidate
from app.models.search import Evaluation, Search, SearchStatus

__all__ = ["Candidate", "Evaluation", "Search", "SearchStatus"]
