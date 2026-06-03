from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
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


