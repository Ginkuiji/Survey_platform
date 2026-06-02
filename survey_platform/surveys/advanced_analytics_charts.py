import json
import math
from collections import defaultdict
from io import BytesIO

try:
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
except ModuleNotFoundError as exc:
    matplotlib = None
    plt = None
    MATPLOTLIB_IMPORT_ERROR = exc
else:
    MATPLOTLIB_IMPORT_ERROR = None

from .advanced_analytics_dataset import build_analysis_dataset
from .advanced_analytics_methods import clean_numeric_pairs, get_column
from .models import Question


MAX_LABEL_LENGTH = 36


def figure_to_png(fig):
    if plt is None:
        raise ValueError("Matplotlib is not installed on the server.")
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def get_report_payload(report):
    result = report.result
    if isinstance(result, str):
        return json.loads(result)
    return result or {}


def build_report_section_chart(report, section_id, chart_type=None) -> BytesIO:
    if MATPLOTLIB_IMPORT_ERROR is not None:
        raise ValueError("Matplotlib is not installed on the server.")

    payload = get_report_payload(report)
    sections = payload.get("sections") or []
    section = next((item for item in sections if str(item.get("id")) == str(section_id)), None)
    if not section:
        raise ValueError("Report section not found.")
    if section.get("error"):
        raise ValueError("Cannot build chart for a section with analysis error.")

    section_type = section.get("type")
    config = section.get("config") or section
    result = section.get("result") or {}
    chart_type = chart_type or "auto"

    builders = {
        "correlation": build_correlation_chart,
        "regression": build_regression_chart,
        "group_comparison": build_group_comparison_chart,
        "factor_analysis": build_factor_analysis_chart,
        "cluster_analysis": build_cluster_analysis_chart,
        "logistic_regression": build_logistic_regression_chart,
        "chi_square": build_crosstab_chart,
        "crosstab": build_crosstab_chart,
        "correspondence_analysis": build_crosstab_chart,
        "time_analysis": build_time_analysis_chart,
        "missing_analysis": build_missing_analysis_chart,
        "reliability_analysis": build_reliability_chart,
        "scale_index": build_scale_index_chart,
    }
    builder = builders.get(section_type)
    if not builder:
        raise ValueError(f"Matplotlib chart is not available for analysis type '{section_type}'.")
    return builder(report, config, result, chart_type)


def _truncate(value, max_length=MAX_LABEL_LENGTH):
    label = str(value or "—")
    return f"{label[:max_length - 1]}…" if len(label) > max_length else label


def _numeric(value):
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _rank_values(values):
    sorted_pairs = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    position = 0
    while position < len(sorted_pairs):
        end = position
        while end + 1 < len(sorted_pairs) and sorted_pairs[end + 1][0] == sorted_pairs[position][0]:
            end += 1
        average_rank = (position + end + 2) / 2
        for _, original_index in sorted_pairs[position:end + 1]:
            ranks[original_index] = average_rank
        position = end + 1
    return ranks


def _linear_trend(values_x, values_y):
    mean_x = sum(values_x) / len(values_x)
    mean_y = sum(values_y) / len(values_y)
    denominator = sum((value - mean_x) ** 2 for value in values_x)
    if denominator == 0:
        return None
    slope = sum((x_value - mean_x) * (y_value - mean_y) for x_value, y_value in zip(values_x, values_y)) / denominator
    return slope, mean_y - slope * mean_x


