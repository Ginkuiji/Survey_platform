from io import BytesIO
from typing import Any

from django.utils import timezone


def format_value(value: Any):
    if value is None or value == "":
        return "—"
    return value


def format_number(value: Any):
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return round(number, 4)


def format_p_value(value: Any):
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    if 0 < number < 0.0001:
        return "<0.0001"
    return round(number, 4)


def format_datetime(value: Any) -> str:
    if not value:
        return "—"
    try:
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime("%d.%m.%Y %H:%M")
    except AttributeError:
        return str(value)


def get_variable_label(result: dict, code: str) -> str:
    if not code:
        return "—"
    if code == "intercept":
        return "Свободный член"
    variable = (result.get("variables_by_code") or {}).get(code) or {}
    return variable.get("label") or code


def append_key_value(ws, key, value):
    ws.append([key, format_value(value)])


def append_section_title(ws, title):
    row_number = ws.max_row + 1
    ws.append([title])
    ws.cell(row=row_number, column=1).style = "Title"


def autosize_columns(ws):
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            cell.alignment = cell.alignment.copy(wrap_text=True, vertical="top")
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, min(len(value), 80))
        ws.column_dimensions[column_letter].width = max(max_length + 2, 12)


def _style_header(ws, row_number):
    from openpyxl.styles import Font, PatternFill

    for cell in ws[row_number]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="EDEDED")


def _append_table(ws, headers, rows):
    start = ws.max_row + 1
    ws.append(headers)
    _style_header(ws, start)
    for row in rows:
        ws.append([format_value(value) for value in row])


def _report_result(analysis_report) -> dict:
    result = analysis_report.result or {}
    return result if isinstance(result, dict) else {}


def _ordered_questions(survey, questions):
    order_by_id = {
        question.id: index
        for index, question in enumerate(
            survey.questions.select_related("page").order_by("page__order", "order", "id")
        )
    }
    return sorted(questions, key=lambda item: order_by_id.get(item.get("id"), 10**9))


def _add_questions_sheet(ws, survey, analytic_data):
    questions = _ordered_questions(survey, analytic_data.get("questions") or [])
    for question in questions:
        result = question.get("result") or {}
        base = question.get("base") or {}
        qtype = question.get("qtype")
        append_section_title(ws, f"Вопрос {question.get('id')}")
        append_key_value(ws, "ID вопроса", question.get("id"))
        append_key_value(ws, "Текст", question.get("text"))
        append_key_value(ws, "Тип", qtype)
        append_key_value(ws, "Завершили опрос", base.get("total_completed"))
        append_key_value(ws, "Видели вопрос", base.get("shown_count"))
        append_key_value(ws, "Ответили", base.get("answered_count"))
        append_key_value(ws, "Пропустили", base.get("skipped_count"))

        if qtype in ("single", "multi", "dropdown", "yesno"):
            _append_table(
                ws,
                ["Вариант", "Количество", "% от ответивших", "% от завершивших"],
                [
                    [
                        option.get("text"),
                        option.get("count"),
                        format_number(option.get("percent_answered")),
                        format_number(option.get("percent_total")),
                    ]
                    for option in result.get("options") or []
                ],
            )
        elif qtype in ("scale", "number"):
            append_key_value(ws, "Среднее", format_number(result.get("average")))
            append_key_value(ws, "Медиана", format_number(result.get("median")))
            append_key_value(ws, "Минимум", format_number(result.get("min")))
            append_key_value(ws, "Максимум", format_number(result.get("max")))
            _append_table(
                ws,
                ["Значение", "Количество"],
                [[item.get("value"), item.get("count")] for item in result.get("distribution") or []],
            )
        elif qtype in ("text", "date"):
            append_key_value(ws, "Количество текстовых ответов", result.get("total_text_answers"))
            _append_table(
                ws,
                ["№", "Ответ"],
                [[index + 1, text] for index, text in enumerate((result.get("text_answers") or [])[:20])],
            )
        elif qtype in ("matrix_single", "matrix_multi"):
            rows = []
            for matrix_row in result.get("rows") or []:
                for column in matrix_row.get("columns") or []:
                    rows.append([
                        matrix_row.get("text"),
                        column.get("text"),
                        column.get("count"),
                        format_number(column.get("percent_answered")),
                        format_number(column.get("percent_total")),
                    ])
            _append_table(ws, ["Строка", "Колонка", "Количество", "% от ответивших", "% от завершивших"], rows)
        elif qtype == "ranking":
            options = result.get("options") or []
            _append_table(
                ws,
                ["Вариант", "Средний ранг", "Первое место"],
                [[option.get("text"), format_number(option.get("average_rank")), option.get("first_place_count")] for option in options],
            )
            rank_rows = []
            for option in options:
                for item in option.get("rank_distribution") or []:
                    rank_rows.append([
                        option.get("text"),
                        item.get("rank"),
                        item.get("count"),
                        format_number(item.get("percent_answered")),
                        format_number(item.get("percent_total")),
                    ])
            _append_table(ws, ["Вариант", "Ранг", "Количество", "% от ответивших", "% от завершивших"], rank_rows)
        ws.append([])


