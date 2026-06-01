from copy import deepcopy

from .analytics_data_quality import (
    build_applicability_warnings,
    build_data_quality_summary,
    deduplicate_warnings,
)

ANALYSIS_TITLES = {
    "correlation": "Корреляционный анализ",
    "crosstab": "Таблица сопряженности",
    "chi_square": "χ²-критерий независимости",
    "correspondence_analysis": "Анализ соответствий",
    "regression": "Линейная регрессия",
    "logistic_regression": "Логистическая регрессия",
    "factor_analysis": "Факторный анализ",
    "cluster_analysis": "Кластерный анализ",
    "group_comparison": "Сравнение групп",
    "time_analysis": "Анализ времени прохождения и отсева",
    "reliability_analysis": "Анализ надежности шкалы",
    "scale_index": "Индекс шкалы",
    "missing_analysis": "Анализ пропусков",
}

ANALYSIS_PURPOSES = {
    "correlation": "Метод используется для оценки направления и силы связи между числовыми или порядковыми переменными.",
    "crosstab": "Метод показывает совместное распределение значений двух категориальных переменных.",
    "chi_square": "Метод используется для проверки связи между двумя категориальными переменными.",
    "correspondence_analysis": "Метод помогает визуально исследовать связи между категориями таблицы сопряженности.",
    "regression": "Метод используется для оценки влияния факторов на числовую целевую переменную.",
    "logistic_regression": "Метод оценивает влияние факторов на вероятность наступления бинарного события.",
    "factor_analysis": "Метод используется для выявления скрытых факторов, объясняющих связи между переменными.",
    "cluster_analysis": "Метод используется для выделения групп респондентов со схожими характеристиками.",
    "group_comparison": "Метод используется для проверки различий показателя между группами.",
    "time_analysis": "Метод показывает время прохождения опроса, завершения и отсева респондентов.",
    "reliability_analysis": "Метод оценивает внутреннюю согласованность пунктов шкалы.",
    "scale_index": "Метод объединяет ответы по нескольким пунктам в интегральный показатель.",
    "missing_analysis": "Метод помогает найти пропуски ответов и отличить их от ветвления анкеты.",
}

RECOMMENDATIONS = {
    "correlation": ["Для значимых связей рекомендуется построить диаграмму рассеяния и проверить наличие выбросов."],
    "chi_square": ["Для интерпретации связи учитывайте не только p-value, но и V Крамера, а также распределение по ячейкам таблицы."],
    "factor_analysis": ["Для выбора числа факторов учитывайте scree plot, объясненную дисперсию и содержательную интерпретацию факторов."],
    "missing_analysis": ["Для вопросов с высокой долей пропусков проверьте формулировку, обязательность заполнения и условия ветвления."],
}

VISUALIZATIONS = {
    "correlation": [("heatmap", "Тепловая карта корреляций"), ("scatter_plot", "Диаграмма рассеяния")],
    "crosstab": [("stacked_bar", "Составная столбчатая диаграмма")],
    "chi_square": [("stacked_bar", "Составная столбчатая диаграмма"), ("residual_heatmap", "Тепловая карта стандартизированных остатков")],
    "correspondence_analysis": [("correspondence_map", "Карта соответствий"), ("inertia_chart", "Объясненная инерция")],
    "regression": [("coefficient_chart", "Коэффициенты регрессии")],
    "logistic_regression": [("odds_ratio_chart", "Отношения шансов"), ("probability_histogram", "Распределение прогнозных вероятностей")],
    "factor_analysis": [("scree_plot", "Каменистая осыпь"), ("loadings_heatmap", "Тепловая карта факторных нагрузок")],
    "cluster_analysis": [("cluster_sizes", "Размеры кластеров"), ("cluster_profiles", "Профили кластеров")],
    "group_comparison": [("group_means", "Сравнение групп")],
    "time_analysis": [("time_distribution", "Распределение времени прохождения")],
    "reliability_analysis": [("item_statistics", "Статистики пунктов шкалы")],
    "scale_index": [("score_distribution", "Распределение индекса шкалы")],
    "missing_analysis": [("missing_rate", "Доля пропусков по вопросам")],
}


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
            relationships.append({
                "left": left.get("code"),
                "right": right.get("code"),
                "coefficient": value,
                "p_value": p_values[row_index][column_index] if row_index < len(p_values) and column_index < len(p_values[row_index]) else None,
                "n": n_matrix[row_index][column_index] if row_index < len(n_matrix) and column_index < len(n_matrix[row_index]) else None,
            })
    return sorted(relationships, key=lambda item: abs(item["coefficient"]), reverse=True)[:5]