def _default_spec(question, analysis_type, role="variable"):
    qtype = question.qtype

    if analysis_type == "logistic_regression" and role == "target" and qtype == Question.YESNO:
        return {"question_id": question.id, "encoding": "binary", "measure": "binary"}

    if analysis_type in {"logistic_regression", "regression"} and role == "feature":
        if qtype in (Question.NUMBER, Question.SCALE):
            return {"question_id": question.id, "encoding": "numeric", "measure": "interval"}
        if qtype == Question.YESNO:
            return {"question_id": question.id, "encoding": "binary", "measure": "binary"}
        if qtype in (Question.SINGLE, Question.DROPDOWN, Question.MULTI):
            return {"question_id": question.id, "encoding": "one_hot", "measure": "nominal"}
        if qtype == Question.RANKING:
            return {"question_id": question.id, "encoding": "rank", "measure": "ordinal"}
        if qtype == Question.MATRIX_SINGLE:
            return {"question_id": question.id, "encoding": "matrix_ordinal", "measure": "ordinal"}
        if qtype == Question.MATRIX_MULTI:
            return {"question_id": question.id, "encoding": "matrix_multi_binary", "measure": "binary"}

    if analysis_type == "cluster_analysis":
        if qtype in (Question.NUMBER, Question.SCALE):
            return {"question_id": question.id, "encoding": "numeric", "measure": "interval"}
        if qtype == Question.YESNO:
            return {"question_id": question.id, "encoding": "binary", "measure": "binary"}
        if qtype in (Question.SINGLE, Question.DROPDOWN):
            return {"question_id": question.id, "encoding": "ordinal", "measure": "nominal" if role == "profile" else "ordinal"}
        if qtype == Question.MULTI and role == "profile":
            return {"question_id": question.id, "encoding": "one_hot", "measure": "nominal"}
        if qtype == Question.RANKING:
            return {"question_id": question.id, "encoding": "rank", "measure": "ordinal"}
        if qtype == Question.MATRIX_SINGLE:
            return {"question_id": question.id, "encoding": "matrix_ordinal", "measure": "ordinal"}
        if qtype == Question.MATRIX_MULTI:
            return {"question_id": question.id, "encoding": "matrix_multi_binary", "measure": "binary"}

    if analysis_type in {"time_analysis", "missing_analysis"} and role == "group":
        if qtype == Question.YESNO:
            return {"question_id": question.id, "encoding": "binary", "measure": "binary"}
        if qtype in (Question.SINGLE, Question.DROPDOWN):
            return {"question_id": question.id, "encoding": "ordinal", "measure": "nominal"}

    if analysis_type == "scale_index":
        if qtype in (Question.NUMBER, Question.SCALE):
            return {"question_id": question.id, "encoding": "numeric", "measure": "interval"}
        if qtype == Question.YESNO:
            return {"question_id": question.id, "encoding": "binary", "measure": "binary"}
        if qtype in (Question.SINGLE, Question.DROPDOWN, Question.MATRIX_SINGLE):
            encoding = "matrix_ordinal" if qtype == Question.MATRIX_SINGLE else "ordinal"
            return {"question_id": question.id, "encoding": encoding, "measure": "ordinal"}

    if qtype in (Question.NUMBER, Question.SCALE):
        return {"question_id": question.id, "encoding": "numeric", "measure": "interval"}
    if qtype == Question.YESNO:
        return {"question_id": question.id, "encoding": "binary", "measure": "binary"}
    if qtype in (Question.SINGLE, Question.DROPDOWN):
        measure = "nominal" if analysis_type in {"crosstab", "chi_square", "correspondence_analysis"} or role == "group" else "ordinal"
        return {"question_id": question.id, "encoding": "ordinal", "measure": measure}
    if qtype == Question.RANKING:
        return {"question_id": question.id, "encoding": "rank", "measure": "ordinal"}
    if qtype == Question.MATRIX_SINGLE:
        return {"question_id": question.id, "encoding": "matrix_ordinal", "measure": "ordinal"}
    if qtype == Question.MATRIX_MULTI and analysis_type == "cluster_analysis":
        return {"question_id": question.id, "encoding": "matrix_multi_binary", "measure": "binary"}
    return None


def _question_specs(survey_id, question_ids, analysis_type, role="variable"):
    question_ids = [int(question_id) for question_id in question_ids or [] if question_id]
    questions = {
        question.id: question
        for question in Question.objects.filter(survey_id=survey_id, id__in=question_ids)
    }
    specs = []
    for question_id in question_ids:
        question = questions.get(question_id)
        if not question:
            raise ValueError(f"Question {question_id} does not belong to survey.")
        spec = _default_spec(question, analysis_type, role)
        if not spec:
            raise ValueError(f"Question {question_id} is not supported for this chart.")
        specs.append(spec)
    return specs


def _single_spec(survey_id, question_id, analysis_type, role):
    specs = _question_specs(survey_id, [question_id], analysis_type, role)
    if not specs:
        raise ValueError(f"Question for {role} is not selected.")
    return specs[0]


def _value_label(variable, value):
    labels = getattr(variable, "value_labels", None) or {}
    if value in labels:
        return labels[value]
    try:
        int_value = int(float(value))
        if int_value in labels:
            return labels[int_value]
        if str(int_value) in labels:
            return labels[str(int_value)]
    except (TypeError, ValueError):
        pass
    return str(value)


