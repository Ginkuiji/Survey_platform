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
            cramers_v = result.get("cramers_v") or {}
            story.append(key_value_table([
                ["chi2", chi.get("chi2")],
                ["p_value", _format_p_value(chi.get("p_value"))],
                ["dof", chi.get("dof")],
                ["Cramer's V", cramers_v.get("cramers_v")],
                ["Interpretation", cramers_v.get("interpretation")],
                ["n", cramers_v.get("n")],
                ["rows", cramers_v.get("rows")],
                ["columns", cramers_v.get("columns")],
            ]))
            add_matrix_table(story, "Expected values", chi.get("expected") or [])
        elif section_type == "correspondence_analysis":
            story.append(key_value_table([
                ["method", result.get("method")],
                ["n", result.get("n")],
                ["n_rows", result.get("n_rows")],
                ["n_columns", result.get("n_columns")],
                ["n_dimensions", result.get("n_dimensions")],
                ["total_inertia", result.get("total_inertia")],
            ]))
            warnings = result.get("warnings") or []
            if warnings:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table([["Warnings"], *[[warning] for warning in warnings]], [16 * cm]))
            story.append(Spacer(1, 0.15 * cm))
            add_crosstab(story, result.get("crosstab") or {})
            dimensions = result.get("dimensions") or []
            if dimensions:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Dimension", "Eigenvalue", "Explained inertia", "%"], *[
                        [
                            item.get("dimension"),
                            item.get("eigenvalue"),
                            item.get("explained_inertia"),
                            f"{float(item.get('explained_inertia') or 0) * 100:.2f}%",
                        ]
                        for item in dimensions
                    ]],
                ))

            def add_ca_coordinates(title_text, points):
                if not points:
                    return
                dimension_names = [item.get("dimension") for item in dimensions]
                rows = [["Category", "Mass", *dimension_names, *[f"Contribution {name}" for name in dimension_names], "Cos2"]]
                for point in points:
                    coordinates = {item.get("dimension"): item.get("value") for item in point.get("coordinates") or []}
                    contributions = {item.get("dimension"): item.get("value") for item in point.get("contributions") or []}
                    rows.append([
                        point.get("label") or point.get("value"),
                        point.get("mass"),
                        *[coordinates.get(name) for name in dimension_names],
                        *[contributions.get(name) for name in dimension_names],
                        point.get("cos2"),
                    ])
                story.append(Spacer(1, 0.15 * cm))
                story.append(p(title_text, "AnalyticsHeading"))
                story.append(table(rows))

            add_ca_coordinates("Row coordinates", result.get("row_coordinates") or [])
            add_ca_coordinates("Column coordinates", result.get("column_coordinates") or [])
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
            recommendations = result.get("factor_recommendations") or {}
            kmo = result.get("kmo") or {}
            bartlett = result.get("bartlett") or {}
            story.append(Spacer(1, 0.15 * cm))
            story.append(key_value_table([
                ["kaiser_n_factors", recommendations.get("kaiser_n_factors")],
                ["selected_n_factors", recommendations.get("selected_n_factors")],
                ["kaiser_message", recommendations.get("message")],
                ["kmo_overall", kmo.get("overall")],
                ["kmo_interpretation", kmo.get("interpretation")],
                ["bartlett_chi_square", bartlett.get("chi_square")],
                ["bartlett_dof", bartlett.get("dof")],
                ["bartlett_p_value", _format_p_value(bartlett.get("p_value"))],
                ["bartlett_significant", bartlett.get("significant")],
                ["bartlett_interpretation", bartlett.get("interpretation")],
            ]))
            scree = result.get("scree") or []
            if scree:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Component", "Eigenvalue", "Explained", "Cumulative"], *[
                        [
                            item.get("component"),
                            item.get("eigenvalue"),
                            item.get("explained_variance"),
                            item.get("cumulative_explained_variance"),
                        ]
                        for item in scree
                    ]],
                ))
            kmo_variables = kmo.get("variables") or []
            if kmo_variables:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Variable", "KMO", "Interpretation"], *[
                        [item.get("label") or item.get("code"), item.get("kmo"), item.get("interpretation")]
                        for item in kmo_variables
                    ]],
                ))
            factor_scores = result.get("factor_scores") or []
            if factor_scores:
                story.append(Spacer(1, 0.15 * cm))
                story.append(p(f"Factor scores рассчитаны для {len(factor_scores)} респондентов. Полная таблица доступна в CSV/XLSX."))
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
            for profile in result.get("cluster_profiles") or []:
                story.append(Spacer(1, 0.15 * cm))
                story.append(p(
                    f"Кластер {profile.get('cluster')} — {profile.get('size')} респондентов ({_format_value(profile.get('percent'))}%)",
                    "AnalyticsHeading",
                ))
                story.append(p(profile.get("interpretation") or "—"))
                features = (profile.get("top_distinguishing_features") or [])[:5]
                if features:
                    story.append(table(
                        [["Feature", "Type", "Cluster", "Overall", "Difference", "Interpretation"], *[
                            [
                                item.get("label"),
                                item.get("type"),
                                item.get("cluster_value"),
                                item.get("overall_value"),
                                item.get("difference"),
                                item.get("interpretation"),
                            ]
                            for item in features
                        ]],
                        [4 * cm, 2 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 4 * cm],
                    ))
        elif section_type == "group_comparison":
            test = result.get("test") or {}
            effect_size = result.get("effect_size") or {}
            story.append(key_value_table([
                ["method", result.get("method_name") or result.get("method")],
                ["group variable", (result.get("group_variable") or {}).get("label")],
                ["value variable", (result.get("value_variable") or {}).get("label")],
                ["n", result.get("n")],
                ["n_groups", result.get("n_groups")],
                ["statistic", test.get("statistic")],
                ["p_value", _format_p_value(test.get("p_value"))],
                ["significant", test.get("significant")],
                ["interpretation", test.get("interpretation")],
                ["effect size", effect_size.get("type")],
                ["effect size value", effect_size.get("value")],
                ["effect size interpretation", effect_size.get("interpretation")],
            ]))
            groups = result.get("groups") or []
            if groups:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Group", "n", "Mean", "Median", "Std", "Min", "Max"], *[
                        [
                            group.get("label") or group.get("group"),
                            group.get("n"),
                            group.get("mean"),
                            group.get("median"),
                            group.get("std"),
                            group.get("min"),
                            group.get("max"),
                        ]
                        for group in groups
                    ]],
                ))
            warnings = result.get("warnings") or []
            if warnings:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table([["Warnings"], *[[warning] for warning in warnings]], [16 * cm]))
            post_hoc = result.get("post_hoc") or {}
            if post_hoc.get("enabled"):
                story.extend(heading("Post-hoc сравнения"))
                story.append(key_value_table([
                    ["method", post_hoc.get("method")],
                    ["p_adjust", post_hoc.get("p_adjust")],
                    ["comparisons", post_hoc.get("comparisons_count")],
                ]))
                post_hoc_warnings = post_hoc.get("warnings") or []
                if post_hoc_warnings:
                    story.append(table([["Warnings"], *[[warning] for warning in post_hoc_warnings]], [16 * cm]))
                comparisons = post_hoc.get("comparisons") or []
                if comparisons:
                    limited = comparisons[:20]
                    story.append(table(
                        [["Group A", "Group B", "Test", "p adjusted", "Significant", "Difference", "Effect size"], *[
                            [
                                item.get("group_a_label") or item.get("group_a"),
                                item.get("group_b_label") or item.get("group_b"),
                                item.get("test"),
                                _format_p_value(item.get("p_adjusted")),
                                item.get("significant"),
                                item.get("difference"),
                                (item.get("effect_size") or {}).get("value"),
                            ]
                            for item in limited
                        ]],
                    ))
                    if len(comparisons) > 20:
                        story.append(p("Показаны первые 20 post-hoc сравнений."))
        elif section_type == "time_analysis":
            summary = result.get("summary") or {}
            story.append(key_value_table([
                ["total_started", summary.get("total_started")],
                ["total_finished", summary.get("total_finished")],
                ["total_completed", summary.get("total_completed")],
                ["total_screened_out", summary.get("total_screened_out")],
                ["total_active_unfinished", summary.get("total_active_unfinished")],
                ["completion_rate", summary.get("completion_rate")],
                ["screenout_rate", summary.get("screenout_rate")],
                ["finish_rate", summary.get("finish_rate")],
                ["average_completion_time_seconds", summary.get("average_completion_time_seconds")],
                ["median_completion_time_seconds", summary.get("median_completion_time_seconds")],
                ["average_screenout_time_seconds", summary.get("average_screenout_time_seconds")],
                ["median_screenout_time_seconds", summary.get("median_screenout_time_seconds")],
            ]))
            for title_text, items in (
                ("Completion time distribution", result.get("completion_time_distribution") or []),
                ("Screenout time distribution", result.get("screenout_time_distribution") or []),
            ):
                if items:
                    story.append(Spacer(1, 0.15 * cm))
                    limited = items[:20]
                    story.append(table(
                        [["Bucket", "Count", "Percent"], *[
                            [item.get("label"), item.get("count"), item.get("percent")]
                            for item in limited
                        ]],
                    ))
                    if len(items) > 20:
                        story.append(p(f"{title_text}: показаны первые 20 интервалов распределения времени."))
            reasons = result.get("screenout_reasons") or []
            if reasons:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Reason", "Count", "% screened out", "Avg time"], *[
                        [
                            item.get("reason"),
                            item.get("count"),
                            item.get("percent_screened_out"),
                            item.get("average_time_to_screenout_seconds"),
                        ]
                        for item in reasons
                    ]],
                ))
            groups = result.get("group_breakdown") or []
            if groups:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Group", "Started", "Completed", "Screened out", "Completion %", "Screenout %", "Median completion"], *[
                        [
                            item.get("group_label") or item.get("group"),
                            item.get("total_started"),
                            item.get("total_completed"),
                            item.get("total_screened_out"),
                            item.get("completion_rate"),
                            item.get("screenout_rate"),
                            (item.get("completion_time") or {}).get("median"),
                        ]
                        for item in groups
                    ]],
                ))
            group_test = result.get("group_time_test") or {}
            if group_test:
                story.append(Spacer(1, 0.15 * cm))
                story.append(key_value_table([
                    ["group_time_test_method", group_test.get("method")],
                    ["statistic", group_test.get("statistic")],
                    ["p_value", _format_p_value(group_test.get("p_value"))],
                    ["significant", group_test.get("significant")],
                    ["interpretation", group_test.get("interpretation")],
                ]))
            warnings = result.get("warnings") or []
            if warnings:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table([["Warnings"], *[[warning] for warning in warnings]], [16 * cm]))
        elif section_type == "reliability_analysis":
            story.append(key_value_table([
                ["method", result.get("method")],
                ["n", result.get("n")],
                ["n_items", result.get("n_items")],
                ["alpha", result.get("alpha")],
                ["standardized_alpha", result.get("standardized_alpha")],
                ["mean_inter_item_correlation", result.get("mean_inter_item_correlation")],
                ["interpretation", result.get("interpretation")],
            ]))
            warnings = result.get("warnings") or []
            if warnings:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table([["Warnings"], *[[warning] for warning in warnings]], [16 * cm]))
            items = result.get("item_statistics") or []
            if items:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Item", "Mean", "Variance", "Std", "Item-total", "Alpha deleted"], *[
                        [
                            item.get("label") or item.get("code"),
                            item.get("mean"),
                            item.get("variance"),
                            item.get("std"),
                            item.get("item_total_correlation"),
                            item.get("alpha_if_deleted"),
                        ]
                        for item in items
                    ]],
                ))
            variables = (result.get("variables") or [])[:8]
            matrix = result.get("inter_item_correlation_matrix") or []
            if variables and matrix:
                story.append(Spacer(1, 0.15 * cm))
                if len(result.get("variables") or []) > len(variables):
                    story.append(p("Inter-item correlation matrix is truncated for readability."))
                header = ["Item", *[variable.get("label") or variable.get("code") for variable in variables]]
                rows = []
                for row_index, variable in enumerate(variables):
                    rows.append([
                        variable.get("label") or variable.get("code"),
                        *[
                            matrix[row_index][col_index]
                            if row_index < len(matrix) and col_index < len(matrix[row_index])
                            else None
                            for col_index in range(len(variables))
                        ],
                    ])
                story.append(table([header, *rows]))
        elif section_type == "scale_index":
            story.append(key_value_table([
                ["title", result.get("title")],
                ["calculation", result.get("calculation")],
                ["n_items", result.get("n_items")],
                ["n_scored", result.get("n_scored")],
                ["min_answered_items", result.get("min_answered_items")],
                ["n_complete_cases_for_alpha", result.get("n_complete_cases_for_alpha")],
                ["missing_count", result.get("missing_count")],
            ]))
            warnings = result.get("warnings") or []
            if warnings:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table([["Warnings"], *[[warning] for warning in warnings]], [16 * cm]))
            summary = result.get("score_summary") or {}
            story.append(Spacer(1, 0.15 * cm))
            story.append(p("Score summary", "AnalyticsHeading"))
            story.append(key_value_table([
                ["n", summary.get("n")],
                ["mean", summary.get("mean")],
                ["median", summary.get("median")],
                ["std", summary.get("std")],
                ["variance", summary.get("variance")],
                ["min", summary.get("min")],
                ["max", summary.get("max")],
                ["p25", summary.get("p25")],
                ["p75", summary.get("p75")],
                ["iqr", summary.get("iqr")],
            ]))
            reliability = result.get("reliability") or {}
            if reliability:
                story.append(Spacer(1, 0.15 * cm))
                story.append(p("Reliability", "AnalyticsHeading"))
                story.append(key_value_table([
                    ["alpha", reliability.get("alpha")],
                    ["standardized_alpha", reliability.get("standardized_alpha")],
                    ["mean_inter_item_correlation", reliability.get("mean_inter_item_correlation")],
                    ["interpretation", reliability.get("interpretation")],
                ]))
                rel_warnings = reliability.get("warnings") or []
                if rel_warnings:
                    story.append(table([["Reliability warnings"], *[[warning] for warning in rel_warnings]], [16 * cm]))
            items = result.get("item_statistics") or []
            if items:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Item", "Reverse", "n", "Missing", "Mean", "Std", "Min", "Max", "Item-total"], *[
                        [
                            item.get("label") or item.get("code"),
                            item.get("reverse"),
                            item.get("n"),
                            item.get("missing"),
                            item.get("mean"),
                            item.get("std"),
                            item.get("min"),
                            item.get("max"),
                            item.get("item_total_correlation"),
                        ]
                        for item in items
                    ]],
                ))
            distribution = result.get("score_distribution") or []
            if distribution:
                story.append(Spacer(1, 0.15 * cm))
                story.append(table(
                    [["Bucket", "Count", "Percent"], *[
                        [item.get("label"), item.get("count"), item.get("percent")]
                        for item in distribution
                    ]],
                    [8 * cm, 3 * cm, 3 * cm],
                ))
            if result.get("scores"):
                story.append(p("Индивидуальные значения индекса доступны в CSV/XLSX."))
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
        elif section_type == "logistic_regression":
            metrics = result.get("metrics") or {}
            confusion = result.get("confusion_matrix") or {}
            story.append(key_value_table([
                ["method", result.get("method")],
                ["target", _variable_label(result, result.get("target"))],
                ["features", ", ".join(_variable_label(result, code) for code in (result.get("features") or []))],
                ["n", result.get("n")],
                ["positive_class_count", result.get("positive_class_count")],
                ["negative_class_count", result.get("negative_class_count")],
                ["base_rate", result.get("base_rate")],
                ["threshold", result.get("threshold")],
                ["accuracy", metrics.get("accuracy")],
                ["precision", metrics.get("precision")],
                ["recall", metrics.get("recall")],
                ["f1", metrics.get("f1")],
                ["mcfadden_r2", metrics.get("mcfadden_r2")],
            ]))
            story.append(table([
                ["", "Predicted 0", "Predicted 1"],
                ["Actual 0", confusion.get("tn"), confusion.get("fp")],
                ["Actual 1", confusion.get("fn"), confusion.get("tp")],
            ], [5 * cm, 5 * cm, 5 * cm]))
            coefficients = result.get("coefficients") or []
            if coefficients:
                story.append(table(
                    [["Name", "Coefficient", "Odds ratio", "Interpretation"], *[
                        [
                            _variable_label(result, item.get("name")),
                            item.get("coefficient"),
                            item.get("odds_ratio"),
                            item.get("interpretation"),
                        ]
                        for item in coefficients
                    ]],
                    [5 * cm, 3 * cm, 3 * cm, 5 * cm],
                ))
            for warning in result.get("warnings") or []:
                story.append(p(f"Warning: {warning}"))

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
