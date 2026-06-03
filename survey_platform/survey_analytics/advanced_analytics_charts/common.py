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

from survey_analytics.advanced_analytics_dataset import build_analysis_dataset
from survey_analytics.advanced_analytics_methods import clean_numeric_pairs, get_column
from surveys.models import Question


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
