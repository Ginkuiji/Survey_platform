import math
from collections import Counter, defaultdict
from typing import Any

try:
    import numpy as np
except ImportError:  # pragma: no cover - depends on deployment environment
    np = None

try:
    from scipy import stats
except ImportError:  # pragma: no cover - depends on deployment environment
    stats = None


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    return float(value)


def _is_numeric(value: Any) -> bool:
    if _is_missing(value):
        return False
    try:
        _as_float(value)
    except (TypeError, ValueError):
        return False
    return True


QUESTION_TYPE_LABELS = {
    "single": "Одиночный выбор",
    "multi": "Множественный выбор",
    "dropdown": "Выпадающий список",
    "yesno": "Да/нет",
    "text": "Текстовый ответ",
    "date": "Дата",
    "number": "Числовой ответ",
    "scale": "Шкала",
    "matrix_single": "Матрица с одиночным выбором",
    "matrix_multi": "Матрица с множественным выбором",
    "ranking": "Ранжирование",
}

MISSING_TYPE_LABELS = {
    "not_shown": "Не показывался",
    "no_missing": "Без пропусков",
    "branching_limited": "Ограниченная видимость из-за ветвления",
    "high_missing": "Высокая доля пропусков",
    "moderate_missing": "Умеренная доля пропусков",
    "low_missing": "Низкая доля пропусков",
}


def _question_type_label(qtype):
    return QUESTION_TYPE_LABELS.get(qtype, str(qtype) if qtype is not None else "")


def _missing_type_label(missing_type):
    return MISSING_TYPE_LABELS.get(missing_type, str(missing_type) if missing_type is not None else "")


def get_column(rows, code):
    return [row.get(code) for row in rows]


def clean_numeric_pairs(x_values, y_values):
    pairs = []
    for x_value, y_value in zip(x_values, y_values):
        if _is_numeric(x_value) and _is_numeric(y_value):
            pairs.append((_as_float(x_value), _as_float(y_value)))
    return pairs


def _manual_pearson(x_values, y_values):
    n = len(x_values)
    if n < 2:
        return None

    mean_x = sum(x_values) / n
    mean_y = sum(y_values) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
    denominator_x = math.sqrt(sum((x - mean_x) ** 2 for x in x_values))
    denominator_y = math.sqrt(sum((y - mean_y) ** 2 for y in y_values))
    denominator = denominator_x * denominator_y
    if denominator == 0:
        return None
    return numerator / denominator


def _rank_values(values):
    sorted_pairs = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    position = 0
    while position < len(sorted_pairs):
        end = position
        while end + 1 < len(sorted_pairs) and sorted_pairs[end + 1][0] == sorted_pairs[position][0]:
            end += 1
        average_rank = (position + 1 + end + 1) / 2
        for _, original_index in sorted_pairs[position:end + 1]:
            ranks[original_index] = average_rank
        position = end + 1
    return ranks


def _manual_correlation(x_values, y_values, method):
    if method == "spearman":
        x_values = _rank_values(x_values)
        y_values = _rank_values(y_values)
    return _manual_pearson(x_values, y_values)




def _finite_or_none(value):
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _sort_values(values):
    return sorted(values, key=lambda value: (str(type(value)), value))


def _sample_variance(values):
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _sample_std(values):
    variance = _sample_variance(values)
    return math.sqrt(variance) if variance is not None else None


def _percentile(sorted_values, percentile):
    if not sorted_values:
        return None
    position = (len(sorted_values) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(sorted_values[int(position)])
    weight = position - lower
    return float(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight)


def _numeric_summary(values):
    clean_values = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
    n = len(clean_values)
    if not n:
        return {
            "n": 0, "mean": None, "median": None, "std": None, "variance": None,
            "min": None, "max": None, "p25": None, "p75": None, "q1": None, "q3": None, "iqr": None,
        }
    mean_value = sum(clean_values) / n
    variance = _sample_variance(clean_values)
    p25 = _percentile(clean_values, 0.25)
    p75 = _percentile(clean_values, 0.75)
    return {
        "n": n, "mean": float(mean_value), "median": _percentile(clean_values, 0.5),
        "std": math.sqrt(variance) if variance is not None else None, "variance": variance,
        "min": float(clean_values[0]), "max": float(clean_values[-1]), "p25": p25, "p75": p75,
        "q1": p25, "q3": p75, "iqr": (p75 - p25) if p25 is not None and p75 is not None else None,
    }
