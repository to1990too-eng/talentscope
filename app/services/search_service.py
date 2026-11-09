"""Сервис оркестрации поиска и оценки кандидатов."""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.search import Evaluation, Search, SearchStatus
from app.services.evaluator import Evaluator
from app.sources.base import BaseSource, RawCandidate

logger = logging.getLogger(__name__)


class SearchService:
    """Управляет процессом поиска: сбор данных -> оценка -> сохранение в БД."""

    def __init__(
            self,
            db: AsyncSession,
            sources: list[BaseSource],
            evaluator: Evaluator,
    ) -> None:
        """
        Инициализация сервиса.

        :param db: Асинхронная сессия базы данных.
        :param sources: Список активных источников (GitHub, arXiv, OpenAlex).
        :param evaluator: Сервис оценки (Claude).
        """
        self.db = db
        self.sources = sources
        self.evaluator = evaluator

    async def execute_search(self, query: str, limit_per_source: int = 5) -> UUID:
        """
        Выполняет полный цикл поиска и сохраняет результаты.

        :return: UUID созданного поискового запроса.
        """
        # 1. Создаем запись о поиске в статусе PROCESSING
        search = Search(query=query, status=SearchStatus.PROCESSING)
        self.db.add(search)
        await self.db.flush()  # Получаем UUID для search.id

        try:
            # 2. Параллельно опрашиваем все источники через asyncio.gather
            logger.info(f"Запуск поиска '{query}' по {len(self.sources)} источникам...")
            tasks = [source.search(query, limit=limit_per_source) for source in self.sources]

            # return_exceptions=True не дает упасть всему gather, если один источник упал
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Собираем всех найденных кандидатов в один список
            raw_candidates: list[RawCandidate] = []
            for i, result in enumerate(results):
                # Проверяем именно BaseException, чтобы mypy понял, что дальше идет list[RawCandidate]
                if isinstance(result, BaseException):
                    logger.error(f"Ошибка в источнике {self.sources[i].__class__.__name__}: {result}")
                    continue
                raw_candidates.extend(result)

            logger.info(f"Найдено {len(raw_candidates)} кандидатов. Начинаем оценку...")

            # 3. Обрабатываем каждого кандидата
            for raw_cand in raw_candidates:
                # Проверяем, есть ли уже такой кандидат в БД (чтобы не дублировать)
                stmt = select(Candidate).where(
                    Candidate.source == raw_cand.source,
                    Candidate.external_id == raw_cand.external_id,
                )
                existing_cand = (await self.db.execute(stmt)).scalar_one_or_none()

                if not existing_cand:
                    # Если нет — создаем нового
                    db_cand = Candidate(
                        source=raw_cand.source,
                        external_id=raw_cand.external_id,
                        name=raw_cand.name,
                        url=raw_cand.url,
                        description=raw_cand.description,
                    )
                    self.db.add(db_cand)
                    await self.db.flush()  # Получаем UUID для db_cand.id
                else:
                    db_cand = existing_cand

                # 4. Оцениваем кандидата через Evaluator (Claude + Redis)
                evaluation_result = await self.evaluator.evaluate(query, raw_cand)

                # 5. Сохраняем оценку в БД
                db_eval = Evaluation(
                    search_id=search.id,
                    candidate_id=db_cand.id,
                    score=evaluation_result.score,
                    reasoning=evaluation_result.reasoning,
                )
                self.db.add(db_eval)

            # 6. Если всё прошло успешно, меняем статус на COMPLETED и коммитим
            search.status = SearchStatus.COMPLETED
            await self.db.commit()
            logger.info(f"Поиск {search.id} успешно завершен.")

            return search.id

        except Exception as e:
            # 7. Обработка ошибок: откатываем транзакцию и ставим статус FAILED
            logger.exception(f"Критическая ошибка при выполнении поиска {search.id}: {e}")
            await self.db.rollback()

            # ИСПРАВЛЕНИЕ: используем новую переменную failed_search, чтобы не ломать типизацию
            failed_search = await self.db.get(Search, search.id)
            if failed_search:
                failed_search.status = SearchStatus.FAILED
                await self.db.commit()

            raise e
