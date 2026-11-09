"""Фоновый воркер для обработки очереди поисковых задач."""

import asyncio
import json
import logging
from typing import cast
from uuid import UUID

from app.database import async_session_factory, engine
from app.redis_client import redis_client
from app.services.evaluator import Evaluator
from app.services.search_service import SearchService
from app.sources.arxiv import ArxivSource
from app.sources.github import GitHubSource
from app.sources.openalex import OpenAlexSource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUEUE_NAME = "search_queue"


async def process_task(payload_str: str) -> None:
    """Обрабатывает одну задачу из очереди."""
    payload = json.loads(payload_str)
    search_id = UUID(payload["search_id"])
    query = payload["query"]

    logger.info(f"Воркер взял задачу {search_id} (запрос: '{query}')")

    # Открываем новую сессию БД для каждой задачи
    async with async_session_factory() as db:
        # Инициализируем зависимости
        sources = [GitHubSource(), ArxivSource(), OpenAlexSource()]
        evaluator = Evaluator()
        service = SearchService(db=db, sources=sources, evaluator=evaluator)

        try:
            # Передаем search_id, чтобы сервис обновил существующую запись
            await service.execute_search(query=query, search_id=search_id)
            logger.info(f"Задача {search_id} успешно выполнена.")
        except Exception as e:
            logger.error(f"Ошибка при выполнении задачи {search_id}: {e}")


async def main() -> None:
    """Бесконечный цикл прослушивания очереди Redis."""
    logger.info("Воркер запущен и ждет задачи...")

    try:
        while True:
            # BRPOP блокирует выполнение, пока в списке не появится элемент.
            # 0 означает "ждать бесконечно".
            result = await redis_client.brpop(QUEUE_NAME, timeout=0)

            if result:
                # result возвращает кортеж (имя_ключа, значение)
                # ИСПРАВЛЕНИЕ: используем cast(str, ...), чтобы успокоить mypy
                _, payload_str = result
                await process_task(cast(str, payload_str))

    except asyncio.CancelledError:
        logger.info("Воркер остановлен.")
    finally:
        # Корректно закрываем соединения при выключении
        await engine.dispose()
        await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Воркер прерван пользователем (Ctrl+C).")
