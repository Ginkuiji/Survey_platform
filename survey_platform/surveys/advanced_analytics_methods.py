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


def compute_correlation_matrix(rows, variables, method="pearson") -> dict:
    if method not in ("pearson", "spearman", "kendall"):
        raise ValueError("Метод корреляции должен быть одним из: pearson, spearman, kendall.")

    matrix = []
    p_values = []
    n_matrix = []

    for left in variables:
        matrix_row = []
        p_row = []
        n_row = []
        for right in variables:
            pairs = clean_numeric_pairs(get_column(rows, left.code), get_column(rows, right.code))
            n = len(pairs)
            n_row.append(n)

            if left.code == right.code:
                matrix_row.append(1.0 if n > 0 else None)
                p_row.append(0.0 if n > 0 else None)
                continue

            if n < 2:
                matrix_row.append(None)
                p_row.append(None)
                continue

            x_values = [pair[0] for pair in pairs]
            y_values = [pair[1] for pair in pairs]

            if stats is not None:
                if method == "pearson":
                    result = stats.pearsonr(x_values, y_values)
                elif method == "spearman":
                    result = stats.spearmanr(x_values, y_values)
                else:
                    result = stats.kendalltau(x_values, y_values)
                coefficient = None if math.isnan(result.statistic) else float(result.statistic)
                p_value = None if math.isnan(result.pvalue) else float(result.pvalue)
            else:
                if method == "kendall":
                    raise ValueError("Для корреляции Кендалла требуется установленный пакет scipy.")
                coefficient = _manual_correlation(x_values, y_values, method)
                p_value = None

            matrix_row.append(coefficient)
            p_row.append(p_value)

        matrix.append(matrix_row)
        p_values.append(p_row)
        n_matrix.append(n_row)

    return {
        "method": method,
        "variables": [{"code": variable.code, "label": variable.label} for variable in variables],
        "matrix": matrix,
        "p_values": p_values,
        "n_matrix": n_matrix,
    }


def _sort_values(values):
    return sorted(values, key=lambda value: (str(type(value)), value))


def compute_crosstab(rows, row_var_code, col_var_code, row_variable=None, column_variable=None) -> dict:
    counts = defaultdict(Counter)
    row_totals = Counter()
    column_values = set()
    total = 0

    for item in rows:
        row_value = item.get(row_var_code)
        column_value = item.get(col_var_code)
        if _is_missing(row_value) or _is_missing(column_value):
            continue
        counts[row_value][column_value] += 1
        row_totals[row_value] += 1
        column_values.add(column_value)
        total += 1

    ordered_column_values = _sort_values(column_values)
    result_rows = []
    for row_value in _sort_values(row_totals.keys()):
        row_total = row_totals[row_value]
        columns = []
        for column_value in ordered_column_values:
            count = counts[row_value][column_value]
            columns.append({
                "raw_value": column_value,
                "value": _label_for_value(column_value, getattr(column_variable, "value_labels", None)),
                "count": count,
                "percent_row": round(count / row_total * 100, 2) if row_total else 0,
                "percent_total": round(count / total * 100, 2) if total else 0,
            })
        result_rows.append({
            "raw_value": row_value,
            "value": _label_for_value(row_value, getattr(row_variable, "value_labels", None)),
            "columns": columns,
            "total": row_total,
        })

    return {
        "row_variable": getattr(row_variable, "label", None) or row_var_code,
        "column_variable": getattr(column_variable, "label", None) or col_var_code,
        "row_variable_code": row_var_code,
        "column_variable_code": col_var_code,
        "rows": result_rows,
        "total": total,
    }


def _label_for_value(value, value_labels):
    if not value_labels:
        return str(value)
    if value in value_labels:
        return value_labels[value]
    try:
        int_value = int(value)
        if int_value in value_labels:
            return value_labels[int_value]
    except (TypeError, ValueError):
        pass
    return str(value)


def _contingency_from_crosstab(crosstab_result):
    return [
        [column["count"] for column in row["columns"]]
        for row in crosstab_result["rows"]
    ]


def compute_correspondence_analysis(crosstab_result, row_variable=None, column_variable=None, n_dimensions=2) -> dict:
    if np is None:
        raise ValueError("Для анализа соответствий требуется установленный пакет numpy.")

    observed = _contingency_from_crosstab(crosstab_result)
    if len(observed) < 2 or not observed or len(observed[0]) < 2:
        raise ValueError("Для анализа соответствий нужна таблица сопряженности размером не менее 2x2.")

    matrix = np.array(observed, dtype=float)
    n_rows, n_columns = matrix.shape
    grand_total = float(np.sum(matrix))
    if grand_total <= 0:
        raise ValueError("Для анализа соответствий нужна непустая таблица сопряженности.")

    row_sums = np.sum(matrix, axis=1)
    col_sums = np.sum(matrix, axis=0)
    if np.any(row_sums == 0):
        raise ValueError("Анализ соответствий невозможен: в таблице есть строка с нулевой суммой.")
    if np.any(col_sums == 0):
        raise ValueError("Анализ соответствий невозможен: в таблице есть столбец с нулевой суммой.")

    max_dimensions = min(n_rows - 1, n_columns - 1)
    warnings = []
    dims = n_dimensions
    if dims > max_dimensions:
        dims = max_dimensions
        warnings.append("Число измерений уменьшено до максимально доступного для этой таблицы.")

    p_matrix = matrix / grand_total
    row_masses = np.sum(p_matrix, axis=1)
    col_masses = np.sum(p_matrix, axis=0)
    expected = np.outer(row_masses, col_masses)
    standardized_residuals = (p_matrix - expected) / np.sqrt(expected)

    u_matrix, singular_values, vt_matrix = np.linalg.svd(standardized_residuals, full_matrices=False)
    eigenvalues = singular_values ** 2
    total_inertia = float(np.sum(eigenvalues))
    if total_inertia == 0:
        raise ValueError("Структура связи не обнаружена: инерция анализа соответствий равна нулю.")

    row_coordinates_all = (u_matrix * singular_values) / np.sqrt(row_masses[:, None])
    column_coordinates_all = (vt_matrix.T * singular_values) / np.sqrt(col_masses[:, None])
    selected_eigenvalues = eigenvalues[:dims]
    dimension_names = [f"Измерение {index + 1}" for index in range(dims)]

    row_values = [row.get("value") for row in crosstab_result.get("rows") or []]
    column_values = []
    if crosstab_result.get("rows"):
        column_values = [
            column.get("value")
            for column in crosstab_result["rows"][0].get("columns") or []
        ]

    def contribution_items(masses, coordinates, index):
        items = []
        for dim_index, dimension in enumerate(dimension_names):
            eigenvalue = selected_eigenvalues[dim_index]
            value = 0.0 if eigenvalue == 0 else float(masses[index] * coordinates[index, dim_index] ** 2 / eigenvalue)
            items.append({"dimension": dimension, "value": value})
        return items

    def coordinate_items(coordinates, index):
        return [
            {"dimension": dimension, "value": float(coordinates[index, dim_index])}
            for dim_index, dimension in enumerate(dimension_names)
        ]

    def cos2(coordinates, index):
        total = float(np.sum(coordinates[index, :] ** 2))
        if total <= 0:
            return None
        selected = float(np.sum(coordinates[index, :dims] ** 2))
        return selected / total

    dimensions = [
        {
            "dimension": dimension,
            "eigenvalue": float(selected_eigenvalues[index]),
            "explained_inertia": float(selected_eigenvalues[index] / total_inertia),
        }
        for index, dimension in enumerate(dimension_names)
    ]

    return {
        "method": "correspondence_analysis",
        "n": int(grand_total),
        "n_rows": n_rows,
        "n_columns": n_columns,
        "n_dimensions": dims,
        "total_inertia": total_inertia,
        "row_variable": {
            "code": row_variable.code if row_variable else crosstab_result.get("row_variable_code"),
            "label": row_variable.label if row_variable else crosstab_result.get("row_variable"),
        },
        "column_variable": {
            "code": column_variable.code if column_variable else crosstab_result.get("column_variable_code"),
            "label": column_variable.label if column_variable else crosstab_result.get("column_variable"),
        },
        "dimensions": dimensions,
        "row_coordinates": [
            {
                "value": value,
                "label": _label_for_value(value, getattr(row_variable, "value_labels", None)),
                "mass": float(row_masses[index]),
                "coordinates": coordinate_items(row_coordinates_all, index),
                "contributions": contribution_items(row_masses, row_coordinates_all, index),
                "cos2": cos2(row_coordinates_all, index),
            }
            for index, value in enumerate(row_values)
        ],
        "column_coordinates": [
            {
                "value": value,
                "label": _label_for_value(value, getattr(column_variable, "value_labels", None)),
                "mass": float(col_masses[index]),
                "coordinates": coordinate_items(column_coordinates_all, index),
                "contributions": contribution_items(col_masses, column_coordinates_all, index),
                "cos2": cos2(column_coordinates_all, index),
            }
            for index, value in enumerate(column_values)
        ],
        "crosstab": crosstab_result,
        "warnings": warnings,
    }


RESIDUAL_IMPORTANT_THRESHOLD = 2.0
TOP_CHI_CELLS_LIMIT = 10


def build_expected_frequency_diagnostics(expected) -> dict:
    values = [float(value) for row in expected for value in row if value is not None]
    below_five = [value for value in values if value < 5]
    below_one = [value for value in values if value < 1]
    below_five_rate = round(len(below_five) / len(values) * 100, 2) if values else 0
    return {
        "cells_count": len(values),
        "below_5_count": len(below_five),
        "below_5_rate": below_five_rate,
        "below_1_count": len(below_one),
        "min_expected": min(values) if values else None,
        "assumption_warning": below_five_rate > 20 or bool(below_one),
    }


def _chi_square_cell_details(crosstab_result, observed, expected):
    residuals = []
    contributions = []
    top_cells = []
    rows = crosstab_result.get("rows") or []
    for row_index, observed_row in enumerate(observed):
        residual_row = []
        contribution_row = []
        for column_index, observed_value in enumerate(observed_row):
            expected_value = expected[row_index][column_index]
            residual = None if expected_value == 0 else (observed_value - expected_value) / math.sqrt(expected_value)
            contribution = None if expected_value == 0 else (observed_value - expected_value) ** 2 / expected_value
            residual_row.append(residual)
            contribution_row.append(contribution)
            if contribution is None:
                continue
            row = rows[row_index] if row_index < len(rows) else {}
            columns = row.get("columns") or []
            column = columns[column_index] if column_index < len(columns) else {}
            direction = "higher_than_expected" if observed_value > expected_value else "lower_than_expected"
            relation = "выше" if direction == "higher_than_expected" else "ниже"
            row_label = row.get("value", row.get("raw_value", row_index))
            column_label = column.get("value", column.get("raw_value", column_index))
            top_cells.append({
                "row_index": row_index,
                "column_index": column_index,
                "row_value": row.get("raw_value", row_label),
                "row_label": row_label,
                "column_value": column.get("raw_value", column_label),
                "column_label": column_label,
                "observed": observed_value,
                "expected": expected_value,
                "standardized_residual": residual,
                "important_residual": abs(residual) >= RESIDUAL_IMPORTANT_THRESHOLD if residual is not None else False,
                "contribution": contribution,
                "direction": direction,
                "interpretation": f"В категории «{row_label} × {column_label}» наблюдаемая частота {relation} ожидаемой.",
            })
        residuals.append(residual_row)
        contributions.append(contribution_row)
    top_cells.sort(key=lambda item: item["contribution"], reverse=True)
    return residuals, contributions, top_cells[:TOP_CHI_CELLS_LIMIT]


def compute_chi_square(crosstab_result) -> dict:
    observed = _contingency_from_crosstab(crosstab_result)
    if len(observed) < 2 or not observed or len(observed[0]) < 2:
        raise ValueError("Для χ²-критерия нужна таблица сопряженности размером не менее 2x2.")

    if stats is not None:
        chi2, p_value, dof, expected = stats.chi2_contingency(observed)
        expected = [[float(value) for value in row] for row in expected]
        chi2 = float(chi2)
        p_value = float(p_value)
        dof = int(dof)

    else:
        row_totals = [sum(row) for row in observed]
        column_totals = [sum(observed[row_index][col_index] for row_index in range(len(observed))) for col_index in range(len(observed[0]))]
        total = sum(row_totals)
        if total == 0:
            raise ValueError("Для χ²-критерия нужна непустая таблица сопряженности.")

        expected = [
            [row_total * column_total / total for column_total in column_totals]
            for row_total in row_totals
        ]
        chi2 = 0.0
        for row_index, row in enumerate(observed):
            for col_index, observed_value in enumerate(row):
                expected_value = expected[row_index][col_index]
                if expected_value:
                    chi2 += (observed_value - expected_value) ** 2 / expected_value
        p_value = None
        dof = (len(observed) - 1) * (len(observed[0]) - 1)

    residuals, contributions, top_cells = _chi_square_cell_details(crosstab_result, observed, expected)
    diagnostics = build_expected_frequency_diagnostics(expected)
    warnings = []
    if diagnostics["below_5_count"]:
        warnings.append("Для χ²-критерия часть ожидаемых частот меньше 5; результат следует интерпретировать осторожно.")
    if diagnostics["below_5_rate"] > 20:
        warnings.append("Более 20% ожидаемых частот меньше 5; χ²-критерий может быть ненадёжен.")
    if diagnostics["below_1_count"]:
        warnings.append("В таблице есть ожидаемые частоты меньше 1; χ²-критерий может быть неприменим.")

    return {
        "chi2": chi2,
        "p_value": p_value,
        "dof": dof,
        "observed": observed,
        "expected": expected,
        "standardized_residuals": residuals,
        "cell_contributions": contributions,
        "expected_diagnostics": diagnostics,
        "top_contributing_cells": top_cells,
        "warnings": warnings,
    }


def interpret_cramers_v(value: float) -> str:
    if value < 0.10:
        return "Очень слабая связь"
    if value < 0.30:
        return "Слабая связь"
    if value < 0.50:
        return "Умеренная связь"
    if value < 0.70:
        return "Заметная связь"
    return "Сильная связь"


def compute_cramers_v(crosstab_result, chi_square_result=None) -> dict:
    observed = _contingency_from_crosstab(crosstab_result)
    if not observed or not observed[0]:
        raise ValueError("Для V Крамера нужна непустая таблица сопряженности.")

    n = sum(sum(row) for row in observed)
    rows = len(observed)
    columns = len(observed[0])
    min_dimension = min(rows - 1, columns - 1)

    if n == 0:
        raise ValueError("Для V Крамера нужна непустая таблица сопряженности.")
    if min_dimension == 0:
        raise ValueError("Для V Крамера нужна таблица сопряженности размером не менее 2x2.")

    if chi_square_result is None:
        chi_square_result = compute_chi_square(crosstab_result)
    chi2 = chi_square_result.get("chi2")
    if chi2 is None:
        raise ValueError("Для V Крамера требуется значение χ².")

    value = math.sqrt(float(chi2) / (n * min_dimension))
    value = max(0.0, min(1.0, value))

    return {
        "cramers_v": value,
        "n": n,
        "rows": rows,
        "columns": columns,
        "interpretation": interpret_cramers_v(value),
        "effect_size_name": "Cramér’s V",
        "effect_size_description": "Показывает силу связи между двумя категориальными переменными.",
    }


MAX_DIAGNOSTIC_POINTS = 500


def _complete_regression_cases(rows, target_code, feature_codes):
    y_values = []
    x_values = []
    response_ids = []
    for row in rows:
        values = [row.get(target_code)] + [row.get(code) for code in feature_codes]
        if all(_is_numeric(value) for value in values):
            y_values.append(_as_float(values[0]))
            x_values.append([_as_float(value) for value in values[1:]])
            response_ids.append(row.get("response_id"))
    return response_ids, y_values, x_values


def _diagnostic_sample(items, notes):
    if len(items) <= MAX_DIAGNOSTIC_POINTS:
        return items
    notes.append("Для диагностических графиков сохранена ограниченная выборка наблюдений.")
    indexes = np.linspace(0, len(items) - 1, MAX_DIAGNOSTIC_POINTS, dtype=int)
    return [items[index] for index in indexes]


def _numeric_summary(values):
    if not len(values):
        return {}
    q1, median_value, q3 = (float(np.percentile(values, percentile)) for percentile in (25, 50, 75))
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outliers_count = int(np.sum((values < lower_fence) | (values > upper_fence)))
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=1)) if len(values) > 1 else None,
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "q1": q1,
        "median": median_value,
        "q3": q3,
        "iqr": iqr,
        "outliers_count": outliers_count,
        "outliers_rate": round(outliers_count / len(values) * 100, 2),
    }


def _vif_diagnostics(x_matrix, feature_codes):
    if len(feature_codes) < 2:
        return {"vif": [], "max_vif": None, "high_vif_variables": [], "notes": ["VIF не рассчитывается для модели с одним предиктором."]}
    items = []
    for index, name in enumerate(feature_codes):
        target = x_matrix[:, index]
        predictors = np.delete(x_matrix, index, axis=1)
        predictors = np.column_stack([np.ones(len(predictors)), predictors])
        coefficients, _, _, _ = np.linalg.lstsq(predictors, target, rcond=None)
        residual = target - predictors @ coefficients
        total = float(np.sum((target - np.mean(target)) ** 2))
        r2 = 1 - float(np.sum(residual ** 2)) / total if total else 1
        vif = None if r2 >= 1 else float(1 / (1 - r2))
        if vif is None:
            interpretation = "Не удалось рассчитать"
        elif vif < 5:
            interpretation = "Приемлемый уровень"
        elif vif < 10:
            interpretation = "Возможная мультиколлинеарность"
        else:
            interpretation = "Выраженная мультиколлинеарность"
        items.append({"name": name, "vif": vif, "interpretation": interpretation})
    valid = [item["vif"] for item in items if item["vif"] is not None]
    return {
        "vif": items,
        "max_vif": max(valid) if valid else None,
        "high_vif_variables": [item["name"] for item in items if item["vif"] is None or item["vif"] >= 5],
        "notes": [],
    }


def _residual_normality(residuals):
    if stats is None or len(residuals) < 3:
        return {"method": None, "statistic": None, "p_value": None, "likely_normal": None, "interpretation": "Проверка нормальности остатков недоступна."}
    result = stats.shapiro(residuals) if len(residuals) <= 5000 else stats.normaltest(residuals)
    p_value = _finite_or_none(result.pvalue)
    return {
        "method": "shapiro" if len(residuals) <= 5000 else "dagostino_k2",
        "statistic": _finite_or_none(result.statistic),
        "p_value": p_value,
        "likely_normal": p_value is not None and p_value >= 0.05,
        "interpretation": "Распределение остатков не показывает заметного отклонения от нормального." if p_value is not None and p_value >= 0.05 else "Распределение остатков может отличаться от нормального.",
    }


def _heteroscedasticity_diagnostics(predicted, residuals):
    if len(predicted) < 2 or float(np.std(predicted)) == 0 or float(np.std(np.abs(residuals))) == 0:
        correlation = None
    else:
        correlation = float(np.corrcoef(predicted, np.abs(residuals))[0, 1])
    warning = correlation is not None and abs(correlation) >= 0.3
    return {
        "method": "correlation_abs_residuals_predicted",
        "correlation": correlation,
        "warning": warning,
        "interpretation": "Разброс остатков может зависеть от предсказанного значения." if warning else "Явных признаков зависимости разброса остатков от предсказанных значений не обнаружено.",
    }


