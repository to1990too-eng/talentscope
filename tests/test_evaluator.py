"""Тесты для сервиса оценки (Evaluator)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.evaluator import Evaluator
from app.sources.base import RawCandidate


@pytest.fixture
def candidate() -> RawCandidate:
    """Фикстура для тестового кандидата."""
    return RawCandidate(
        source="github",
        external_id="123",
        name="John Doe",
        url="https://github.com/johndoe",
        description="Python developer"
    )


@pytest.mark.asyncio
async def test_evaluator_cache_hit(candidate: RawCandidate) -> None:
    """Тест: если данные есть в кэше, Claude API не вызывается."""
    # Мокаем Redis (возвращает сохраненный JSON)
    mock_redis = AsyncMock()
    mock_redis.get.return_value = '{"score": 9.5, "reasoning": "Отличный кандидат (из кэша)"}'

    # Мокаем Claude
    mock_anthropic = MagicMock()

    evaluator = Evaluator(redis_conn=mock_redis, anthropic_client=mock_anthropic)

    result = await evaluator.evaluate("python", candidate)

    assert result.score == 9.5
    assert "из кэша" in result.reasoning

    # Проверяем, что Claude НЕ вызывался
    mock_anthropic.messages.create.assert_not_called()
    # Проверяем, что в Redis сделали только 1 запрос (get), но не set
    mock_redis.get.assert_called_once()
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_evaluator_cache_miss(candidate: RawCandidate) -> None:
    """Тест: если кэш пуст, делается запрос к Claude и результат сохраняется."""
    # Мокаем Redis (возвращает None - кэш пуст)
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    # Мокаем ответ Claude
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"score": 8.0, "reasoning": "Хороший специалист"}')]

    mock_anthropic = MagicMock()
    # Имитируем асинхронный вызов messages.create
    mock_anthropic.messages.create = AsyncMock(return_value=mock_response)

    evaluator = Evaluator(redis_conn=mock_redis, anthropic_client=mock_anthropic)

    result = await evaluator.evaluate("python", candidate)

    assert result.score == 8.0
    assert result.reasoning == "Хороший специалист"

    # Проверяем, что Claude вызван
    mock_anthropic.messages.create.assert_called_once()
    # Проверяем, что результат сохранен в Redis (set)
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_evaluator_fallback_on_bad_json(candidate: RawCandidate) -> None:
    """Тест: если LLM вернула мусор вместо JSON, срабатывает fallback."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    # Claude возвращает обычный текст вместо JSON
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Я не могу оценить этого кандидата.")]

    mock_anthropic = MagicMock()
    mock_anthropic.messages.create = AsyncMock(return_value=mock_response)

    evaluator = Evaluator(redis_conn=mock_redis, anthropic_client=mock_anthropic)

    result = await evaluator.evaluate("python", candidate)

    # Сработал fallback
    assert result.score == 5.0
    assert "Ошибка автоматической оценки" in result.reasoning