def build_main_results(analysis_type, result):
    if analysis_type == "correlation":
        return {"method": result.get("method"), "strongest_relationships": _strongest_correlations(result)}
    if analysis_type == "chi_square":
        chi_square = result.get("chi_square") or {}
        p_value = chi_square.get("p_value")
        return {**{key: chi_square.get(key) for key in ("chi2", "p_value", "dof")}, "significant": p_value is not None and p_value < 0.05}
    if analysis_type == "regression":
        return {key: result.get(key) for key in ("r2", "adjusted_r2", "n", "coefficients")}
    if analysis_type == "logistic_regression":
        return {"n": result.get("n"), "metrics": result.get("metrics"), "top_coefficients": result.get("coefficients", [])[:5]}
    if analysis_type == "factor_analysis":
        return {key: result.get(key) for key in ("n", "n_factors", "cumulative_explained_variance")}
    if analysis_type == "cluster_analysis":
        return {"n_clusters": result.get("n_clusters"), "cluster_sizes": result.get("clusters", []), "silhouette_score": result.get("silhouette_score")}
    if analysis_type == "group_comparison":
        return {"method": result.get("method"), "n": result.get("n"), "test": result.get("test")}
    if analysis_type in ("time_analysis", "missing_analysis", "scale_index"):
        return result.get("summary") or {}
    if analysis_type == "reliability_analysis":
        return {key: result.get(key) for key in ("n", "n_items", "alpha", "standardized_alpha")}
    if analysis_type == "correspondence_analysis":
        return {key: result.get(key) for key in ("n", "n_dimensions", "total_inertia")}
    if analysis_type == "crosstab":
        return {"total": (result.get("crosstab") or {}).get("total")}
    return {}


def build_effect_size_summary(analysis_type, result):
    if analysis_type == "correlation":
        strongest = _strongest_correlations(result)
        if strongest:
            value = abs(strongest[0]["coefficient"])
            return {"name": "Максимальный |r|", "value": value, "interpretation": interpret_correlation(value)}
    if analysis_type == "chi_square":
        value = (result.get("cramers_v") or {}).get("cramers_v")
        if value is not None:
            return {"name": "V Крамера", "value": value, "interpretation": interpret_cramers_v(value)}
    if analysis_type == "regression" and result.get("r2") is not None:
        return {"name": "R²", "value": result["r2"], "interpretation": interpret_r2(result["r2"])}
    if analysis_type == "logistic_regression":
        return {"name": "Отношения шансов", "values": result.get("coefficients", [])}
    if analysis_type == "group_comparison":
        return result.get("effect_size") or {}
    if analysis_type == "cluster_analysis" and result.get("silhouette_score") is not None:
        value = result["silhouette_score"]
        return {"name": "Silhouette score", "value": value, "interpretation": interpret_silhouette(value)}
    if analysis_type == "factor_analysis" and result.get("cumulative_explained_variance") is not None:
        return {"name": "Накопленная объясненная дисперсия", "value": result["cumulative_explained_variance"]}
    if analysis_type == "reliability_analysis" and result.get("alpha") is not None:
        return {"name": "α Кронбаха", "value": result["alpha"], "interpretation": interpret_cronbach_alpha(result["alpha"])}
    if analysis_type == "scale_index":
        value = (result.get("reliability") or {}).get("alpha")
        if value is not None:
            return {"name": "α Кронбаха", "value": value, "interpretation": interpret_cronbach_alpha(value)}
    return {}


