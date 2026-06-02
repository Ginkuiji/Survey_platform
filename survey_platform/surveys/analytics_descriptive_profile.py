import math
from collections import Counter
from statistics import median, stdev


NUMERIC_ENCODINGS = {"numeric", "binary", "ordinal", "rank", "matrix_ordinal"}
BINARY_ENCODINGS = {"one_hot", "matrix_multi_binary"}
HIGH_MISSING_RATE = 30.0


def is_missing(value):
    return value is None or value == ""


def _percent(part, whole):
    return round(part / whole * 100, 2) if whole else 0.0


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def detect_iqr_outliers(values):
    if not values:
        return {
            "method": "iqr",
            "lower_fence": None,
            "upper_fence": None,
            "count": 0,
            "rate": 0.0,
        }
    q1 = _percentile(values, 0.25)
    q3 = _percentile(values, 0.75)
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    count = sum(value < lower_fence or value > upper_fence for value in values)
    return {
        "method": "iqr",
        "lower_fence": lower_fence,
        "upper_fence": upper_fence,
        "count": count,
        "rate": _percent(count, len(values)),
    }


def describe_numeric_values(values, total_count=None):
    numeric_values = []
    for value in values:
        if is_missing(value):
            continue
        try:
            numeric_values.append(float(value))
        except (TypeError, ValueError):
            continue
    total_count = len(values) if total_count is None else total_count
    missing_count = total_count - len(numeric_values)
    q1 = _percentile(numeric_values, 0.25)
    q3 = _percentile(numeric_values, 0.75)
    return {
        "n": len(numeric_values),
        "missing_count": missing_count,
        "missing_rate": _percent(missing_count, total_count),
        "mean": round(sum(numeric_values) / len(numeric_values), 4) if numeric_values else None,
        "median": median(numeric_values) if numeric_values else None,
        "std": round(stdev(numeric_values), 4) if len(numeric_values) > 1 else None,
        "min": min(numeric_values) if numeric_values else None,
        "max": max(numeric_values) if numeric_values else None,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1 if q1 is not None and q3 is not None else None,
        "unique_values_count": len(set(numeric_values)),
        "outliers": detect_iqr_outliers(numeric_values),
    }


def describe_categorical_values(values, value_labels=None):
    non_missing = [value for value in values if not is_missing(value)]
    counts = Counter(non_missing)
    distribution = [
        {
            "value": value,
            "label": (value_labels or {}).get(value, str(value)),
            "count": count,
            "percent_answered": _percent(count, len(non_missing)),
        }
        for value, count in counts.most_common()
    ]
    return {
        "n": len(non_missing),
        "missing_count": len(values) - len(non_missing),
        "missing_rate": _percent(len(values) - len(non_missing), len(values)),
        "categories_count": len(counts),
        "top_category": distribution[0] if distribution else None,
        "distribution": distribution,
    }


def _numeric_notes(profile):
    notes = []
    if profile["std"] and abs(profile["mean"] - profile["median"]) > 0.5 * profile["std"]:
        notes.append("Среднее и медиана заметно различаются; распределение может быть асимметричным или содержать выбросы.")
    if profile["outliers"]["rate"] >= 5:
        notes.append("Обнаружена заметная доля выбросов по правилу IQR.")
    if profile["unique_values_count"] < 2:
        notes.append("Переменная не имеет вариативности и не подходит для анализа связей или различий.")
    if profile["missing_rate"] >= HIGH_MISSING_RATE:
        notes.append("У переменной высокий уровень пропусков; интерпретация требует осторожности.")
    return notes


def _base_variable(variable):
    return {
        "code": getattr(variable, "code", None),
        "label": getattr(variable, "label", None),
        "question_id": getattr(variable, "question_id", None),
        "qtype": getattr(variable, "qtype", None),
        "encoding": getattr(variable, "encoding", None),
        "measure": getattr(variable, "measure", None),
    }


