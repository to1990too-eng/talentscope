"""Тесты для сервиса оркестрации (SearchService)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.search import Search, SearchStatus
from app.services.evaluator import EvaluationResult
from app.services.search_service import SearchService
from app.sources.base import BaseSource, RawCandidate


@pytest.fixture
def mock_db() -> AsyncMock:
    """Фикстура для мока базы данных (AsyncSession)."""
    db = AsyncMock()

    # Имитируем поведение add: он синхронный, но нам нужно, чтобы при добавлении
    # объекта ему присваивался id (как это сделала бы реальная БД).
    def add_side_effect(instance):
        if hasattr(instance, "id") and instance.id is None:
            instance.id = uuid4()

    # В SQLAlchemy AsyncSession:
    # add() - синхронный метод
    # flush(), commit(), rollback(), execute(), get() - асинхронные
    db.add = MagicMock(side_effect=add_side_effect)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.get = AsyncMock()  # Явно делаем асинхронным

    # Имитируем execute: возвращаем объект, у которого scalar_one_or_none() возвращает None
    # (как будто кандидата нет в базе)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    return db


@pytest.fixture
def mock_source() -> AsyncMock:
    """Фикстура для мока источника данных."""
    source = AsyncMock(spec=BaseSource)
    source.search.return_value = [
        RawCandidate(
            source="github",
            external_id="123",
            name="Test User",
            url="https://github.com/test",
            description="Python Dev"
        )
    ]
    return source


@pytest.fixture
def mock_evaluator() -> AsyncMock:
    """Фикстура для мока Evaluator."""
    evaluator = AsyncMock()
    evaluator.evaluate.return_value = EvaluationResult(
        score=9.0,
        reasoning="Отличный специалист"
    )
    return evaluator


@pytest.mark.asyncio
async def test_execute_search_success(
        mock_db: AsyncMock,
        mock_source: AsyncMock,
        mock_evaluator: AsyncMock
) -> None:
    """Тест успешного выполнения поиска и сохранения результатов."""

    # Создаем сервис с моками
    service = SearchService(
        db=mock_db,
        sources=[mock_source],
        evaluator=mock_evaluator
    )

    # Мокаем db.get для обработки rollback
    mock_db.get.return_value = Search(id=uuid4(), query="python", status=SearchStatus.PROCESSING)

    # Вызываем поиск
    search_id = await service.execute_search("python", limit_per_source=1)

    # --- Проверки ---

    # 1. Проверяем, что база данных использовалась корректно
    assert mock_db.add.call_count >= 3  # Должны добавить Search, Candidate и Evaluation
    assert mock_db.flush.call_count >= 2  # После Search и после Candidate
    mock_db.commit.assert_called_once()  # Финальный коммит
    mock_db.rollback.assert_not_called()  # Откатов не было

    # 2. Проверяем, что источник был вызван
    mock_source.search.assert_called_once_with("python", limit=1)

    # 3. Проверяем, что Evaluator был вызван для найденного кандидата
    mock_evaluator.evaluate.assert_called_once()

    # 4. Проверяем, что вернулся UUID (благодаря add_side_effect он теперь не None)
    assert search_id is not None


@pytest.mark.asyncio
async def test_execute_search_source_error(
        mock_db: AsyncMock,
        mock_evaluator: AsyncMock
) -> None:
    """Тест: если один из источников падает, поиск продолжается с другими."""
    # Создаем два источника: один рабочий, другой падающий
    good_source = AsyncMock(spec=BaseSource)
    good_source.search.return_value = [RawCandidate(
        source="arxiv", external_id="999", name="Good", url="http://url", description=None
    )]

    bad_source = AsyncMock(spec=BaseSource)
    bad_source.search.side_effect = Exception("API Error")

    service = SearchService(
        db=mock_db,
        sources=[good_source, bad_source],
        evaluator=mock_evaluator
    )

    mock_db.get.return_value = Search(id=uuid4(), query="test", status=SearchStatus.PROCESSING)

    # Поиск не должен упасть с исключением
    search_id = await service.execute_search("test")

    # Проверяем, что оба источника были вызваны
    good_source.search.assert_called_once()
    bad_source.search.assert_called_once()

    # Несмотря на ошибку, Evaluator был вызван для рабочего источника
    mock_evaluator.evaluate.assert_called_once()

    # Финальный коммит прошел успешно
    mock_db.commit.assert_called_once()
    assert search_id is not None


@pytest.mark.asyncio
async def test_execute_search_critical_error(
        mock_db: AsyncMock,
        mock_source: AsyncMock,
        mock_evaluator: AsyncMock
) -> None:
    """Тест: если при сохранении в БД происходит ошибка, статус меняется на FAILED."""

    # Заставляем Evaluator выбросить исключение
    mock_evaluator.evaluate.side_effect = Exception("Critical DB Error")

    service = SearchService(
        db=mock_db,
        sources=[mock_source],
        evaluator=mock_evaluator
    )

    # Имитируем поиск в БД при rollback
    mock_search_obj = Search(id=uuid4(), query="test", status=SearchStatus.PROCESSING)
    mock_db.get.return_value = mock_search_obj

    # Ожидаем, что исключение пробросится дальше
    with pytest.raises(Exception, match="Critical DB Error"):
        await service.execute_search("test")

    # Проверяем, что был вызван rollback
    mock_db.rollback.assert_called_once()
    # Проверяем, что после rollback мы сходили в БД за объектом поиска
    mock_db.get.assert_called_once()
    # Проверяем, что статус изменился на FAILED
    assert mock_search_obj.status == SearchStatus.FAILED
    # Проверяем, что был вызван финальный коммит для сохранения статуса FAILED
    mock_db.commit.assert_called_once()
