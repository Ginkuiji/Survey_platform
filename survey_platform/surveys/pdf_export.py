from __future__ import annotations

from io import BytesIO
from pathlib import Path
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


def _get_report_result(analysis_report) -> dict:
    result = analysis_report.result or {}
    return result if isinstance(result, dict) else {}


def _variable_label(result: dict, code: str) -> str:
    if not code:
        return "вЂ”"
    if code == "intercept":
        return "РЎРІРѕР±РѕРґРЅС‹Р№ С‡Р»РµРЅ"
    variable = (result.get("variables_by_code") or {}).get(code) or {}
    return variable.get("label") or code


def build_analytics_pdf(survey, analytic_result, analysis_report) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:  # pragma: no cover - depends on deployment environment
        raise RuntimeError("PDF export requires reportlab to be installed") from exc

    font_name = "Helvetica"
    for font_path in (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ):
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("AnalyticsFont", str(font_path)))
            font_name = "AnalyticsFont"
            break

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="AnalyticsTitle", parent=styles["Title"], fontName=font_name, fontSize=18, leading=22))
    styles.add(ParagraphStyle(name="AnalyticsHeading", parent=styles["Heading2"], fontName=font_name, fontSize=13, leading=16, spaceBefore=10))
    styles.add(ParagraphStyle(name="AnalyticsText", parent=styles["BodyText"], fontName=font_name, fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="AnalyticsSmall", parent=styles["BodyText"], fontName=font_name, fontSize=8, leading=10))

    def p(value, style="AnalyticsText"):
        return Paragraph(str(_format_value(value)).replace("\n", "<br/>"), styles[style])

    def heading(text):
        return [Spacer(1, 0.2 * cm), p(text, "AnalyticsHeading")]

    def table(rows, col_widths=None):
        prepared = [[cell if hasattr(cell, "wrap") else p(cell, "AnalyticsSmall") for cell in row] for row in rows]
        item = Table(prepared, colWidths=col_widths, repeatRows=1)
        item.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bdbdbd")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return item

    def key_value_table(items):
        return table([["Показатель", "Значение"], *items], [7 * cm, 9 * cm])

    def add_summary(story, summary):
        keys = [
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
        ]
        story.extend(heading("Summary"))
        story.append(key_value_table([[key, _format_value(summary.get(key))] for key in keys]))

    def add_screening(story, screening):
        story.extend(heading("Screening"))
        story.append(key_value_table([
            ["total_screened_out", _format_value(screening.get("total_screened_out"))],
            ["average_screenout_time", _format_value(screening.get("average_screenout_time"))],
        ]))
        reasons = screening.get("reasons") or []
        if reasons:
            story.append(Spacer(1, 0.15 * cm))
            story.append(table([["Причина", "Count"], *[[item.get("reason"), item.get("count")] for item in reasons]], [12 * cm, 4 * cm]))

    def add_question_result(story, question):
        result = question.get("result") or {}
        qtype = question.get("qtype")
        story.extend(heading(question.get("text") or f"Question {question.get('id')}"))
        story.append(key_value_table([
            ["Тип", qtype],
            ["total_completed", (question.get("base") or {}).get("total_completed")],
            ["shown_count", (question.get("base") or {}).get("shown_count")],
            ["answered_count", (question.get("base") or {}).get("answered_count")],
            ["skipped_count", (question.get("base") or {}).get("skipped_count")],
        ]))

        if qtype in ("single", "multi", "dropdown", "yesno"):
            options = result.get("options") or []
            if options:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Option", "Count", "% answered", "% total"], *[
                        [option.get("text"), option.get("count"), option.get("percent_answered"), option.get("percent_total")]
                        for option in options
                    ]],
                    [7 * cm, 2 * cm, 3 * cm, 3 * cm],
                ))
        elif qtype in ("scale", "number"):
            story.append(Spacer(1, 0.15 * cm))
            story.append(key_value_table([
                ["average", result.get("average")],
                ["median", result.get("median")],
                ["min", result.get("min")],
                ["max", result.get("max")],
            ]))
        elif qtype in ("text", "date"):
            texts = result.get("text_answers") or []
            rows = [["Всего текстовых ответов", result.get("total_text_answers")]]
            rows.extend([[f"Ответ {index + 1}", text] for index, text in enumerate(texts[:10])])
            story.append(Spacer(1, 0.15 * cm))
            story.append(key_value_table(rows))
        elif qtype == "matrix_single":
            matrix_rows = result.get("rows") or []
            if matrix_rows and matrix_rows[0].get("columns"):
                header = ["Row", *[column.get("text") for column in matrix_rows[0].get("columns", [])]]
                body = [
                    [row.get("text"), *[column.get("count") for column in row.get("columns", [])]]
                    for row in matrix_rows
                ]
                story.append(Spacer(1, 0.15 * cm))
                story.append(table([header, *body]))
        elif qtype == "matrix_multi":
            matrix_rows = result.get("rows") or []
            matrix_columns = result.get("columns") or []
            cells_by_key = {
                (cell.get("row_id"), cell.get("column_id")): cell
                for cell in result.get("cells") or []
            }
            if matrix_rows and matrix_columns:
                header = ["Row", *[column.get("text") for column in matrix_columns]]
                body = []
                for matrix_row in matrix_rows:
                    body.append([
                        matrix_row.get("text"),
                        *[
                            (
                                f"{cell.get('count', 0)}\n"
                                f"{_format_value(cell.get('percent_answered'))}% answered\n"
                                f"{_format_value(cell.get('percent_total'))}% total"
                            )
                            for column in matrix_columns
                            for cell in [cells_by_key.get((matrix_row.get("id"), column.get("id")), {})]
                        ],
                    ])
                story.append(Spacer(1, 0.15 * cm))
                story.append(table([header, *body]))
            row_summary = result.get("row_summary") or []
            if row_summary:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Row", "Selected total", "Respondents", "% respondents", "Avg selected"], *[
                        [
                            item.get("row_text"),
                            item.get("selected_total"),
                            item.get("respondent_count"),
                            item.get("respondent_share"),
                            item.get("avg_selected_per_respondent"),
                        ]
                        for item in row_summary
                    ]],
                ))
            column_summary = result.get("column_summary") or []
            if column_summary:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Column", "Selected total", "Respondents", "% respondents"], *[
                        [
                            item.get("column_text"),
                            item.get("selected_total"),
                            item.get("respondent_count"),
                            item.get("respondent_share"),
                        ]
                        for item in column_summary
                    ]],
                ))
        elif qtype == "ranking":
            options = result.get("options") or []
            if options:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Option", "Average rank", "First place"], *[
                        [option.get("text"), option.get("average_rank"), option.get("first_place_count")]
                        for option in options
                    ]],
                    [9 * cm, 3 * cm, 3 * cm],
                ))

    def add_matrix_table(story, title, matrix, variables=None, formatter=_format_value):
        if not matrix:
            return
        story.extend(heading(title))
        header = [""] + [
            (variable.get("label") or variable.get("code")) if isinstance(variable, dict) else f"C{index + 1}"
            for index, variable in enumerate(variables or matrix[0])
        ]
        rows = []
        for row_index, row in enumerate(matrix):
            label = ""
            if variables and row_index < len(variables):
                label = variables[row_index].get("label") or variables[row_index].get("code")
            else:
                label = f"R{row_index + 1}"
            rows.append([label, *[formatter(value) for value in row]])
        story.append(table([header, *rows]))

    def add_crosstab(story, crosstab):
        rows = crosstab.get("rows") or []
        if not rows:
            story.append(p("Нет данных для таблицы сопряжённости."))
            return
        header = [crosstab.get("row_variable") or "Row", *[column.get("value") for column in rows[0].get("columns", [])], "Total"]
        body = []
        for row in rows:
            body.append([
                row.get("value"),
                *[f"{column.get('count')} ({column.get('percent_row')}%)" for column in row.get("columns", [])],
                row.get("total"),
            ])
        story.append(table([header, *body]))
        story.append(p(f"Total: {crosstab.get('total')}"))

    def add_report_section(story, section):
        story.extend(heading(section.get("title") or section.get("type")))
        story.append(p(f"Type: {section.get('type')}"))
        if section.get("error"):
            story.append(p(f"Error: {section.get('error')}"))
            return

        result = section.get("result") or {}
        section_type = section.get("type")
        if section_type == "correlation":
            story.append(key_value_table([
                ["method", result.get("method")],
                ["dataset_size", result.get("dataset_size")],
            ]))
            add_matrix_table(story, "Correlation matrix", result.get("matrix") or [], result.get("variables") or [])
            add_matrix_table(story, "P-values", result.get("p_values") or [], result.get("variables") or [], _format_p_value)
        elif section_type == "crosstab":
            add_crosstab(story, result.get("crosstab") or {})
        elif section_type == "chi_square":
            add_crosstab(story, result.get("crosstab") or {})
            chi = result.get("chi_square") or {}
            story.append(key_value_table([
                ["chi2", chi.get("chi2")],
                ["p_value", _format_p_value(chi.get("p_value"))],
                ["dof", chi.get("dof")],
            ]))
            add_matrix_table(story, "Expected values", chi.get("expected") or [])
        elif section_type == "factor_analysis":
            story.append(key_value_table([
                ["method", result.get("method")],
                ["n", result.get("n")],
                ["n_variables", result.get("n_variables")],
                ["n_factors", result.get("n_factors")],
                ["rotation", result.get("rotation")],
                ["standardize", result.get("standardize")],
                ["cumulative_explained_variance", result.get("cumulative_explained_variance")],
            ]))
            warnings = result.get("warnings") or []
            if warnings:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table([["Warnings"], *[[warning] for warning in warnings]], [16 * cm]))
            explained = result.get("explained_variance") or []
            if explained:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Factor", "Value", "Percent"], *[
                        [item.get("factor"), item.get("value"), f"{float(item.get('value') or 0) * 100:.2f}%"]
                        for item in explained
                    ]],
                    [6 * cm, 4 * cm, 4 * cm],
                ))
            loadings = result.get("loadings") or []
            factors = [item.get("factor") for item in explained]
            if loadings and factors:
                story.append(Spacer(1, 0.15 * cm))
                rows = [["Variable", "Communality", *factors]]
                for item in loadings:
                    factors_by_name = {
                        factor.get("factor"): factor.get("loading")
                        for factor in item.get("factors") or []
                    }
                    rows.append([
                        item.get("label") or item.get("variable"),
                        item.get("communality"),
                        *[factors_by_name.get(factor) for factor in factors],
                    ])
                story.append(table(rows))
            eigenvalues = result.get("eigenvalues") or []
            if eigenvalues:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Component", "Eigenvalue"], *[
                        [f"Component {index}", value]
                        for index, value in enumerate(eigenvalues, start=1)
                    ]],
                    [8 * cm, 5 * cm],
                ))
        elif section_type == "cluster_analysis":
            story.append(key_value_table([
                ["method", result.get("method")],
                ["n", result.get("n")],
                ["n_clusters", result.get("n_clusters")],
                ["standardize", result.get("standardize")],
                ["inertia", result.get("inertia")],
            ]))
            warnings = result.get("warnings") or []
            if warnings:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table([["Warnings"], *[[warning] for warning in warnings]], [16 * cm]))
            variables = result.get("variables") or []
            if result.get("clusters"):
                header = ["Cluster", "Size", "Percent", *[
                    variable.get("label") or variable.get("code")
                    for variable in variables
                ]]
                rows = []
                for cluster in result.get("clusters") or []:
                    centroid = cluster.get("centroid") or {}
                    rows.append([
                        cluster.get("cluster"),
                        cluster.get("size"),
                        cluster.get("percent"),
                        *[centroid.get(variable.get("code")) for variable in variables],
                    ])
                story.append(Spacer(1, 0.15 * cm))
                story.append(table([header, *rows]))
        elif section_type == "regression":
            story.append(key_value_table([
                ["target", _variable_label(result, result.get("target"))],
                ["features", ", ".join(_variable_label(result, code) for code in (result.get("features") or []))],
                ["n", result.get("n")],
                ["r2", result.get("r2")],
                ["adjusted_r2", result.get("adjusted_r2")],
            ]))
            coefficients = result.get("coefficients") or []
            if coefficients:
                story.append(table([["Name", "Value"], *[[_variable_label(result, item.get("name")), item.get("value")] for item in coefficients]], [9 * cm, 5 * cm]))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.4 * cm, leftMargin=1.4 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm)
    story = []

    story.append(p("Аналитический отчёт по опросу", "AnalyticsTitle"))
    story.append(p(survey.title, "AnalyticsHeading"))
    if survey.description:
        story.append(p(survey.description))
    story.append(p(f"Дата формирования PDF: {_format_datetime(timezone.now())}"))

    story.extend(heading("Информация об опросе"))
    story.append(key_value_table([
        ["ID опроса", survey.id],
        ["Название", survey.title],
        ["Статус", survey.status],
        ["Дата начала", _format_datetime(survey.starts_at)],
        ["Дата окончания", _format_datetime(survey.ends_at)],
        ["Анонимность", "Да" if survey.is_anonymous else "Нет"],
    ]))

    data = analytic_result.data or {}
    story.extend(heading("Сохранённый срез общей аналитики"))
    story.append(key_value_table([
        ["Название версии", analytic_result.title],
        ["Дата сохранения", _format_datetime(analytic_result.generated_at)],
        ["total_responses", analytic_result.total_responses],
    ]))
    add_summary(story, data.get("summary") or {})
    add_screening(story, data.get("screening") or {})
    story.extend(heading("Вопросы общей аналитики"))
    for question in data.get("questions") or []:
        add_question_result(story, question)

    story.append(PageBreak())
    report_result = _get_report_result(analysis_report)
    story.append(p("Пользовательский аналитический отчёт", "AnalyticsTitle"))
    story.append(key_value_table([
        ["Название", analysis_report.title],
        ["Дата создания", _format_datetime(analysis_report.created_at)],
    ]))
    for section in report_result.get("sections") or []:
        add_report_section(story, section)

    doc.build(story)
    return buffer.getvalue()
