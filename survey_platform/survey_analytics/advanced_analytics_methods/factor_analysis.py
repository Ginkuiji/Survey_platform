from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
from .associations import compute_correlation_matrix
from .clustering import _complete_factor_cases_with_ids
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
