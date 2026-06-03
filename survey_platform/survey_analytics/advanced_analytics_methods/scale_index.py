from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
from .reliability import compute_cronbach_alpha
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


