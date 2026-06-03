from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
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


