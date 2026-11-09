"""Сервис оценки кандидатов с помощью Claude API."""

import hashlib
import json
import logging
import re

import redis.asyncio as redis
from anthropic import AnthropicError, AsyncAnthropic
from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.redis_client import redis_client
from app.sources.base import RawCandidate

logger = logging.getLogger(__name__)


class EvaluationResult(BaseModel):
    """Результат оценки кандидата."""
    score: float = Field(..., ge=1.0, le=10.0, description="Оценка релевантности от 1.0 до 10.0")
    reasoning: str = Field(..., description="Обоснование оценки на русском языке")


class Evaluator:
    """Сервис для оценки кандидатов с использованием LLM (Claude)."""

    def __init__(
            self,
            redis_conn: redis.Redis | None = None,
            anthropic_client: AsyncAnthropic | None = None
    ) -> None:
        self.settings = get_settings()
        self.redis = redis_conn or redis_client

        # Ленивая инициализация клиента Anthropic (для удобства тестирования)
        if anthropic_client:
            self.anthropic = anthropic_client
        else:
            self.anthropic = AsyncAnthropic(api_key=self.settings.anthropic_api_key)

    def _get_cache_key(self, query: str, external_id: str) -> str:
        """Генерирует уникальный ключ для кэша Redis."""
        query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
        return f"eval:{query_hash}:{external_id}"

    def _build_prompt(self, query: str, candidate: RawCandidate) -> str:
        """Формирует промпт для LLM."""
        return f"""
        Ты — опытный IT-рекрутер. Оцени релевантность кандидата для следующего поискового запроса.

        Поисковый запрос: "{query}"

        Данные кандидата:
        - Источник: {candidate.source}
        - Имя: {candidate.name}
        - Описание: {candidate.description or "Нет описания"}
        - Ссылка: {candidate.url}

        Оцени кандидата по шкале от 1.0 до 10.0, где 10 — идеальное совпадение.
        ВАЖНО: Твой ответ должен быть СТРОГО в формате JSON без каких-либо дополнительных текстов.
        Формат ответа:
        {{
            "score": 8.5,
            "reasoning": "Краткое обоснование на русском языке, почему поставлена такая оценка."
        }}
        """

    def _parse_llm_response(self, response_text: str) -> EvaluationResult:
        """Извлекает JSON из ответа LLM и валидирует его. Содержит fallback."""
        try:
            # Иногда LLM оборачивает JSON в markdown-блоки (```json ... ```)
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if not json_match:
                raise ValueError("В ответе LLM не найден JSON")

            data = json.loads(json_match.group(0))
            return EvaluationResult(**data)

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            logger.error(f"Ошибка парсинга ответа LLM: {e}. Текст ответа: {response_text}")
            # Fallback: если LLM сломалась, ставим нейтральную оценку
            return EvaluationResult(
                score=5.0,
                reasoning="Ошибка автоматической оценки. Не удалось разобрать ответ AI."
            )

    async def evaluate(self, query: str, candidate: RawCandidate) -> EvaluationResult:
        """Оценивает кандидата, используя кэш Redis или обращаясь к Claude API."""
        cache_key = self._get_cache_key(query, candidate.external_id)

        # 1. Проверяем кэш в Redis
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.info(f"Кэш-хит для {candidate.external_id}")
            try:
                return EvaluationResult.model_validate_json(cached_data)
            except ValidationError:
                logger.warning("Битые данные в кэше, перезапрашиваем LLM")

        # 2. Если в кэше нет — идем в Claude API
        logger.info(f"Запрос к Claude API для {candidate.external_id}")
        prompt = self._build_prompt(query, candidate)

        try:
            response = await self.anthropic.messages.create(
                model=self.settings.anthropic_model,
                max_tokens=500,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )

            # ИСПРАВЛЕНИЕ: используем getattr для безопасного извлечения текста
            first_block = response.content[0]
            response_text = str(getattr(first_block, "text", ""))

        except AnthropicError as e:
            logger.error(f"Ошибка Claude API: {e}")
            return EvaluationResult(
                score=5.0,
                reasoning="Ошибка API Claude. Пожалуйста, проверьте логи."
            )

        # 3. Парсим ответ
        result = self._parse_llm_response(response_text)

        # 4. Сохраняем в кэш на 24 часа (86400 секунд)
        await self.redis.set(
            cache_key,
            result.model_dump_json(),
            ex=86400
        )

        return result
