from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
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


