# ==========================================
# Stage 1: Builder (Сборка зависимостей)
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Устанавливаем системные зависимости для сборки (компиляторы и заголовочные файлы)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements.txt, чтобы Docker закэшировал этот слой
COPY requirements.txt .

# Устанавливаем Python-зависимости в отдельную папку /install
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ==========================================
# Stage 2: Final (Финальный образ)
# ==========================================
FROM python:3.11-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Устанавливаем только те системные библиотеки, которые нужны для работы в рантайме
# libpq5 - нужна для asyncpg (PostgreSQL), curl - нужен для healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные пакеты из стадии builder
COPY --from=builder /install /usr/local

# Создаем непривилегированного пользователя (non-root)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Копируем код проекта (с правами для appuser)
COPY --chown=appuser:appuser . .

# Переключаемся на непривилегированного пользователя
USER appuser

# Открываем порт (информативно)
EXPOSE 8000

# По умолчанию запускаем веб-сервер (воркер переопределит эту команду в compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]