def _append_matrix(ws, title, variables, matrix, formatter=format_number):
    append_section_title(ws, title)
    labels = [variable.get("label") or variable.get("code") for variable in variables]
    if not labels and matrix:
        labels = [f"C{index + 1}" for index in range(len(matrix[0]))]
    ws.append([""] + labels)
    _style_header(ws, ws.max_row)
    for index, row in enumerate(matrix or []):
        label = labels[index] if index < len(labels) else f"R{index + 1}"
        ws.append([label] + [formatter(value) for value in row])


def _append_crosstab(ws, crosstab):
    rows = crosstab.get("rows") or []
    if not rows:
        ws.append(["Нет данных для таблицы сопряжённости"])
        return
    column_values = [column.get("value") for column in rows[0].get("columns") or []]
    ws.append([crosstab.get("row_variable") or "row"] + column_values + ["Итого"])
    _style_header(ws, ws.max_row)
    for row in rows:
        ws.append([
            row.get("value"),
            *[
                f"{column.get('count')} | row {format_number(column.get('percent_row'))}% | total {format_number(column.get('percent_total'))}%"
                for column in row.get("columns") or []
            ],
            row.get("total"),
        ])


def _add_report_sheet(ws, analysis_report):
    report_result = _report_result(analysis_report)
    append_key_value(ws, "Название отчёта", analysis_report.title)
    append_key_value(ws, "Дата создания", format_datetime(analysis_report.created_at))
    append_key_value(ws, "Количество секций", len(report_result.get("sections") or []))
    ws.append([])

    for section in report_result.get("sections") or []:
        title = section.get("title") or section.get("type")
        section_type = section.get("type")
        result = section.get("result") or {}
        append_section_title(ws, title)
        append_key_value(ws, "Тип", section_type)

        if section.get("error"):
            append_key_value(ws, "Ошибка", section.get("error"))
            ws.append([])
            continue

        if section_type == "correlation":
            append_key_value(ws, "Метод", result.get("method"))
            append_key_value(ws, "Dataset size", result.get("dataset_size"))
            variables = result.get("variables") or []
            _append_matrix(ws, "Корреляционная матрица", variables, result.get("matrix") or [])
            _append_matrix(ws, "P-values", variables, result.get("p_values") or [], format_p_value)
            _append_matrix(ws, "N matrix", variables, result.get("n_matrix") or [], format_value)
        elif section_type == "crosstab":
            _append_crosstab(ws, result.get("crosstab") or {})
        elif section_type == "chi_square":
            chi = result.get("chi_square") or {}
            append_key_value(ws, "chi2", format_number(chi.get("chi2")))
            append_key_value(ws, "p_value", format_p_value(chi.get("p_value")))
            append_key_value(ws, "dof", chi.get("dof"))
            _append_crosstab(ws, result.get("crosstab") or {})
            _append_matrix(ws, "Expected values", [], chi.get("expected") or [])
        elif section_type == "regression":
            append_key_value(ws, "target", get_variable_label(result, result.get("target")))
            append_key_value(ws, "features", ", ".join(get_variable_label(result, code) for code in (result.get("features") or [])))
            append_key_value(ws, "n", result.get("n"))
            append_key_value(ws, "r2", format_number(result.get("r2")))
            append_key_value(ws, "adjusted_r2", format_number(result.get("adjusted_r2")))
            _append_table(
                ws,
                ["Коэффициент", "Значение"],
                [
                    [get_variable_label(result, coefficient.get("name")), format_number(coefficient.get("value"))]
                    for coefficient in result.get("coefficients") or []
                ],
            )
        ws.append([])