def compute_linear_regression(rows, target_code, feature_codes, include_intercept=True) -> dict:
    if not feature_codes:
        raise ValueError("Для линейной регрессии требуется хотя бы один предиктор.")
    if np is None:
        raise ValueError("Для линейной регрессии требуется установленный пакет numpy.")

    response_ids, y_values, x_values = _complete_regression_cases(rows, target_code, feature_codes)
    n = len(y_values)
    feature_count = len(feature_codes)
    parameter_count = feature_count + (1 if include_intercept else 0)

    if n <= parameter_count:
        raise ValueError("Недостаточно полных наблюдений для линейной регрессии.")

    x_matrix = np.array(x_values, dtype=float)
    if include_intercept:
        x_matrix = np.column_stack([np.ones(n), x_matrix])
    y_vector = np.array(y_values, dtype=float)

    warnings = []
    notes = []
    coefficients, _, rank, _ = np.linalg.lstsq(x_matrix, y_vector, rcond=None)
    if rank < parameter_count:
        warnings.append("Матрица признаков близка к вырожденной; стандартные ошибки и p-value могут быть нестабильными.")

    predicted = x_matrix @ coefficients
    residual_sum_squares = float(np.sum((y_vector - predicted) ** 2))
    total_sum_squares = float(np.sum((y_vector - np.mean(y_vector)) ** 2))
    r2 = 1.0 if total_sum_squares == 0 else 1 - residual_sum_squares / total_sum_squares
    degrees_of_freedom = n - parameter_count
    adjusted_r2 = 1 - (1 - r2) * (n - 1) / degrees_of_freedom if degrees_of_freedom > 0 else None
    residuals = y_vector - predicted
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mae = float(np.mean(np.abs(residuals)))
    residual_standard_error = float(np.sqrt(residual_sum_squares / degrees_of_freedom)) if degrees_of_freedom > 0 else None
    inverse_xtx = np.linalg.pinv(x_matrix.T @ x_matrix)
    covariance = inverse_xtx * (residual_sum_squares / degrees_of_freedom)
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0))
    critical = float(stats.t.ppf(0.975, degrees_of_freedom)) if stats is not None else 1.96
    if stats is None:
        warnings.append("Пакет scipy недоступен; p-value коэффициентов линейной регрессии не рассчитаны.")
    feature_matrix = np.array(x_values, dtype=float)
    target_std = float(np.std(y_vector, ddof=1))

    names = ["intercept"] + feature_codes if include_intercept else feature_codes
    coefficient_items = []
    for index, (name, value) in enumerate(zip(names, coefficients)):
        standard_error = float(standard_errors[index])
        t_statistic = float(value / standard_error) if standard_error else None
        p_value = float(2 * stats.t.sf(abs(t_statistic), degrees_of_freedom)) if stats is not None and t_statistic is not None else None
        feature_index = index - 1 if include_intercept else index
        standardized = None
        if name != "intercept" and target_std:
            feature_std = float(np.std(feature_matrix[:, feature_index], ddof=1))
            standardized = float(value * feature_std / target_std) if feature_std else None
        direction = "увеличивается" if value > 0 else "уменьшается"
        interpretation = "Свободный член модели." if name == "intercept" else f"При увеличении переменной на одну единицу целевая переменная в среднем {direction} на {abs(float(value)):.4f} при прочих равных условиях."
        coefficient_items.append({
            "name": name,
            "value": float(value),
            "standard_error": standard_error,
            "t_statistic": t_statistic,
            "p_value": p_value,
            "confidence_interval_95": {"low": float(value - critical * standard_error), "high": float(value + critical * standard_error)},
            "standardized_coefficient": standardized,
            "interpretation": interpretation,
        })
    observed_vs_predicted = [
        {"response_id": response_id, "observed": float(observed), "predicted": float(prediction), "residual": float(residual)}
        for response_id, observed, prediction, residual in zip(response_ids, y_vector, predicted, residuals)
    ]
    sampled_points = _diagnostic_sample(observed_vs_predicted, notes)
    residual_summary = _numeric_summary(residuals)
    normality = _residual_normality(residuals)
    heteroscedasticity = _heteroscedasticity_diagnostics(predicted, residuals)
    leverage = np.diag(x_matrix @ inverse_xtx @ x_matrix.T)
    standardized_residuals = residuals / (residual_standard_error * np.sqrt(np.maximum(1 - leverage, 1e-12))) if residual_standard_error else np.full(n, np.nan)
    cooks_distance = standardized_residuals ** 2 * leverage / (parameter_count * np.maximum(1 - leverage, 1e-12))
    leverage_threshold = 2 * parameter_count / n
    cooks_threshold = 4 / n
    influential = sorted([
        {**point, "standardized_residual": _finite_or_none(std_residual), "leverage": float(item_leverage), "cooks_distance": _finite_or_none(cooks)}
        for point, std_residual, item_leverage, cooks in zip(observed_vs_predicted, standardized_residuals, leverage, cooks_distance)
    ], key=lambda item: item.get("cooks_distance") or 0, reverse=True)
    multicollinearity = _vif_diagnostics(feature_matrix, feature_codes)
    if residual_summary.get("outliers_rate", 0) >= 5:
        warnings.append("Обнаружены выбросы по остаткам; отдельные наблюдения могут заметно влиять на модель.")
    if abs(residual_summary.get("mean", 0)) > max((residual_summary.get("std") or 0) * 0.1, 1e-9):
        warnings.append("Среднее остатков заметно отличается от нуля; модель может быть смещена.")
    if normality.get("likely_normal") is False:
        warnings.append("Остатки модели могут отличаться от нормального распределения; p-value коэффициентов следует интерпретировать осторожно.")
    if heteroscedasticity["warning"]:
        warnings.append("Обнаружены признаки неоднородности дисперсии остатков; стандартные ошибки и p-value могут быть нестабильными.")
    if multicollinearity["high_vif_variables"]:
        warnings.append("Обнаружена возможная мультиколлинеарность между предикторами; коэффициенты модели могут быть нестабильными.")
    if any(item["leverage"] > leverage_threshold or (item["cooks_distance"] or 0) > cooks_threshold for item in influential):
        warnings.append("Обнаружены потенциально влияющие наблюдения; рекомендуется проверить выбросы и качество ответов.")
    if r2 < 0.1:
        warnings.append("R² низкий; модель объясняет небольшую долю вариации целевой переменной.")
    return {
        "model": "linear",
        "target": target_code,
        "features": feature_codes,
        "coefficients": coefficient_items,
        "feature_count": feature_count,
        "include_intercept": include_intercept,
        "r2": float(r2),
        "adjusted_r2": float(adjusted_r2) if adjusted_r2 is not None else None,
        "rmse": rmse,
        "mae": mae,
        "residual_standard_error": residual_standard_error,
        "degrees_of_freedom": degrees_of_freedom,
        "diagnostics": {
            "residuals": [float(value) for value in residuals[:MAX_DIAGNOSTIC_POINTS]],
            "predictions": [float(value) for value in predicted[:MAX_DIAGNOSTIC_POINTS]],
            "observed_vs_predicted": sampled_points,
            "residual_summary": residual_summary,
            "normality": normality,
            "heteroscedasticity": heteroscedasticity,
            "multicollinearity": multicollinearity,
            "influential_points": {
                "high_leverage_count": sum(item["leverage"] > leverage_threshold for item in influential),
                "large_cooks_distance_count": sum((item["cooks_distance"] or 0) > cooks_threshold for item in influential),
                "thresholds": {"leverage": leverage_threshold, "cooks_distance": cooks_threshold},
                "top_points": influential[:10],
            },
        },
        "n": n,
        "warnings": warnings,
        "notes": notes,
    }


def _complete_logistic_cases(rows, target_code, feature_codes):
    y_values = []
    x_values = []
    response_ids = []

    for row in rows:
        values = [row.get(target_code)] + [row.get(code) for code in feature_codes]
        if any(_is_missing(value) for value in values):
            continue
        if not all(_is_numeric(value) for value in values):
            raise ValueError("Для логистической регрессии зависимая переменная и предикторы должны быть числовыми.")

        y_values.append(_as_float(values[0]))
        x_values.append([_as_float(value) for value in values[1:]])
        response_ids.append(row.get("response_id"))

    return response_ids, y_values, x_values


def _sigmoid(values):
    clipped = np.clip(values, -500, 500)
    return 1 / (1 + np.exp(-clipped))


def _safe_odds_ratio(coefficient):
    try:
        value = math.exp(float(coefficient))
    except (OverflowError, TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


def _interpret_odds_ratio(value):
    if value is None:
        return "—"
    if value > 1:
        return "Увеличивает шансы события"
    if value < 1:
        return "Уменьшает шансы события"
    return "Не меняет шансы события"


def _fit_sklearn_logistic(
    x_matrix,
    y_vector,
    include_intercept,
    max_iter,
    regularization,
    lambda_,
):
    from sklearn.linear_model import LogisticRegression

    if regularization == "l2":
        model = LogisticRegression(
            penalty="l2",
            C=(1 / lambda_) if lambda_ > 0 else 1e12,
            fit_intercept=include_intercept,
            max_iter=max_iter,
            solver="lbfgs",
        )
        model.fit(x_matrix, y_vector)
    else:
        try:
            model = LogisticRegression(
                penalty=None,
                fit_intercept=include_intercept,
                max_iter=max_iter,
                solver="lbfgs",
            )
            model.fit(x_matrix, y_vector)
        except (TypeError, ValueError):
            model = LogisticRegression(
                penalty="none",
                fit_intercept=include_intercept,
                max_iter=max_iter,
                solver="lbfgs",
            )
            model.fit(x_matrix, y_vector)

    coefficient_values = []
    if include_intercept:
        coefficient_values.append(float(model.intercept_[0]))
    coefficient_values.extend(float(value) for value in model.coef_[0])
    probabilities = model.predict_proba(x_matrix)[:, 1]
    return coefficient_values, probabilities


def _fit_numpy_logistic(
    x_matrix,
    y_vector,
    include_intercept,
    max_iter,
    learning_rate,
    regularization,
    lambda_,
):
    n = x_matrix.shape[0]
    design_matrix = x_matrix
    if include_intercept:
        design_matrix = np.column_stack([np.ones(n), x_matrix])

    beta = np.zeros(design_matrix.shape[1], dtype=float)
    for _ in range(max_iter):
        probabilities = _sigmoid(design_matrix @ beta)
        gradient = (design_matrix.T @ (probabilities - y_vector)) / n
        if regularization == "l2" and lambda_ > 0:
            penalty = (lambda_ * beta) / n
            if include_intercept:
                penalty[0] = 0.0
            gradient = gradient + penalty

        beta -= learning_rate * gradient
        if float(np.linalg.norm(gradient)) < 1e-6:
            break

    return [float(value) for value in beta], _sigmoid(design_matrix @ beta)


def _classification_metrics(actual, probabilities, threshold):
    predicted = probabilities >= threshold
    tp = int(np.sum((predicted == 1) & (actual == 1)))
    tn = int(np.sum((predicted == 0) & (actual == 0)))
    fp = int(np.sum((predicted == 1) & (actual == 0)))
    fn = int(np.sum((predicted == 0) & (actual == 1)))
    accuracy = (tp + tn) / len(actual)
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    specificity = tn / (tn + fp) if (tn + fp) else None
    f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and (precision + recall) else None
    balanced_accuracy = (recall + specificity) / 2 if recall is not None and specificity is not None else None
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy),
        "precision": float(precision) if precision is not None else None,
        "recall": float(recall) if recall is not None else None,
        "specificity": float(specificity) if specificity is not None else None,
        "f1": float(f1) if f1 is not None else None,
        "balanced_accuracy": float(balanced_accuracy) if balanced_accuracy is not None else None,
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


def _roc_curve_points(actual, probabilities):
    thresholds = sorted({1.0, 0.0, *[float(value) for value in probabilities]}, reverse=True)
    points = []
    positives = int(np.sum(actual == 1))
    negatives = int(np.sum(actual == 0))
    for threshold in thresholds:
        predicted = probabilities >= threshold
        tp = int(np.sum((predicted == 1) & (actual == 1)))
        fp = int(np.sum((predicted == 1) & (actual == 0)))
        points.append({"threshold": threshold, "tpr": tp / positives if positives else None, "fpr": fp / negatives if negatives else None})
    points.sort(key=lambda item: (item["fpr"], item["tpr"]))
    auc = float(np.trapezoid([item["tpr"] for item in points], [item["fpr"] for item in points])) if points else None
    return points, auc


def _calibration_bins(actual, probabilities, bins_count=10):
    bins = []
    for index in range(bins_count):
        low = index / bins_count
        high = (index + 1) / bins_count
        mask = (probabilities >= low) & ((probabilities < high) | ((index == bins_count - 1) & (probabilities <= high)))
        if not np.any(mask):
            continue
        bins.append({
            "low": low,
            "high": high,
            "n": int(np.sum(mask)),
            "mean_predicted_probability": float(np.mean(probabilities[mask])),
            "observed_event_rate": float(np.mean(actual[mask])),
        })
    return bins


def compute_logistic_regression(
    rows,
    target_code,
    feature_codes,
    include_intercept=True,
    threshold=0.5,
    max_iter=1000,
    learning_rate=0.1,
    regularization="l2",
    lambda_=0.01,
) -> dict:
    if np is None:
        raise ValueError("Для логистической регрессии требуется установленный пакет numpy.")
    if not feature_codes:
        raise ValueError("Для логистической регрессии требуется хотя бы один предиктор.")
    if regularization not in ("none", "l2"):
        raise ValueError("Параметр regularization должен быть 'none' или 'l2'.")

    response_ids, y_values, x_values = _complete_logistic_cases(rows, target_code, feature_codes)
    n = len(y_values)
    feature_count = len(feature_codes)
    parameter_count = feature_count + (1 if include_intercept else 0)
    if n <= parameter_count:
        raise ValueError("Недостаточно полных наблюдений для логистической регрессии.")

    unique_y = sorted(set(y_values))
    if unique_y != [0.0, 1.0]:
        raise ValueError("Зависимая переменная логистической регрессии должна быть бинарной (0/1) и содержать оба класса.")

    x_matrix = np.array(x_values, dtype=float)
    y_vector = np.array(y_values, dtype=float)
    if not np.all(np.isfinite(x_matrix)) or not np.all(np.isfinite(y_vector)):
        raise ValueError("Данные логистической регрессии содержат некорректные числовые значения.")

    feature_std = np.std(x_matrix, axis=0, ddof=1)
    zero_variance_indexes = np.where(feature_std == 0)[0]
    if len(zero_variance_indexes):
        labels = [feature_codes[index] for index in zero_variance_indexes]
        raise ValueError(f"Логистическая регрессия не может использовать предикторы с нулевой дисперсией: {', '.join(labels)}.")

    warnings = []
    try:
        coefficient_values, probabilities = _fit_sklearn_logistic(
            x_matrix,
            y_vector,
            include_intercept,
            max_iter,
            regularization,
            lambda_,
        )
        method = "sklearn_logistic_regression"
    except ImportError:
        coefficient_values, probabilities = _fit_numpy_logistic(
            x_matrix,
            y_vector,
            include_intercept,
            max_iter,
            learning_rate,
            regularization,
            lambda_,
        )
        method = "numpy_logistic_regression"
        warnings.append("Пакет sklearn не установлен; использован резервный расчет градиентным спуском на numpy.")

    probabilities = np.array(probabilities, dtype=float)
    actual = y_vector.astype(int)
    selected_metrics = _classification_metrics(actual, probabilities, threshold)

    eps = 1e-15
    clipped_probabilities = np.clip(probabilities, eps, 1 - eps)
    log_loss_model = float(-np.sum(y_vector * np.log(clipped_probabilities) + (1 - y_vector) * np.log(1 - clipped_probabilities)))
    base_rate = float(np.mean(y_vector))
    null_probabilities = np.clip(np.full(n, base_rate), eps, 1 - eps)
    log_loss_null = float(-np.sum(y_vector * np.log(null_probabilities) + (1 - y_vector) * np.log(1 - null_probabilities)))
    pseudo_r2 = 1 - (log_loss_model / log_loss_null) if log_loss_null > 0 else None
    roc_curve, roc_auc = _roc_curve_points(actual, probabilities)
    threshold_analysis = [_classification_metrics(actual, probabilities, value) for value in np.linspace(0.1, 0.9, 9)]
    brier_score = float(np.mean((probabilities - y_vector) ** 2))
    design_matrix = np.column_stack([np.ones(n), x_matrix]) if include_intercept else x_matrix
    weights = probabilities * (1 - probabilities)
    information = design_matrix.T @ (design_matrix * weights[:, None])
    if regularization == "l2" and lambda_ > 0:
        penalty = np.eye(information.shape[0]) * lambda_
        if include_intercept:
            penalty[0, 0] = 0
        information = information + penalty
    covariance = np.linalg.pinv(information)
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0))
    multicollinearity = _vif_diagnostics(x_matrix, feature_codes)
    positive_class_count = int(np.sum(actual == 1))
    negative_class_count = int(np.sum(actual == 0))
    minority_rate = min(positive_class_count, negative_class_count) / n * 100
    events_per_variable = min(positive_class_count, negative_class_count) / feature_count

    names = ["intercept"] + feature_codes if include_intercept else feature_codes
    coefficients = []
    for index, (name, coefficient) in enumerate(zip(names, coefficient_values)):
        odds_ratio = _safe_odds_ratio(coefficient)
        standard_error = float(standard_errors[index])
        z_statistic = float(coefficient / standard_error) if standard_error else None
        p_value = float(2 * stats.norm.sf(abs(z_statistic))) if stats is not None and z_statistic is not None else None
        low = float(coefficient - 1.96 * standard_error)
        high = float(coefficient + 1.96 * standard_error)
        coefficients.append({
            "name": name,
            "coefficient": float(coefficient),
            "standard_error": standard_error,
            "z_statistic": z_statistic,
            "p_value": p_value,
            "confidence_interval_95": {"low": low, "high": high},
            "odds_ratio": odds_ratio,
            "odds_ratio_confidence_interval_95": {"low": _safe_odds_ratio(low), "high": _safe_odds_ratio(high)},
            "interpretation": _interpret_odds_ratio(odds_ratio),
        })
    notes = []
    if regularization != "none":
        notes.append("Стандартные ошибки и p-value коэффициентов регуляризованной логистической регрессии являются приближенными.")
    if multicollinearity["high_vif_variables"]:
        warnings.append("Обнаружена возможная мультиколлинеарность между предикторами; коэффициенты модели могут быть нестабильными.")
    if minority_rate < 10:
        warnings.append("Целевая переменная сильно несбалансирована; accuracy может быть малоинформативной.")
    if events_per_variable < 10:
        warnings.append("Для логистической регрессии мало событий на один предиктор; коэффициенты могут быть нестабильными.")
    if roc_auc is not None and roc_auc < 0.7:
        warnings.append("ROC-AUC низкий; модель слабо различает классы.")
    if (selected_metrics["precision"] is not None and selected_metrics["precision"] < 0.5) or (selected_metrics["recall"] is not None and selected_metrics["recall"] < 0.5):
        warnings.append("Precision или recall низкие; модель может плохо находить один из классов.")
    prediction_items = [
        {
            "response_id": response_id,
            "actual": int(actual_value),
            "probability": float(probability),
            "predicted": int(probability >= threshold),
        }
        for response_id, actual_value, probability in zip(response_ids, actual, probabilities)
    ]
    prediction_items = _diagnostic_sample(prediction_items, notes)

    return {
        "model": "logistic",
        "method": method,
        "target": target_code,
        "features": feature_codes,
        "include_intercept": include_intercept,
        "threshold": threshold,
        "regularization": regularization,
        "lambda_": lambda_,
        "coefficients": coefficients,
        "n": n,
        "feature_count": feature_count,
        "positive_class_count": positive_class_count,
        "negative_class_count": negative_class_count,
        "base_rate": base_rate,
        "class_balance": {
            "positive_rate": round(positive_class_count / n * 100, 2),
            "negative_rate": round(negative_class_count / n * 100, 2),
            "minority_class_rate": round(minority_rate, 2),
            "is_imbalanced": minority_rate < 10,
        },
        "metrics": {
            **{key: selected_metrics[key] for key in ("accuracy", "precision", "recall", "specificity", "f1", "balanced_accuracy")},
            "roc_auc": roc_auc,
            "log_loss": log_loss_model,
            "null_log_loss": log_loss_null,
            "brier_score": brier_score,
            "mcfadden_r2": float(pseudo_r2) if pseudo_r2 is not None else None,
        },
        "confusion_matrix": selected_metrics["confusion_matrix"],
        "roc_curve": roc_curve,
        "threshold_analysis": threshold_analysis,
        "predictions": prediction_items,
        "diagnostics": {
            "multicollinearity": multicollinearity,
            "events_per_variable": events_per_variable,
            "calibration": {"bins": _calibration_bins(actual, probabilities), "brier_score": brier_score},
        },
        "warnings": warnings,
        "notes": notes,
    }