def _find_variable_by_question(dataset, question_id):
    matches = [variable for variable in dataset.variables if variable.question_id == int(question_id)]
    if len(matches) != 1:
        raise ValueError("Selected question must produce exactly one chart column.")
    return matches[0]


def build_correlation_chart(report, config, result, chart_type):
    specs = config.get("variables") or _question_specs(report.survey_id, config.get("questionIds"), "correlation")
    if len(specs) < 2:
        raise ValueError("Correlation chart requires at least two variables.")
    dataset = build_analysis_dataset(report.survey_id, specs)
    if chart_type in {"network", "correlation_network"}:
        raise ValueError("Сетевой граф корреляций доступен в JSON-результате отчета; PNG-визуализация для него пока не поддерживается.")
    if chart_type in {"heatmap", "correlation_heatmap"}:
        matrix = result.get("matrix")
        labels = [item.get("label") or item.get("code") for item in result.get("variables", [])]
        if not matrix or not labels:
            raise ValueError("Correlation matrix is not available for heatmap.")
        return _matrix_heatmap(matrix, labels, labels, "Correlation heatmap", vmin=-1, vmax=1, cmap="coolwarm")

    if len(dataset.variables) == 2:
        left, right = dataset.variables
        pairs = clean_numeric_pairs(get_column(dataset.rows, left.code), get_column(dataset.rows, right.code))
        if not pairs:
            raise ValueError("Not enough numeric pairs for correlation scatter plot.")
        x_values, y_values = map(list, zip(*pairs))
        is_ranked = chart_type in {"ranked_scatterplot", "ranked_scatter_plot"}
        if is_ranked:
            x_values = _rank_values(x_values)
            y_values = _rank_values(y_values)
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(x_values, y_values, alpha=0.72)
        trend = _linear_trend(x_values, y_values)
        if trend:
            slope, intercept = trend
            x_min, x_max = min(x_values), max(x_values)
            ax.plot([x_min, x_max], [intercept + slope * x_min, intercept + slope * x_max], color="#d62728", label="Trend line")
            ax.legend()
        ax.set_xlabel(_truncate(left.label))
        ax.set_ylabel(_truncate(right.label))
        coefficient = (result.get("matrix") or [[None, None], [None, None]])[0][1]
        p_value = (result.get("p_values") or [[None, None], [None, None]])[0][1]
        n = (result.get("n_matrix") or [[None, None], [None, None]])[0][1]
        title = "Ranked correlation scatter plot" if is_ranked else "Correlation scatter plot"
        ax.set_title(f"{title}\nr={_numeric(coefficient)}, p={_numeric(p_value)}, n={n}")
        ax.grid(alpha=0.25)
        return figure_to_png(fig)

    if chart_type in {"scatterplot", "correlation_scatterplot", "ranked_scatterplot", "ranked_scatter_plot"}:
        raise ValueError("Scatter plot requires exactly two expanded correlation variables.")
    matrix = result.get("matrix")
    labels = [item.get("label") or item.get("code") for item in result.get("variables", [])]
    if not matrix or not labels:
        raise ValueError("Correlation matrix is not available for heatmap.")
    return _matrix_heatmap(matrix, labels, labels, "Correlation heatmap", vmin=-1, vmax=1, cmap="coolwarm")


def build_regression_chart(report, config, result, chart_type):
    target_spec = config.get("target") or _single_spec(report.survey_id, config.get("targetQuestionId"), "regression", "target")
    feature_specs = config.get("features") or _question_specs(report.survey_id, config.get("featureQuestionIds"), "regression", "feature")
    if not feature_specs:
        raise ValueError("Regression chart requires at least one feature.")
    dataset = build_analysis_dataset(report.survey_id, [target_spec, *feature_specs])
    target_variable = _find_variable_by_question(dataset, target_spec["question_id"])
    feature_variables = [variable for variable in dataset.variables if variable.code != target_variable.code]

    if len(feature_variables) == 1:
        feature = feature_variables[0]
        pairs = clean_numeric_pairs(get_column(dataset.rows, feature.code), get_column(dataset.rows, target_variable.code))
        if not pairs:
            raise ValueError("Not enough numeric pairs for regression scatter plot.")
        x_values, y_values = zip(*pairs)
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(x_values, y_values, alpha=0.72, label="Observed")
        coefficients = {item.get("name"): item.get("value") for item in result.get("coefficients", [])}
        intercept = _numeric(coefficients.get("intercept")) or 0
        slope = _numeric(coefficients.get(feature.code))
        if slope is not None:
            x_min, x_max = min(x_values), max(x_values)
            ax.plot([x_min, x_max], [intercept + slope * x_min, intercept + slope * x_max], color="#d62728", label="Regression line")
            ax.legend()
        ax.set_xlabel(_truncate(feature.label))
        ax.set_ylabel(_truncate(target_variable.label))
        ax.set_title("Linear regression")
        ax.grid(alpha=0.25)
        return figure_to_png(fig)

    coefficients = [
        (item.get("name"), _numeric(item.get("value")))
        for item in result.get("coefficients", [])
        if item.get("name") != "intercept"
    ]
    coefficients = [(name, value) for name, value in coefficients if value is not None]
    if not coefficients:
        raise ValueError("Regression coefficients are not available.")
    labels = [_truncate(result.get("variables_by_code", {}).get(name, {}).get("label") or name) for name, _ in coefficients]
    values = [value for _, value in coefficients]
    return _bar_chart(labels, values, "Regression coefficients", "Coefficient")


