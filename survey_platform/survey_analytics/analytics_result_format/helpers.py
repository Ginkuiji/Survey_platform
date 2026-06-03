from copy import deepcopy
from .constants import *  # noqa: F401,F403
def interpret_correlation(value):
    value = abs(value)
    if value < 0.1:
        return "очень слабая связь"
    if value < 0.3:
        return "слабая связь"
    if value < 0.5:
        return "умеренная связь"
    if value < 0.7:
        return "заметная связь"
    return "сильная связь"


def correlation_direction(value):
    if value > 0:
        return "положительная"
    if value < 0:
        return "отрицательная"
    return "нулевая"


def interpret_cramers_v(value):
    return interpret_correlation(value)


def interpret_r2(value):
    if value < 0.1:
        return "низкая объясняющая способность модели"
    if value < 0.3:
        return "умеренная объясняющая способность модели"
    if value < 0.5:
        return "достаточная объясняющая способность модели"
    return "высокая объясняющая способность модели"


def interpret_cronbach_alpha(value):
    if value < 0.6:
        return "низкая внутренняя согласованность"
    if value < 0.7:
        return "сомнительная внутренняя согласованность"
    if value < 0.8:
        return "приемлемая внутренняя согласованность"
    if value < 0.9:
        return "хорошая внутренняя согласованность"
    return "очень высокая внутренняя согласованность"


def interpret_silhouette(value):
    if value < 0.25:
        return "кластеры выражены слабо"
    if value < 0.5:
        return "кластеры разделены умеренно"
    if value < 0.7:
        return "кластеры хорошо разделены"
    return "кластеры очень хорошо разделены"


def _clean_raw_result(result):
    if not isinstance(result, dict):
        return {}
    return deepcopy({key: value for key, value in result.items() if key != "standardized_result"})


def _dataset_variables(dataset):
    variables = getattr(dataset, "variables", None) or []
    return [
        {
            "code": getattr(variable, "code", None),
            "label": getattr(variable, "label", None),
            "question_id": getattr(variable, "question_id", None),
            "qtype": getattr(variable, "qtype", None),
            "encoding": getattr(variable, "encoding", None),
            "measure": getattr(variable, "measure", None),
        }
        for variable in variables
    ]


def _variables(result, dataset):
    variables = _dataset_variables(dataset) or result.get("variables")
    return variables if isinstance(variables, list) else []


def build_input_summary(result, payload=None, dataset=None):
    variables = _variables(result, dataset)
    dataset_size = result.get("dataset_size", result.get("n"))
    summary = {"dataset_size": dataset_size, "variables_count": len(variables), "variables": variables}
    if result.get("features") is not None:
        summary["features"] = result["features"]
    if result.get("target") is not None:
        summary["target"] = result["target"]
    return summary


def _strongest_correlations(result):
    variables = result.get("variables") or []
    matrix = result.get("matrix") or []
    p_values = result.get("p_values") or []
    n_matrix = result.get("n_matrix") or []
    relationships = []
    for row_index, left in enumerate(variables):
        for column_index in range(row_index + 1, len(variables)):
            value = matrix[row_index][column_index] if row_index < len(matrix) and column_index < len(matrix[row_index]) else None
            if value is None:
                continue
            right = variables[column_index]
            p_value = p_values[row_index][column_index] if row_index < len(p_values) and column_index < len(p_values[row_index]) else None
            relationships.append({
                "left": left.get("code"),
                "right": right.get("code"),
                "left_label": left.get("label") or left.get("code"),
                "right_label": right.get("label") or right.get("code"),
                "coefficient": value,
                "absolute_coefficient": abs(value),
                "direction": correlation_direction(value),
                "strength": interpret_correlation(value),
                "p_value": p_value,
                "significant": p_value is not None and p_value < 0.05,
                "n": n_matrix[row_index][column_index] if row_index < len(n_matrix) and column_index < len(n_matrix[row_index]) else None,
                "interpretation": (
                    f"Связь {correlation_direction(value)} и {interpret_correlation(value)}. "
                    + ("Статистически значима при α = 0,05." if p_value is not None and p_value < 0.05 else "Статистическая значимость при α = 0,05 не подтверждена.")
                ),
            })
    return sorted(relationships, key=lambda item: abs(item["coefficient"]), reverse=True)[:5]


def build_correlation_method_hint(result):
    method = result.get("method") or "pearson"
    return {
        "method": method,
        "text": CORRELATION_METHOD_HINTS.get(method, "Метод корреляции следует выбирать с учетом шкалы данных и формы связи."),
    }


def build_correlation_network(result):
    return {
        "nodes": [
            {"id": variable.get("code"), "label": variable.get("label") or variable.get("code")}
            for variable in result.get("variables") or []
        ],
        "edges": [
            {
                "source": item["left"],
                "target": item["right"],
                "coefficient": item["coefficient"],
                "strength": item["strength"],
            }
            for item in _strongest_correlations(result)
            if item["absolute_coefficient"] >= 0.3
        ],
    }


