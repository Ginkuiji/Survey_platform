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
        elif section_type == "correspondence_analysis":
            row("Анализ соответствий", title, "method", result.get("method"))
            row("Анализ соответствий", title, "n", result.get("n"))
            row("Анализ соответствий", title, "n_rows", result.get("n_rows"))
            row("Анализ соответствий", title, "n_columns", result.get("n_columns"))
            row("Анализ соответствий", title, "n_dimensions", result.get("n_dimensions"))
            row("Анализ соответствий", title, "total_inertia", result.get("total_inertia"))
            for dimension in result.get("dimensions") or []:
                row(
                    "Анализ соответствий",
                    title,
                    "dimension",
                    dimension.get("dimension"),
                    "eigenvalue",
                    dimension.get("eigenvalue"),
                    "explained_inertia",
                    dimension.get("explained_inertia"),
                )
            crosstab = result.get("crosstab") or {}
            for crosstab_row in crosstab.get("rows") or []:
                for column in crosstab_row.get("columns") or []:
                    row(
                        "Анализ соответствий",
                        title,
                        "crosstab",
                        crosstab_row.get("value"),
                        column.get("value"),
                        "count",
                        column.get("count"),
                    )
            for point in result.get("row_coordinates") or []:
                for coord in point.get("coordinates") or []:
                    row("Анализ соответствий", title, "row_coordinate", point.get("label"), coord.get("dimension"), coord.get("value"), "cos2", point.get("cos2"))
                for contribution in point.get("contributions") or []:
                    row("Анализ соответствий", title, "row_contribution", point.get("label"), contribution.get("dimension"), contribution.get("value"))
            for point in result.get("column_coordinates") or []:
                for coord in point.get("coordinates") or []:
                    row("Анализ соответствий", title, "column_coordinate", point.get("label"), coord.get("dimension"), coord.get("value"), "cos2", point.get("cos2"))
                for contribution in point.get("contributions") or []:
                    row("Анализ соответствий", title, "column_contribution", point.get("label"), contribution.get("dimension"), contribution.get("value"))
            for warning in result.get("warnings") or []:
                row("Анализ соответствий", title, "warning", warning)
        elif section_type == "regression":
            row("Регрессия", title, "target", _variable_label(result, result.get("target")))
            row("Регрессия", title, "features", ", ".join(_variable_label(result, code) for code in (result.get("features") or [])))
            row("Регрессия", title, "n", result.get("n"))
            row("Регрессия", title, "r2", result.get("r2"))
            row("Регрессия", title, "adjusted_r2", result.get("adjusted_r2"))
            for coefficient in result.get("coefficients") or []:
                row("Регрессия", title, "coefficient", _variable_label(result, coefficient.get("name")), "value", coefficient.get("value"))

        elif section_type == "logistic_regression":
            metrics = result.get("metrics") or {}
            confusion = result.get("confusion_matrix") or {}
            row("Логистическая регрессия", title, "method", result.get("method"))
            row("Логистическая регрессия", title, "target", _variable_label(result, result.get("target")))
            row("Логистическая регрессия", title, "features", ", ".join(_variable_label(result, code) for code in (result.get("features") or [])))
            row("Логистическая регрессия", title, "n", result.get("n"))
            row("Логистическая регрессия", title, "positive_class_count", result.get("positive_class_count"))
            row("Логистическая регрессия", title, "negative_class_count", result.get("negative_class_count"))
            row("Логистическая регрессия", title, "base_rate", result.get("base_rate"))
            row("Логистическая регрессия", title, "threshold", result.get("threshold"))
            row("Логистическая регрессия", title, "accuracy", metrics.get("accuracy"))
            row("Логистическая регрессия", title, "precision", metrics.get("precision"))
            row("Логистическая регрессия", title, "recall", metrics.get("recall"))
            row("Логистическая регрессия", title, "f1", metrics.get("f1"))
            row("Логистическая регрессия", title, "mcfadden_r2", metrics.get("mcfadden_r2"))
            row(
                "Логистическая регрессия",
                title,
                "confusion_matrix",
                "tp",
                confusion.get("tp"),
                "tn",
                confusion.get("tn"),
                "fp",
                confusion.get("fp"),
                "fn",
                confusion.get("fn"),
            )
            for coefficient in result.get("coefficients") or []:
                row(
                    "Логистическая регрессия",
                    title,
                    "coefficient",
                    _variable_label(result, coefficient.get("name")),
                    "value",
                    coefficient.get("coefficient"),
                    "odds_ratio",
                    coefficient.get("odds_ratio"),
                    "interpretation",
                    coefficient.get("interpretation"),
                )
            for warning in result.get("warnings") or []:
                row("Логистическая регрессия", title, "warning", warning)

        elif section_type == "factor_analysis":
            row("Factor analysis", title, "method", result.get("method"))
            row("Factor analysis", title, "n", result.get("n"))
            row("Factor analysis", title, "n_variables", result.get("n_variables"))
            row("Factor analysis", title, "n_factors", result.get("n_factors"))
            row("Factor analysis", title, "rotation", result.get("rotation"))
            row("Factor analysis", title, "standardize", result.get("standardize"))
            row("Factor analysis", title, "cumulative_explained_variance", result.get("cumulative_explained_variance"))
            recommendations = result.get("factor_recommendations") or {}
            row("Факторный анализ", title, "kaiser_n_factors", recommendations.get("kaiser_n_factors"))
            row("Факторный анализ", title, "selected_n_factors", recommendations.get("selected_n_factors"))
            row("Факторный анализ", title, "kaiser_message", recommendations.get("message"))
            kmo = result.get("kmo") or {}
            row("Факторный анализ", title, "kmo_overall", kmo.get("overall"))
            row("Факторный анализ", title, "kmo_interpretation", kmo.get("interpretation"))
            for item in kmo.get("variables") or []:
                row("Факторный анализ", title, "kmo_variable", item.get("label") or item.get("code"), "kmo", item.get("kmo"), "interpretation", item.get("interpretation"))
            bartlett = result.get("bartlett") or {}
            row("Факторный анализ", title, "bartlett_chi_square", bartlett.get("chi_square"))
            row("Факторный анализ", title, "bartlett_dof", bartlett.get("dof"))
            row("Факторный анализ", title, "bartlett_p_value", _format_p_value(bartlett.get("p_value")))
            row("Факторный анализ", title, "bartlett_significant", bartlett.get("significant"))
            row("Факторный анализ", title, "bartlett_interpretation", bartlett.get("interpretation"))
            for item in result.get("scree") or []:
                row("Факторный анализ", title, "scree", "component", item.get("component"), "eigenvalue", item.get("eigenvalue"), "explained_variance", item.get("explained_variance"), "cumulative", item.get("cumulative_explained_variance"))
            for index, value in enumerate(result.get("eigenvalues") or [], start=1):
                row("Factor analysis", title, "eigenvalue", f"Component {index}", value)
            for item in result.get("explained_variance") or []:
                row("Factor analysis", title, "explained_variance", item.get("factor"), item.get("value"))
            for item in result.get("loadings") or []:
                for factor in item.get("factors") or []:
                    row("Factor analysis", title, "loading", item.get("label") or item.get("variable"), factor.get("factor"), factor.get("loading"))
                row("Factor analysis", title, "communality", item.get("label") or item.get("variable"), item.get("communality"))
            for item in result.get("factor_scores") or []:
                values = []
                for score in item.get("scores") or []:
                    values.extend([score.get("factor"), score.get("value")])
                row("Факторный анализ", title, "factor_score", "response_id", item.get("response_id"), *values)
            for warning in result.get("warnings") or []:
                row("Factor analysis", title, "warning", warning)
            for warning in kmo.get("warnings") or []:
                row("Факторный анализ", title, "kmo_warning", warning)
            for warning in bartlett.get("warnings") or []:
                row("Факторный анализ", title, "bartlett_warning", warning)

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
            for profile in result.get("cluster_profiles") or []:
                cluster = profile.get("cluster")
                row(
                    "Кластеризация",
                    title,
                    "profile",
                    "cluster",
                    cluster,
                    "size",
                    profile.get("size"),
                    "percent",
                    profile.get("percent"),
                    "interpretation",
                    profile.get("interpretation"),
                )
                for feature in profile.get("top_distinguishing_features") or []:
                    row(
                        "Кластеризация",
                        title,
                        "top_feature",
                        "cluster",
                        cluster,
                        "label",
                        feature.get("label"),
                        "type",
                        feature.get("type"),
                        "cluster_value",
                        feature.get("cluster_value"),
                        "overall_value",
                        feature.get("overall_value"),
                        "difference",
                        feature.get("difference"),
                        "score",
                        feature.get("score"),
                        "interpretation",
                        feature.get("interpretation"),
                    )
                for item in profile.get("numeric_summary") or []:
                    row("Кластеризация", title, "numeric_profile", "cluster", cluster, "label", item.get("label"), "cluster_mean", item.get("cluster_mean"), "overall_mean", item.get("overall_mean"), "difference", item.get("difference"), "z_difference", item.get("z_difference"), "interpretation", item.get("interpretation"))
                for item in profile.get("binary_summary") or []:
                    row("Кластеризация", title, "binary_profile", "cluster", cluster, "label", item.get("label"), "cluster_percent", item.get("cluster_percent_selected"), "overall_percent", item.get("overall_percent_selected"), "difference_pp", item.get("difference_pp"), "interpretation", item.get("interpretation"))
                for item in profile.get("categorical_summary") or []:
                    for category in item.get("categories") or []:
                        row("Кластеризация", title, "categorical_profile", "cluster", cluster, "variable", item.get("label"), "category", category.get("label"), "cluster_percent", category.get("cluster_percent"), "overall_percent", category.get("overall_percent"), "difference_pp", category.get("difference_pp"))
            for warning in result.get("warnings") or []:
                row("Cluster analysis", title, "warning", warning)

        elif section_type == "group_comparison":
            test = result.get("test") or {}
            effect_size = result.get("effect_size") or {}
            row("Сравнение групп", title, "method", result.get("method_name") or result.get("method"))
            row("Сравнение групп", title, "n", result.get("n"))
            row("Сравнение групп", title, "n_groups", result.get("n_groups"))
            row("Сравнение групп", title, "statistic", test.get("statistic"))
            row("Сравнение групп", title, "p_value", _format_p_value(test.get("p_value")))
            row("Сравнение групп", title, "significant", test.get("significant"))
            row("Сравнение групп", title, "interpretation", test.get("interpretation"))
            row("Сравнение групп", title, "effect_size_type", effect_size.get("type"))
            row("Сравнение групп", title, "effect_size_value", effect_size.get("value"))
            row("Сравнение групп", title, "effect_size_interpretation", effect_size.get("interpretation"))
            for group in result.get("groups") or []:
                row(
                    "Сравнение групп",
                    title,
                    "group",
                    group.get("label") or group.get("group"),
                    "n",
                    group.get("n"),
                    "mean",
                    group.get("mean"),
                    "median",
                    group.get("median"),
                    "std",
                    group.get("std"),
                    "min",
                    group.get("min"),
                    "max",
                    group.get("max"),
                )
            for warning in result.get("warnings") or []:
                row("Сравнение групп", title, "warning", warning)

            post_hoc = result.get("post_hoc") or {}
            row("Сравнение групп", title, "post_hoc_enabled", post_hoc.get("enabled"))
            row("Сравнение групп", title, "post_hoc_method", post_hoc.get("method"))
            row("Сравнение групп", title, "p_adjust", post_hoc.get("p_adjust"))
            for warning in post_hoc.get("warnings") or []:
                row("Сравнение групп", title, "post_hoc_warning", warning)
            for comparison in post_hoc.get("comparisons") or []:
                comparison_effect = comparison.get("effect_size") or {}
                row(
                    "Сравнение групп",
                    title,
                    "post_hoc_comparison",
                    comparison.get("group_a_label") or comparison.get("group_a"),
                    comparison.get("group_b_label") or comparison.get("group_b"),
                    "test",
                    comparison.get("test"),
                    "statistic",
                    comparison.get("statistic"),
                    "p_value",
                    _format_p_value(comparison.get("p_value")),
                    "p_adjusted",
                    _format_p_value(comparison.get("p_adjusted")),
                    "significant",
                    comparison.get("significant"),
                    "difference",
                    comparison.get("difference"),
                    "effect_size",
                    comparison_effect.get("value"),
                    "effect_size_interpretation",
                    comparison_effect.get("interpretation"),
                )

        elif section_type == "time_analysis":
            summary = result.get("summary") or {}
            row("Анализ времени", title, "total_started", summary.get("total_started"))
            row("Анализ времени", title, "total_finished", summary.get("total_finished"))
            row("Анализ времени", title, "total_completed", summary.get("total_completed"))
            row("Анализ времени", title, "total_screened_out", summary.get("total_screened_out"))
            row("Анализ времени", title, "total_active_unfinished", summary.get("total_active_unfinished"))
            row("Анализ времени", title, "completion_rate", summary.get("completion_rate"))
            row("Анализ времени", title, "screenout_rate", summary.get("screenout_rate"))
            row("Анализ времени", title, "finish_rate", summary.get("finish_rate"))
            row("Анализ времени", title, "average_completion_time_seconds", summary.get("average_completion_time_seconds"))
            row("Анализ времени", title, "median_completion_time_seconds", summary.get("median_completion_time_seconds"))
            row("Анализ времени", title, "average_screenout_time_seconds", summary.get("average_screenout_time_seconds"))
            row("Анализ времени", title, "median_screenout_time_seconds", summary.get("median_screenout_time_seconds"))
            for item in result.get("completion_time_distribution") or []:
                row("Анализ времени", title, "completion_distribution", item.get("label"), "count", item.get("count"), "percent", item.get("percent"))
            for item in result.get("screenout_time_distribution") or []:
                row("Анализ времени", title, "screenout_distribution", item.get("label"), "count", item.get("count"), "percent", item.get("percent"))
            for item in result.get("screenout_reasons") or []:
                row(
                    "Анализ времени",
                    title,
                    "screenout_reason",
                    item.get("reason"),
                    "count",
                    item.get("count"),
                    "percent_screened_out",
                    item.get("percent_screened_out"),
                    "average_time_to_screenout_seconds",
                    item.get("average_time_to_screenout_seconds"),
                )
            for group in result.get("group_breakdown") or []:
                row(
                    "Анализ времени",
                    title,
                    "group",
                    group.get("group_label") or group.get("group"),
                    "started",
                    group.get("total_started"),
                    "completed",
                    group.get("total_completed"),
                    "screened_out",
                    group.get("total_screened_out"),
                    "completion_rate",
                    group.get("completion_rate"),
                    "screenout_rate",
                    group.get("screenout_rate"),
                    "median_completion_time",
                    (group.get("completion_time") or {}).get("median"),
                )
            group_test = result.get("group_time_test") or {}
            if group_test:
                row(
                    "Анализ времени",
                    title,
                    "group_time_test",
                    "method",
                    group_test.get("method"),
                    "statistic",
                    group_test.get("statistic"),
                    "p_value",
                    _format_p_value(group_test.get("p_value")),
                    "significant",
                    group_test.get("significant"),
                )
            for warning in result.get("warnings") or []:
                row("Анализ времени", title, "warning", warning)

        elif section_type == "reliability_analysis":
            row("Надёжность шкалы", title, "method", result.get("method"))
            row("Надёжность шкалы", title, "n", result.get("n"))
            row("Надёжность шкалы", title, "n_items", result.get("n_items"))
            row("Надёжность шкалы", title, "alpha", result.get("alpha"))
            row("Надёжность шкалы", title, "standardized_alpha", result.get("standardized_alpha"))
            row("Надёжность шкалы", title, "mean_inter_item_correlation", result.get("mean_inter_item_correlation"))
            row("Надёжность шкалы", title, "interpretation", result.get("interpretation"))
            for item in result.get("item_statistics") or []:
                row(
                    "Надёжность шкалы",
                    title,
                    "item",
                    item.get("label") or item.get("code"),
                    "mean",
                    item.get("mean"),
                    "variance",
                    item.get("variance"),
                    "std",
                    item.get("std"),
                    "item_total_correlation",
                    item.get("item_total_correlation"),
                    "alpha_if_deleted",
                    item.get("alpha_if_deleted"),
                )
            variables = result.get("variables") or []
            matrix = result.get("inter_item_correlation_matrix") or []
            for row_index, matrix_row in enumerate(matrix):
                for col_index, value in enumerate(matrix_row):
                    row_label = variables[row_index].get("label") if row_index < len(variables) else f"R{row_index + 1}"
                    col_label = variables[col_index].get("label") if col_index < len(variables) else f"C{col_index + 1}"
                    row("Надёжность шкалы", title, "correlation", row_label, col_label, value)
            for warning in result.get("warnings") or []:
                row("Надёжность шкалы", title, "warning", warning)

        elif section_type == "scale_index":
            row("Индекс шкалы", title, "title", result.get("title"))
            row("Индекс шкалы", title, "method", result.get("calculation"))
            row("Индекс шкалы", title, "n_items", result.get("n_items"))
            row("Индекс шкалы", title, "n_scored", result.get("n_scored"))
            row("Индекс шкалы", title, "min_answered_items", result.get("min_answered_items"))
            row("Индекс шкалы", title, "n_complete_cases_for_alpha", result.get("n_complete_cases_for_alpha"))
            row("Индекс шкалы", title, "missing_count", result.get("missing_count"))

            summary = result.get("score_summary") or {}
            row(
                "Индекс шкалы",
                title,
                "score_summary",
                "mean",
                summary.get("mean"),
                "median",
                summary.get("median"),
                "std",
                summary.get("std"),
                "min",
                summary.get("min"),
                "max",
                summary.get("max"),
            )
            for item in result.get("item_statistics") or []:
                row(
                    "Индекс шкалы",
                    title,
                    "item",
                    item.get("label") or item.get("code"),
                    "reverse",
                    item.get("reverse"),
                    "mean",
                    item.get("mean"),
                    "std",
                    item.get("std"),
                    "item_total_correlation",
                    item.get("item_total_correlation"),
                )
            reliability = result.get("reliability") or {}
            row("Индекс шкалы", title, "alpha", reliability.get("alpha"))
            row("Индекс шкалы", title, "standardized_alpha", reliability.get("standardized_alpha"))
            row("Индекс шкалы", title, "reliability_interpretation", reliability.get("interpretation"))
            row("Индекс шкалы", title, "mean_inter_item_correlation", reliability.get("mean_inter_item_correlation"))
            for item in result.get("score_distribution") or []:
                row("Индекс шкалы", title, "distribution", item.get("label"), "count", item.get("count"), "percent", item.get("percent"))
            for score in result.get("scores") or []:
                row(
                    "Индекс шкалы",
                    title,
                    "score",
                    "response_id",
                    score.get("response_id"),
                    "score",
                    score.get("score"),
                    "answered_items",
                    score.get("answered_items"),
                    "missing_items",
                    score.get("missing_items"),
                )
            for warning in result.get("warnings") or []:
                row("Индекс шкалы", title, "warning", warning)
            for warning in reliability.get("warnings") or []:
                row("Индекс шкалы", title, "reliability_warning", warning)

    csv_text = output.getvalue()
    return ("\ufeff" + csv_text).encode("utf-8")
