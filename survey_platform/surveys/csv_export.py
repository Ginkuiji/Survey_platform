import csv
import io
from typing import Any

from django.utils import timezone


def _format_value(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _format_p_value(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if 0 < numeric_value < 0.0001:
        return "<0.0001"
    return f"{numeric_value:.4f}".rstrip("0").rstrip(".")


def _format_datetime(value: Any) -> str:
    if not value:
        return "—"
    try:
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime("%d.%m.%Y %H:%M")
    except AttributeError:
        return str(value)


def _report_result(analysis_report) -> dict:
    result = analysis_report.result or {}
    return result if isinstance(result, dict) else {}


def _variable_label(result: dict, code: str) -> str:
    if not code:
        return "—"
    if code == "intercept":
        return "Свободный член"
    variable = (result.get("variables_by_code") or {}).get(code) or {}
    return variable.get("label") or code


def build_analytics_csv(survey, analytic_result, analysis_report) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)

    def row(*values):
        writer.writerow([_format_value(value) for value in values])

    row("Раздел", "Показатель", "Значение", "Дополнительно 1", "Дополнительно 2", "Дополнительно 3", "Дополнительно 4", "Дополнительно 5")

    row("Опрос", "ID", survey.id)
    row("Опрос", "Название", survey.title)
    row("Опрос", "Описание", survey.description)
    row("Опрос", "Статус", survey.status)
    row("Опрос", "Дата начала", _format_datetime(survey.starts_at))
    row("Опрос", "Дата окончания", _format_datetime(survey.ends_at))
    row("Опрос", "Анонимный", "Да" if survey.is_anonymous else "Нет")

    data = analytic_result.data or {}
    row("Срез", "ID", analytic_result.id)
    row("Срез", "Название версии", analytic_result.title)
    row("Срез", "Дата сохранения", _format_datetime(analytic_result.generated_at))
    row("Срез", "Total responses", analytic_result.total_responses)

    summary = data.get("summary") or {}
    for key in (
        "total_started",
        "total_completed",
        "total_screened_out",
        "total_finished",
        "completion_rate",
        "screenout_rate",
        "finish_rate",
        "average_completion_time",
        "average_screenout_time",
        "questions_count",
    ):
        row("Summary", key, summary.get(key))

    screening = data.get("screening") or {}
    row("Скрининг", "total_screened_out", screening.get("total_screened_out"))
    row("Скрининг", "average_screenout_time", screening.get("average_screenout_time"))
    for item in screening.get("reasons") or []:
        row("Скрининг", "Причина", item.get("reason"), "count", item.get("count"))

    for question in data.get("questions") or []:
        question_id = question.get("id")
        qtype = question.get("qtype")
        result = question.get("result") or {}
        base = question.get("base") or {}
        section = f"Вопрос {question_id}"

        row("Вопрос", question_id, question.get("text"), "type", qtype)
        row("Вопрос", question_id, "total_completed", base.get("total_completed"))
        row("Вопрос", question_id, "shown_count", base.get("shown_count"))
        row("Вопрос", question_id, "answered_count", base.get("answered_count"))
        row("Вопрос", question_id, "skipped_count", base.get("skipped_count"))

        if qtype in ("single", "multi", "dropdown", "yesno"):
            for option in result.get("options") or []:
                row(
                    section,
                    "Вариант",
                    option.get("text"),
                    "count",
                    option.get("count"),
                    "percent_answered",
                    option.get("percent_answered"),
                    "percent_total",
                    option.get("percent_total"),
                )
        elif qtype in ("scale", "number"):
            row(section, "Среднее", result.get("average"))
            row(section, "Медиана", result.get("median"))
            row(section, "Минимум", result.get("min"))
            row(section, "Максимум", result.get("max"))
            for item in result.get("distribution") or []:
                row(section, "Распределение", item.get("value"), "count", item.get("count"))
        elif qtype in ("text", "date"):
            row(section, "Текстовых ответов", result.get("total_text_answers"))
            for text in (result.get("text_answers") or [])[:20]:
                row(section, "Ответ", text)
        elif qtype == "matrix_single":
            for matrix_row in result.get("rows") or []:
                for column in matrix_row.get("columns") or []:
                    row(
                        section,
                        "Матрица",
                        matrix_row.get("text"),
                        column.get("text"),
                        "count",
                        column.get("count"),
                        "percent_answered",
                        column.get("percent_answered"),
                        "percent_total",
                        column.get("percent_total"),
                    )
        elif qtype == "matrix_multi":
            for cell in result.get("cells") or []:
                row(
                    section,
                    "РњР°С‚СЂРёС†Р°",
                    cell.get("row_text"),
                    cell.get("column_text"),
                    "count",
                    cell.get("count"),
                    "percent_answered",
                    cell.get("percent_answered"),
                    "percent_total",
                    cell.get("percent_total"),
                )
            for item in result.get("row_summary") or []:
                row(
                    section,
                    "Row Summary",
                    item.get("row_text"),
                    "selected_total",
                    item.get("selected_total"),
                    "respondent_count",
                    item.get("respondent_count"),
                    "respondent_share",
                    item.get("respondent_share"),
                    "avg_selected_per_respondent",
                    item.get("avg_selected_per_respondent"),
                )
            for item in result.get("column_summary") or []:
                row(
                    section,
                    "Column Summary",
                    item.get("column_text"),
                    "selected_total",
                    item.get("selected_total"),
                    "respondent_count",
                    item.get("respondent_count"),
                    "respondent_share",
                    item.get("respondent_share"),
                )
        elif qtype == "ranking":
            for option in result.get("options") or []:
                row(
                    section,
                    "Ранжирование",
                    option.get("text"),
                    "average_rank",
                    option.get("average_rank"),
                    "first_place_count",
                    option.get("first_place_count"),
                )
                for item in option.get("rank_distribution") or []:
                    row(section, "Распределение мест", option.get("text"), "rank", item.get("rank"), "count", item.get("count"))

    report_result = _report_result(analysis_report)
    row("Отчёт", "ID", analysis_report.id)
    row("Отчёт", "Название", analysis_report.title)
    row("Отчёт", "Дата создания", _format_datetime(analysis_report.created_at))

    for section in report_result.get("sections") or []:
        title = section.get("title") or section.get("type")
        section_type = section.get("type")
        result = section.get("result") or {}

        if section.get("error"):
            row("Секция", title, "Ошибка", section.get("error"))
            continue

        if section_type == "correlation":
            row("Корреляция", title, "Метод", result.get("method"))
            row("Корреляция", title, "Dataset", result.get("dataset_size"))
            variables = result.get("variables") or []
            matrix = result.get("matrix") or []
            p_values = result.get("p_values") or []
            n_matrix = result.get("n_matrix") or []
            for variable in variables:
                row("Корреляция", title, "Переменная", variable.get("label") or variable.get("code"))
            for row_index, matrix_row in enumerate(matrix):
                for col_index, coefficient in enumerate(matrix_row):
                    row_label = variables[row_index].get("label") if row_index < len(variables) else f"R{row_index + 1}"
                    col_label = variables[col_index].get("label") if col_index < len(variables) else f"C{col_index + 1}"
                    row(
                        "Корреляция",
                        title,
                        "Матрица",
                        row_label,
                        col_label,
                        "coefficient",
                        coefficient,
                        "p_value",
                        _format_p_value((p_values[row_index] or [None])[col_index]) if row_index < len(p_values) and col_index < len(p_values[row_index] or []) else None,
                        "n",
                        (n_matrix[row_index] or [None])[col_index] if row_index < len(n_matrix) and col_index < len(n_matrix[row_index] or []) else None,
                    )
        elif section_type == "crosstab":
            crosstab = result.get("crosstab") or {}
            row("Таблица сопряжённости", title, "row_variable", crosstab.get("row_variable"), "column_variable", crosstab.get("column_variable"))
            for crosstab_row in crosstab.get("rows") or []:
                for column in crosstab_row.get("columns") or []:
                    row(
                        "Таблица сопряжённости",
                        title,
                        crosstab_row.get("value"),
                        column.get("value"),
                        "count",
                        column.get("count"),
                        "percent_row",
                        column.get("percent_row"),
                        "percent_total",
                        column.get("percent_total"),
                    )
        elif section_type == "chi_square":
            crosstab = result.get("crosstab") or {}
            chi = result.get("chi_square") or {}
            cramers_v = result.get("cramers_v") or {}
            row("χ²", title, "chi2", chi.get("chi2"))
            row("χ²", title, "p_value", _format_p_value(chi.get("p_value")))
            row("χ²", title, "dof", chi.get("dof"))
            row("χ²", title, "cramers_v", cramers_v.get("cramers_v"))
            row("χ²", title, "cramers_v_interpretation", cramers_v.get("interpretation"))
            row("χ²", title, "n", cramers_v.get("n"))
            row("χ²", title, "rows", cramers_v.get("rows"))
            row("χ²", title, "columns", cramers_v.get("columns"))
            for crosstab_row in crosstab.get("rows") or []:
                for column in crosstab_row.get("columns") or []:
                    row("χ²", title, crosstab_row.get("value"), column.get("value"), "count", column.get("count"), "percent_row", column.get("percent_row"), "percent_total", column.get("percent_total"))
            for row_index, expected_row in enumerate(chi.get("expected") or []):
                for col_index, value in enumerate(expected_row):
                    row("χ²", title, "expected", f"R{row_index + 1}", f"C{col_index + 1}", value)
        elif section_type == "regression":
            row("Регрессия", title, "target", _variable_label(result, result.get("target")))
            row("Регрессия", title, "features", ", ".join(_variable_label(result, code) for code in (result.get("features") or [])))
            row("Регрессия", title, "n", result.get("n"))
            row("Регрессия", title, "r2", result.get("r2"))
            row("Регрессия", title, "adjusted_r2", result.get("adjusted_r2"))
            for coefficient in result.get("coefficients") or []:
                row("Регрессия", title, "coefficient", _variable_label(result, coefficient.get("name")), "value", coefficient.get("value"))

        elif section_type == "factor_analysis":
            row("Factor analysis", title, "method", result.get("method"))
            row("Factor analysis", title, "n", result.get("n"))
            row("Factor analysis", title, "n_variables", result.get("n_variables"))
            row("Factor analysis", title, "n_factors", result.get("n_factors"))
            row("Factor analysis", title, "rotation", result.get("rotation"))
            row("Factor analysis", title, "standardize", result.get("standardize"))
            row("Factor analysis", title, "cumulative_explained_variance", result.get("cumulative_explained_variance"))
            for index, value in enumerate(result.get("eigenvalues") or [], start=1):
                row("Factor analysis", title, "eigenvalue", f"Component {index}", value)
            for item in result.get("explained_variance") or []:
                row("Factor analysis", title, "explained_variance", item.get("factor"), item.get("value"))
            for item in result.get("loadings") or []:
                for factor in item.get("factors") or []:
                    row("Factor analysis", title, "loading", item.get("label") or item.get("variable"), factor.get("factor"), factor.get("loading"))
                row("Factor analysis", title, "communality", item.get("label") or item.get("variable"), item.get("communality"))
            for warning in result.get("warnings") or []:
                row("Factor analysis", title, "warning", warning)

        elif section_type == "cluster_analysis":
            row("Cluster analysis", title, "method", result.get("method"))
            row("Cluster analysis", title, "n", result.get("n"))
            row("Cluster analysis", title, "n_clusters", result.get("n_clusters"))
            row("Cluster analysis", title, "standardize", result.get("standardize"))
            row("Cluster analysis", title, "inertia", result.get("inertia"))
            variables = result.get("variables") or []
            variables_by_code = {
                variable.get("code"): variable.get("label") or variable.get("code")
                for variable in variables
            }
            for cluster in result.get("clusters") or []:
                row(
                    "Cluster analysis",
                    title,
                    "cluster_size",
                    cluster.get("cluster"),
                    "size",
                    cluster.get("size"),
                    "percent",
                    cluster.get("percent"),
                )
                for code, value in (cluster.get("centroid") or {}).items():
                    row(
                        "Cluster analysis",
                        title,
                        "centroid",
                        cluster.get("cluster"),
                        variables_by_code.get(code, code),
                        value,
                    )
            for warning in result.get("warnings") or []:
                row("Cluster analysis", title, "warning", warning)

    csv_text = output.getvalue()
    return ("\ufeff" + csv_text).encode("utf-8")