def _build_base_interpretation(analysis_type, result, effect_size):
    if analysis_type == "correlation":
        strongest = _strongest_correlations(result)
        if strongest:
            item = strongest[0]
            summary = (
                f"Наиболее выраженная связь обнаружена между переменными {item['left']} и {item['right']}: "
                f"r = {item['coefficient']:.3f}. Связь {correlation_direction(item['coefficient'])} и "
                f"{interpret_correlation(item['coefficient'])}."
            )
        else:
            summary = "Для выбранных переменных не удалось выделить парную корреляционную связь."
        return {"summary": summary, "details": [], "limitations": ["Корреляция не доказывает причинно-следственную связь."]}
    if analysis_type == "chi_square":
        main = build_main_results(analysis_type, result)
        summary = "Обнаружена статистически значимая связь." if main["significant"] else "Статистически значимая связь не обнаружена."
        if effect_size.get("interpretation"):
            summary += f" Сила связи: {effect_size['interpretation']}."
        return {"summary": summary, "details": [], "limitations": ["Статистическая значимость не означает причинно-следственную зависимость."]}
    if analysis_type == "regression" and effect_size:
        return {"summary": f"R² модели составляет {effect_size['value']:.3f}: {effect_size['interpretation']}.", "details": [], "limitations": ["Результат зависит от состава предикторов и качества исходных данных."]}
    return {
        "summary": ANALYSIS_PURPOSES.get(analysis_type, "Результат метода подготовлен для дальнейшей интерпретации."),
        "details": [],
        "limitations": [],
    }


def extract_primary_p_value(analysis_type, result):
    if analysis_type == "chi_square":
        return (result.get("chi_square") or {}).get("p_value")
    if analysis_type == "group_comparison":
        return (
            result.get("p_value")
            if result.get("p_value") is not None
            else (result.get("test") or {}).get(
                "p_value",
                (result.get("omnibus") or {}).get("p_value"),
            )
        )
    if analysis_type == "correlation":
        strongest = _strongest_correlations(result)
        return strongest[0].get("p_value") if strongest else None
    if analysis_type == "factor_analysis":
        return (result.get("bartlett") or {}).get("p_value")
    return result.get("p_value")


def build_statistical_significance(analysis_type, result, alpha=0.05):
    p_value = extract_primary_p_value(analysis_type, result)
    if p_value is None:
        return {
            "available": False,
            "p_value": None,
            "alpha": alpha,
            "is_significant": None,
            "interpretation": "Для данного результата p-value не найден или не рассчитывается.",
        }
    is_significant = p_value < alpha
    if analysis_type == "factor_analysis":
        interpretation = (
            "Критерий Бартлетта статистически значим: данные содержат основания для применения факторного анализа."
            if is_significant
            else "Критерий Бартлетта не достигает статистической значимости: пригодность данных для факторного анализа ограничена."
        )
    elif is_significant:
        interpretation = "Результат статистически значим при уровне значимости 0,05."
    else:
        interpretation = "Результат не достигает статистической значимости при уровне значимости 0,05."
    return {
        "available": True,
        "p_value": p_value,
        "alpha": alpha,
        "is_significant": is_significant,
        "interpretation": interpretation,
    }


def _effect_strength_level(effect_size):
    text = str((effect_size or {}).get("interpretation") or "").lower()
    if any(marker in text for marker in ("слаб", "низк", "незнач", "огранич")):
        return "weak"
    if any(marker in text for marker in ("умерен", "замет", "достаточ", "приемлем")):
        return "moderate"
    if any(marker in text for marker in ("сильн", "высок", "хорош", "выраж")):
        return "strong"
    value = (effect_size or {}).get("value")
    if isinstance(value, (int, float)):
        if abs(value) < 0.3:
            return "weak"
        if abs(value) < 0.5:
            return "moderate"
        return "strong"
    return "unknown"


def build_effect_interpretation(effect_size):
    effect_size = effect_size or {}
    value = effect_size.get("value")
    if not effect_size.get("name") or value is None:
        return {
            "available": False,
            "interpretation": "Для данного результата размер эффекта не найден или не был рассчитан.",
        }
    strength = effect_size.get("interpretation") or "размер эффекта рассчитан"
    return {
        "available": True,
        "effect_name": effect_size["name"],
        "effect_value": value,
        "strength": strength,
        "strength_level": _effect_strength_level(effect_size),
        "interpretation": f"Размер эффекта указывает на следующий уровень выраженности результата: {strength}.",
    }


