"""Сервис генерации Excel-файлов."""

import io
from typing import cast

from openpyxl import Workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.models.search import Evaluation


class ExcelExporter:
    """Класс для генерации Excel-отчета с кандидатами."""

    @staticmethod
    def _format_worksheet(ws: Worksheet) -> None:
        """Делает заголовки жирными и красивыми, а колонки — широкими."""
        # Стилизация заголовков (первая строка)
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="4F81BD", end_color="4F81BD", fill_type="solid"
        )
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Автоподбор ширины колонок
        for col_idx, col in enumerate(ws.columns, start=1):
            max_length = 0
            # ИСПРАВЛЕНИЕ: используем get_column_letter вместо col[0].column_letter
            column_letter = get_column_letter(col_idx)

            for cell in col:
                # Пропускаем объединенные ячейки (MergedCell), у них нет значения
                if isinstance(cell, MergedCell):
                    continue
                try:
                    if cell.value is not None:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass

            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

    @classmethod
    def export_to_excel(cls, evaluations: list[Evaluation]) -> bytes:
        """
        Генерирует Excel-файл на основе списка оценок.

        :param evaluations: Список объектов Evaluation из базы данных.
        :return: Бинарное содержимое файла (bytes).
        """
        wb = Workbook()
        # ИСПРАВЛЕНИЕ: явно приводим тип, так как mypy думает, что active может быть None
        ws = cast(Worksheet, wb.active)
        ws.title = "Candidates"

        # 1. Записываем заголовки
        headers = ["ID", "Источник", "Имя", "Ссылка", "Описание", "Оценка", "Обоснование"]
        ws.append(headers)

        # 2. Заполняем данными
        for eval_obj in evaluations:
            cand = eval_obj.candidate
            ws.append([
                str(cand.id),
                cand.source,
                cand.name,
                cand.url,
                cand.description or "Нет описания",
                eval_obj.score,
                eval_obj.reasoning,
            ])

        # 3. Применяем стили
        cls._format_worksheet(ws)

        # 4. Сохраняем в BytesIO
        output = io.BytesIO()
        wb.save(output)

        return output.getvalue()