def build_analytics_xlsx(survey, analytic_result, analysis_report) -> bytes:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError as exc:  # pragma: no cover - depends on deployment environment
        raise RuntimeError("XLSX export requires openpyxl to be installed.") from exc

    wb = Workbook()
    ws_survey = wb.active
    ws_survey.title = "Опрос"
    ws_summary = wb.create_sheet("Сводка")
    ws_screening = wb.create_sheet("Скрининг")
    ws_questions = wb.create_sheet("Вопросы")
    ws_report = wb.create_sheet("Отчёт")

    analytic_data = analytic_result.data or {}

    for ws in wb.worksheets:
        ws.freeze_panes = "A2"

    ws_survey.append(["Показатель", "Значение"])
    _style_header(ws_survey, 1)
    for key, value in (
        ("ID опроса", survey.id),
        ("Название", survey.title),
        ("Описание", survey.description),
        ("Статус", survey.status),
        ("Дата начала", format_datetime(survey.starts_at)),
        ("Дата окончания", format_datetime(survey.ends_at)),
        ("Анонимный", "Да" if survey.is_anonymous else "Нет"),
        ("Дата формирования XLSX", format_datetime(timezone.now())),
        ("Название среза общей аналитики", analytic_result.title),
        ("Дата среза", format_datetime(analytic_result.generated_at)),
        ("Название пользовательского отчёта", analysis_report.title),
        ("Дата пользовательского отчёта", format_datetime(analysis_report.created_at)),
    ):
        append_key_value(ws_survey, key, value)

    ws_summary.append(["Показатель", "Значение"])
    _style_header(ws_summary, 1)
    summary = analytic_data.get("summary") or {}
    summary_labels = {
        "total_started": "Начали",
        "total_completed": "Завершили полностью",
        "total_screened_out": "Отсечены",
        "total_finished": "Завершили всего",
        "completion_rate": "Процент полного завершения",
        "screenout_rate": "Процент скрининга",
        "finish_rate": "Процент завершения всего",
        "average_completion_time": "Среднее время завершения",
        "average_screenout_time": "Среднее время до скрининга",
        "questions_count": "Количество вопросов",
    }
    for key, label in summary_labels.items():
        append_key_value(ws_summary, label, format_number(summary.get(key)))

    ws_screening.append(["Показатель", "Значение"])
    _style_header(ws_screening, 1)
    screening = analytic_data.get("screening") or {}
    append_key_value(ws_screening, "total_screened_out", screening.get("total_screened_out"))
    append_key_value(ws_screening, "average_screenout_time", format_number(screening.get("average_screenout_time")))
    ws_screening.append([])
    reasons = screening.get("reasons") or []
    if reasons:
        _append_table(ws_screening, ["Причина", "Количество"], [[item.get("reason"), item.get("count")] for item in reasons])
    else:
        ws_screening.append(["Нет screened_out ответов"])

    _add_questions_sheet(ws_questions, survey, analytic_data)
    _add_report_sheet(ws_report, analysis_report)

    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = True
        for cell in ws[1]:
            cell.font = Font(bold=True)
        autosize_columns(ws)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
