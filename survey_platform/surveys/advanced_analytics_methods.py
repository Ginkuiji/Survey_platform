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
        raise ValueError("Correlation method must be 'pearson', 'spearman', or 'kendall'.")

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
                    raise ValueError("Kendall correlation requires scipy to be installed.")
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


def compute_crosstab(rows, row_var_code, col_var_code) -> dict:
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
                "value": column_value,
                "count": count,
                "percent_row": round(count / row_total * 100, 2) if row_total else 0,
                "percent_total": round(count / total * 100, 2) if total else 0,
            })
        result_rows.append({
            "value": row_value,
            "columns": columns,
            "total": row_total,
        })

    return {
        "row_variable": row_var_code,
        "column_variable": col_var_code,
        "rows": result_rows,
        "total": total,
    }


def _contingency_from_crosstab(crosstab_result):
    return [
        [column["count"] for column in row["columns"]]
        for row in crosstab_result["rows"]
    ]


def compute_chi_square(crosstab_result) -> dict:
    observed = _contingency_from_crosstab(crosstab_result)
    if len(observed) < 2 or not observed or len(observed[0]) < 2:
        raise ValueError("Chi-square requires at least a 2x2 crosstab.")

    if stats is not None:
        chi2, p_value, dof, expected = stats.chi2_contingency(observed)
        return {
            "chi2": float(chi2),
            "p_value": float(p_value),
            "dof": int(dof),
            "expected": [[float(value) for value in row] for row in expected],
        }

    row_totals = [sum(row) for row in observed]
    column_totals = [sum(observed[row_index][col_index] for row_index in range(len(observed))) for col_index in range(len(observed[0]))]
    total = sum(row_totals)
    if total == 0:
        raise ValueError("Chi-square requires non-empty crosstab counts.")

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

    return {
        "chi2": chi2,
        "p_value": None,
        "dof": (len(observed) - 1) * (len(observed[0]) - 1),
        "expected": expected,
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
        raise ValueError("Cramer's V requires a non-empty crosstab.")

    n = sum(sum(row) for row in observed)
    rows = len(observed)
    columns = len(observed[0])
    min_dimension = min(rows - 1, columns - 1)

    if n == 0:
        raise ValueError("Cramer's V requires non-empty crosstab counts.")
    if min_dimension == 0:
        raise ValueError("Cramer's V requires at least a 2x2 crosstab.")

    if chi_square_result is None:
        chi_square_result = compute_chi_square(crosstab_result)
    chi2 = chi_square_result.get("chi2")
    if chi2 is None:
        raise ValueError("Cramer's V requires chi-square value.")

    value = math.sqrt(float(chi2) / (n * min_dimension))
    value = max(0.0, min(1.0, value))

    return {
        "cramers_v": value,
        "n": n,
        "rows": rows,
        "columns": columns,
        "interpretation": interpret_cramers_v(value),
    }


def _complete_regression_cases(rows, target_code, feature_codes):
    y_values = []
    x_values = []
    for row in rows:
        values = [row.get(target_code)] + [row.get(code) for code in feature_codes]
        if all(_is_numeric(value) for value in values):
            y_values.append(_as_float(values[0]))
            x_values.append([_as_float(value) for value in values[1:]])
    return y_values, x_values


def compute_linear_regression(rows, target_code, feature_codes, include_intercept=True) -> dict:
    if not feature_codes:
        raise ValueError("Linear regression requires at least one feature.")
    if np is None:
        raise ValueError("Linear regression requires numpy to be installed.")

    y_values, x_values = _complete_regression_cases(rows, target_code, feature_codes)
    n = len(y_values)
    feature_count = len(feature_codes)
    parameter_count = feature_count + (1 if include_intercept else 0)

    if n <= parameter_count:
        raise ValueError("Not enough complete cases for linear regression.")

    x_matrix = np.array(x_values, dtype=float)
    if include_intercept:
        x_matrix = np.column_stack([np.ones(n), x_matrix])
    y_vector = np.array(y_values, dtype=float)

    coefficients, _, rank, _ = np.linalg.lstsq(x_matrix, y_vector, rcond=None)
    if rank < parameter_count:
        raise ValueError("Regression design matrix is rank deficient.")

    predicted = x_matrix @ coefficients
    residual_sum_squares = float(np.sum((y_vector - predicted) ** 2))
    total_sum_squares = float(np.sum((y_vector - np.mean(y_vector)) ** 2))
    r2 = 1.0 if total_sum_squares == 0 else 1 - residual_sum_squares / total_sum_squares
    adjusted_denominator = n - parameter_count
    adjusted_r2 = 1 - (1 - r2) * (n - 1) / adjusted_denominator if adjusted_denominator > 0 else None

    names = ["intercept"] + feature_codes if include_intercept else feature_codes
    return {
        "model": "linear",
        "target": target_code,
        "features": feature_codes,
        "coefficients": [
            {"name": name, "value": float(value)}
            for name, value in zip(names, coefficients)
        ],
        "r2": float(r2),
        "adjusted_r2": float(adjusted_r2) if adjusted_r2 is not None else None,
        "n": n,
    }


def _complete_factor_cases(rows, variables):
    matrix = []
    codes = [variable.code for variable in variables]
    for row in rows:
        values = [row.get(code) for code in codes]
        if all(_is_numeric(value) for value in values):
            matrix.append([_as_float(value) for value in values])
    return matrix


def _complete_kmeans_cases(rows, variables):
    matrix = []
    response_ids = []
    codes = [variable.code for variable in variables]
    for row in rows:
        values = [row.get(code) for code in codes]
        if any(_is_missing(value) for value in values):
            continue
        if not all(_is_numeric(value) for value in values):
            raise ValueError("Cluster analysis requires all selected values to be numeric.")
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


def compute_kmeans_clustering(
    rows,
    variables,
    n_clusters=3,
    standardize=True,
    max_iter=300,
    random_state=42,
) -> dict:
    if np is None:
        raise ValueError("Cluster analysis requires numpy to be installed.")
    if len(variables) < 2:
        raise ValueError("Cluster analysis requires at least two variables.")
    if n_clusters < 2 or n_clusters > 10:
        raise ValueError("n_clusters must be between 2 and 10.")
    if max_iter < 10 or max_iter > 1000:
        raise ValueError("max_iter must be between 10 and 1000.")

    response_ids, complete_cases = _complete_kmeans_cases(rows, variables)
    n = len(complete_cases)
    p = len(variables)
    if n < n_clusters:
        raise ValueError("Cluster analysis requires at least as many complete cases as clusters.")

    raw_matrix = np.array(complete_cases, dtype=float)
    if not np.all(np.isfinite(raw_matrix)):
        raise ValueError("Cluster analysis data contains non-finite numeric values.")

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
        warnings.append("sklearn is not installed; numpy fallback k-means was used.")

    output_centers = (centers * standard_deviations + means) if standardize else centers
    order = sorted(range(n_clusters), key=lambda index: (-int(np.sum(labels == index)), index))
    cluster_number_by_label = {label: position + 1 for position, label in enumerate(order)}

    clusters = []
    for label in order:
        size = int(np.sum(labels == label))
        center = output_centers[label]
        clusters.append({
            "cluster": cluster_number_by_label[label],
            "size": size,
            "percent": round(size / n * 100, 2) if n else 0,
            "centroid": {
                variable.code: float(center[index])
                for index, variable in enumerate(variables)
            },
        })

    return {
        "method": method,
        "n": n,
        "n_variables": p,
        "n_clusters": n_clusters,
        "standardize": standardize,
        "variables": [
            {"code": variable.code, "label": variable.label}
            for variable in variables
        ],
        "clusters": clusters,
        "assignments": [
            {
                "response_id": response_id,
                "cluster": cluster_number_by_label[int(label)],
            }
            for response_id, label in zip(response_ids, labels)
        ],
        "inertia": inertia,
        "warnings": warnings,
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


def _describe_group(group_value, values, value_labels=None):
    ordered = sorted(values)
    n = len(values)
    mean = sum(values) / n
    middle = n // 2
    median = ordered[middle] if n % 2 else (ordered[middle - 1] + ordered[middle]) / 2
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
        "label": label or str(group_value),
        "n": n,
        "mean": float(mean),
        "median": float(median),
        "std": _sample_std(values),
        "min": float(min(values)),
        "max": float(max(values)),
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


def _finite_or_none(value):
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def compute_group_comparison(rows, group_var, value_var, method="anova", alpha=0.05) -> dict:
    if stats is None:
        raise ValueError("Group comparison requires scipy to be installed.")
    if method not in ("t_test", "anova", "mann_whitney", "kruskal_wallis"):
        raise ValueError("Unsupported group comparison method.")

    groups = defaultdict(list)
    warnings = []
    for row in rows:
        group_value = row.get(group_var.code)
        value = row.get(value_var.code)
        if _is_missing(group_value) or _is_missing(value):
            continue
        if not _is_numeric(value):
            raise ValueError("Group comparison value variable must contain numeric values.")
        groups[group_value].append(_as_float(value))

    ordered_group_keys = _sort_values(groups.keys())
    group_values = [groups[key] for key in ordered_group_keys]
    n_groups = len(group_values)
    n = sum(len(values) for values in group_values)

    if n_groups < 2:
        raise ValueError("Group comparison requires at least two groups with complete data.")
    if any(len(values) < 2 for values in group_values):
        raise ValueError("Each group must contain at least two observations.")
    if method in ("t_test", "mann_whitney") and n_groups != 2:
        raise ValueError("Selected method requires exactly two groups.")
    if method in ("anova", "kruskal_wallis") and n_groups < 2:
        raise ValueError("Selected method requires at least two groups.")
    if n <= n_groups:
        raise ValueError("Group comparison requires more observations than groups.")

    if method == "t_test":
        result = stats.ttest_ind(group_values[0], group_values[1], equal_var=False, nan_policy="omit")
        method_name = "Welch t-test"
        groups_compared = [ordered_group_keys[0], ordered_group_keys[1]]
        effect_value = _cohens_d(group_values)
        effect_size = None if effect_value is None else {
            "type": "cohens_d",
            "value": float(effect_value),
            "interpretation": _interpret_cohens_d(effect_value),
        }
    elif method == "anova":
        result = stats.f_oneway(*group_values)
        method_name = "One-way ANOVA"
        groups_compared = ordered_group_keys
        effect_value = _eta_squared(group_values)
        effect_size = None if effect_value is None else {
            "type": "eta_squared",
            "value": float(effect_value),
            "interpretation": _interpret_eta_squared(effect_value),
        }
    elif method == "mann_whitney":
        result = stats.mannwhitneyu(group_values[0], group_values[1], alternative="two-sided")
        method_name = "Mann-Whitney U"
        groups_compared = [ordered_group_keys[0], ordered_group_keys[1]]
        effect_size = None
        warnings.append("Effect size is not returned for Mann-Whitney U in MVP.")
    else:
        result = stats.kruskal(*group_values)
        method_name = "Kruskal-Wallis"
        groups_compared = ordered_group_keys
        statistic = _finite_or_none(result.statistic)
        denominator = n - n_groups
        effect_value = None if statistic is None or denominator <= 0 else (statistic - n_groups + 1) / denominator
        effect_size = None if effect_value is None else {
            "type": "epsilon_squared",
            "value": float(max(0.0, effect_value)),
            "interpretation": _interpret_eta_squared(max(0.0, effect_value)),
        }

    statistic = _finite_or_none(result.statistic)
    p_value = _finite_or_none(result.pvalue)

    return {
        "method": method,
        "method_name": method_name,
        "alpha": alpha,
        "n": n,
        "n_groups": n_groups,
        "group_variable": {
            "code": group_var.code,
            "label": group_var.label,
        },
        "value_variable": {
            "code": value_var.code,
            "label": value_var.label,
        },
        "groups": [
            _describe_group(group_key, groups[group_key], group_var.value_labels)
            for group_key in ordered_group_keys
        ],
        "test": {
            "statistic": statistic,
            "p_value": p_value,
            "significant": bool(p_value is not None and p_value < alpha),
            "interpretation": interpret_p_value(p_value, alpha),
            "groups_compared": groups_compared,
        },
        "effect_size": effect_size,
        "warnings": warnings,
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


def compute_factor_analysis(rows, variables, n_factors=2, rotation="varimax", standardize=True) -> dict:
    if np is None:
        raise ValueError("Factor analysis requires numpy to be installed.")
    if rotation not in ("none", "varimax"):
        raise ValueError("Factor analysis rotation must be 'none' or 'varimax'.")

    p = len(variables)
    if p < 3:
        raise ValueError("Factor analysis requires at least three variables.")
    if n_factors < 1:
        raise ValueError("n_factors must be at least 1.")
    if n_factors >= p:
        raise ValueError("n_factors must be less than number of variables.")

    complete_cases = _complete_factor_cases(rows, variables)
    n = len(complete_cases)
    if n <= p:
        raise ValueError("Not enough complete cases for factor analysis.")

    x_matrix = np.array(complete_cases, dtype=float)
    warnings = []
    if n < max(20, 5 * p):
        warnings.append("Small sample size for factor analysis; interpret results cautiously.")

    means = np.mean(x_matrix, axis=0)
    standard_deviations = np.std(x_matrix, axis=0, ddof=1)
    zero_variance_indexes = np.where(standard_deviations == 0)[0]
    if len(zero_variance_indexes):
        labels = [variables[index].label for index in zero_variance_indexes]
        raise ValueError(f"Factor analysis cannot use variables with zero variance: {', '.join(labels)}.")

    if standardize:
        x_matrix = (x_matrix - means) / standard_deviations

    correlation_matrix = np.corrcoef(x_matrix, rowvar=False)
    if not np.all(np.isfinite(correlation_matrix)):
        raise ValueError("Factor analysis correlation matrix contains non-finite values.")

    eigenvalues, eigenvectors = np.linalg.eigh(correlation_matrix)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    eigenvalues = np.maximum(eigenvalues, 0)

    selected_eigenvalues = eigenvalues[:n_factors]
    loadings = eigenvectors[:, :n_factors] * np.sqrt(selected_eigenvalues)
    if rotation == "varimax" and n_factors > 1:
        try:
            loadings = _varimax(loadings)
        except (np.linalg.LinAlgError, ValueError):
            warnings.append("Varimax rotation failed; unrotated loadings returned.")

    total_eigenvalue = float(np.sum(eigenvalues))
    explained = [
        float(value / total_eigenvalue) if total_eigenvalue else 0
        for value in selected_eigenvalues
    ]
    communalities = np.sum(loadings ** 2, axis=1)

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
        "explained_variance": [
            {"factor": f"Factor {index + 1}", "value": value}
            for index, value in enumerate(explained)
        ],
        "cumulative_explained_variance": float(sum(explained)),
        "loadings": [
            {
                "variable": variable.code,
                "label": variable.label,
                "factors": [
                    {"factor": f"Factor {index + 1}", "loading": float(loadings[row_index, index])}
                    for index in range(n_factors)
                ],
                "communality": float(communalities[row_index]),
            }
            for row_index, variable in enumerate(variables)
        ],
        "correlation_matrix": correlation_matrix.tolist(),
        "warnings": warnings,
    }
