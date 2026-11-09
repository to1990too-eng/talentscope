"""Тесты для сервиса экспорта в Excel."""

import io
from uuid import uuid4

import pytest
from openpyxl import load_workbook

from app.models.candidate import Candidate
from app.models.search import Evaluation
from app.services.exporter import ExcelExporter


@pytest.fixture
def sample_evaluations() -> list[Evaluation]:
    """Фикстура с тестовыми данными."""
    # Создаем фейкового кандидата (без сохранения в БД)
    candidate = Candidate(
        id=uuid4(),
        source="github",
        external_id="12345",
        name="John Doe",
        url="https://github.com/johndoe",
        description="Python Developer"
    )

    # Создаем оценку
    evaluation = Evaluation(
        id=uuid4(),
        search_id=uuid4(),
        candidate_id=candidate.id,
        score=9.5,
        reasoning="Отличный специалист",
        candidate=candidate
    )

    return [evaluation]


def test_export_to_excel(sample_evaluations: list[Evaluation]) -> None:
    """Проверяем, что Excel-файл генерируется и содержит нужные колонки."""

    # 1. Генерируем файл
    excel_bytes = ExcelExporter.export_to_excel(sample_evaluations)

    # Проверяем, что это не пустой файл
    assert len(excel_bytes) > 0

    # 2. Загружаем сгенерированный файл обратно в память для проверки
    wb = load_workbook(io.BytesIO(excel_bytes))
    ws = wb.active

    # 3. Проверяем заголовки
    expected_headers = ["ID", "Источник", "Имя", "Ссылка", "Описание", "Оценка", "Обоснование"]
    for col_idx, header in enumerate(expected_headers, start=1):
        assert ws.cell(row=1, column=col_idx).value == header

    # 4. Проверяем данные первой строки (нашего тестового кандидата)
    row = 2
    assert ws.cell(row=row, column=2).value == "github"
    assert ws.cell(row=row, column=3).value == "John Doe"
    assert ws.cell(row=row, column=6).value == 9.5
    assert ws.cell(row=row, column=7).value == "Отличный специалист"


def test_export_to_excel_empty() -> None:
    """Проверяем, что пустой список генерирует файл только с заголовками."""
    excel_bytes = ExcelExporter.export_to_excel([])
    wb = load_workbook(io.BytesIO(excel_bytes))
    ws = wb.active

    # В таблице должна быть только 1 строка (с заголовками)
    assert ws.max_row == 1
    assert ws.cell(row=1, column=1).value == "ID"