def describe_dataset_variables(dataset):
    if dataset is None:
        return []
    profiles = []
    for variable in getattr(dataset, "variables", None) or []:
        values = [row.get(variable.code) for row in getattr(dataset, "rows", None) or []]
        if getattr(variable, "encoding", None) in BINARY_ENCODINGS:
            numeric = describe_numeric_values(values)
            profiles.append({
                **_base_variable(variable),
                "kind": "binary",
                "n": numeric["n"],
                "missing_count": numeric["missing_count"],
                "missing_rate": numeric["missing_rate"],
                "mean": numeric["mean"],
                "sum": sum(value for value in values if isinstance(value, (int, float))),
                "share": round((numeric["mean"] or 0) * 100, 2) if numeric["mean"] is not None else None,
                "unique_values_count": numeric["unique_values_count"],
                "zero_variance": numeric["unique_values_count"] < 2,
                "interpretation": {"summary": "Бинарный признак показывает долю выбранной категории.", "notes": _numeric_notes(numeric)},
                "visualizations": [{"type": "horizontal_bar", "title": "Доля выбранной категории", "recommended": True}],
            })
            continue
        if getattr(variable, "encoding", None) in NUMERIC_ENCODINGS:
            numeric = describe_numeric_values(values)
            profiles.append({
                **_base_variable(variable),
                "kind": "numeric",
                **numeric,
                "interpretation": {
                    "summary": "Среднее значение показывает общий уровень признака, медиана - типичное значение без сильного влияния выбросов.",
                    "notes": _numeric_notes(numeric),
                },
                "visualizations": [
                    {"type": "histogram", "title": "Гистограмма распределения", "recommended": True, "description": "Показывает форму распределения числового признака."},
                    {"type": "boxplot", "title": "Boxplot", "recommended": True, "description": "Показывает медиану, квартильный размах и возможные выбросы."},
                ],
            })
            continue
        categorical = describe_categorical_values(values, getattr(variable, "value_labels", None))
        profiles.append({
            **_base_variable(variable),
            "kind": "categorical",
            **categorical,
            "interpretation": {"summary": "Частоты показывают распределение наблюдений по категориям.", "notes": []},
            "visualizations": [{"type": "horizontal_bar", "title": "Горизонтальная столбчатая диаграмма", "recommended": True}],
        })
    return profiles


def build_descriptive_profile(result, payload=None, dataset=None, survey_id=None):
    variables = describe_dataset_variables(dataset)
    notes = ["Описательная статистика помогает оценить структуру данных перед применением сложных методов анализа."]
    if dataset is None:
        notes.append("Подробный описательный профиль недоступен: набор данных метода не передан.")
    return {"variables": variables, "notes": notes}


def collect_descriptive_warnings(profile):
    warnings = []
    variables = (profile or {}).get("variables") or []
    if any(item.get("missing_rate", 0) >= HIGH_MISSING_RATE for item in variables):
        warnings.append("У одной или нескольких переменных высокий уровень пропусков.")
    if any(item.get("zero_variance") or item.get("unique_values_count") == 1 for item in variables):
        warnings.append("У одной или нескольких переменных отсутствует вариативность.")
    if any("асимметрич" in note for item in variables for note in (item.get("interpretation") or {}).get("notes", [])):
        warnings.append("Среднее и медиана заметно различаются; распределение может быть асимметричным.")
    if any((item.get("outliers") or {}).get("count", 0) > 0 for item in variables):
        warnings.append("Обнаружены выбросы по правилу IQR.")
    return warnings


def build_descriptive_recommendations(profile):
    variables = (profile or {}).get("variables") or []
    recommendations = []
    if any(item.get("kind") == "numeric" for item in variables):
        recommendations.append("Для числовых переменных рекомендуется смотреть не только среднее, но и медиану, квартильный размах и выбросы.")
    if any("асимметрич" in note for item in variables for note in (item.get("interpretation") or {}).get("notes", [])):
        recommendations.append("Среднее и медиана заметно различаются; рекомендуется проверить форму распределения на гистограмме.")
    if any((item.get("outliers") or {}).get("count", 0) > 0 for item in variables):
        recommendations.append("Обнаружены выбросы по правилу IQR; рекомендуется проверить, являются ли они ошибками ввода или содержательно важными наблюдениями.")
    return recommendations
