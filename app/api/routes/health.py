"""Роутер для проверки состояния приложения."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Проверка доступности сервера."""
    return HealthResponse(status="ok")
