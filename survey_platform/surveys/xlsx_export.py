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
        elif qtype == "matrix_single":
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
        elif qtype == "matrix_multi":
            append_section_title(ws, "Matrix")
            matrix_rows = result.get("rows") or []
            matrix_columns = result.get("columns") or []
            cells_by_key = {
                (cell.get("row_id"), cell.get("column_id")): cell
                for cell in result.get("cells") or []
            }
            ws.append(["Row"] + [column.get("text") for column in matrix_columns])
            _style_header(ws, ws.max_row)
            for matrix_row in matrix_rows:
                ws.append([
                    matrix_row.get("text"),
                    *[
                        (
                            f"{cell.get('count', 0)} | "
                            f"{format_number(cell.get('percent_answered'))}% answered | "
                            f"{format_number(cell.get('percent_total'))}% total"
                        )
                        for column in matrix_columns
                        for cell in [cells_by_key.get((matrix_row.get("id"), column.get("id")), {})]
                    ],
                ])
            _append_table(
                ws,
                ["Row Summary", "Selected total", "Respondents", "% respondents", "Avg selected"],
                [
                    [
                        item.get("row_text"),
                        item.get("selected_total"),
                        item.get("respondent_count"),
                        format_number(item.get("respondent_share")),
                        format_number(item.get("avg_selected_per_respondent")),
                    ]
                    for item in result.get("row_summary") or []
                ],
            )
            _append_table(
                ws,
                ["Column Summary", "Selected total", "Respondents", "% respondents"],
                [
                    [
                        item.get("column_text"),
                        item.get("selected_total"),
                        item.get("respondent_count"),
                        format_number(item.get("respondent_share")),
                    ]
                    for item in result.get("column_summary") or []
                ],
            )
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
            cramers_v = result.get("cramers_v") or {}
            append_key_value(ws, "chi2", format_number(chi.get("chi2")))
            append_key_value(ws, "p_value", format_p_value(chi.get("p_value")))
            append_key_value(ws, "dof", chi.get("dof"))
            append_key_value(ws, "Cramer's V", format_number(cramers_v.get("cramers_v")))
            append_key_value(ws, "Интерпретация", cramers_v.get("interpretation"))
            append_key_value(ws, "N", cramers_v.get("n"))
            append_key_value(ws, "Число строк", cramers_v.get("rows"))
            append_key_value(ws, "Число столбцов", cramers_v.get("columns"))
            _append_crosstab(ws, result.get("crosstab") or {})
            _append_matrix(ws, "Expected values", [], chi.get("expected") or [])
        elif section_type == "correspondence_analysis":
            append_key_value(ws, "method", result.get("method"))
            append_key_value(ws, "n", result.get("n"))
            append_key_value(ws, "n_rows", result.get("n_rows"))
            append_key_value(ws, "n_columns", result.get("n_columns"))
            append_key_value(ws, "n_dimensions", result.get("n_dimensions"))
            append_key_value(ws, "total_inertia", format_number(result.get("total_inertia")))
            warnings = result.get("warnings") or []
            if warnings:
                _append_table(ws, ["Warnings"], [[warning] for warning in warnings])
            _append_crosstab(ws, result.get("crosstab") or {})
            _append_table(
                ws,
                ["Dimension", "Eigenvalue", "Explained inertia", "Percent"],
                [
                    [
                        item.get("dimension"),
                        format_number(item.get("eigenvalue")),
                        format_number(item.get("explained_inertia")),
                        f"{float(item.get('explained_inertia') or 0) * 100:.2f}%",
                    ]
                    for item in result.get("dimensions") or []
                ],
            )

            def append_ca_coordinates(title_text, points):
                dimensions = [item.get("dimension") for item in result.get("dimensions") or []]
                rows = []
                for point in points:
                    coordinates = {item.get("dimension"): item.get("value") for item in point.get("coordinates") or []}
                    contributions = {item.get("dimension"): item.get("value") for item in point.get("contributions") or []}
                    rows.append([
                        point.get("label") or point.get("value"),
                        format_number(point.get("mass")),
                        *[format_number(coordinates.get(dimension)) for dimension in dimensions],
                        *[format_number(contributions.get(dimension)) for dimension in dimensions],
                        format_number(point.get("cos2")),
                    ])
                _append_table(
                    ws,
                    ["Category", "Mass", *dimensions, *[f"Contribution {dimension}" for dimension in dimensions], "Cos2"],
                    rows,
                )

            append_section_title(ws, "Row coordinates")
            append_ca_coordinates("Row coordinates", result.get("row_coordinates") or [])
            append_section_title(ws, "Column coordinates")
            append_ca_coordinates("Column coordinates", result.get("column_coordinates") or [])
        elif section_type == "factor_analysis":
            append_key_value(ws, "method", result.get("method"))
            append_key_value(ws, "n", result.get("n"))
            append_key_value(ws, "n_variables", result.get("n_variables"))
            append_key_value(ws, "n_factors", result.get("n_factors"))
            append_key_value(ws, "rotation", result.get("rotation"))
            append_key_value(ws, "standardize", result.get("standardize"))
            append_key_value(ws, "cumulative_explained_variance", format_number(result.get("cumulative_explained_variance")))
            _append_table(
                ws,
                ["Component", "Eigenvalue"],
                [
                    [f"Component {index}", format_number(value)]
                    for index, value in enumerate(result.get("eigenvalues") or [], start=1)
                ],
            )
            _append_table(
                ws,
                ["Factor", "Value", "Percent"],
                [
                    [item.get("factor"), format_number(item.get("value")), f"{float(item.get('value') or 0) * 100:.2f}%"]
                    for item in result.get("explained_variance") or []
                ],
            )
            factors = [item.get("factor") for item in result.get("explained_variance") or []]
            loading_rows = []
            for item in result.get("loadings") or []:
                factors_by_name = {
                    factor.get("factor"): factor.get("loading")
                    for factor in item.get("factors") or []
                }
                loading_rows.append([
                    item.get("label") or item.get("variable"),
                    format_number(item.get("communality")),
                    *[format_number(factors_by_name.get(factor)) for factor in factors],
                ])
            _append_table(ws, ["Variable", "Communality", *factors], loading_rows)
            warnings = result.get("warnings") or []
            if warnings:
                _append_table(ws, ["Warnings"], [[warning] for warning in warnings])
        elif section_type == "cluster_analysis":
            append_key_value(ws, "method", result.get("method"))
            append_key_value(ws, "n", result.get("n"))
            append_key_value(ws, "n_clusters", result.get("n_clusters"))
            append_key_value(ws, "standardize", result.get("standardize"))
            append_key_value(ws, "inertia", format_number(result.get("inertia")))
            variables = result.get("variables") or []
            _append_table(
                ws,
                ["Cluster", "Size", "Percent", *[
                    variable.get("label") or variable.get("code")
                    for variable in variables
                ]],
                [
                    [
                        cluster.get("cluster"),
                        cluster.get("size"),
                        format_number(cluster.get("percent")),
                        *[
                            format_number((cluster.get("centroid") or {}).get(variable.get("code")))
                            for variable in variables
                        ],
                    ]
                    for cluster in result.get("clusters") or []
                ],
            )
            for profile in result.get("cluster_profiles") or []:
                cluster = profile.get("cluster")
                append_section_title(ws, f"Cluster {cluster} profile")
                append_key_value(ws, "size", profile.get("size"))
                append_key_value(ws, "percent", format_number(profile.get("percent")))
                append_key_value(ws, "interpretation", profile.get("interpretation"))
                _append_table(
                    ws,
                    ["Feature", "Type", "Cluster value", "Overall value", "Difference", "Score", "Interpretation"],
                    [
                        [
                            feature.get("label"),
                            feature.get("type"),
                            format_number(feature.get("cluster_value")),
                            format_number(feature.get("overall_value")),
                            format_number(feature.get("difference")),
                            format_number(feature.get("score")),
                            feature.get("interpretation"),
                        ]
                        for feature in profile.get("top_distinguishing_features") or []
                    ],
                )
                _append_table(
                    ws,
                    ["Variable", "Cluster mean", "Overall mean", "Difference", "z_difference", "Interpretation"],
                    [
                        [
                            item.get("label"),
                            format_number(item.get("cluster_mean")),
                            format_number(item.get("overall_mean")),
                            format_number(item.get("difference")),
                            format_number(item.get("z_difference")),
                            item.get("interpretation"),
                        ]
                        for item in profile.get("numeric_summary") or []
                    ],
                )
                _append_table(
                    ws,
                    ["Variable", "Cluster %", "Overall %", "Difference pp", "Interpretation"],
                    [
                        [
                            item.get("label"),
                            format_number(item.get("cluster_percent_selected")),
                            format_number(item.get("overall_percent_selected")),
                            format_number(item.get("difference_pp")),
                            item.get("interpretation"),
                        ]
                        for item in profile.get("binary_summary") or []
                    ],
                )
                categorical_rows = []
                for item in profile.get("categorical_summary") or []:
                    for category in item.get("categories") or []:
                        categorical_rows.append([
                            item.get("label"),
                            category.get("label"),
                            format_number(category.get("cluster_percent")),
                            format_number(category.get("overall_percent")),
                            format_number(category.get("difference_pp")),
                        ])
                _append_table(ws, ["Variable", "Category", "Cluster %", "Overall %", "Difference pp"], categorical_rows)
            warnings = result.get("warnings") or []
            if warnings:
                _append_table(ws, ["Warnings"], [[warning] for warning in warnings])
        elif section_type == "group_comparison":
            test = result.get("test") or {}
            effect_size = result.get("effect_size") or {}
            append_key_value(ws, "method", result.get("method_name") or result.get("method"))
            append_key_value(ws, "group variable", (result.get("group_variable") or {}).get("label"))
            append_key_value(ws, "value variable", (result.get("value_variable") or {}).get("label"))
            append_key_value(ws, "n", result.get("n"))
            append_key_value(ws, "n_groups", result.get("n_groups"))
            append_key_value(ws, "statistic", format_number(test.get("statistic")))
            append_key_value(ws, "p_value", format_p_value(test.get("p_value")))
            append_key_value(ws, "significant", test.get("significant"))
            append_key_value(ws, "interpretation", test.get("interpretation"))
            append_key_value(ws, "effect_size_type", effect_size.get("type"))
            append_key_value(ws, "effect_size_value", format_number(effect_size.get("value")))
            append_key_value(ws, "effect_size_interpretation", effect_size.get("interpretation"))
            _append_table(
                ws,
                ["Group", "n", "Mean", "Median", "Std", "Min", "Max"],
                [
                    [
                        group.get("label") or group.get("group"),
                        group.get("n"),
                        format_number(group.get("mean")),
                        format_number(group.get("median")),
                        format_number(group.get("std")),
                        format_number(group.get("min")),
                        format_number(group.get("max")),
                    ]
                    for group in result.get("groups") or []
                ],
            )
            warnings = result.get("warnings") or []
            if warnings:
                _append_table(ws, ["Warnings"], [[warning] for warning in warnings])
        elif section_type == "reliability_analysis":
            append_key_value(ws, "method", result.get("method"))
            append_key_value(ws, "n", result.get("n"))
            append_key_value(ws, "n_items", result.get("n_items"))
            append_key_value(ws, "alpha", format_number(result.get("alpha")))
            append_key_value(ws, "standardized_alpha", format_number(result.get("standardized_alpha")))
            append_key_value(ws, "mean_inter_item_correlation", format_number(result.get("mean_inter_item_correlation")))
            append_key_value(ws, "interpretation", result.get("interpretation"))
            warnings = result.get("warnings") or []
            if warnings:
                _append_table(ws, ["Warnings"], [[warning] for warning in warnings])
            _append_table(
                ws,
                ["Item", "Mean", "Variance", "Std", "Item-total correlation", "Alpha if deleted"],
                [
                    [
                        item.get("label") or item.get("code"),
                        format_number(item.get("mean")),
                        format_number(item.get("variance")),
                        format_number(item.get("std")),
                        format_number(item.get("item_total_correlation")),
                        format_number(item.get("alpha_if_deleted")),
                    ]
                    for item in result.get("item_statistics") or []
                ],
            )
            variables = result.get("variables") or []
            matrix = result.get("inter_item_correlation_matrix") or []
            if variables and matrix:
                labels = [variable.get("label") or variable.get("code") for variable in variables]
                _append_table(
                    ws,
                    ["Item", *labels],
                    [
                        [
                            labels[row_index],
                            *[
                                format_number(value)
                                for value in (matrix[row_index] if row_index < len(matrix) else [])
                            ],
                        ]
                        for row_index in range(len(labels))
                    ],
                )
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
        elif section_type == "logistic_regression":
            metrics = result.get("metrics") or {}
            confusion = result.get("confusion_matrix") or {}
            append_key_value(ws, "method", result.get("method"))
            append_key_value(ws, "target", get_variable_label(result, result.get("target")))
            append_key_value(ws, "features", ", ".join(get_variable_label(result, code) for code in (result.get("features") or [])))
            append_key_value(ws, "n", result.get("n"))
            append_key_value(ws, "positive_class_count", result.get("positive_class_count"))
            append_key_value(ws, "negative_class_count", result.get("negative_class_count"))
            append_key_value(ws, "base_rate", format_number(result.get("base_rate")))
            append_key_value(ws, "threshold", format_number(result.get("threshold")))
            append_key_value(ws, "accuracy", format_number(metrics.get("accuracy")))
            append_key_value(ws, "precision", format_number(metrics.get("precision")))
            append_key_value(ws, "recall", format_number(metrics.get("recall")))
            append_key_value(ws, "f1", format_number(metrics.get("f1")))
            append_key_value(ws, "mcfadden_r2", format_number(metrics.get("mcfadden_r2")))
            _append_table(
                ws,
                ["", "Predicted 0", "Predicted 1"],
                [
                    ["Actual 0", confusion.get("tn"), confusion.get("fp")],
                    ["Actual 1", confusion.get("fn"), confusion.get("tp")],
                ],
            )
            _append_table(
                ws,
                ["Variable", "Coefficient", "Odds ratio", "Interpretation"],
                [
                    [
                        get_variable_label(result, coefficient.get("name")),
                        format_number(coefficient.get("coefficient")),
                        format_number(coefficient.get("odds_ratio")),
                        coefficient.get("interpretation"),
                    ]
                    for coefficient in result.get("coefficients") or []
                ],
            )
            for warning in result.get("warnings") or []:
                append_key_value(ws, "warning", warning)
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