def _complete_factor_cases(rows, variables):
    matrix = []
    codes = [variable.code for variable in variables]
    for row in rows:
        values = [row.get(code) for code in codes]
        if all(_is_numeric(value) for value in values):
            matrix.append([_as_float(value) for value in values])
    return matrix


def _mean(values):
    return sum(values) / len(values) if values else None


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    middle = n // 2
    return ordered[middle] if n % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _percent(part, whole):
    return (part / whole * 100) if whole else 0


def _duration_seconds(start, end):
    if not start or not end:
        return None
    return (end - start).total_seconds()


def _duration_percentile(values, percentile):
    if not values:
        return None
    if np is not None:
        return float(np.percentile(values, percentile))
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * percentile / 100
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(ordered[lower])
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))


def _describe_durations(values):
    if not values:
        return {
            "count": 0,
            "average": None,
            "median": None,
            "min": None,
            "max": None,
            "p25": None,
            "p75": None,
            "iqr": None,
            "std": None,
        }
    p25 = _duration_percentile(values, 25)
    p75 = _duration_percentile(values, 75)
    return {
        "count": len(values),
        "average": float(_mean(values)),
        "median": float(_median(values)),
        "min": float(min(values)),
        "max": float(max(values)),
        "p25": p25,
        "p75": p75,
        "iqr": float(p75 - p25) if p25 is not None and p75 is not None else None,
        "std": float(np.std(values, ddof=1)) if np is not None and len(values) > 1 else None,
    }