def build_practical_significance(statistical_significance, effect_interpretation, data_quality=None):
    if not statistical_significance.get("available") or not effect_interpretation.get("available"):
        return {
            "level": "unclear",
            "interpretation": "Практическую значимость невозможно оценить полностью, так как отсутствуют данные о статистической значимости или размере эффекта.",
        }
    significant = statistical_significance.get("is_significant")
    strength = effect_interpretation.get("strength_level")
    if significant and strength in ("moderate", "strong"):
        return {
            "level": "high" if strength == "strong" else "moderate",
            "interpretation": "Результат статистически значим и имеет выраженный размер эффекта, поэтому он может иметь практическое значение.",
        }
    if significant and strength == "weak":
        return {
            "level": "limited",
            "interpretation": "Результат статистически значим, однако размер эффекта невелик. Практическая значимость результата может быть ограниченной.",
        }
    if not significant and strength in ("moderate", "strong"):
        return {
            "level": "unclear",
            "interpretation": "Размер эффекта выглядит заметным, но статистическая значимость не достигнута. Возможно, выборка недостаточна для устойчивого вывода.",
        }
    return {
        "level": "limited",
        "interpretation": "Статистически значимый и практически выраженный эффект не выявлен; содержательный вывод следует формулировать осторожно.",
    }


def build_result_confidence(data_quality, warnings, statistical_significance, effect_interpretation):
    quality = data_quality or {}
    method_checks = quality.get("method_checks") or {}
    dataset = quality.get("dataset") or {}
    if not quality or (dataset.get("analysis_n") is None and not warnings):
        return {
            "level": "unknown",
            "interpretation": "Недостаточно информации для оценки устойчивости результата.",
        }
    critical_quality_issue = any(
        method_checks.get(key) is False
        for key in ("sample_size_ok", "missing_rate_ok", "zero_variance_ok")
    )
    if critical_quality_issue or len(warnings) >= 4:
        return {
            "level": "low",
            "interpretation": "Надежность вывода ограничена из-за качества данных или условий применимости метода.",
        }
    if (
        not warnings
        and statistical_significance.get("is_significant") is True
        and effect_interpretation.get("strength_level") in ("moderate", "strong")
    ):
        return {
            "level": "high",
            "interpretation": "Результат выглядит достаточно устойчивым: размер выборки приемлемый, качество данных не содержит критичных предупреждений.",
        }
    return {
        "level": "medium",
        "interpretation": "Результат можно использовать как ориентир, но его следует интерпретировать с учетом предупреждений о данных или применимости метода.",
    }


def _build_common_limitations(analysis_type, significance, data_quality, warnings):
    limitations = []
    association_methods = {
        "correlation", "crosstab", "chi_square", "correspondence_analysis",
        "regression", "logistic_regression",
    }
    if analysis_type in ("regression", "logistic_regression"):
        limitations.append("Регрессионная модель показывает статистическую связь между факторами и целевой переменной, но сама по себе не доказывает причинное влияние.")
    elif analysis_type in association_methods:
        limitations.append("Обнаруженная связь не доказывает причинно-следственную зависимость.")
    if significance.get("available"):
        limitations.append("p-value не показывает силу эффекта; для оценки практической значимости следует учитывать размер эффекта.")
    dataset = (data_quality or {}).get("dataset") or {}
    if dataset.get("analysis_n") is not None and dataset["analysis_n"] < 30:
        limitations.append("При малом размере выборки статистические выводы могут быть нестабильными.")
    if dataset.get("missing_rate") is not None and dataset["missing_rate"] >= 30:
        limitations.append("Высокий уровень пропусков может смещать результаты анализа.")
    if analysis_type == "missing_analysis" and any("ветвлен" in warning.lower() for warning in warnings):
        limitations.append("Вопросы, не показанные из-за ветвления, не следует трактовать как обычные пропуски.")
    return limitations