def build_group_comparison_chart(report, config, result, chart_type):
    group_spec = config.get("group") or _single_spec(report.survey_id, config.get("groupQuestionId"), "group_comparison", "group")
    value_spec = config.get("value") or _single_spec(report.survey_id, config.get("valueQuestionId"), "group_comparison", "value")
    dataset = build_analysis_dataset(report.survey_id, [group_spec, value_spec])
    group_variable = _find_variable_by_question(dataset, group_spec["question_id"])
    value_variable = _find_variable_by_question(dataset, value_spec["question_id"])
    grouped = defaultdict(list)
    for row in dataset.rows:
        group_value = row.get(group_variable.code)
        value = _numeric(row.get(value_variable.code))
        if group_value is not None and value is not None:
            grouped[_value_label(group_variable, group_value)].append(value)
    groups = [(label, values) for label, values in grouped.items() if values]
    if len(groups) < 2:
        raise ValueError("Boxplot requires at least two non-empty groups.")
    fig, ax = plt.subplots(figsize=(max(7, len(groups) * 1.1), 5))
    ax.boxplot([values for _, values in groups], labels=[_truncate(label, 18) for label, _ in groups], patch_artist=True)
    ax.set_title("Group comparison boxplot")
    ax.set_ylabel(_truncate(value_variable.label))
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.25)
    return figure_to_png(fig)


def build_factor_analysis_chart(report, config, result, chart_type):
    scree = result.get("scree") or []
    if scree:
        labels = [str(item.get("component")) for item in scree]
        eigenvalues = [_numeric(item.get("eigenvalue")) for item in scree]
    else:
        eigenvalues = [_numeric(value) for value in result.get("eigenvalues", [])]
        labels = [f"C{index + 1}" for index in range(len(eigenvalues))]
    points = [(label, value) for label, value in zip(labels, eigenvalues) if value is not None]
    if not points:
        return _factor_loadings_heatmap(result)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot([label for label, _ in points], [value for _, value in points], marker="o")
    ax.axhline(1, color="#666", linestyle="--", linewidth=1)
    ax.set_title("Scree plot")
    ax.set_ylabel("Eigenvalue")
    ax.grid(alpha=0.25)
    return figure_to_png(fig)


def _factor_loadings_heatmap(result):
    loadings = result.get("loadings") or []
    if not loadings:
        raise ValueError("Factor analysis data is not available for chart.")
    factors = [item.get("factor") for item in loadings[0].get("factors", [])]
    matrix = []
    labels = []
    for item in loadings:
        by_factor = {factor.get("factor"): _numeric(factor.get("loading")) for factor in item.get("factors", [])}
        matrix.append([by_factor.get(factor) or 0 for factor in factors])
        labels.append(item.get("label") or item.get("variable"))
    return _matrix_heatmap(matrix, factors, labels, "Factor loadings", vmin=-1, vmax=1, cmap="coolwarm")


def build_cluster_analysis_chart(report, config, result, chart_type):
    clusters = result.get("clusters") or result.get("cluster_sizes") or []
    if not clusters:
        raise ValueError("Cluster sizes are not available for chart.")
    labels = [f"Cluster {item.get('cluster')}" for item in clusters]
    values = [_numeric(item.get("size")) or 0 for item in clusters]
    return _bar_chart(labels, values, "Cluster sizes", "Responses")