def _duration_distribution(values, bucket_size_seconds=60, max_buckets=30):
    if not values:
        return [], None
    bucket_counts = Counter(int(value // bucket_size_seconds) for value in values)
    max_bucket = max(bucket_counts)
    truncated = max_bucket + 1 > max_buckets
    buckets = []
    total = len(values)
    limit = max_buckets - 1 if truncated else max_bucket + 1
    for bucket in range(limit):
        start = bucket * bucket_size_seconds
        end = start + bucket_size_seconds
        count = bucket_counts.get(bucket, 0)
        buckets.append({
            "bucket_start_seconds": start,
            "bucket_end_seconds": end,
            "label": f"{start}-{end} сек.",
            "count": count,
            "percent": _percent(count, total),
        })
    if truncated:
        start = (max_buckets - 1) * bucket_size_seconds
        count = sum(count for bucket, count in bucket_counts.items() if bucket >= max_buckets - 1)
        buckets.append({
            "bucket_start_seconds": start,
            "bucket_end_seconds": None,
            "label": f"{start}+ сек.",
            "count": count,
            "percent": _percent(count, total),
        })
    return buckets, ("Распределение длительности сокращено до максимального числа интервалов." if truncated else None)


def _time_group_label(value, value_labels):
    if not value_labels:
        return str(value)
    if value in value_labels:
        return value_labels[value]
    try:
        int_value = int(float(value))
        if int_value in value_labels:
            return value_labels[int_value]
        if str(int_value) in value_labels:
            return value_labels[str(int_value)]
    except (TypeError, ValueError):
        pass
    return str(value)


def _time_analysis_group_test(group_breakdown, warnings):
    completion_groups = [
        item["_completion_values"]
        for item in group_breakdown
        if len(item.get("_completion_values") or []) >= 2
    ]
    if len(completion_groups) < 2:
        if group_breakdown:
            warnings.append("Недостаточно данных о времени завершения для проверки различий между группами.")
        return None
    if stats is None:
        warnings.append("Пакет scipy не установлен; проверка значимости различий времени между группами недоступна.")
        return {
            "method": None,
            "statistic": None,
            "p_value": None,
            "significant": None,
            "interpretation": "p-value недоступен; невозможно оценить различия между группами.",
        }
    if len(completion_groups) == 2:
        result = stats.mannwhitneyu(completion_groups[0], completion_groups[1], alternative="two-sided")
        method = "Mann-Whitney U"
    else:
        result = stats.kruskal(*completion_groups)
        method = "Kruskal-Wallis"
    statistic = _finite_or_none(result.statistic)
    p_value = _finite_or_none(result.pvalue)
    significant = bool(p_value is not None and p_value < 0.05)
    return {
        "method": method,
        "statistic": statistic,
        "p_value": p_value,
        "significant": significant,
        "interpretation": "Время прохождения статистически различается между группами." if significant else "Статистически значимых различий времени между группами не выявлено.",
    }


def compute_time_analysis(
    response_items,
    group_rows=None,
    group_variable=None,
    bucket_size_seconds=60,
    max_buckets=30,
    page_items=None,
    include_quality_flags=True,
    include_page_dropout=True,
    include_flow=True,
    too_fast_threshold_seconds=None,
) -> dict:
    warnings = []
    total_started = len(response_items)
    total_finished = 0
    total_completed = 0
    total_screened_out = 0
    total_active_unfinished = 0
    completion_durations = []
    screenout_durations = []
    screenout_reason_values = defaultdict(list)
    response_metrics = {}
    invalid_duration_count = 0

    for item in response_items:
        response_id = item.get("response_id")
        started_at = item.get("started_at")
        finished_at = item.get("finished_at")
        screened_out = bool(item.get("screened_out"))
        is_complete = bool(item.get("is_complete"))
        complete_reason = item.get("complete_reason")
        duration = _duration_seconds(started_at, finished_at)
        invalid_duration = duration is not None and duration <= 0
        if duration is not None and duration <= 0:
            warnings.append("Обнаружены неположительные длительности прохождения; они исключены из статистики.")
            invalid_duration_count += 1
            duration = None
        if finished_at:
            total_finished += 1
        elif not is_complete:
            total_active_unfinished += 1

        completion_duration = None
        if is_complete and not screened_out and complete_reason == "completed":
            total_completed += 1
            completion_duration = duration
            if completion_duration is not None:
                completion_durations.append(completion_duration)

        screenout_duration = None
        if screened_out:
            total_screened_out += 1
            screenout_duration = _duration_seconds(started_at, item.get("screened_out_at")) or duration
            if screenout_duration is not None and screenout_duration <= 0:
                warnings.append("Обнаружены неположительные длительности до screenout; они исключены из статистики.")
                screenout_duration = None
            if screenout_duration is not None:
                screenout_durations.append(screenout_duration)
                reason = (item.get("screened_out_reason") or "").strip() or "Без указания причины"
                screenout_reason_values[reason].append(screenout_duration)

        response_metrics[response_id] = {
            "finished": bool(finished_at),
            "completed": bool(completion_duration is not None or (is_complete and not screened_out and complete_reason == "completed")),
            "screened_out": screened_out,
            "completion_duration": completion_duration,
            "screenout_duration": screenout_duration,
            "answered_question_ids": set(item.get("answered_question_ids") or []),
            "invalid_duration": invalid_duration,
        }

    completion_distribution, completion_warning = _duration_distribution(completion_durations, bucket_size_seconds, max_buckets)
    screenout_distribution, screenout_warning = _duration_distribution(screenout_durations, bucket_size_seconds, max_buckets)
    if completion_warning:
        warnings.append(completion_warning)
    if screenout_warning:
        warnings.append(screenout_warning)

    screenout_reasons = [
        {
            "reason": reason,
            "count": len(values),
            "percent_screened_out": _percent(len(values), total_screened_out),
            "average_time_to_screenout_seconds": _mean(values),
        }
        for reason, values in sorted(screenout_reason_values.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    ]

    group_breakdown = []
    if group_rows is not None and group_variable is not None:
        grouped = defaultdict(list)
        for row in group_rows:
            response_id = row.get("response_id")
            value = row.get(group_variable.code)
            if response_id in response_metrics and not _is_missing(value):
                grouped[value].append(response_id)
        for group_value in _sort_values(grouped.keys()):
            ids = grouped[group_value]
            metrics = [response_metrics[response_id] for response_id in ids]
            completion_values = [item["completion_duration"] for item in metrics if item.get("completion_duration") is not None]
            screenout_values = [item["screenout_duration"] for item in metrics if item.get("screenout_duration") is not None]
            completed = sum(1 for item in metrics if item.get("completed"))
            screened = sum(1 for item in metrics if item.get("screened_out"))
            finished = sum(1 for item in metrics if item.get("finished"))
            group_breakdown.append({
                "group": group_value,
                "group_label": _time_group_label(group_value, group_variable.value_labels),
                "total_started": len(ids),
                "total_finished": finished,
                "total_completed": completed,
                "total_screened_out": screened,
                "completion_rate": _percent(completed, len(ids)),
                "screenout_rate": _percent(screened, len(ids)),
                "completion_time": _describe_durations(completion_values),
                "screenout_time": _describe_durations(screenout_values),
                "_completion_values": completion_values,
            })

    group_time_test = _time_analysis_group_test(group_breakdown, warnings) if group_breakdown else None
    completion_stats = _describe_durations(completion_durations)
    screenout_stats = _describe_durations(screenout_durations)
    p25 = completion_stats["p25"]
    p75 = completion_stats["p75"]
    iqr = completion_stats["iqr"]
    lower_fence = max(0, p25 - 1.5 * iqr) if p25 is not None and iqr is not None else None
    upper_fence = p75 + 1.5 * iqr if p75 is not None and iqr is not None else None
    median = completion_stats["median"]
    fast_threshold = float(too_fast_threshold_seconds) if too_fast_threshold_seconds is not None else max(30, (median or 0) * 0.25)
    short_outliers = [value for value in completion_durations if lower_fence is not None and value < lower_fence]
    long_outliers = [value for value in completion_durations if upper_fence is not None and value > upper_fence]
    too_fast_ids = {
        response_id for response_id, metrics in response_metrics.items()
        if metrics.get("completion_duration") is not None and metrics["completion_duration"] < fast_threshold
    }
    too_long_ids = {
        response_id for response_id, metrics in response_metrics.items()
        if metrics.get("completion_duration") is not None and upper_fence is not None and metrics["completion_duration"] > upper_fence
    }
    response_flags = []
    if include_quality_flags:
        for response_id, metrics in response_metrics.items():
            flags = []
            duration = metrics.get("completion_duration") or metrics.get("screenout_duration")
            if response_id in too_fast_ids:
                flags.append("too_fast")
            if response_id in too_long_ids:
                flags.append("too_long")
            if metrics.get("invalid_duration"):
                flags.append("invalid_duration")
            if metrics.get("screened_out"):
                flags.append("screened_out")
            if not metrics.get("finished"):
                flags.append("unfinished")
            if flags:
                response_flags.append({"response_id": response_id, "duration_seconds": duration, "flags": flags, "possibly_low_quality": bool({"too_fast", "too_long"} & set(flags)), "reason": "Прохождение требует проверки с учетом длительности и итогового статуса."})
    page_items = page_items or []
    dropout_by_page = []
    funnel_steps = [{"step": 0, "label": "Начали опрос", "count": total_started, "percent_of_started": 100.0}]
    if include_page_dropout:
        previous_entered = total_started
        for index, page in enumerate(page_items, start=1):
            question_ids = set(page.get("question_ids") or [])
            entered = sum(bool(metrics["answered_question_ids"] & question_ids) for metrics in response_metrics.values())
            dropout = max(0, previous_entered - entered)
            dropout_by_page.append({"page_id": page.get("page_id"), "page_title": page.get("page_title"), "page_order": page.get("page_order", index), "entered_count": previous_entered, "completed_page_count": entered, "dropout_count": dropout, "dropout_rate": _percent(dropout, previous_entered)})
            funnel_steps.append({"step": index, "page_id": page.get("page_id"), "label": page.get("page_title"), "count": entered, "percent_of_started": _percent(entered, total_started)})
            previous_entered = entered
    funnel_steps.append({"step": 999, "label": "Завершили", "count": total_completed, "percent_of_started": _percent(total_completed, total_started)})
    highest_dropout = max(dropout_by_page, key=lambda item: item["dropout_rate"], default=None)
    flow_nodes = [{"id": "start", "label": "Начали"}, *[{"id": f"page_{item.get('page_id')}", "label": item.get("page_title")} for item in page_items], {"id": "completed", "label": "Завершили"}, {"id": "screenout", "label": "Отсечены"}, {"id": "unfinished", "label": "Не завершили"}]
    flow_links = []
    if include_flow:
        previous = "start"
        for step in funnel_steps[1:-1]:
            current = f"page_{step.get('page_id')}"
            flow_links.append({"source": previous, "target": current, "value": step["count"]})
            previous = current
        flow_links.extend([{"source": previous, "target": "completed", "value": total_completed}, {"source": previous, "target": "screenout", "value": total_screened_out}, {"source": previous, "target": "unfinished", "value": total_active_unfinished}])
    duration_outliers = {"method": "iqr", "lower_fence_seconds": lower_fence, "upper_fence_seconds": upper_fence, "short_outliers_count": len(short_outliers), "long_outliers_count": len(long_outliers), "outliers_count": len(short_outliers) + len(long_outliers), "outliers_rate": _percent(len(short_outliers) + len(long_outliers), len(completion_durations))}
    quality_flags = {"too_fast": {"threshold_seconds": fast_threshold, "count": len(too_fast_ids), "rate": _percent(len(too_fast_ids), len(completion_durations)), "interpretation": "Слишком быстрое прохождение может указывать на невнимательное заполнение, но не является доказательством низкого качества ответа."}, "too_long": {"threshold_seconds": upper_fence, "count": len(too_long_ids), "rate": _percent(len(too_long_ids), len(completion_durations))}, "possibly_low_quality_count": len(too_fast_ids | too_long_ids), "possibly_low_quality_rate": _percent(len(too_fast_ids | too_long_ids), len(completion_durations))}
    if quality_flags["too_fast"]["rate"] >= 5:
        warnings.append("Обнаружены слишком быстрые прохождения; они требуют проверки перед содержательной интерпретацией.")
    if long_outliers:
        warnings.append("Обнаружены аномально длинные прохождения; они могут быть связаны с перерывами при заполнении анкеты.")
    if highest_dropout and highest_dropout["dropout_rate"] >= 20:
        warnings.append("На отдельных страницах наблюдается повышенный dropout; страница может требовать содержательной проверки.")
    if _percent(total_screened_out, total_started) >= 30:
        warnings.append("Доля screenout заметна; следует проверить условия скрининга.")
    duration_summary = {"count": completion_stats["count"], "average_seconds": completion_stats["average"], "median_seconds": median, "min_seconds": completion_stats["min"], "max_seconds": completion_stats["max"], "p25_seconds": p25, "p75_seconds": p75, "iqr_seconds": iqr, "std_seconds": completion_stats["std"], "invalid_duration_count": invalid_duration_count}
    screenout_block = {"total_screened_out": total_screened_out, "screenout_rate": _percent(total_screened_out, total_started), "reasons": [{**item, "percent_of_screened_out": item["percent_screened_out"], "percent_of_started": _percent(item["count"], total_started)} for item in screenout_reasons], "top_reason": screenout_reasons[0] if screenout_reasons else None}
    group_comparison = {"enabled": bool(group_breakdown), "group_variable": {"code": getattr(group_variable, "code", None), "label": getattr(group_variable, "label", None)} if group_variable else None, "groups": [{"group_value": item["group"], "group_label": item["group_label"], "n": item["total_started"], "median_seconds": item["completion_time"]["median"], "average_seconds": item["completion_time"]["average"], "p25_seconds": item["completion_time"]["p25"], "p75_seconds": item["completion_time"]["p75"], "iqr_seconds": item["completion_time"]["iqr"], "too_fast_count": sum(value < fast_threshold for value in item["_completion_values"]), "too_fast_rate": _percent(sum(value < fast_threshold for value in item["_completion_values"]), len(item["_completion_values"]))} for item in group_breakdown], "test": group_time_test, "warnings": []}
    for item in group_breakdown:
        item.pop("_completion_values", None)
    notes = []
    if include_page_dropout:
        notes.append("Dropout по страницам рассчитан приближенно на основе наличия ответов на вопросы страниц.")
    if len(response_flags) > 500:
        notes.append("Список флагов респондентов ограничен первыми 500 записями.")
    notes.append("Straight-lining и повторяющиеся паттерны ответов следует проверять отдельными методами контроля качества.")
    return {
        "method": "time_and_dropout_analysis",
        "n": total_started,
        "summary": {
            "total_started": total_started,
            "total_finished": total_finished,
            "total_completed": total_completed,
            "total_screened_out": total_screened_out,
            "total_active_unfinished": total_active_unfinished,
            "completion_rate": _percent(total_completed, total_started),
            "screenout_rate": _percent(total_screened_out, total_started),
            "finish_rate": _percent(total_finished, total_started),
            "active_unfinished_rate": _percent(total_active_unfinished, total_started),
            "average_completion_time_seconds": completion_stats["average"],
            "median_completion_time_seconds": completion_stats["median"],
            "min_completion_time_seconds": completion_stats["min"],
            "max_completion_time_seconds": completion_stats["max"],
            "average_screenout_time_seconds": screenout_stats["average"],
            "median_screenout_time_seconds": screenout_stats["median"],
            "min_screenout_time_seconds": screenout_stats["min"],
            "max_screenout_time_seconds": screenout_stats["max"],
        },
        "completion_time_distribution": completion_distribution,
        "duration_distribution": completion_distribution,
        "duration_summary": duration_summary,
        "duration_outliers": duration_outliers,
        "quality_flags": quality_flags,
        "response_flags": response_flags[:500],
        "dropout": {"by_page": dropout_by_page, "highest_dropout_page": highest_dropout},
        "page_funnel": {"steps": funnel_steps},
        "retention_curve": {"unit": "page", "points": [{"step": item["step"], "label": item["label"], "retained_count": item["count"], "retention_rate": item["percent_of_started"]} for item in funnel_steps]},
        "screenout": screenout_block,
        "group_comparison": group_comparison,
        "flow": {"nodes": flow_nodes if include_flow else [], "links": flow_links, "notes": ["Flow diagram построен приближенно по достижению страниц и итоговым статусам прохождения."] if include_flow else []},
        "screenout_time_distribution": screenout_distribution,
        "screenout_reasons": screenout_reasons,
        "group_breakdown": group_breakdown,
        "group_time_test": group_time_test,
        "warnings": warnings,
        "recommendations": ["Проверьте слишком быстрые прохождения перед использованием данных в сложном анализе.", "Если dropout концентрируется на конкретной странице, проверьте длину, сложность и обязательность вопросов на этой странице."],
        "notes": notes,
    }


def _complete_factor_cases_with_ids(rows, variables):
    matrix = []
    response_ids = []
    codes = [variable.code for variable in variables]
    for row in rows:
        values = [row.get(code) for code in codes]
        if all(_is_numeric(value) for value in values):
            matrix.append([_as_float(value) for value in values])
            response_ids.append(row.get("response_id"))
    return response_ids, matrix


def _complete_kmeans_cases(rows, variables):
    matrix = []
    response_ids = []
    codes = [variable.code for variable in variables]
    for row in rows:
        values = [row.get(code) for code in codes]
        if any(_is_missing(value) for value in values):
            continue
        if not all(_is_numeric(value) for value in values):
            raise ValueError("Для кластерного анализа все выбранные значения должны быть числовыми.")
        matrix.append([_as_float(value) for value in values])
        response_ids.append(row.get("response_id"))
    return response_ids, matrix


def _run_numpy_kmeans(x_matrix, n_clusters, max_iter, random_state):
    rng = np.random.default_rng(random_state)
    n = x_matrix.shape[0]
    initial_indexes = rng.choice(n, size=n_clusters, replace=False)
    centers = x_matrix[initial_indexes].copy()
    labels = np.zeros(n, dtype=int)

    for _ in range(max_iter):
        distances = np.sum((x_matrix[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        next_labels = np.argmin(distances, axis=1)

        next_centers = centers.copy()
        for cluster_index in range(n_clusters):
            members = x_matrix[next_labels == cluster_index]
            if len(members):
                next_centers[cluster_index] = np.mean(members, axis=0)
            else:
                farthest_index = int(np.argmax(np.min(distances, axis=1)))
                next_centers[cluster_index] = x_matrix[farthest_index]

        if np.array_equal(labels, next_labels) and np.allclose(centers, next_centers):
            labels = next_labels
            centers = next_centers
            break

        labels = next_labels
        centers = next_centers

    inertia = float(np.sum((x_matrix - centers[labels]) ** 2))
    return labels, centers, inertia


def _profile_label_for_value(value, value_labels):
    if not value_labels:
        return str(value)
    if value in value_labels:
        return value_labels[value]
    try:
        int_value = int(float(value))
        if int_value in value_labels:
            return value_labels[int_value]
        if str(int_value) in value_labels:
            return value_labels[str(int_value)]
    except (TypeError, ValueError):
        pass
    if str(value) in value_labels:
        return value_labels[str(value)]
    return str(value)


def _profile_value_key(value):
    try:
        numeric = float(value)
        if numeric.is_integer():
            return int(numeric)
        return numeric
    except (TypeError, ValueError):
        return value


def _profile_median(values):
    ordered = sorted(values)
    n = len(ordered)
    middle = n // 2
    return ordered[middle] if n % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _numeric_profile_summary(variable, all_values, cluster_values):
    if not all_values or not cluster_values:
        return None
    overall_mean = sum(all_values) / len(all_values)
    cluster_mean = sum(cluster_values) / len(cluster_values)
    overall_std = _sample_std(all_values) if len(all_values) > 1 else None
    cluster_std = _sample_std(cluster_values) if len(cluster_values) > 1 else None
    difference = cluster_mean - overall_mean
    z_difference = difference / overall_std if overall_std and overall_std > 0 else None
    if z_difference is None:
        interpretation = "около среднего"
    elif z_difference >= 0.5:
        interpretation = "выше среднего"
    elif z_difference <= -0.5:
        interpretation = "ниже среднего"
    else:
        interpretation = "около среднего"
    return {
        "variable": variable.code,
        "label": variable.label,
        "encoding": variable.encoding,
        "cluster_mean": float(cluster_mean),
        "cluster_median": float(_profile_median(cluster_values)),
        "cluster_std": float(cluster_std) if cluster_std is not None else None,
        "cluster_min": float(min(cluster_values)),
        "cluster_max": float(max(cluster_values)),
        "overall_mean": float(overall_mean),
        "overall_std": float(overall_std) if overall_std is not None else None,
        "difference": float(difference),
        "z_difference": float(z_difference) if z_difference is not None else None,
        "interpretation": interpretation,
    }


def _binary_profile_summary(variable, all_values, cluster_values):
    if not all_values or not cluster_values:
        return None
    overall_selected = sum(1 for value in all_values if value > 0)
    cluster_selected = sum(1 for value in cluster_values if value > 0)
    overall_percent = overall_selected / len(all_values) * 100
    cluster_percent = cluster_selected / len(cluster_values) * 100
    difference_pp = cluster_percent - overall_percent
    if difference_pp >= 10:
        interpretation = "чаще, чем в среднем"
    elif difference_pp <= -10:
        interpretation = "реже, чем в среднем"
    else:
        interpretation = "примерно как в среднем"
    return {
        "variable": variable.code,
        "label": variable.label,
        "encoding": variable.encoding,
        "cluster_count_selected": int(cluster_selected),
        "cluster_percent_selected": float(cluster_percent),
        "overall_percent_selected": float(overall_percent),
        "difference_pp": float(difference_pp),
        "interpretation": interpretation,
    }


def _categorical_distribution_summary(variable, all_values, cluster_values):
    value_labels = getattr(variable, "value_labels", None)
    if not value_labels or not all_values or not cluster_values:
        return None

    overall_counts = Counter(_profile_value_key(value) for value in all_values)
    cluster_counts = Counter(_profile_value_key(value) for value in cluster_values)
    categories = []
    for value in sorted(overall_counts.keys(), key=lambda item: str(item)):
        cluster_count = cluster_counts.get(value, 0)
        overall_count = overall_counts.get(value, 0)
        cluster_percent = cluster_count / len(cluster_values) * 100 if cluster_values else 0
        overall_percent = overall_count / len(all_values) * 100 if all_values else 0
        categories.append({
            "value": value,
            "label": _profile_label_for_value(value, value_labels),
            "cluster_count": int(cluster_count),
            "cluster_percent": float(cluster_percent),
            "overall_count": int(overall_count),
            "overall_percent": float(overall_percent),
            "difference_pp": float(cluster_percent - overall_percent),
        })

    return {
        "variable": variable.code,
        "label": variable.label,
        "encoding": variable.encoding,
        "categories": categories,
    }


def _cluster_interpretation(top_features):
    if not top_features:
        return "Выраженных отличий от общей выборки не выявлено."

    high = []
    low = []
    more = []
    less = []
    for feature in top_features[:3]:
        label = feature.get("label") or feature.get("variable")
        difference = feature.get("difference") or 0
        if feature.get("type") == "numeric":
            (high if difference > 0 else low).append(label)
        else:
            (more if difference > 0 else less).append(label)

    parts = []
    if high:
        parts.append(f"высокими значениями по признакам: {', '.join(high)}")
    if low:
        parts.append(f"низкими значениями по признакам: {', '.join(low)}")
    if more:
        parts.append(f"чаще встречается: {', '.join(more)}")
    if less:
        parts.append(f"реже встречается: {', '.join(less)}")
    if not parts:
        return "Выраженных отличий от общей выборки не выявлено."
    return f"Кластер характеризуется {'; '.join(parts)}."


def _build_cluster_profiles(profile_rows, profile_variables, assignments, max_profile_features=5):
    if not profile_rows or not profile_variables or not assignments:
        return []

    cluster_by_response_id = {
        assignment.get("response_id"): assignment.get("cluster")
        for assignment in assignments
        if assignment.get("response_id") is not None
    }
    cluster_ids = sorted(set(cluster_by_response_id.values()))
    total_assigned = len(cluster_by_response_id)
    rows_by_cluster = defaultdict(list)
    for row in profile_rows:
        response_id = row.get("response_id")
        cluster = cluster_by_response_id.get(response_id)
        if cluster is not None:
            rows_by_cluster[cluster].append(row)

    profiles = []
    numeric_encodings = {"numeric", "ordinal", "rank", "matrix_ordinal"}
    binary_encodings = {"binary", "one_hot", "matrix_multi_binary"}

    for cluster in cluster_ids:
        cluster_rows = rows_by_cluster.get(cluster, [])
        numeric_summary = []
        binary_summary = []
        categorical_summary = []
        top_features = []

        for variable in profile_variables:
            all_raw_values = [
                row.get(variable.code)
                for row in profile_rows
                if row.get("response_id") in cluster_by_response_id and not _is_missing(row.get(variable.code))
            ]
            cluster_raw_values = [
                row.get(variable.code)
                for row in cluster_rows
                if not _is_missing(row.get(variable.code))
            ]
            if not all_raw_values or not cluster_raw_values:
                continue

            if variable.encoding in numeric_encodings and all(_is_numeric(value) for value in all_raw_values + cluster_raw_values):
                all_values = [_as_float(value) for value in all_raw_values]
                cluster_values = [_as_float(value) for value in cluster_raw_values]
                summary = _numeric_profile_summary(variable, all_values, cluster_values)
                if summary:
                    numeric_summary.append(summary)
                    if not (variable.encoding == "ordinal" and getattr(variable, "value_labels", None)):
                        score = abs(summary["z_difference"]) if summary["z_difference"] is not None else abs(summary["difference"])
                        top_features.append({
                            "variable": variable.code,
                            "label": variable.label,
                            "type": "numeric",
                            "cluster_value": summary["cluster_mean"],
                            "overall_value": summary["overall_mean"],
                            "difference": summary["difference"],
                            "standardized_difference": summary["z_difference"],
                            "score": float(score),
                            "interpretation": summary["interpretation"],
                        })

            if variable.encoding in binary_encodings and all(_is_numeric(value) for value in all_raw_values + cluster_raw_values):
                all_values = [_as_float(value) for value in all_raw_values]
                cluster_values = [_as_float(value) for value in cluster_raw_values]
                summary = _binary_profile_summary(variable, all_values, cluster_values)
                if summary:
                    binary_summary.append(summary)
                    top_features.append({
                        "variable": variable.code,
                        "label": variable.label,
                        "type": "binary",
                        "cluster_value": summary["cluster_percent_selected"],
                        "overall_value": summary["overall_percent_selected"],
                        "difference": summary["difference_pp"],
                        "score": abs(summary["difference_pp"]),
                        "interpretation": summary["interpretation"],
                    })

            if variable.encoding == "ordinal" and getattr(variable, "value_labels", None):
                summary = _categorical_distribution_summary(variable, all_raw_values, cluster_raw_values)
                if summary:
                    categorical_summary.append(summary)
                    categories = summary.get("categories") or []
                    if categories:
                        top_category = max(categories, key=lambda item: abs(item.get("difference_pp") or 0))
                        top_features.append({
                            "variable": variable.code,
                            "label": f"{variable.label}: {top_category.get('label')}",
                            "type": "categorical",
                            "cluster_value": top_category.get("cluster_percent"),
                            "overall_value": top_category.get("overall_percent"),
                            "difference": top_category.get("difference_pp"),
                            "score": abs(top_category.get("difference_pp") or 0),
                            "interpretation": "чаще, чем в среднем" if (top_category.get("difference_pp") or 0) >= 10 else ("реже, чем в среднем" if (top_category.get("difference_pp") or 0) <= -10 else "примерно как в среднем"),
                        })

        top_features = sorted(top_features, key=lambda item: item.get("score") or 0, reverse=True)[:max_profile_features]
        size = len(cluster_rows)
        positive_features = [
            item for item in top_features
            if (item.get("difference") or 0) > 0
        ]
        negative_features = [
            item for item in top_features
            if (item.get("difference") or 0) < 0
        ]
        profiles.append({
            "cluster": cluster,
            "label": f"Кластер {cluster}",
            "size": size,
            "percent": round(size / total_assigned * 100, 2) if total_assigned else 0,
            "numeric_summary": numeric_summary,
            "categorical_summary": categorical_summary,
            "binary_summary": binary_summary,
            "top_distinguishing_features": top_features,
            "top_positive_features": positive_features,
            "top_negative_features": negative_features,
            "profile_values": [
                {
                    "code": item["variable"],
                    "label": item["label"],
                    "cluster_mean": item["cluster_mean"],
                    "overall_mean": item["overall_mean"],
                    "difference": item["difference"],
                    "standardized_difference": item["z_difference"],
                    "interpretation": item["interpretation"],
                }
                for item in numeric_summary
            ],
            "summary": _cluster_interpretation(top_features),
            "interpretation": _cluster_interpretation(top_features),
            "interpretation_hint": "Кластер можно содержательно рассматривать как возможный сегмент респондентов после проверки профиля признаков.",
        })

    return profiles


MAX_CLUSTER_ASSIGNMENTS = 500
MAX_SILHOUETTE_SAMPLES = 500
MAX_CLUSTER_SCATTER_POINTS = 500
MAX_RADAR_FEATURES = 8
DISTINGUISHING_FEATURE_THRESHOLD = 0.3


def _cluster_elbow(x_matrix, include_elbow, min_k, max_k, max_iter, random_state):
    if not include_elbow:
        return {"enabled": False, "points": [], "suggested_k": None, "interpretation": "Elbow plot отключен в настройках отчета."}
    upper = min(max_k, len(x_matrix) - 1)
    lower = max(1, min_k)
    if upper < lower:
        return {"enabled": False, "points": [], "suggested_k": None, "interpretation": "Недостаточно наблюдений для elbow plot."}
    points = []
    for k in range(lower, upper + 1):
        _, _, inertia = _run_numpy_kmeans(x_matrix, k, max_iter, random_state)
        points.append({"k": k, "inertia": inertia})
    suggested = None
    if len(points) >= 3:
        improvements = [points[index - 1]["inertia"] - points[index]["inertia"] for index in range(1, len(points))]
        if improvements and max(improvements) > 0:
            changes = [
                improvements[index - 1] - improvements[index]
                for index in range(1, len(improvements))
            ]
            if changes and max(changes) > 0:
                suggested = points[int(np.argmax(changes)) + 1]["k"]
    interpretation = (
        f"На elbow plot улучшение заметно замедляется после k={suggested}."
        if suggested is not None
        else "Явный локоть не обнаружен; число кластеров следует выбирать с учетом silhouette score и содержательной интерпретации."
    )
    return {"enabled": True, "min_k": lower, "max_k": upper, "points": points, "suggested_k": suggested, "interpretation": interpretation}


def _cluster_dimension_reduction(x_matrix, response_ids, labels, centers, cluster_number_by_label, include_projection):
    if not include_projection or x_matrix.shape[1] < 2:
        return {"method": "pca", "available": False, "points": [], "centroids": [], "explained_variance": [], "reason": "Для двумерной визуализации требуется не менее двух переменных."}
    centered = x_matrix - np.mean(x_matrix, axis=0)
    _, singular_values, vh = np.linalg.svd(centered, full_matrices=False)
    components = vh[:2]
    points = centered @ components.T
    projected_centers = (centers - np.mean(x_matrix, axis=0)) @ components.T
    total_variance = float(np.sum(singular_values ** 2))
    explained = [
        {"component": f"PC{index + 1}", "explained_variance": float(singular_values[index] ** 2 / total_variance) if total_variance else 0}
        for index in range(min(2, len(singular_values)))
    ]
    return {
        "method": "pca",
        "available": True,
        "explained_variance": explained,
        "points": [
            {"response_id": response_id, "x": float(points[index, 0]), "y": float(points[index, 1]), "cluster": cluster_number_by_label[int(label)], "cluster_label": f"Кластер {cluster_number_by_label[int(label)]}"}
            for index, (response_id, label) in enumerate(zip(response_ids, labels))
        ][:MAX_CLUSTER_SCATTER_POINTS],
        "centroids": [
            {"cluster": cluster_number_by_label[label], "cluster_label": f"Кластер {cluster_number_by_label[label]}", "x": float(projected_centers[label, 0]), "y": float(projected_centers[label, 1])}
            for label in sorted(cluster_number_by_label)
        ],
    }


def compute_kmeans_clustering(
    rows,
    variables,
    n_clusters=3,
    standardize=True,
    max_iter=300,
    random_state=42,
    profile_rows=None,
    profile_variables=None,
    max_profile_features=5,
    include_elbow=True,
    elbow_min_k=2,
    elbow_max_k=8,
    include_pca_projection=True,
) -> dict:
    if np is None:
        raise ValueError("Для кластерного анализа требуется установленный пакет numpy.")
    if len(variables) < 2:
        raise ValueError("Для кластерного анализа требуется не менее двух переменных.")
    if n_clusters < 2 or n_clusters > 10:
        raise ValueError("Число кластеров должно быть от 2 до 10.")
    if max_iter < 10 or max_iter > 1000:
        raise ValueError("max_iter должен быть от 10 до 1000.")

    response_ids, complete_cases = _complete_kmeans_cases(rows, variables)
    n = len(complete_cases)
    p = len(variables)
    if n < n_clusters:
        raise ValueError("Для кластерного анализа число полных наблюдений должно быть не меньше числа кластеров.")

    raw_matrix = np.array(complete_cases, dtype=float)
    if not np.all(np.isfinite(raw_matrix)):
        raise ValueError("Данные кластерного анализа содержат некорректные числовые значения.")

    means = np.mean(raw_matrix, axis=0)
    standard_deviations = np.std(raw_matrix, axis=0, ddof=1)
    zero_variance_indexes = np.where(standard_deviations == 0)[0]
    if len(zero_variance_indexes):
        labels = [variables[index].label for index in zero_variance_indexes]
        raise ValueError(f"Cluster analysis cannot use variables with zero variance: {', '.join(labels)}.")

    x_matrix = (raw_matrix - means) / standard_deviations if standardize else raw_matrix
    warnings = []
    method = "numpy_kmeans"

    try:
        from sklearn.cluster import KMeans

        model = KMeans(
            n_clusters=n_clusters,
            max_iter=max_iter,
            random_state=random_state,
            n_init=10,
        )
        labels = model.fit_predict(x_matrix)
        centers = model.cluster_centers_
        inertia = float(model.inertia_)
        method = "sklearn_kmeans"
    except ImportError:
        labels, centers, inertia = _run_numpy_kmeans(x_matrix, n_clusters, max_iter, random_state)
        warnings.append("Пакет sklearn не установлен; использован резервный расчет k-средних на numpy.")

    output_centers = (centers * standard_deviations + means) if standardize else centers
    order = sorted(range(n_clusters), key=lambda index: (-int(np.sum(labels == index)), index))
    cluster_number_by_label = {label: position + 1 for position, label in enumerate(order)}

    clusters = []
    cluster_sizes = []
    cluster_centroids = []
    for label in order:
        size = int(np.sum(labels == label))
        center = output_centers[label]
        standardized_center = centers[label]
        cluster_number = cluster_number_by_label[label]
        clusters.append({
            "cluster": cluster_number,
            "size": size,
            "percent": round(size / n * 100, 2) if n else 0,
            "centroid": {
                variable.code: float(center[index])
                for index, variable in enumerate(variables)
            },
        })
        cluster_sizes.append({"cluster": cluster_number, "label": f"Кластер {cluster_number}", "count": size, "size": size, "percent": round(size / n * 100, 2) if n else 0})
        cluster_centroids.append({
            "cluster": cluster_number,
            "label": f"Кластер {cluster_number}",
            "values": [
                {"code": variable.code, "label": variable.label, "value": float(center[index]), "standardized_value": float(standardized_center[index])}
                for index, variable in enumerate(variables)
            ],
        })

    assigned_distances = np.linalg.norm(x_matrix - centers[labels], axis=1)
    assignments = [
        {
            "response_id": response_id,
            "cluster": cluster_number_by_label[int(label)],
            "cluster_label": f"Кластер {cluster_number_by_label[int(label)]}",
            "distance_to_centroid": float(assigned_distances[index]),
        }
        for index, (response_id, label) in enumerate(zip(response_ids, labels))
    ]
    profile_rows = profile_rows if profile_rows is not None else rows
    profile_variables = profile_variables if profile_variables is not None else variables
    cluster_profiles = _build_cluster_profiles(
        profile_rows,
        profile_variables,
        assignments,
        max_profile_features=max_profile_features,
    )
    distances_summary = []
    for label in order:
        values = assigned_distances[labels == label]
        distances_summary.append({
            "cluster": cluster_number_by_label[label],
            "label": f"Кластер {cluster_number_by_label[label]}",
            "mean_distance_to_centroid": float(np.mean(values)),
            "median_distance_to_centroid": float(np.median(values)),
            "min_distance_to_centroid": float(np.min(values)),
            "max_distance_to_centroid": float(np.max(values)),
            "std_distance_to_centroid": float(np.std(values, ddof=1)) if len(values) > 1 else 0,
        })
    distance_threshold = float(np.mean(assigned_distances) + 2 * np.std(assigned_distances, ddof=1)) if n > 1 else None
    high_distance_count = int(np.sum(assigned_distances > distance_threshold)) if distance_threshold is not None else 0
    cluster_distances = {
        "summary": distances_summary,
        "overall_mean_distance_to_centroid": float(np.mean(assigned_distances)),
        "high_distance_points_count": high_distance_count,
    }

    silhouette_score_value = None
    silhouette_samples_values = None
    try:
        from sklearn.metrics import silhouette_samples, silhouette_score
        if n_clusters < n and len(set(labels)) > 1:
            silhouette_score_value = float(silhouette_score(x_matrix, labels))
            silhouette_samples_values = silhouette_samples(x_matrix, labels)
    except ImportError:
        warnings.append("Пакет sklearn не установлен; silhouette score недоступен.")
    silhouette_summary = []
    silhouette_sample_rows = []
    if silhouette_samples_values is not None:
        silhouette_sample_rows = [
            {"response_id": response_id, "cluster": cluster_number_by_label[int(label)], "silhouette": float(silhouette_samples_values[index])}
            for index, (response_id, label) in enumerate(zip(response_ids, labels))
        ][:MAX_SILHOUETTE_SAMPLES]
        for label in order:
            values = silhouette_samples_values[labels == label]
            negative_count = int(np.sum(values < 0))
            silhouette_summary.append({
                "cluster": cluster_number_by_label[label],
                "label": f"Кластер {cluster_number_by_label[label]}",
                "mean_silhouette": float(np.mean(values)),
                "min_silhouette": float(np.min(values)),
                "negative_silhouette_count": negative_count,
                "negative_silhouette_rate": round(negative_count / len(values) * 100, 2) if len(values) else 0,
            })
    silhouette_interpretation = (
        "кластеры выражены слабо" if silhouette_score_value is not None and silhouette_score_value < 0.25
        else "кластеры разделены умеренно" if silhouette_score_value is not None and silhouette_score_value < 0.5
        else "кластеры хорошо разделены" if silhouette_score_value is not None and silhouette_score_value < 0.7
        else "кластеры очень хорошо разделены" if silhouette_score_value is not None
        else "silhouette score недоступен"
    )
    total_sum_of_squares = float(np.sum((x_matrix - np.mean(x_matrix, axis=0)) ** 2))
    cluster_quality = {"silhouette_score": silhouette_score_value, "silhouette_interpretation": silhouette_interpretation, "inertia": inertia, "within_cluster_sum_of_squares": inertia, "between_cluster_sum_of_squares": total_sum_of_squares - inertia, "warnings": []}
    elbow = _cluster_elbow(x_matrix, include_elbow, elbow_min_k, elbow_max_k, max_iter, random_state)
    dimension_reduction = _cluster_dimension_reduction(x_matrix, response_ids, labels, centers, cluster_number_by_label, include_pca_projection)

    standardized_centers_by_cluster = {cluster_number_by_label[label]: centers[label] for label in order}
    profile_heatmap = {
        "rows": [
            {"cluster": cluster_number, "cluster_label": f"Кластер {cluster_number}", "values": [{"code": variable.code, "label": variable.label, "value": float(output_centers[label, index]), "standardized_value": float(centers[label, index])} for index, variable in enumerate(variables)]}
            for label, cluster_number in [(label, cluster_number_by_label[label]) for label in order]
        ]
    }
    feature_variation = np.std(np.array(list(standardized_centers_by_cluster.values())), axis=0)
    radar_indexes = np.argsort(feature_variation)[::-1][:MAX_RADAR_FEATURES]
    radar_profiles = [
        {"cluster": cluster_number_by_label[label], "cluster_label": f"Кластер {cluster_number_by_label[label]}", "values": [{"axis": variables[index].label, "code": variables[index].code, "value": float(centers[label, index])} for index in radar_indexes]}
        for label in order
    ]
    top_distinguishing_features = []
    weak_profile_clusters = []
    for profile in cluster_profiles:
        distinguishing = [
            item for item in profile.get("top_distinguishing_features", [])
            if abs(item.get("standardized_difference") if item.get("standardized_difference") is not None else item.get("difference") or 0) >= DISTINGUISHING_FEATURE_THRESHOLD
        ]
        if not distinguishing:
            weak_profile_clusters.append(profile["cluster"])
        for item in distinguishing:
            difference = item.get("difference") or 0
            top_distinguishing_features.append({
                "cluster": profile["cluster"], "cluster_label": profile.get("label"), "code": item.get("variable"), "label": item.get("label"),
                "cluster_mean": item.get("cluster_value"), "overall_mean": item.get("overall_value"), "standardized_difference": item.get("standardized_difference", item.get("score")),
                "direction": "higher" if difference > 0 else "lower", "interpretation": item.get("interpretation"),
            })
    notes = ["В текущей реализации для двумерной визуализации кластеров используется PCA-проекция."]
    if len(assignments) > MAX_CLUSTER_ASSIGNMENTS:
        notes.append("Для отображения сохранена ограниченная выборка назначений респондентов к кластерам.")
    if n > MAX_SILHOUETTE_SAMPLES:
        notes.append("Для отображения сохранена ограниченная выборка silhouette-значений.")
    if n > MAX_CLUSTER_SCATTER_POINTS:
        notes.append("Для PCA scatterplot сохранена ограниченная выборка респондентов.")
    sizes = [item["size"] for item in clusters]
    if min(sizes) < 5:
        warnings.append("Один или несколько кластеров содержат мало респондентов; такие кластеры могут быть нестабильными.")
    if min(sizes) and max(sizes) / min(sizes) >= 10:
        warnings.append("Размеры кластеров сильно различаются; сегментацию следует интерпретировать осторожно.")
    if max(sizes) / n > 0.7:
        warnings.append("Один кластер содержит большую часть выборки, поэтому структура сегментов может быть слабой.")
    if silhouette_score_value is not None and silhouette_score_value < 0.25:
        cluster_quality["warnings"].append("Silhouette score низкий, кластеры могут быть плохо разделены.")
    if any(item["negative_silhouette_count"] for item in silhouette_summary):
        warnings.append("В одном или нескольких кластерах есть респонденты с отрицательным silhouette; их принадлежность может быть неустойчивой.")
    if high_distance_count:
        warnings.append("Обнаружены респонденты, находящиеся далеко от центроидов кластеров; они могут быть плохо представлены выбранной структурой.")
    if weak_profile_clusters:
        warnings.append("Профили некоторых кластеров выражены слабо; отличающие признаки почти не выделяются.")

    return {
        "method": method,
        "n": n,
        "n_variables": p,
        "n_clusters": n_clusters,
        "standardize": standardize,
        "max_iter": max_iter,
        "variables": [
            {"code": variable.code, "label": variable.label}
            for variable in variables
        ],
        "clusters": clusters,
        "assignments": assignments,
        "cluster_assignments": assignments[:MAX_CLUSTER_ASSIGNMENTS],
        "cluster_sizes": cluster_sizes,
        "cluster_centroids": cluster_centroids,
        "cluster_distances": cluster_distances,
        "cluster_profiles": cluster_profiles,
        "top_distinguishing_features": top_distinguishing_features,
        "cluster_quality": cluster_quality,
        "silhouette_score": silhouette_score_value,
        "silhouette": {"score": silhouette_score_value, "samples": silhouette_sample_rows, "cluster_summary": silhouette_summary},
        "elbow": elbow,
        "dimension_reduction": dimension_reduction,
        "radar_profiles": radar_profiles,
        "profile_heatmap": profile_heatmap,
        "inertia": inertia,
        "warnings": warnings,
        "notes": notes,
    }


def interpret_p_value(p_value, alpha):
    if p_value is None:
        return "Недостаточно данных для интерпретации."
    if p_value < alpha:
        return "Различия между группами статистически значимы."
    return "Статистически значимых различий между группами не выявлено."


def _sample_std(values):
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (n - 1))


def _group_percentile(ordered_values, fraction):
    if not ordered_values:
        return None
    position = (len(ordered_values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered_values) - 1)
    return ordered_values[lower] + (ordered_values[upper] - ordered_values[lower]) * (position - lower)


def _mean_confidence_interval(values, confidence=0.95):
    std = _sample_std(values)
    if std is None or stats is None:
        return None
    mean = sum(values) / len(values)
    critical = float(stats.t.ppf((1 + confidence) / 2, len(values) - 1))
    margin = critical * std / math.sqrt(len(values))
    return {"low": float(mean - margin), "high": float(mean + margin)}


def _mean_difference_confidence_interval(first, second, confidence=0.95):
    std1 = _sample_std(first)
    std2 = _sample_std(second)
    if std1 is None or std2 is None or stats is None:
        return None
    variance = std1 ** 2 / len(first) + std2 ** 2 / len(second)
    if variance <= 0:
        return None
    numerator = variance ** 2
    denominator = (
        (std1 ** 2 / len(first)) ** 2 / (len(first) - 1)
        + (std2 ** 2 / len(second)) ** 2 / (len(second) - 1)
    )
    dof = numerator / denominator if denominator else len(first) + len(second) - 2
    margin = float(stats.t.ppf((1 + confidence) / 2, dof)) * math.sqrt(variance)
    difference = sum(first) / len(first) - sum(second) / len(second)
    return {"low": float(difference - margin), "high": float(difference + margin)}


def _describe_group(group_value, values, value_labels=None, missing_count=0):
    ordered = sorted(values)
    n = len(values)
    mean = sum(values) / n
    middle = n // 2
    median = ordered[middle] if n % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    q1 = _group_percentile(ordered, 0.25)
    q3 = _group_percentile(ordered, 0.75)
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    label = None
    if value_labels:
        label = value_labels.get(group_value)
        if label is None:
            try:
                label = value_labels.get(int(group_value))
            except (TypeError, ValueError):
                label = None
    return {
        "group": group_value,
        "group_value": group_value,
        "label": label or str(group_value),
        "group_label": label or str(group_value),
        "n": n,
        "mean": float(mean),
        "median": float(median),
        "std": _sample_std(values),
        "min": float(min(values)),
        "max": float(max(values)),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(iqr),
        "missing_count": missing_count,
        "outliers_count": sum(value < lower_fence or value > upper_fence for value in values),
        "confidence_interval_95": _mean_confidence_interval(values),
    }


def _cohens_d(group_values):
    first, second = group_values
    n1 = len(first)
    n2 = len(second)
    std1 = _sample_std(first)
    std2 = _sample_std(second)
    if std1 is None or std2 is None or n1 + n2 <= 2:
        return None
    pooled_variance = ((n1 - 1) * std1 ** 2 + (n2 - 1) * std2 ** 2) / (n1 + n2 - 2)
    if pooled_variance <= 0:
        return None
    return ((sum(first) / n1) - (sum(second) / n2)) / math.sqrt(pooled_variance)


def _interpret_cohens_d(value):
    absolute = abs(value)
    if absolute < 0.2:
        return "Очень малый эффект"
    if absolute < 0.5:
        return "Малый эффект"
    if absolute < 0.8:
        return "Средний эффект"
    return "Большой эффект"


def _eta_squared(groups):
    all_values = [value for values in groups for value in values]
    grand_mean = sum(all_values) / len(all_values)
    ss_total = sum((value - grand_mean) ** 2 for value in all_values)
    if ss_total <= 0:
        return None
    ss_between = sum(
        len(values) * ((sum(values) / len(values)) - grand_mean) ** 2
        for values in groups
    )
    return ss_between / ss_total


def _interpret_eta_squared(value):
    if value < 0.01:
        return "Очень малый эффект"
    if value < 0.06:
        return "Малый эффект"
    if value < 0.14:
        return "Средний эффект"
    return "Большой эффект"


def adjust_p_values(p_values, method="bonferroni"):
    if method not in ("bonferroni", "holm"):
        raise ValueError("Неподдерживаемый метод поправки p-значения.")

    adjusted = [None] * len(p_values)
    valid = [
        (index, float(value))
        for index, value in enumerate(p_values)
        if value is not None and math.isfinite(float(value))
    ]
    m = len(valid)
    if not m:
        return adjusted

    if method == "bonferroni":
        for index, value in valid:
            adjusted[index] = min(value * m, 1.0)
        return adjusted

    ordered = sorted(valid, key=lambda item: item[1])
    previous = 0.0
    for rank, (index, value) in enumerate(ordered):
        corrected = min((m - rank) * value, 1.0)
        corrected = max(corrected, previous)
        adjusted[index] = corrected
        previous = corrected
    return adjusted


def _group_label(group_value, group_labels):
    if group_value in group_labels:
        return group_labels[group_value]
    try:
        int_value = int(group_value)
        if int_value in group_labels:
            return group_labels[int_value]
    except (TypeError, ValueError):
        pass
    return str(group_value)


def _interpret_rank_biserial(value):
    absolute = abs(value)
    if absolute < 0.1:
        return "Очень малый эффект"
    if absolute < 0.3:
        return "Малый эффект"
    if absolute < 0.5:
        return "Средний эффект"
    return "Большой эффект"


def _variance_diagnostics(group_values):
    variances = [
        std ** 2
        for std in (_sample_std(values) for values in group_values)
        if std is not None
    ]
    positive_variances = [value for value in variances if value > 0]
    ratio = max(positive_variances) / min(positive_variances) if positive_variances else None
    return {
        "variance_ratio": ratio,
        "variances_comparable": ratio is None or ratio <= 4,
    }


def _two_group_differences(group_items, group_values=None):
    if len(group_items) != 2:
        return {}
    first, second = group_items
    mean_difference = first["mean"] - second["mean"]
    median_difference = first["median"] - second["median"]
    higher = first if first["mean"] >= second["mean"] else second
    lower = second if higher is first else first
    return {
        "mean_difference": float(mean_difference),
        "median_difference": float(median_difference),
        "higher_mean_group": higher["label"],
        "lower_mean_group": lower["label"],
        "confidence_interval_95": _mean_difference_confidence_interval(*group_values) if group_values else None,
    }


def _empty_post_hoc(enabled=False, method=None, p_adjust="bonferroni", alpha=0.05, warnings=None):
    return {
        "enabled": enabled,
        "method": method,
        "p_adjust": p_adjust,
        "alpha": alpha,
        "comparisons_count": 0,
        "comparisons": [],
        "warnings": warnings or [],
    }


def _compute_tukey_hsd(groups, ordered_group_keys, group_labels, alpha):
    try:
        from statsmodels.stats.multicomp import pairwise_tukeyhsd
    except ImportError as exc:
        raise ValueError("Для критерия Тьюки HSD требуется установленный пакет statsmodels.") from exc

    values = []
    labels = []
    label_to_key = {}
    for key in ordered_group_keys:
        label = _group_label(key, group_labels)
        label_to_key[label] = key
        for value in groups[key]:
            values.append(value)
            labels.append(label)

    result = pairwise_tukeyhsd(values, labels, alpha=alpha)
    comparisons = []
    for row in result._results_table.data[1:]:
        group_a_label, group_b_label, _, p_value, _, _, reject = row[:7]
        key_a = label_to_key.get(group_a_label, group_a_label)
        key_b = label_to_key.get(group_b_label, group_b_label)
        mean_a = sum(groups[key_a]) / len(groups[key_a]) if key_a in groups else None
        mean_b = sum(groups[key_b]) / len(groups[key_b]) if key_b in groups else None
        comparisons.append({
            "group_a": key_a,
            "group_a_label": group_a_label,
            "group_b": key_b,
            "group_b_label": group_b_label,
            "test": "Tukey HSD",
            "statistic": None,
            "p_value": _finite_or_none(p_value),
            "p_adjusted": _finite_or_none(p_value),
            "significant": bool(reject),
            "mean_a": float(mean_a) if mean_a is not None else None,
            "mean_b": float(mean_b) if mean_b is not None else None,
            "difference": float(mean_a - mean_b) if mean_a is not None and mean_b is not None else None,
            "effect_size": None,
        })
    return comparisons


def compute_post_hoc_comparisons(
    groups,
    group_labels=None,
    method="anova",
    alpha=0.05,
    p_adjust="bonferroni",
    post_hoc_method="auto",
):
    group_labels = group_labels or {}
    ordered_group_keys = _sort_values(groups.keys())
    n_groups = len(ordered_group_keys)

    if method in ("t_test", "mann_whitney"):
        return _empty_post_hoc(
            True,
            post_hoc_method,
            p_adjust,
            alpha,
            ["Post-hoc сравнения не требуются для тестов с двумя группами."],
        )
    if n_groups < 3:
        return _empty_post_hoc(
            True,
            post_hoc_method,
            p_adjust,
            alpha,
            ["Post-hoc сравнения обычно применяются для трех и более групп."],
        )

    resolved_method = post_hoc_method
    if resolved_method == "auto":
        resolved_method = "pairwise_t_test" if method == "anova" else "pairwise_mann_whitney"
    if resolved_method == "pairwise_t_test" and method != "anova":
        raise ValueError("Попарные t-критерии можно использовать только после ANOVA.")
    if resolved_method == "pairwise_mann_whitney" and method != "kruskal_wallis":
        raise ValueError("Попарные критерии Манна-Уитни можно использовать только после критерия Краскела-Уоллиса.")
    if resolved_method == "tukey_hsd" and method != "anova":
        raise ValueError("Критерий Тьюки HSD можно использовать только после ANOVA.")

    if resolved_method == "tukey_hsd":
        comparisons = _compute_tukey_hsd(groups, ordered_group_keys, group_labels, alpha)
        return {
            "enabled": True,
            "method": resolved_method,
            "p_adjust": "tukey_hsd",
            "alpha": alpha,
            "comparisons_count": len(comparisons),
            "comparisons": comparisons,
            "warnings": [],
        }

    comparisons = []
    raw_p_values = []
    for left_index, group_a in enumerate(ordered_group_keys):
        for group_b in ordered_group_keys[left_index + 1:]:
            values_a = groups[group_a]
            values_b = groups[group_b]
            if resolved_method == "pairwise_t_test":
                result = stats.ttest_ind(values_a, values_b, equal_var=False, nan_policy="omit")
                effect_value = _cohens_d([values_a, values_b])
                effect_size = None if effect_value is None else {
                    "type": "cohens_d",
                    "name": "Cohen’s d",
                    "value": float(effect_value),
                    "interpretation": _interpret_cohens_d(effect_value),
                }
                mean_a = sum(values_a) / len(values_a)
                mean_b = sum(values_b) / len(values_b)
                comparison = {
                    "group_a": group_a,
                    "group_a_label": _group_label(group_a, group_labels),
                    "group_b": group_b,
                    "group_b_label": _group_label(group_b, group_labels),
                    "test": "Welch t-test",
                    "statistic": _finite_or_none(result.statistic),
                    "p_value": _finite_or_none(result.pvalue),
                    "mean_a": float(mean_a),
                    "mean_b": float(mean_b),
                    "difference": float(mean_a - mean_b),
                    "mean_difference": float(mean_a - mean_b),
                    "median_difference": float(_profile_median(values_a) - _profile_median(values_b)),
                    "effect_size": effect_size,
                }
            else:
                result = stats.mannwhitneyu(values_a, values_b, alternative="two-sided")
                statistic = _finite_or_none(result.statistic)
                denominator = len(values_a) * len(values_b)
                rbc = None if statistic is None or denominator <= 0 else 1 - (2 * statistic) / denominator
                median_a = _profile_median(values_a)
                median_b = _profile_median(values_b)
                comparison = {
                    "group_a": group_a,
                    "group_a_label": _group_label(group_a, group_labels),
                    "group_b": group_b,
                    "group_b_label": _group_label(group_b, group_labels),
                    "test": "Mann-Whitney U",
                    "statistic": statistic,
                    "p_value": _finite_or_none(result.pvalue),
                    "median_a": float(median_a),
                    "median_b": float(median_b),
                    "difference": float(median_a - median_b),
                    "mean_difference": float(sum(values_a) / len(values_a) - sum(values_b) / len(values_b)),
                    "median_difference": float(median_a - median_b),
                    "effect_size": None if rbc is None else {
                        "type": "rank_biserial_correlation",
                        "name": "Rank-biserial correlation",
                        "value": float(rbc),
                        "abs_value": float(abs(rbc)),
                        "interpretation": _interpret_rank_biserial(rbc),
                    },
                }
            comparisons.append(comparison)
            raw_p_values.append(comparison.get("p_value"))

    adjusted_values = adjust_p_values(raw_p_values, p_adjust)
    for comparison, adjusted_value in zip(comparisons, adjusted_values):
        comparison["p_adjusted"] = adjusted_value
        comparison["significant"] = bool(adjusted_value is not None and adjusted_value < alpha)

    return {
        "enabled": True,
        "method": resolved_method,
        "p_adjust": p_adjust,
        "alpha": alpha,
        "comparisons_count": len(comparisons),
        "comparisons": comparisons,
        "warnings": [],
    }


def _finite_or_none(value):
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def compute_group_comparison(
    rows,
    group_var,
    value_var,
    method="anova",
    alpha=0.05,
    post_hoc=False,
    post_hoc_method="auto",
    p_adjust="bonferroni",
) -> dict:
    if stats is None:
        raise ValueError("Для сравнения групп требуется установленный пакет scipy.")
    if method not in ("t_test", "anova", "mann_whitney", "kruskal_wallis"):
        raise ValueError("Неподдерживаемый метод сравнения групп.")

    groups = defaultdict(list)
    missing_by_group = Counter()
    warnings = []
    for row in rows:
        group_value = row.get(group_var.code)
        value = row.get(value_var.code)
        if _is_missing(group_value):
            continue
        if _is_missing(value):
            missing_by_group[group_value] += 1
            continue
        if not _is_numeric(value):
            raise ValueError("Зависимая переменная для сравнения групп должна содержать числовые значения.")
        groups[group_value].append(_as_float(value))

    ordered_group_keys = _sort_values(groups.keys())
    group_values = [groups[key] for key in ordered_group_keys]
    n_groups = len(group_values)
    n = sum(len(values) for values in group_values)

    if n_groups < 2:
        raise ValueError("Для сравнения групп нужны как минимум две группы с полными данными.")
    if any(len(values) < 2 for values in group_values):
        raise ValueError("В каждой группе должно быть не менее двух наблюдений.")
    if method in ("t_test", "mann_whitney") and n_groups != 2:
        raise ValueError("Выбранный метод требует ровно две группы.")
    if method in ("anova", "kruskal_wallis") and n_groups < 2:
        raise ValueError("Выбранный метод требует как минимум две группы.")
    if n <= n_groups:
        raise ValueError("Для сравнения групп число наблюдений должно быть больше числа групп.")

    if method == "t_test":
        result = stats.ttest_ind(group_values[0], group_values[1], equal_var=False, nan_policy="omit")
        method_name = "Welch t-test"
        groups_compared = [ordered_group_keys[0], ordered_group_keys[1]]
        effect_value = _cohens_d(group_values)
        effect_size = None if effect_value is None else {
            "type": "cohens_d",
            "name": "Cohen’s d",
            "value": float(effect_value),
            "interpretation": _interpret_cohens_d(effect_value),
            "description": "Показывает выраженность различия средних значений между двумя группами.",
        }
    elif method == "anova":
        result = stats.f_oneway(*group_values)
        method_name = "One-way ANOVA"
        groups_compared = ordered_group_keys
        effect_value = _eta_squared(group_values)
        effect_size = None if effect_value is None else {
            "type": "eta_squared",
            "name": "Eta squared",
            "value": float(effect_value),
            "interpretation": _interpret_eta_squared(effect_value),
            "description": "Показывает долю вариации показателя, связанную с различиями между группами.",
        }
    elif method == "mann_whitney":
        result = stats.mannwhitneyu(group_values[0], group_values[1], alternative="two-sided")
        method_name = "Mann-Whitney U"
        groups_compared = [ordered_group_keys[0], ordered_group_keys[1]]
        statistic = _finite_or_none(result.statistic)
        denominator = len(group_values[0]) * len(group_values[1])
        effect_value = None if statistic is None or denominator <= 0 else 1 - (2 * statistic) / denominator
        effect_size = None if effect_value is None else {
            "type": "rank_biserial_correlation",
            "name": "Rank-biserial correlation",
            "value": float(effect_value),
            "interpretation": _interpret_rank_biserial(effect_value),
            "description": "Показывает выраженность различия рангов между двумя группами.",
        }
    else:
        result = stats.kruskal(*group_values)
        method_name = "Kruskal-Wallis"
        groups_compared = ordered_group_keys
        statistic = _finite_or_none(result.statistic)
        denominator = n - n_groups
        effect_value = None if statistic is None or denominator <= 0 else (statistic - n_groups + 1) / denominator
        effect_size = None if effect_value is None else {
            "type": "epsilon_squared",
            "name": "Epsilon squared",
            "value": float(max(0.0, effect_value)),
            "interpretation": _interpret_eta_squared(max(0.0, effect_value)),
            "description": "Показывает выраженность различий рангов между несколькими группами.",
        }

    statistic = _finite_or_none(result.statistic)
    p_value = _finite_or_none(result.pvalue)
    group_labels = {
        group_key: _describe_group(group_key, groups[group_key], group_var.value_labels)["label"]
        for group_key in ordered_group_keys
    }
    post_hoc_result = _empty_post_hoc(False, None, p_adjust, alpha)
    if post_hoc:
        post_hoc_result = compute_post_hoc_comparisons(
            groups=groups,
            group_labels=group_labels,
            method=method,
            alpha=alpha,
            p_adjust=p_adjust,
            post_hoc_method=post_hoc_method,
        )

    group_items = [
        _describe_group(group_key, groups[group_key], group_var.value_labels, missing_by_group[group_key])
        for group_key in ordered_group_keys
    ]
    variance_diagnostics = _variance_diagnostics(group_values)
    if any(len(values) < 5 for values in group_values):
        warnings.append("В одной или нескольких группах меньше 5 наблюдений; сравнение групп может быть ненадёжным.")
    sizes = [len(values) for values in group_values]
    if min(sizes) and max(sizes) / min(sizes) >= 3:
        warnings.append("Размеры групп сильно различаются; результаты следует интерпретировать осторожно.")
    if method in ("t_test", "anova") and not variance_diagnostics["variances_comparable"]:
        warnings.append("Дисперсии групп заметно различаются; результаты параметрических тестов следует интерпретировать осторожно.")
    if effect_size is None:
        warnings.append("Размер эффекта не удалось рассчитать из-за недостаточной вариативности данных.")

    return {
        "method": method,
        "method_name": method_name,
        "alpha": alpha,
        "n": n,
        "n_groups": n_groups,
        "groups_count": n_groups,
        "group_variable": {
            "code": group_var.code,
            "label": group_var.label,
        },
        "value_variable": {
            "code": value_var.code,
            "label": value_var.label,
        },
        "groups": group_items,
        "test": {
            "statistic": statistic,
            "p_value": p_value,
            "significant": bool(p_value is not None and p_value < alpha),
            "interpretation": interpret_p_value(p_value, alpha),
            "groups_compared": groups_compared,
        },
        "effect_size": effect_size,
        "differences": _two_group_differences(group_items, group_values if method == "t_test" else None),
        "variance_diagnostics": variance_diagnostics,
        "post_hoc": post_hoc_result,
        "warnings": warnings,
    }


def interpret_cronbach_alpha(alpha):
    if alpha is None:
        return "Недостаточно данных для интерпретации."
    if alpha < 0.6:
        return "Низкая внутренняя согласованность"
    if alpha < 0.7:
        return "Сомнительная внутренняя согласованность"
    if alpha < 0.8:
        return "Приемлемая внутренняя согласованность"
    if alpha < 0.9:
        return "Хорошая внутренняя согласованность"
    return "Очень высокая внутренняя согласованность"


def _interpret_item_total_correlation(value):
    if value is None:
        return "Недостаточно данных для интерпретации."
    if value < 0:
        return "Пункт имеет отрицательную связь с общей шкалой; стоит проверить reverse coding."
    if value < 0.2:
        return "Пункт слабо согласуется с общей шкалой."
    if value < 0.3:
        return "Пункт имеет пограничную связь с общей шкалой."
    if value < 0.5:
        return "Пункт приемлемо согласуется с общей шкалой."
    return "Пункт хорошо согласуется с общей шкалой."


def _complete_numeric_matrix(rows, variables, analysis_name):
    matrix = []
    codes = [variable.code for variable in variables]
    for row in rows:
        values = [row.get(code) for code in codes]
        if any(_is_missing(value) for value in values):
            continue
        if not all(_is_numeric(value) for value in values):
            raise ValueError(f"{analysis_name} requires all selected values to be numeric.")
        matrix.append([_as_float(value) for value in values])
    return matrix


def _cronbach_alpha_from_matrix(x_matrix):
    k = x_matrix.shape[1]
    if k < 2:
        return None
    item_variances = np.var(x_matrix, axis=0, ddof=1)
    total_scores = np.sum(x_matrix, axis=1)
    total_variance = float(np.var(total_scores, ddof=1))
    if total_variance <= 0:
        return None
    return float((k / (k - 1)) * (1 - float(np.sum(item_variances)) / total_variance))


def _standardized_cronbach_alpha(correlation_matrix):
    k = correlation_matrix.shape[0]
    if k < 2:
        return None, None
    upper_indexes = np.triu_indices(k, k=1)
    inter_item_values = correlation_matrix[upper_indexes]
    mean_inter_item_correlation = float(np.mean(inter_item_values))
    denominator = 1 + (k - 1) * mean_inter_item_correlation
    if denominator == 0:
        return None, mean_inter_item_correlation
    alpha = float((k * mean_inter_item_correlation) / denominator)
    return alpha, mean_inter_item_correlation


def _safe_corr(left, right):
    if len(left) < 2:
        return None
    if float(np.var(left, ddof=1)) <= 0 or float(np.var(right, ddof=1)) <= 0:
        return None
    value = float(np.corrcoef(left, right)[0, 1])
    return value if math.isfinite(value) else None


def compute_cronbach_alpha(rows, variables, standardize=False) -> dict:
    if np is None:
        raise ValueError("Для расчета α Кронбаха требуется установленный пакет numpy.")

    k = len(variables)
    if k < 2:
        raise ValueError("Для расчета α Кронбаха требуется не менее двух переменных.")

    complete_cases = _complete_numeric_matrix(rows, variables, "Cronbach's alpha")
    n = len(complete_cases)
    if n < 2:
        raise ValueError("Для расчета α Кронбаха требуется не менее двух полных наблюдений.")

    x_matrix = np.array(complete_cases, dtype=float)
    if not np.all(np.isfinite(x_matrix)):
        raise ValueError("Данные для расчета α Кронбаха содержат некорректные числовые значения.")

    item_variances = np.var(x_matrix, axis=0, ddof=1)
    zero_variance_indexes = np.where(item_variances == 0)[0]
    if len(zero_variance_indexes):
        labels = [variables[index].label for index in zero_variance_indexes]
        raise ValueError(f"α Кронбаха нельзя рассчитать для переменных с нулевой дисперсией: {', '.join(labels)}.")

    alpha = _cronbach_alpha_from_matrix(x_matrix)
    if alpha is None:
        raise ValueError("Дисперсия суммарного балла равна нулю; α Кронбаха не может быть рассчитана.")

    correlation_matrix = np.corrcoef(x_matrix, rowvar=False)
    if not np.all(np.isfinite(correlation_matrix)):
        raise ValueError("Матрица межпунктовых корреляций содержит некорректные значения.")
    standardized_alpha, mean_inter_item_correlation = _standardized_cronbach_alpha(correlation_matrix)

    selected_alpha = standardized_alpha if standardize else alpha
    item_means = np.mean(x_matrix, axis=0)
    item_stds = np.std(x_matrix, axis=0, ddof=1)
    item_statistics = []
    alpha_if_item_deleted = []
    item_total_correlations = []
    negative_item_total = False

    for index, variable in enumerate(variables):
        item_values = x_matrix[:, index]
        raw_item_summary = _numeric_summary([
            _as_float(row.get(variable.code))
            for row in rows
            if _is_numeric(row.get(variable.code))
        ])
        item_total_correlation = None
        if k > 2:
            total_without_item = np.sum(np.delete(x_matrix, index, axis=1), axis=1)
            item_total_correlation = _safe_corr(item_values, total_without_item)
            if item_total_correlation is not None and item_total_correlation < 0:
                negative_item_total = True

        alpha_if_deleted = None
        if k > 2:
            reduced_matrix = np.delete(x_matrix, index, axis=1)
            alpha_if_deleted = _cronbach_alpha_from_matrix(reduced_matrix)

        delta_alpha = alpha_if_deleted - selected_alpha if alpha_if_deleted is not None and selected_alpha is not None else None
        improves_alpha = bool(delta_alpha is not None and delta_alpha > 0.02)
        item_total_interpretation = _interpret_item_total_correlation(item_total_correlation)
        item_statistics.append({
            "code": variable.code,
            "label": variable.label,
            "question_id": getattr(variable, "question_id", None),
            "qtype": getattr(variable, "qtype", None),
            "encoding": getattr(variable, "encoding", None),
            "n": raw_item_summary["n"],
            "missing_count": len(rows) - raw_item_summary["n"],
            "missing_rate": round((len(rows) - raw_item_summary["n"]) / len(rows) * 100, 2) if rows else 0,
            "mean": raw_item_summary["mean"],
            "median": raw_item_summary["median"],
            "variance": float(item_variances[index]),
            "std": raw_item_summary["std"],
            "min": raw_item_summary["min"],
            "max": raw_item_summary["max"],
            "q1": raw_item_summary["p25"],
            "q3": raw_item_summary["p75"],
            "iqr": raw_item_summary["iqr"],
            "item_total_correlation": item_total_correlation,
            "alpha_if_deleted": alpha_if_deleted,
            "delta_alpha": delta_alpha,
            "improves_alpha": improves_alpha,
            "interpretation": item_total_interpretation,
        })
        item_total_correlations.append({"code": variable.code, "label": variable.label, "item_total_correlation": item_total_correlation, "interpretation": item_total_interpretation})
        alpha_if_item_deleted.append({
            "code": variable.code, "label": variable.label, "alpha_if_deleted": alpha_if_deleted,
            "delta_alpha": delta_alpha, "improves_alpha": improves_alpha,
            "interpretation": "Удаление пункта может повысить alpha; пункт стоит проверить содержательно." if improves_alpha else "Удаление пункта не дает заметного повышения alpha.",
        })

    warnings = []
    notes = []
    if n < 30:
        warnings.append("Малый объем выборки для анализа надежности; интерпретируйте α Кронбаха с осторожностью.")
    if k < 3:
        warnings.append("Для устойчивой оценки надежности шкалы желательно использовать не менее трех пунктов.")
    if selected_alpha is not None and selected_alpha < 0.7:
        warnings.append("Cronbach’s alpha ниже 0.7, внутренняя согласованность шкалы может быть недостаточной.")
    if selected_alpha is not None and selected_alpha >= 0.95:
        warnings.append("Cronbach’s alpha очень высокая; пункты шкалы могут быть избыточными.")
    if mean_inter_item_correlation is not None and mean_inter_item_correlation < 0:
        warnings.append("Средняя межпунктовая корреляция отрицательна; выбранные пункты могут измерять разные конструкты.")
    if negative_item_total:
        warnings.append("Некоторые пункты имеют отрицательную item-total correlation; возможно, требуется reverse coding или исключение пункта.")
    if any(item["item_total_correlation"] is not None and item["item_total_correlation"] < 0.2 for item in item_total_correlations):
        warnings.append("Некоторые пункты слабо связаны с общей шкалой.")
    if any(item["improves_alpha"] for item in alpha_if_item_deleted):
        warnings.append("Удаление одного или нескольких пунктов может повысить Cronbach’s alpha; эти пункты стоит проверить содержательно.")
    upper_values = correlation_matrix[np.triu_indices(k, k=1)]
    if any(value < 0 for value in upper_values):
        warnings.append("Между некоторыми пунктами обнаружены отрицательные корреляции; возможно, часть пунктов требует обратного кодирования.")
    if mean_inter_item_correlation is not None and mean_inter_item_correlation < 0.15:
        warnings.append("Средняя межпунктовая корреляция низкая; пункты могут измерять разные конструкты.")
    if mean_inter_item_correlation is not None and mean_inter_item_correlation > 0.7:
        warnings.append("Средняя межпунктовая корреляция очень высокая; пункты могут быть избыточными или дублирующими.")
    problematic_items = []
    for item, deleted in zip(item_total_correlations, alpha_if_item_deleted):
        reasons = []
        value = item.get("item_total_correlation")
        if value is not None and value < 0.2:
            reasons.append("low_item_total_correlation")
        if value is not None and value < 0:
            reasons.extend(["negative_item_total_correlation", "possible_reverse_coding_needed"])
        if deleted.get("improves_alpha"):
            reasons.append("alpha_improves_if_deleted")
        if reasons:
            problematic_items.append({**item, "alpha_if_deleted": deleted.get("alpha_if_deleted"), "reasons": reasons, "recommendation": "Пункт стоит проверить содержательно: он может хуже согласовываться с остальными пунктами шкалы."})

    return {
        "method": "cronbach_alpha",
        "n": n,
        "n_items": k,
        "items_count": k,
        "complete_cases": n,
        "min_answered_items": k,
        "standardize": standardize,
        "alpha": float(alpha),
        "cronbach_alpha": float(alpha),
        "standardized_alpha": standardized_alpha,
        "interpretation": interpret_cronbach_alpha(selected_alpha),
        "alpha_interpretation": interpret_cronbach_alpha(selected_alpha),
        "variables": [
            {"code": variable.code, "label": variable.label}
            for variable in variables
        ],
        "item_statistics": item_statistics,
        "item_total_correlations": item_total_correlations,
        "alpha_if_item_deleted": alpha_if_item_deleted,
        "inter_item_correlation_matrix": correlation_matrix.tolist(),
        "mean_inter_item_correlation": mean_inter_item_correlation,
        "average_inter_item_correlation": mean_inter_item_correlation,
        "inter_item_correlations": {
            "variables": [{"code": variable.code, "label": variable.label} for variable in variables],
            "matrix": correlation_matrix.tolist(),
            "average_inter_item_correlation": mean_inter_item_correlation,
            "min_inter_item_correlation": float(np.min(upper_values)) if len(upper_values) else None,
            "max_inter_item_correlation": float(np.max(upper_values)) if len(upper_values) else None,
        },
        "problematic_items": problematic_items,
        "recommendations": ["Проверьте пункты с низкой item-total correlation.", "Для проверки одномерности шкалы рекомендуется дополнительно использовать факторный анализ."],
        "warnings": warnings,
        "notes": notes,
    }


def _reverse_value(value, min_value, max_value):
    return max_value + min_value - value


def _sample_variance(values):
    if len(values) < 2:
        return None
    mean_value = sum(values) / len(values)
    return sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)


def _sample_std(values):
    variance = _sample_variance(values)
    return math.sqrt(variance) if variance is not None else None


def _percentile(sorted_values, percentile):
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
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
            "n": 0,
            "mean": None,
            "median": None,
            "std": None,
            "variance": None,
            "min": None,
            "max": None,
            "p25": None,
            "p75": None,
            "q1": None,
            "q3": None,
            "iqr": None,
        }
    mean_value = sum(clean_values) / n
    variance = _sample_variance(clean_values)
    p25 = _percentile(clean_values, 0.25)
    p75 = _percentile(clean_values, 0.75)
    return {
        "n": n,
        "mean": float(mean_value),
        "median": _percentile(clean_values, 0.5),
        "std": math.sqrt(variance) if variance is not None else None,
        "variance": variance,
        "min": float(clean_values[0]),
        "max": float(clean_values[-1]),
        "p25": p25,
        "p75": p75,
        "q1": p25,
        "q3": p75,
        "iqr": (p75 - p25) if p25 is not None and p75 is not None else None,
    }


def _numeric_distribution(values, buckets=10):
    clean_values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not clean_values:
        return []
    minimum = min(clean_values)
    maximum = max(clean_values)
    total = len(clean_values)
    if minimum == maximum:
        return [{
            "bucket_start": minimum,
            "bucket_end": maximum,
            "label": f"{minimum:g}",
            "count": total,
            "percent": 100.0,
        }]

    bucket_count = max(1, int(buckets))
    width = (maximum - minimum) / bucket_count
    counts = [0] * bucket_count
    for value in clean_values:
        index = bucket_count - 1 if value == maximum else int((value - minimum) / width)
        counts[index] += 1

    distribution = []
    for index, count in enumerate(counts):
        start = minimum + index * width
        end = maximum if index == bucket_count - 1 else start + width
        distribution.append({
            "bucket_start": float(start),
            "bucket_end": float(end),
            "label": f"{start:.2f}-{end:.2f}",
            "count": count,
            "percent": (count / total * 100) if total else 0,
        })
    return distribution


def _score_from_values(values, method):
    if not values:
        return None
    if method == "sum":
        return float(sum(values))
    return float(sum(values) / len(values))


def _row_item_values(row, variables, reverse_configs):
    values = {}
    for variable in variables:
        value = row.get(variable.code)
        if _is_missing(value):
            values[variable.code] = None
            continue
        if not _is_numeric(value):
            raise ValueError("Для индекса шкалы после кодирования нужны числовые значения пунктов.")
        numeric_value = _as_float(value)
        config = reverse_configs.get(variable.question_id) or {}
        if config.get("reverse"):
            numeric_value = _reverse_value(numeric_value, config.get("min_value"), config.get("max_value"))
        values[variable.code] = numeric_value
    return values


def _complete_cases_count(rows, variables):
    count = 0
    for row in rows:
        if all(_is_numeric(row.get(variable.code)) for variable in variables):
            count += 1
    return count


def compute_scale_index(
    rows,
    variables,
    item_configs,
    title="Индекс шкалы",
    method="mean",
    min_answered_items=1,
    include_cronbach_alpha=True,
) -> dict:
    if method not in ("mean", "sum", "standardized_mean"):
        raise ValueError("Метод индекса шкалы должен быть mean, sum или standardized_mean.")
    if len(variables) < 2:
        raise ValueError("Для индекса шкалы требуется не менее двух развернутых переменных.")
    if min_answered_items > len(variables):
        raise ValueError("min_answered_items не может быть больше числа развернутых пунктов.")

    reverse_configs = {
        int(item["question_id"]): {
            "reverse": bool(item.get("reverse")),
            "min_value": item.get("min_value"),
            "max_value": item.get("max_value"),
        }
        for item in item_configs
    }
    warnings = []
    if any(config.get("reverse") for config in reverse_configs.values()):
        warnings.append("К выбранным пунктам применено обратное кодирование.")
    if min_answered_items < len(variables):
        warnings.append("Индексы рассчитаны по частичным ответам; включены респонденты с достаточным числом отвеченных пунктов.")

    transformed_rows = []
    item_columns = defaultdict(list)
    for row in rows:
        item_values = _row_item_values(row, variables, reverse_configs)
        transformed_row = {"response_id": row.get("response_id"), **item_values}
        transformed_rows.append(transformed_row)
        for variable in variables:
            value = item_values.get(variable.code)
            if value is not None:
                item_columns[variable.code].append(value)

    z_params = {}
    if method == "standardized_mean":
        for variable in variables:
            values = item_columns.get(variable.code) or []
            std = _sample_std(values)
            if not values or std is None or std <= 0:
                z_params[variable.code] = None
                warnings.append(f"Item '{variable.label}' has zero or insufficient variance and was excluded from z-score averaging.")
            else:
                z_params[variable.code] = {"mean": sum(values) / len(values), "std": std}

    scores = []
    score_values = []
    missing_count = 0
    for transformed_row in transformed_rows:
        raw_values = []
        score_input_values = []
        for variable in variables:
            value = transformed_row.get(variable.code)
            if value is None:
                continue
            raw_values.append(value)
            if method == "standardized_mean":
                params = z_params.get(variable.code)
                if params:
                    score_input_values.append((value - params["mean"]) / params["std"])
            else:
                score_input_values.append(value)

        answered_count = len(raw_values)
        if answered_count < min_answered_items or not score_input_values:
            missing_count += 1
            score = None
        else:
            score = _score_from_values(score_input_values, method)
            score_values.append(score)

        if score is not None:
            scores.append({
                "response_id": transformed_row.get("response_id"),
                "score": score,
                "answered_items": answered_count,
                "missing_items": len(variables) - answered_count,
            })

    item_statistics = []
    negative_item_total = False
    for variable in variables:
        values = item_columns.get(variable.code) or []
        config = reverse_configs.get(variable.question_id) or {}
        item_total_pairs = []
        for transformed_row in transformed_rows:
            item_value = transformed_row.get(variable.code)
            if item_value is None:
                continue
            other_values = []
            for other in variables:
                if other.code == variable.code:
                    continue
                other_value = transformed_row.get(other.code)
                if other_value is None:
                    continue
                if method == "standardized_mean":
                    params = z_params.get(other.code)
                    if params:
                        other_values.append((other_value - params["mean"]) / params["std"])
                else:
                    other_values.append(other_value)
            if len(other_values) >= max(1, min_answered_items - 1):
                item_total_pairs.append((item_value, _score_from_values(other_values, method)))
        item_total_correlation = None
        clean_pairs = [(left, right) for left, right in item_total_pairs if right is not None]
        if len(clean_pairs) >= 2:
            left_values = [pair[0] for pair in clean_pairs]
            right_values = [pair[1] for pair in clean_pairs]
            item_total_correlation = _manual_pearson(left_values, right_values)
            if item_total_correlation is not None and item_total_correlation < 0:
                negative_item_total = True

        summary = _numeric_summary(values)
        item_statistics.append({
            "code": variable.code,
            "label": variable.label,
            "question_id": variable.question_id,
            "reverse": bool(config.get("reverse")),
            "min_value": config.get("min_value") if config.get("reverse") else None,
            "max_value": config.get("max_value") if config.get("reverse") else None,
            "n": summary["n"],
            "missing": len(rows) - summary["n"],
            "mean": summary["mean"],
            "std": summary["std"],
            "min": summary["min"],
            "max": summary["max"],
            "item_total_correlation": item_total_correlation,
        })

    reliability = None
    n_complete_cases_for_alpha = _complete_cases_count(transformed_rows, variables)
    if include_cronbach_alpha:
        try:
            reliability_result = compute_cronbach_alpha(transformed_rows, variables, standardize=False)
            reliability = {
                "alpha": reliability_result.get("alpha"),
                "cronbach_alpha": reliability_result.get("cronbach_alpha"),
                "standardized_alpha": reliability_result.get("standardized_alpha"),
                "interpretation": reliability_result.get("interpretation"),
                "alpha_interpretation": reliability_result.get("alpha_interpretation"),
                "mean_inter_item_correlation": reliability_result.get("mean_inter_item_correlation"),
                "average_inter_item_correlation": reliability_result.get("average_inter_item_correlation"),
                "item_total_correlations": reliability_result.get("item_total_correlations") or [],
                "alpha_if_item_deleted": reliability_result.get("alpha_if_item_deleted") or [],
                "inter_item_correlations": reliability_result.get("inter_item_correlations") or {},
                "problematic_items": reliability_result.get("problematic_items") or [],
                "warnings": reliability_result.get("warnings") or [],
            }
        except ValueError as exc:
            warnings.append(f"α Кронбаха не удалось рассчитать: {exc}")

    if reliability and reliability.get("alpha") is not None and reliability["alpha"] < 0.6:
        warnings.append("Надежность шкалы низкая; интерпретируйте интегральный индекс с осторожностью.")
    if negative_item_total:
        warnings.append("У некоторых пунктов отрицательная корреляция с суммарной шкалой; проверьте обратное кодирование и согласованность пунктов.")
    if len(score_values) < 30:
        warnings.append("Малый объем выборки для индекса шкалы.")
    score_summary = _numeric_summary(score_values)
    normalized_scores = []
    observed_min = score_summary.get("min")
    observed_max = score_summary.get("max")
    for score in scores:
        normalized = None
        if observed_min is not None and observed_max is not None and observed_max > observed_min:
            normalized = (score["score"] - observed_min) / (observed_max - observed_min) * 100
        normalized_scores.append({**score, "normalized_score": normalized})
    normalized_values = [item["normalized_score"] for item in normalized_scores if item["normalized_score"] is not None]
    normalized_summary = _numeric_summary(normalized_values)
    group_items = []
    for key, label, lower, upper in (
        ("low", "Низкий уровень индекса", None, 33.333333),
        ("medium", "Средний уровень индекса", 33.333333, 66.666667),
        ("high", "Высокий уровень индекса", 66.666667, None),
    ):
        count = sum(
            1 for value in normalized_values
            if (lower is None or value < lower) and (upper is None or value < upper)
        )
        group_items.append({"group": key, "label": label, "count": count, "percent": round(count / len(normalized_values) * 100, 2) if normalized_values else 0})
    reverse_coding = {
        "applied": any(config.get("reverse") for config in reverse_configs.values()),
        "items": [
            {"question_id": question_id, **config}
            for question_id, config in reverse_configs.items()
            if config.get("reverse")
        ],
        "interpretation": "Reverse coding выполнен по формуле max + min - value для пунктов с обратной формулировкой.",
    }
    if observed_min == observed_max and score_values:
        warnings.append("Нормировка индекса в диапазон 0–100 недоступна: у рассчитанных значений нет вариативности.")

    return {
        "method": "scale_index",
        "title": title,
        "index_title": title,
        "calculation": method,
        "n_items": len(variables),
        "items_count": len(variables),
        "n_scored": len(score_values),
        "n": len(score_values),
        "n_complete_cases_for_alpha": n_complete_cases_for_alpha,
        "missing_count": missing_count,
        "min_answered_items": min_answered_items,
        "items": [
            {
                "code": variable.code,
                "label": variable.label,
                "question_id": variable.question_id,
                "reverse": bool((reverse_configs.get(variable.question_id) or {}).get("reverse")),
                "reverse_applied": bool((reverse_configs.get(variable.question_id) or {}).get("reverse")),
                "min_value": (reverse_configs.get(variable.question_id) or {}).get("min_value")
                if (reverse_configs.get(variable.question_id) or {}).get("reverse") else None,
                "max_value": (reverse_configs.get(variable.question_id) or {}).get("max_value")
                if (reverse_configs.get(variable.question_id) or {}).get("reverse") else None,
            }
            for variable in variables
        ],
        "reverse_coding": reverse_coding,
        "score_summary": score_summary,
        "normalized_score_summary": normalized_summary,
        "item_statistics": item_statistics,
        "reliability": reliability,
        "score_distribution": _numeric_distribution(score_values, buckets=10),
        "distribution": _numeric_distribution(normalized_values, buckets=10),
        "groups": {"method": "normalized_tertiles", "items": group_items},
        "scores": normalized_scores,
        "warnings": warnings,
        "notes": ["Нормировка 0–100 построена по наблюдаемому диапазону рассчитанных значений индекса."],
    }


HIGH_SKIP_RATE = 30
MODERATE_SKIP_RATE = 10
LOW_VISIBILITY_RATE = 50


def _response_id(response):
    if isinstance(response, dict):
        return response.get("id") or response.get("response_id")
    return response.id


def _question_value(question, name, default=None):
    if isinstance(question, dict):
        return question.get(name, default)
    return getattr(question, name, default)


def _question_label(question):
    return _question_value(question, "short_label") or _question_value(question, "text") or str(_question_value(question, "id"))


def _question_page_id(question):
    return _question_value(question, "page_id")


def _question_page_title(question):
    if isinstance(question, dict):
        return question.get("page_title")
    page = getattr(question, "page", None)
    return getattr(page, "title", "") if page else ""


def classify_missing_item(shown_count, skipped_count, visibility_rate, skip_rate_shown):
    if shown_count == 0:
        return "not_shown"
    if skipped_count == 0:
        return "no_missing"
    if visibility_rate < LOW_VISIBILITY_RATE and (skip_rate_shown or 0) < MODERATE_SKIP_RATE:
        return "branching_limited"
    if (skip_rate_shown or 0) >= HIGH_SKIP_RATE:
        return "high_missing"
    if (skip_rate_shown or 0) >= MODERATE_SKIP_RATE:
        return "moderate_missing"
    return "low_missing"


def interpret_missing_item(item) -> str:
    shown_count = item.get("shown_count") or 0
    skipped_count = item.get("skipped_count") or 0
    visibility_rate = item.get("visibility_rate") or 0
    skip_rate_shown = item.get("skip_rate_shown")

    if shown_count == 0:
        return "Вопрос не был показан ни одному респонденту. Проверьте условия ветвления."
    if visibility_rate < LOW_VISIBILITY_RATE and (skip_rate_shown or 0) < MODERATE_SKIP_RATE:
        return "Вопрос показан только части респондентов из-за ветвления; это не является обычным пропуском."
    if skip_rate_shown is not None and skip_rate_shown >= HIGH_SKIP_RATE:
        return "Высокая доля реальных пропусков среди респондентов, которым вопрос был показан."
    if skipped_count == 0:
        return "Все респонденты, которым был показан вопрос, дали ответ."
    return "Доля пропусков находится в допустимых пределах."


def _missing_question_short_item(item):
    return {
        "question_id": item.get("question_id"),
        "label": item.get("label"),
        "shown_count": item.get("shown_count"),
        "skipped_count": item.get("skipped_count"),
        "skip_rate_shown": item.get("skip_rate_shown"),
        "visibility_rate": item.get("visibility_rate"),
        "missing_type_code": item.get("missing_type_code"),
        "missing_type": item.get("missing_type"),
    }


def _missing_group_label(value, value_labels):
    if value_labels is None:
        return str(value)
    if value in value_labels:
        return value_labels[value]
    try:
        int_value = int(value)
        if int_value in value_labels:
            return value_labels[int_value]
    except (TypeError, ValueError):
        pass
    return str(value)


def compute_missing_analysis(
    questions,
    completed_responses,
    visibility_by_question,
    answers_by_question,
    group_rows=None,
    group_variable=None,
    include_group_breakdown=False,
) -> dict:
    response_ids = [_response_id(response) for response in completed_responses]
    response_id_set = set(response_ids)
    total_completed_normal = len(response_ids)
    questions_count = len(questions)
    question_items = []

    for question in questions:
        question_id = _question_value(question, "id")
        shown_response_ids = set(visibility_by_question.get(question_id) or set()) & response_id_set
        answered_response_ids = set(answers_by_question.get(question_id) or set()) & shown_response_ids
        shown_count = len(shown_response_ids)
        answered_count = len(answered_response_ids)
        skipped_count = max(shown_count - answered_count, 0)
        not_shown_count = max(total_completed_normal - shown_count, 0)
        visibility_rate = round(shown_count / total_completed_normal * 100, 2) if total_completed_normal else 0
        answer_rate_shown = round(answered_count / shown_count * 100, 2) if shown_count else None
        skip_rate_shown = round(skipped_count / shown_count * 100, 2) if shown_count else None
        answer_rate_total = round(answered_count / total_completed_normal * 100, 2) if total_completed_normal else 0
        missing_type_code = classify_missing_item(shown_count, skipped_count, visibility_rate, skip_rate_shown)
        qtype = _question_value(question, "qtype")

        item = {
            "question_id": question_id,
            "label": _question_label(question),
            "qtype_code": qtype,
            "qtype": _question_type_label(qtype),
            "required": bool(_question_value(question, "required", False)),
            "page_id": _question_page_id(question),
            "page_title": _question_page_title(question),
            "total_completed_normal": total_completed_normal,
            "shown_count": shown_count,
            "not_shown_count": not_shown_count,
            "answered_count": answered_count,
            "skipped_count": skipped_count,
            "visibility_rate": visibility_rate,
            "answer_rate_shown": answer_rate_shown,
            "skip_rate_shown": skip_rate_shown,
            "answer_rate_total": answer_rate_total,
            "missing_type_code": missing_type_code,
            "missing_type": _missing_type_label(missing_type_code),
        }
        item["interpretation"] = interpret_missing_item(item)
        question_items.append(item)

    total_shown_slots = sum(item["shown_count"] for item in question_items)
    total_answered_slots = sum(item["answered_count"] for item in question_items)
    total_skipped_slots = sum(item["skipped_count"] for item in question_items)
    total_not_shown_slots = sum(item["not_shown_count"] for item in question_items)
    total_possible_slots = total_completed_normal * questions_count

    top_skipped_questions = [
        _missing_question_short_item(item)
        for item in sorted(
            [item for item in question_items if item["shown_count"] > 0 and item["skipped_count"] > 0],
            key=lambda item: (item["skip_rate_shown"] or 0, item["skipped_count"]),
            reverse=True,
        )
    ]
    low_visibility_questions = [
        _missing_question_short_item(item)
        for item in sorted(
            [item for item in question_items if item["visibility_rate"] < LOW_VISIBILITY_RATE],
            key=lambda item: item["visibility_rate"],
        )
    ]
    never_shown_questions = [
        _missing_question_short_item(item)
        for item in question_items
        if item["shown_count"] == 0
    ]
    required_questions_with_missing = [
        _missing_question_short_item(item)
        for item in question_items
        if item["required"] and item["skipped_count"] > 0
    ]

    groups = []
    if include_group_breakdown and group_rows is not None and group_variable is not None:
        group_by_response = {
            row.get("response_id"): row.get(group_variable.code)
            for row in group_rows
            if not _is_missing(row.get(group_variable.code))
        }
        group_totals = {}
        for item in question_items:
            question_id = item["question_id"]
            shown_ids = set(visibility_by_question.get(question_id) or set()) & response_id_set
            answered_ids = set(answers_by_question.get(question_id) or set()) & shown_ids
            for response_id in shown_ids:
                group_value = group_by_response.get(response_id)
                if group_value is None:
                    continue
                bucket = group_totals.setdefault(group_value, {
                    "group": group_value,
                    "group_label": _missing_group_label(group_value, group_variable.value_labels),
                    "total_shown_slots": 0,
                    "total_answered_slots": 0,
                    "total_skipped_slots": 0,
                })
                bucket["total_shown_slots"] += 1
                if response_id in answered_ids:
                    bucket["total_answered_slots"] += 1
                else:
                    bucket["total_skipped_slots"] += 1
        for group in sorted(group_totals.values(), key=lambda item: str(item["group_label"])):
            shown_slots = group["total_shown_slots"]
            group["overall_skip_rate_shown"] = round(group["total_skipped_slots"] / shown_slots * 100, 2) if shown_slots else None
            groups.append(group)

    return {
        "method": "missing_analysis",
        "summary": {
            "total_completed_normal": total_completed_normal,
            "questions_count": questions_count,
            "total_shown_slots": total_shown_slots,
            "total_answered_slots": total_answered_slots,
            "total_skipped_slots": total_skipped_slots,
            "total_not_shown_slots": total_not_shown_slots,
            "overall_skip_rate_shown": round(total_skipped_slots / total_shown_slots * 100, 2) if total_shown_slots else None,
            "overall_visibility_rate": round(total_shown_slots / total_possible_slots * 100, 2) if total_possible_slots else 0,
            "questions_with_high_missing": sum(1 for item in question_items if item["missing_type_code"] == "high_missing"),
            "questions_with_moderate_missing": sum(1 for item in question_items if item["missing_type_code"] == "moderate_missing"),
            "questions_with_low_visibility": sum(1 for item in question_items if item["visibility_rate"] < LOW_VISIBILITY_RATE),
        },
        "questions": question_items,
        "top_skipped_questions": top_skipped_questions,
        "low_visibility_questions": low_visibility_questions,
        "never_shown_questions": never_shown_questions,
        "required_questions_with_missing": required_questions_with_missing,
        "groups": groups,
        "warnings": [],
    }


def _varimax(loadings, gamma=1.0, q=20, tol=1e-6):
    p, k = loadings.shape
    rotation = np.eye(k)
    previous = 0
    for _ in range(q):
        rotated = loadings @ rotation
        u, singular_values, vh = np.linalg.svd(
            loadings.T @ (
                rotated ** 3
                - (gamma / p) * rotated @ np.diag(np.diag(rotated.T @ rotated))
            )
        )
        rotation = u @ vh
        current = np.sum(singular_values)
        if previous and current < previous * (1 + tol):
            break
        previous = current
    return loadings @ rotation


def interpret_kmo(value):
    if value is None:
        return "Недостаточно данных"
    if value < 0.5:
        return "Низкая пригодность"
    if value < 0.6:
        return "Слабая пригодность"
    if value < 0.7:
        return "Приемлемая пригодность"
    if value < 0.8:
        return "Хорошая пригодность"
    if value < 0.9:
        return "Очень хорошая пригодность"
    return "Отличная пригодность"


def compute_kmo(correlation_matrix, variables) -> dict:
    warnings = []
    try:
        inverse = np.linalg.inv(correlation_matrix)
    except np.linalg.LinAlgError:
        inverse = np.linalg.pinv(correlation_matrix)
        warnings.append("Корреляционная матрица вырождена; для расчета KMO использована псевдообратная матрица.")

    diagonal = np.diag(inverse)
    denominator = np.sqrt(np.outer(diagonal, diagonal))
    with np.errstate(divide="ignore", invalid="ignore"):
        partial = -inverse / denominator
    np.fill_diagonal(partial, 0.0)
    partial = np.where(np.isfinite(partial), partial, 0.0)

    r_squared = np.array(correlation_matrix, dtype=float) ** 2
    p_squared = partial ** 2
    np.fill_diagonal(r_squared, 0.0)
    np.fill_diagonal(p_squared, 0.0)

    numerator = float(np.sum(r_squared))
    denominator_value = numerator + float(np.sum(p_squared))
    overall = numerator / denominator_value if denominator_value > 0 else None

    variable_results = []
    for index, variable in enumerate(variables):
        variable_numerator = float(np.sum(r_squared[index, :]))
        variable_denominator = variable_numerator + float(np.sum(p_squared[index, :]))
        value = variable_numerator / variable_denominator if variable_denominator > 0 else None
        variable_results.append({
            "code": variable.code,
            "label": variable.label,
            "kmo": float(value) if value is not None else None,
            "interpretation": interpret_kmo(value),
        })

    return {
        "overall": float(overall) if overall is not None else None,
        "interpretation": interpret_kmo(overall),
        "variables": variable_results,
        "warnings": warnings,
    }


def compute_bartlett_sphericity(correlation_matrix, n, p) -> dict:
    warnings = []
    determinant = float(np.linalg.det(correlation_matrix))
    if determinant <= 0:
        determinant = 1e-12
        warnings.append("Определитель корреляционной матрицы неположителен; для критерия Бартлетта он был ограничен малым положительным значением.")
    if n <= p:
        warnings.append("Объем выборки мал относительно числа переменных; критерий Бартлетта может быть нестабильным.")

    chi_square = float(-(n - 1 - (2 * p + 5) / 6) * math.log(determinant))
    dof = int(p * (p - 1) / 2)
    p_value = None
    if stats is not None:
        p_value = float(stats.chi2.sf(chi_square, dof))
    else:
        warnings.append("Пакет scipy не установлен; p-значение критерия Бартлетта недоступно.")

    significant = None if p_value is None else bool(p_value < 0.05)
    if p_value is None:
        interpretation = "p-value недоступен; невозможно оценить значимость теста."
    elif significant:
        interpretation = "Корреляционная матрица значимо отличается от единичной; факторный анализ применим."
    else:
        interpretation = "Корреляционная матрица не отличается значимо от единичной; факторный анализ может быть неуместен."

    return {
        "chi_square": chi_square,
        "dof": dof,
        "p_value": p_value,
        "significant": significant,
        "interpretation": interpretation,
        "warnings": warnings,
    }


def _factor_scores(response_ids, z_matrix, loadings, n_factors):
    scores = z_matrix @ loadings
    score_stds = np.std(scores, axis=0, ddof=1)
    score_means = np.mean(scores, axis=0)
    nonzero = score_stds > 0
    scores[:, nonzero] = (scores[:, nonzero] - score_means[nonzero]) / score_stds[nonzero]
    rows = []
    for row_index, response_id in enumerate(response_ids):
        score_items = [
            {"factor": f"Фактор {index + 1}", "value": float(scores[row_index, index])}
            for index in range(n_factors)
        ]
        rows.append({
            "response_id": response_id,
            "scores": score_items,
            **{item["factor"]: item["value"] for item in score_items},
        })
    return rows


SALIENT_LOADING_THRESHOLD = 0.4
MAX_FACTOR_SCORE_ROWS = 500


def _scree_elbow_n_factors(eigenvalues):
    if len(eigenvalues) < 3:
        return None
    drops = np.diff(eigenvalues) * -1
    if not len(drops) or max(drops) <= 0:
        return None
    index = int(np.argmax(drops))
    next_drop = drops[index + 1] if index + 1 < len(drops) else None
    if next_drop is None or drops[index] < max(0.15, next_drop * 1.5):
        return None
    return index + 1


def compute_parallel_analysis(matrix, n_iter=100, percentile=95, random_state=42) -> dict:
    if np is None:
        return {
            "enabled": False,
            "recommended_n_factors": None,
            "components": [],
            "interpretation": "Parallel analysis недоступен.",
        }
    try:
        n, p = matrix.shape
        rng = np.random.default_rng(random_state)
        random_eigenvalues = []
        for _ in range(n_iter):
            random_matrix = rng.normal(size=(n, p))
            random_eigenvalues.append(np.linalg.eigvalsh(np.corrcoef(random_matrix, rowvar=False))[::-1])
        random_eigenvalues = np.asarray(random_eigenvalues)
        real_eigenvalues = np.linalg.eigvalsh(np.corrcoef(matrix, rowvar=False))[::-1]
        means = np.mean(random_eigenvalues, axis=0)
        thresholds = np.percentile(random_eigenvalues, percentile, axis=0)
        components = [
            {
                "component": index + 1,
                "real_eigenvalue": float(real_eigenvalues[index]),
                "random_mean_eigenvalue": float(means[index]),
                "random_percentile_eigenvalue": float(thresholds[index]),
                "keep": bool(real_eigenvalues[index] > thresholds[index]),
            }
            for index in range(p)
        ]
        recommended = sum(item["keep"] for item in components)
        return {
            "enabled": True,
            "n_iter": n_iter,
            "percentile": percentile,
            "recommended_n_factors": recommended,
            "components": components,
            "interpretation": f"Parallel analysis рекомендует оставить {recommended} факторов.",
        }
    except (ValueError, np.linalg.LinAlgError):
        return {
            "enabled": False,
            "recommended_n_factors": None,
            "components": [],
            "interpretation": "Parallel analysis недоступен для выбранных данных.",
        }


def compute_factor_analysis(
    rows,
    variables,
    n_factors=2,
    rotation="varimax",
    standardize=True,
    include_factor_scores=False,
    parallel_analysis=True,
    parallel_iterations=100,
    parallel_percentile=95,
) -> dict:
    if np is None:
        raise ValueError("Для факторного анализа требуется установленный пакет numpy.")
    if rotation not in ("none", "varimax"):
        raise ValueError("Метод вращения в факторном анализе должен быть 'none' или 'varimax'.")

    p = len(variables)
    if p < 3:
        raise ValueError("Для факторного анализа требуется не менее трех переменных.")
    if n_factors < 1:
        raise ValueError("Число факторов должно быть не меньше 1.")
    if n_factors >= p:
        raise ValueError("Число факторов должно быть меньше числа переменных.")

    response_ids, complete_cases = _complete_factor_cases_with_ids(rows, variables)
    n = len(complete_cases)
    if n <= p:
        raise ValueError("Недостаточно полных наблюдений для факторного анализа.")

    x_matrix = np.array(complete_cases, dtype=float)
    warnings = []
    notes = []
    if n < max(20, 5 * p):
        warnings.append("Малый объем выборки для факторного анализа; интерпретируйте результаты с осторожностью.")

    means = np.mean(x_matrix, axis=0)
    standard_deviations = np.std(x_matrix, axis=0, ddof=1)
    zero_variance_indexes = np.where(standard_deviations == 0)[0]
    if len(zero_variance_indexes):
        labels = [variables[index].label for index in zero_variance_indexes]
        raise ValueError(f"Факторный анализ не может использовать переменные с нулевой дисперсией: {', '.join(labels)}.")

    z_matrix = (x_matrix - means) / standard_deviations
    if standardize:
        x_matrix = z_matrix

    correlation_matrix = np.corrcoef(x_matrix, rowvar=False)
    if not np.all(np.isfinite(correlation_matrix)):
        raise ValueError("Корреляционная матрица факторного анализа содержит некорректные числовые значения.")

    eigenvalues, eigenvectors = np.linalg.eigh(correlation_matrix)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    eigenvalues = np.maximum(eigenvalues, 0)

    off_diagonal = correlation_matrix[np.triu_indices(p, 1)]
    if len(off_diagonal) and float(np.mean(np.abs(off_diagonal))) < 0.3:
        warnings.append("Средние корреляции между переменными низкие; факторная структура может быть слабой.")

    selected_eigenvalues = eigenvalues[:n_factors]
    loadings = eigenvectors[:, :n_factors] * np.sqrt(selected_eigenvalues)
    if rotation == "varimax" and n_factors > 1:
        try:
            loadings = _varimax(loadings)
        except (np.linalg.LinAlgError, ValueError):
            warnings.append("Вращение varimax выполнить не удалось; возвращены невращенные факторные нагрузки.")

    total_eigenvalue = float(np.sum(eigenvalues))
    scree = []
    cumulative = 0.0
    for index, value in enumerate(eigenvalues, start=1):
        explained_value = float(value / total_eigenvalue) if total_eigenvalue else 0
        cumulative += explained_value
        scree.append({
            "component": index,
            "eigenvalue": float(value),
            "explained_variance": explained_value,
            "cumulative_explained_variance": float(cumulative),
            "kaiser_keep": bool(value > 1.0),
            "kaiser_threshold": 1.0,
        })
    raw_kaiser_n_factors = sum(1 for value in eigenvalues if value > 1.0)
    kaiser_n_factors = raw_kaiser_n_factors or 1
    if not raw_kaiser_n_factors:
        warnings.append("По критерию Kaiser компоненты с eigenvalue > 1 не обнаружены; факторная структура может быть слабой.")
    scree_elbow_n_factors = _scree_elbow_n_factors(eigenvalues)
    if scree_elbow_n_factors is None:
        notes.append("Локоть на scree plot выражен неявно; число факторов следует выбирать с учетом содержательной интерпретации.")
    parallel_result = (
        compute_parallel_analysis(z_matrix, parallel_iterations, parallel_percentile)
        if parallel_analysis
        else {
            "enabled": False,
            "recommended_n_factors": None,
            "components": [],
            "interpretation": "Parallel analysis отключен в настройках отчета.",
        }
    )
    parallel_n_factors = parallel_result.get("recommended_n_factors")
    if parallel_result.get("enabled") and not parallel_n_factors:
        notes.append("Parallel analysis не выделил компоненты выше случайного порога; факторное решение требует осторожной содержательной проверки.")
    recommended_n_factors = parallel_n_factors or scree_elbow_n_factors or kaiser_n_factors
    recommendation_method = "parallel_analysis" if parallel_n_factors else "scree_elbow" if scree_elbow_n_factors else "kaiser"
    recommendation_message = f"Рекомендуемое число факторов: {recommended_n_factors}. Использован ориентир: {recommendation_method}."

    explained = [
        float(value / total_eigenvalue) if total_eigenvalue else 0
        for value in selected_eigenvalues
    ]
    communalities = np.sum(loadings ** 2, axis=1)
    uniquenesses = np.maximum(0, 1 - communalities)
    kmo = compute_kmo(correlation_matrix, variables)
    bartlett = compute_bartlett_sphericity(correlation_matrix, n, p)
    kmo["per_variable"] = kmo["variables"]
    low_kmo_variables = [item for item in kmo["variables"] if item.get("kmo") is not None and item["kmo"] < 0.6]
    if kmo.get("overall") is not None and kmo["overall"] < 0.6:
        kmo["warnings"].append("KMO ниже 0.6, данные могут быть недостаточно пригодны для факторного анализа.")
    if low_kmo_variables:
        kmo["warnings"].append("У отдельных переменных низкий KMO; они могут плохо согласовываться с общей факторной структурой.")
    if bartlett.get("significant") is False:
        bartlett["warnings"].append("Критерий Бартлетта незначим; факторный анализ может быть неинформативен.")
    if float(sum(explained)) < 0.5:
        warnings.append("Выбранные факторы объясняют небольшую долю дисперсии; факторное решение может быть слабым.")

    communalities_result = []
    loadings_result = []
    flattened_loadings = []
    factor_structure = []
    weak_variables = []
    cross_loading_variables = []
    for row_index, variable in enumerate(variables):
        communality = float(communalities[row_index])
        uniqueness = float(uniquenesses[row_index])
        factor_items = []
        salient_count = 0
        for index in range(n_factors):
            loading = float(loadings[row_index, index])
            is_salient = abs(loading) >= SALIENT_LOADING_THRESHOLD
            salient_count += int(is_salient)
            factor_item = {
                "factor": f"Фактор {index + 1}",
                "loading": loading,
                "abs_loading": abs(loading),
                "is_salient": is_salient,
                "direction": "positive" if loading >= 0 else "negative",
            }
            factor_items.append(factor_item)
            flattened_loadings.append({
                "variable": variable.code,
                "label": variable.label,
                **factor_item,
                "communality": communality,
                "uniqueness": uniqueness,
            })
        if salient_count == 0:
            weak_variables.append({"variable": variable.code, "label": variable.label})
        if salient_count >= 2:
            cross_loading_variables.append({"variable": variable.code, "label": variable.label})
        interpretation = (
            "Переменная плохо объясняется выделенными факторами."
            if communality < 0.3
            else "Переменная хорошо объясняется выделенными факторами."
            if communality >= 0.6
            else "Переменная умеренно объясняется выделенными факторами."
        )
        communalities_result.append({
            "variable": variable.code,
            "label": variable.label,
            "communality": communality,
            "uniqueness": uniqueness,
            "interpretation": interpretation,
        })
        loadings_result.append({
            "variable": variable.code,
            "label": variable.label,
            "factors": factor_items,
            "communality": communality,
            "uniqueness": uniqueness,
        })
    if weak_variables:
        warnings.append("Некоторые переменные не имеют существенных нагрузок ни на один фактор.")
    if cross_loading_variables:
        warnings.append("Некоторые переменные имеют высокие нагрузки сразу на несколько факторов; их интерпретация может быть неоднозначной.")
    if any(item["communality"] < 0.3 for item in communalities_result):
        warnings.append("Некоторые переменные имеют низкую communality; они плохо объясняются выделенными факторами.")

    for index in range(n_factors):
        factor_name = f"Фактор {index + 1}"
        variables_for_factor = sorted(
            [item for item in flattened_loadings if item["factor"] == factor_name and item["is_salient"]],
            key=lambda item: item["abs_loading"],
            reverse=True,
        )
        top_variables = [
            {key: item[key] for key in ("variable", "label", "loading", "direction")}
            for item in variables_for_factor[:5]
        ]
        labels = ", ".join(f"«{item['label']}»" for item in top_variables)
        factor_structure.append({
            "factor": factor_name,
            "explained_variance": explained[index],
            "top_variables": top_variables,
            "positive_variables": [item for item in top_variables if item["direction"] == "positive"],
            "negative_variables": [item for item in top_variables if item["direction"] == "negative"],
            "cross_loading_variables": cross_loading_variables,
            "weak_variables": weak_variables,
            "interpretation_hint": (
                f"{factor_name} объединяет вопросы с существенными нагрузками: {labels}. "
                "Его можно рассматривать как возможную основу шкалы после содержательной проверки."
                if labels else f"Для {factor_name} существенные нагрузки не выделены; содержательная интерпретация ограничена."
            ),
            "suggested_label": None,
        })
    factor_scores = []
    if include_factor_scores:
        factor_scores = _factor_scores(response_ids, z_matrix, loadings, n_factors)[:MAX_FACTOR_SCORE_ROWS]
        if n > MAX_FACTOR_SCORE_ROWS:
            notes.append("Для отображения сохранена ограниченная выборка факторных значений.")
    biplot = {
        "available": bool(include_factor_scores and n_factors >= 2 and factor_scores),
        "points": [
            {"response_id": item["response_id"], "x": item.get("Фактор 1"), "y": item.get("Фактор 2")}
            for item in factor_scores
        ] if n_factors >= 2 else [],
        "vectors": [
            {"variable": variable.code, "label": variable.label, "x": float(loadings[index, 0]), "y": float(loadings[index, 1])}
            for index, variable in enumerate(variables)
        ] if n_factors >= 2 else [],
    }

    return {
        "method": "pca_factor_extraction",
        "n": n,
        "n_variables": p,
        "n_factors": n_factors,
        "rotation": rotation,
        "standardize": standardize,
        "variables": [
            {"code": variable.code, "label": variable.label}
            for variable in variables
        ],
        "eigenvalues": [float(value) for value in eigenvalues],
        "eigenvalue_details": scree,
        "scree": scree,
        "parallel_analysis": parallel_result,
        "factor_recommendations": {
            "requested_n_factors": n_factors,
            "kaiser_n_factors": int(kaiser_n_factors),
            "scree_elbow_n_factors": scree_elbow_n_factors,
            "parallel_analysis_n_factors": parallel_n_factors,
            "recommended_n_factors": recommended_n_factors,
            "method": recommendation_method,
            "selected_n_factors": n_factors,
            "message": recommendation_message,
        },
        "explained_variance": [
            {
                "factor": f"Фактор {index + 1}",
                "value": value,
                "eigenvalue": float(selected_eigenvalues[index]),
                "explained_variance": value,
                "cumulative_explained_variance": float(sum(explained[:index + 1])),
            }
            for index, value in enumerate(explained)
        ],
        "cumulative_explained_variance": float(sum(explained)),
        "loadings": loadings_result,
        "loadings_matrix": flattened_loadings,
        "communalities": communalities_result,
        "uniquenesses": [{"variable": item["variable"], "label": item["label"], "uniqueness": item["uniqueness"]} for item in communalities_result],
        "weak_variables": weak_variables,
        "cross_loading_variables": cross_loading_variables,
        "factor_structure": factor_structure,
        "correlation_matrix": correlation_matrix.tolist(),
        "kmo": kmo,
        "bartlett": bartlett,
        "factor_scores": factor_scores,
        "biplot": biplot,
        "warnings": warnings,
        "notes": notes,
    }