def build_interpretation(analysis_type, result, effect_size=None, data_quality=None, warnings=None):
    base = _build_base_interpretation(analysis_type, result, effect_size or {})
    warnings = warnings or []
    significance = build_statistical_significance(analysis_type, result)
    effect_interpretation = build_effect_interpretation(effect_size)
    practical_significance = build_practical_significance(significance, effect_interpretation, data_quality)
    confidence = build_result_confidence(data_quality, warnings, significance, effect_interpretation)
    details = list(base.get("details") or [])
    details.extend([
        "p-value показывает, насколько наблюдаемый результат совместим с предположением об отсутствии эффекта или связи.",
        "Статистическая значимость не показывает силу эффекта и не доказывает практическую важность результата.",
    ])
    if effect_interpretation.get("available"):
        details.append("Размер эффекта показывает, насколько выражена связь, различие или объясняющая способность модели.")
    limitations = deduplicate_warnings([
        *(base.get("limitations") or []),
        *_build_common_limitations(analysis_type, significance, data_quality, warnings),
    ])
    return {
        **base,
        "statistical_significance": significance,
        "effect_interpretation": effect_interpretation,
        "practical_significance": practical_significance,
        "confidence": confidence,
        "details": deduplicate_warnings(details),
        "limitations": limitations,
    }


def build_common_recommendations(analysis_type, interpretation, warnings):
    significance = interpretation["statistical_significance"]
    effect = interpretation["effect_interpretation"]
    recommendations = []
    if significance.get("available") and not effect.get("available"):
        recommendations.append("Рекомендуется дополнить результат оценкой размера эффекта, чтобы понять практическую значимость результата.")
    if significance.get("is_significant") is True and effect.get("strength_level") == "weak":
        recommendations.append("Рекомендуется не ограничиваться статистической значимостью и оценить, имеет ли слабый эффект содержательный смысл для исследования.")
    if significance.get("is_significant") is False and effect.get("strength_level") in ("moderate", "strong"):
        recommendations.append("Рекомендуется проверить размер выборки: возможно, данных недостаточно для статистически устойчивого вывода.")
    if len(warnings) >= 3:
        recommendations.append("Перед содержательной интерпретацией рекомендуется проверить качество данных: пропуски, слишком быстрые прохождения и переменные без вариативности.")
    if analysis_type in {"correlation", "crosstab", "chi_square", "correspondence_analysis", "regression", "logistic_regression"}:
        recommendations.append("Для содержательного вывода рекомендуется сопоставить статистический результат с исследовательской гипотезой и контекстом вопроса анкеты.")
    return recommendations


def collect_warnings(result):
    warnings = list(result.get("warnings") or [])
    chi_square = result.get("chi_square") or {}
    if "p_value" in chi_square and chi_square.get("p_value") is None:
        warnings.append("Для данного метода не удалось рассчитать p-value.")
    return warnings


def standardize_analysis_result(analysis_type, result, payload=None, dataset=None):
    raw_result = _clean_raw_result(result)
    data_quality = build_data_quality_summary(analysis_type, raw_result, payload, dataset)
    warnings = collect_warnings(raw_result)
    warnings.extend(build_applicability_warnings(analysis_type, raw_result, payload, dataset, data_quality))
    warnings = deduplicate_warnings(warnings)
    effect_size = build_effect_size_summary(analysis_type, raw_result)
    interpretation = build_interpretation(analysis_type, raw_result, effect_size, data_quality, warnings)
    recommendations = [
        *RECOMMENDATIONS.get(
            analysis_type,
            ["Интерпретируйте результат вместе с подробными таблицами и графиками метода."],
        ),
        *build_common_recommendations(analysis_type, interpretation, warnings),
    ]
    return {
        "analysis_type": analysis_type,
        "title": ANALYSIS_TITLES.get(analysis_type, analysis_type.replace("_", " ").title()),
        "purpose": ANALYSIS_PURPOSES.get(analysis_type, "Аналитический метод."),
        "input_summary": build_input_summary(raw_result, payload, dataset),
        "data_quality": data_quality,
        "main_results": build_main_results(analysis_type, raw_result),
        "effect_size": effect_size,
        "interpretation": interpretation,
        "visualizations": [
            {"type": chart_type, "title": title, "recommended": index == 0}
            for index, (chart_type, title) in enumerate(VISUALIZATIONS.get(analysis_type, []))
        ],
        "warnings": warnings,
        "recommendations": deduplicate_warnings(recommendations),
        "raw_result": raw_result,
    }