def build_logistic_regression_chart(report, config, result, chart_type):
    if chart_type == "probabilities":
        probabilities = [_numeric(item.get("probability")) for item in result.get("predictions", [])]
        probabilities = [value for value in probabilities if value is not None]
        if not probabilities:
            raise ValueError("Predicted probabilities are not available.")
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.hist(probabilities, bins=10, range=(0, 1), color="#1f77b4", edgecolor="white")
        ax.set_title("Predicted probability distribution")
        ax.set_xlabel("Probability")
        ax.set_ylabel("Count")
        return figure_to_png(fig)

    matrix = result.get("confusion_matrix") or {}
    values = [
        [matrix.get("tn", 0), matrix.get("fp", 0)],
        [matrix.get("fn", 0), matrix.get("tp", 0)],
    ]
    return _matrix_heatmap(values, ["Predicted 0", "Predicted 1"], ["Actual 0", "Actual 1"], "Confusion matrix", cmap="Blues")


def build_crosstab_chart(report, config, result, chart_type):
    crosstab = result.get("crosstab")
    if not crosstab:
        raise ValueError("Crosstab data is not available for chart.")
    rows = crosstab.get("rows") or []
    if not rows:
        raise ValueError("Crosstab rows are empty.")
    x_labels = [str(column.get("value")) for column in rows[0].get("columns", [])]
    y_labels = [str(row.get("label") or row.get("value")) for row in rows]
    matrix = [[column.get("count", 0) for column in row.get("columns", [])] for row in rows]
    return _matrix_heatmap(matrix, x_labels, y_labels, "Crosstab heatmap", cmap="YlGnBu")


def build_time_analysis_chart(report, config, result, chart_type):
    rows = result.get("completion_time_distribution") or []
    if not rows:
        raise ValueError("Completion time distribution is not available.")
    labels = [item.get("label") for item in rows]
    values = [_numeric(item.get("count")) or 0 for item in rows]
    return _bar_chart(labels, values, "Completion time distribution", "Responses")


def build_missing_analysis_chart(report, config, result, chart_type):
    questions = result.get("top_skipped_questions") or result.get("questions") or []
    questions = questions[:15]
    if not questions:
        raise ValueError("Missing analysis questions are not available.")
    labels = [_truncate(item.get("label") or item.get("question_id"), 24) for item in questions]
    values = [
        _numeric(item.get("skip_rate_shown")) if item.get("skip_rate_shown") is not None else _numeric(item.get("skipped_count")) or 0
        for item in questions
    ]
    return _bar_chart(labels, values, "Top skipped questions", "Skip rate among shown, %")


def build_reliability_chart(report, config, result, chart_type):
    items = result.get("item_statistics") or []
    if not items:
        raise ValueError("Reliability item statistics are not available.")
    labels = [_truncate(item.get("label") or item.get("code"), 24) for item in items[:20]]
    values = [_numeric(item.get("item_total_correlation")) or 0 for item in items[:20]]
    return _bar_chart(labels, values, "Item-total correlation", "Correlation")


def build_scale_index_chart(report, config, result, chart_type):
    rows = result.get("score_distribution") or []
    if not rows:
        raise ValueError("Scale index score distribution is not available.")
    labels = [item.get("label") for item in rows]
    values = [_numeric(item.get("count")) or 0 for item in rows]
    return _bar_chart(labels, values, "Scale score distribution", "Responses")


def _matrix_heatmap(matrix, x_labels, y_labels, title, vmin=None, vmax=None, cmap="viridis"):
    if not matrix:
        raise ValueError("Matrix data is not available for chart.")
    fig_width = max(7, len(x_labels) * 0.75)
    fig_height = max(5, len(y_labels) * 0.45)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    image = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels([_truncate(label, 18) for label in x_labels], rotation=35, ha="right")
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels([_truncate(label, 24) for label in y_labels])
    ax.set_title(title)
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            numeric = _numeric(value)
            if numeric is not None:
                ax.text(column_index, row_index, f"{numeric:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    return figure_to_png(fig)


def _bar_chart(labels, values, title, ylabel):
    if not labels or not values:
        raise ValueError("Bar chart data is not available.")
    fig_width = max(7, len(labels) * 0.55)
    fig, ax = plt.subplots(figsize=(fig_width, 5))
    ax.bar(range(len(values)), values, color="#1f77b4")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([_truncate(label, 20) for label in labels], rotation=30, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    return figure_to_png(fig)
