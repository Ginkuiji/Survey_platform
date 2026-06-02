from copy import deepcopy

from .analytics_data_quality import (
    build_applicability_warnings,
    build_data_quality_summary,
    deduplicate_warnings,
)
from .analytics_descriptive_profile import (
    build_descriptive_profile,
    build_descriptive_recommendations,
    collect_descriptive_warnings,
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
    "crosstab": [
        "Для проверки статистической значимости связи можно дополнительно использовать χ²-критерий и Cramér’s V.",
        "Для интерпретации таблицы важно смотреть не только абсолютные частоты, но и проценты по строкам и по всей выборке.",
    ],
    "group_comparison": ["Сопоставляйте p-value с размером эффекта, распределениями внутри групп и результатами post-hoc сравнений."],
    "regression": [
        "Сравнивайте R² и adjusted R², особенно если в модели несколько предикторов.",
        "Проверяйте VIF: высокая мультиколлинеарность делает коэффициенты нестабильными.",
        "Используйте график остатков для проверки применимости линейной модели.",
        "Не интерпретируйте регрессионные коэффициенты как причинное влияние без соответствующего дизайна исследования.",
    ],
    "logistic_regression": [
        "Интерпретируйте коэффициенты логистической регрессии через odds ratio.",
        "При дисбалансе классов accuracy следует оценивать вместе с precision, recall, F1 и balanced accuracy.",
        "ROC-AUC помогает оценить способность модели различать классы независимо от одного выбранного порога.",
        "Проверьте events per variable: при малом числе событий коэффициенты могут быть нестабильными.",
    ],
    "factor_analysis": [
        "Проверьте KMO и критерий Бартлетта перед содержательной интерпретацией факторов.",
        "Используйте scree plot и parallel analysis для выбора числа факторов.",
        "Интерпретируйте фактор по вопросам с наибольшими абсолютными нагрузками.",
        "Переменные с низкой communality или cross-loading стоит проверить и при необходимости исключить из шкалы.",
        "После выбора набора вопросов для шкалы рекомендуется проверить надежность шкалы с помощью alpha Кронбаха.",
    ],
    "cluster_analysis": [
        "Интерпретируйте кластеры по профилям и топ отличающим признакам, а не только по номерам кластеров.",
        "Проверьте silhouette score и размеры кластеров перед содержательной интерпретацией.",
        "Используйте PCA scatterplot для визуальной проверки разделения кластеров.",
        "Используйте elbow plot для оценки выбранного числа кластеров.",
        "Если кластер имеет мало респондентов, его следует рассматривать осторожно.",
    ],
    "missing_analysis": ["Для вопросов с высокой долей пропусков проверьте формулировку, обязательность заполнения и условия ветвления."],
}

VISUALIZATIONS = {
    "correlation": [
        ("correlation_heatmap", "Тепловая карта корреляций"),
        ("correlation_scatterplot", "Диаграмма рассеяния"),
        ("ranked_scatterplot", "Ранговая диаграмма рассеяния"),
        ("correlation_network", "Сеть сильных корреляций"),
    ],
    "crosstab": [
        {"type": "stacked_bar", "title": "Составная столбчатая диаграмма", "recommended": True, "description": "Показывает распределение категорий столбцовой переменной внутри категорий строковой переменной."},
        {"type": "crosstab_table", "title": "Таблица сопряженности", "recommended": True},
        {"type": "mosaic_plot", "title": "Mosaic plot", "recommended": False, "description": "Показывает структуру совместного распределения категорий."},
    ],
    "chi_square": [
        {"type": "stacked_bar", "title": "Составная столбчатая диаграмма", "recommended": True},
        {"type": "standardized_residual_heatmap", "title": "Тепловая карта стандартизированных остатков", "recommended": True, "description": "Показывает ячейки, которые сильнее всего отличаются от ожидаемых частот."},
        {"type": "chi_square_contribution_heatmap", "title": "Тепловая карта вкладов в χ²", "recommended": True, "description": "Показывает, какие ячейки дают наибольший вклад в значение χ²."},
        {"type": "mosaic_plot", "title": "Mosaic plot", "recommended": False},
    ],
    "correspondence_analysis": [("correspondence_map", "Карта соответствий"), ("inertia_chart", "Объясненная инерция")],
    "regression": [
        {"type": "regression_coefficients", "title": "Коэффициенты регрессии", "recommended": True, "description": "Показывает направление и величину связи предикторов с целевой переменной."},
        {"type": "coefficient_confidence_intervals", "title": "Доверительные интервалы коэффициентов", "recommended": True, "description": "Показывает неопределенность оценки коэффициентов."},
        {"type": "observed_vs_predicted", "title": "Наблюдаемые и предсказанные значения", "recommended": True, "description": "Показывает, насколько хорошо модель воспроизводит фактические значения."},
        {"type": "residual_plot", "title": "График остатков", "recommended": True, "description": "Помогает оценить нелинейность, выбросы и неоднородность дисперсии."},
        {"type": "residual_histogram", "title": "Распределение остатков", "recommended": False},
        {"type": "partial_effect", "title": "Частичный эффект фактора", "recommended": False},
    ],
    "logistic_regression": [
        {"type": "odds_ratio_forest_plot", "title": "Odds ratio по факторам", "recommended": True},
        {"type": "confusion_matrix_heatmap", "title": "Матрица ошибок", "recommended": True},
        {"type": "roc_curve", "title": "ROC-кривая", "recommended": True},
        {"type": "probability_histogram", "title": "Распределение предсказанных вероятностей", "recommended": True},
        {"type": "calibration_plot", "title": "Калибровка вероятностей", "recommended": False},
        {"type": "threshold_metrics", "title": "Метрики при разных порогах", "recommended": False},
    ],
    "factor_analysis": [
        {"type": "scree_plot", "title": "Scree plot", "recommended": True, "description": "Показывает eigenvalues компонентов и помогает выбрать число факторов."},
        {"type": "parallel_analysis_plot", "title": "Parallel analysis", "recommended": True, "description": "Сравнивает eigenvalues реальных данных со случайными данными."},
        {"type": "factor_loadings_heatmap", "title": "Тепловая карта факторных нагрузок", "recommended": True},
        {"type": "explained_variance_bar", "title": "Объясненная дисперсия", "recommended": True},
        {"type": "communalities_bar", "title": "Communalities", "recommended": True},
        {"type": "factor_score_scatterplot", "title": "Диаграмма факторных значений", "recommended": False},
        {"type": "pca_biplot", "title": "PCA biplot", "recommended": False},
    ],
    "cluster_analysis": [
        {"type": "cluster_sizes", "title": "Размеры кластеров", "recommended": True},
        {"type": "profile_heatmap", "title": "Профили кластеров", "recommended": True},
        {"type": "pca_scatter", "title": "PCA scatterplot кластеров", "recommended": True},
        {"type": "radar", "title": "Radar chart профиля кластера", "recommended": False},
        {"type": "silhouette", "title": "Silhouette plot", "recommended": True},
        {"type": "elbow", "title": "Elbow plot", "recommended": True},
        {"type": "distances", "title": "Расстояния до центроидов", "recommended": False},
    ],
    "group_comparison": [
        {"type": "group_boxplot", "title": "Boxplot по группам", "recommended": True, "description": "Показывает медиану, квартильный размах и выбросы в каждой группе."},
        {"type": "group_mean_ci_plot", "title": "Средние значения с доверительными интервалами", "recommended": True, "description": "Показывает различия средних значений между группами."},
        {"type": "group_violin_plot", "title": "Violin plot", "recommended": False, "description": "Показывает форму распределения внутри групп."},
        {"type": "post_hoc_table", "title": "Таблица post-hoc сравнений", "recommended": True},
    ],
    "time_analysis": [("time_distribution", "Распределение времени прохождения")],
    "reliability_analysis": [("item_statistics", "Статистики пунктов шкалы")],
    "scale_index": [("score_distribution", "Распределение индекса шкалы")],
    "missing_analysis": [
        ("missing_rate", "Доля пропусков по вопросам"),
        ("missing_stacked_status", "Причины отсутствия ответов"),
    ],
}

CORRELATION_METHOD_HINTS = {
    "pearson": "Pearson оценивает линейную связь числовых переменных. Проверьте диаграмму рассеяния и выбросы.",
    "spearman": "Spearman оценивает монотонную связь по рангам и подходит для порядковых данных или нелинейной монотонной зависимости.",
    "kendall": "Kendall оценивает ранговую согласованность и полезен для порядковых данных, небольших выборок и большого числа совпадающих рангов.",
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


def build_main_results(analysis_type, result):
    if analysis_type == "correlation":
        return {
            "method": result.get("method"),
            "method_hint": build_correlation_method_hint(result),
            "strongest_relationships": _strongest_correlations(result),
            "network": build_correlation_network(result),
        }
    if analysis_type == "chi_square":
        chi_square = result.get("chi_square") or {}
        cramers_v = result.get("cramers_v") or {}
        diagnostics = chi_square.get("expected_diagnostics") or {}
        p_value = chi_square.get("p_value")
        return {
            **{key: chi_square.get(key) for key in ("chi2", "p_value", "dof")},
            "significant": p_value is not None and p_value < 0.05,
            "n": cramers_v.get("n"),
            "table_size": f"{cramers_v.get('rows')}×{cramers_v.get('columns')}" if cramers_v.get("rows") is not None and cramers_v.get("columns") is not None else None,
            "expected_below_5_rate": diagnostics.get("below_5_rate"),
            "top_contributing_cells": chi_square.get("top_contributing_cells") or [],
        }
    if analysis_type == "regression":
        coefficients = result.get("coefficients") or []
        return {
            **{key: result.get(key) for key in ("model", "target", "n", "r2", "adjusted_r2", "rmse", "mae")},
            "features_count": result.get("feature_count", len(result.get("features") or [])),
            "significant_coefficients_count": sum(item.get("name") != "intercept" and item.get("p_value") is not None and item["p_value"] < 0.05 for item in coefficients),
            "top_coefficients": sorted([item for item in coefficients if item.get("name") != "intercept"], key=lambda item: abs(item.get("standardized_coefficient") or item.get("value") or 0), reverse=True)[:5],
        }
    if analysis_type == "logistic_regression":
        metrics = result.get("metrics") or {}
        return {
            "model": result.get("model"),
            "target": result.get("target"),
            "n": result.get("n"),
            "features_count": result.get("feature_count", len(result.get("features") or [])),
            "base_rate": result.get("base_rate"),
            **{key: metrics.get(key) for key in ("accuracy", "precision", "recall", "specificity", "f1", "balanced_accuracy", "roc_auc", "mcfadden_r2")},
            "top_coefficients": result.get("coefficients", [])[:5],
        }
    if analysis_type == "factor_analysis":
        recommendations = result.get("factor_recommendations") or {}
        return {
            **{key: result.get(key) for key in ("n", "n_variables", "n_factors", "cumulative_explained_variance")},
            "kmo_overall": (result.get("kmo") or {}).get("overall"),
            "bartlett_p_value": (result.get("bartlett") or {}).get("p_value"),
            "recommended_n_factors": recommendations.get("recommended_n_factors", recommendations.get("kaiser_n_factors")),
        }
    if analysis_type == "cluster_analysis":
        sizes = [item.get("size", item.get("count")) for item in (result.get("clusters") or result.get("cluster_sizes") or [])]
        sizes = [value for value in sizes if value is not None]
        return {
            **{key: result.get(key) for key in ("method", "n", "n_clusters", "n_variables", "silhouette_score", "inertia")},
            "min_cluster_size": min(sizes) if sizes else None,
            "max_cluster_size": max(sizes) if sizes else None,
        }
    if analysis_type == "group_comparison":
        groups = result.get("groups") or []
        highest = max(groups, key=lambda item: item.get("mean", float("-inf")), default=None)
        lowest = min(groups, key=lambda item: item.get("mean", float("inf")), default=None)
        test = result.get("test") or {}
        comparisons = (result.get("post_hoc") or {}).get("comparisons") or []
        return {
            "method": result.get("method"),
            "n": result.get("n"),
            "groups_count": result.get("groups_count", result.get("n_groups")),
            "p_value": test.get("p_value"),
            "significant": test.get("significant"),
            "highest_group": {"label": highest.get("label"), "mean": highest.get("mean"), "median": highest.get("median")} if highest else None,
            "lowest_group": {"label": lowest.get("label"), "mean": lowest.get("mean"), "median": lowest.get("median")} if lowest else None,
            "significant_post_hoc_pairs_count": sum(bool(item.get("significant")) for item in comparisons),
        }
    if analysis_type == "cluster_analysis":
        silhouette = result.get("silhouette_score")
        summary = f"Выделено {result.get('n_clusters', '—')} кластеров респондентов."
        if silhouette is not None:
            summary += f" Silhouette score равен {silhouette:.3f}: {interpret_silhouette(silhouette)}. Сегменты следует рассматривать как предварительные и проверять содержательно."
        else:
            summary += " Silhouette score недоступен; интерпретация разделения кластеров ограничена."
        return {
            "summary": summary,
            "details": [
                "Кластеризация группирует респондентов по схожести выбранных признаков.",
                "Размер кластера показывает, какая часть выборки попала в данный сегмент.",
                "Профиль кластера показывает средние значения признаков внутри сегмента.",
                "Топ отличающих признаков показывает, по каким переменным кластер сильнее всего отличается от общей выборки.",
                "Silhouette score помогает оценить разделенность кластеров.",
                "Elbow plot помогает подобрать разумное число кластеров по снижению inertia.",
            ],
            "limitations": [
                "Кластеризация является разведочным методом и не доказывает существование естественных групп в генеральной совокупности.",
                "Результат зависит от выбранных переменных, масштаба данных и числа кластеров.",
                "При низком silhouette score сегменты могут быть нестабильными.",
                "Названия и смысл кластеров должны задаваться исследователем на основе профиля признаков.",
            ],
        }
    if analysis_type == "missing_analysis":
        return result.get("detailed_missing_analysis") or result.get("summary") or {}
    if analysis_type in ("time_analysis", "scale_index"):
        return result.get("summary") or {}
    if analysis_type == "reliability_analysis":
        return {key: result.get(key) for key in ("n", "n_items", "alpha", "standardized_alpha")}
    if analysis_type == "correspondence_analysis":
        return {key: result.get(key) for key in ("n", "n_dimensions", "total_inertia")}
    if analysis_type == "crosstab":
        crosstab = result.get("crosstab") or {}
        rows = crosstab.get("rows") or []
        cells = [
            {"row_label": row.get("value"), "column_label": column.get("value"), **column}
            for row in rows
            for column in row.get("columns") or []
        ]
        return {
            "n": crosstab.get("total"),
            "rows_count": len(rows),
            "columns_count": len(rows[0].get("columns") or []) if rows else 0,
            "table_size": f"{len(rows)}×{len(rows[0].get('columns') or []) if rows else 0}",
            "largest_cell": max(cells, key=lambda item: item.get("count", 0), default=None),
        }
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
            return {"name": "Cramér’s V", "value": value, "interpretation": interpret_cramers_v(value), "description": "Показывает силу связи между категориальными переменными."}
    if analysis_type == "regression" and result.get("r2") is not None:
        return {"name": "R²", "value": result["r2"], "interpretation": interpret_r2(result["r2"]), "description": "Показывает долю вариации целевой переменной, объясняемую моделью."}
    if analysis_type == "logistic_regression":
        value = (result.get("metrics") or {}).get("roc_auc")
        if value is not None:
            interpretation = "низкое качество различения классов" if value < 0.7 else "приемлемое качество различения классов" if value < 0.8 else "хорошее качество различения классов"
            return {"name": "ROC-AUC", "value": value, "interpretation": interpretation, "description": "Показывает способность модели различать классы независимо от одного выбранного порога."}
        return {"name": "Odds ratio", "values": result.get("coefficients", [])}
    if analysis_type == "group_comparison":
        return result.get("effect_size") or {}
    if analysis_type == "cluster_analysis" and result.get("silhouette_score") is not None:
        value = result["silhouette_score"]
        return {"name": "Silhouette score", "value": value, "interpretation": interpret_silhouette(value), "description": "Показывает, насколько объекты похожи на свой кластер по сравнению с ближайшим другим кластером."}
    if analysis_type == "factor_analysis" and result.get("cumulative_explained_variance") is not None:
        value = result["cumulative_explained_variance"]
        interpretation = "факторы объясняют небольшую долю вариации" if value < 0.5 else "факторы объясняют заметную долю вариации"
        return {"name": "Накопленная объясненная дисперсия", "value": value, "interpretation": interpretation}
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
        summary = (
            "Между выбранными категориальными переменными обнаружена статистически значимая связь."
            if main["significant"]
            else "Статистически значимая связь между выбранными категориальными переменными не выявлена. Следует учитывать размер выборки и распределение частот по ячейкам."
        )
        if effect_size.get("interpretation"):
            summary += f" Сила связи по Cramér’s V: {effect_size['interpretation']}."
        if ((result.get("chi_square") or {}).get("expected_diagnostics") or {}).get("assumption_warning"):
            summary += " Часть ожидаемых частот мала, поэтому результат χ²-критерия следует интерпретировать осторожно."
        return {
            "summary": summary,
            "details": [
                "χ²-критерий проверяет, отличается ли наблюдаемое распределение от ожидаемого при отсутствии связи между переменными.",
                "Cramér’s V показывает силу связи между категориальными переменными.",
                "Стандартизированные остатки помогают понять, какие ячейки таблицы сильнее всего отличаются от ожидаемых значений.",
            ],
            "limitations": [
                "Статистическая связь не доказывает причинно-следственную зависимость.",
                "При малых ожидаемых частотах χ²-критерий может быть ненадёжен.",
            ],
        }
    if analysis_type == "crosstab":
        return {
            "summary": "Таблица сопряженности показывает совместное распределение двух категориальных переменных. Она позволяет увидеть, какие сочетания категорий встречаются чаще или реже.",
            "details": ["Для содержательной интерпретации сопоставляйте абсолютные частоты и проценты по строкам."],
            "limitations": ["Сама таблица сопряженности не подтверждает статистическую значимость наблюдаемой ассоциации."],
        }
    if analysis_type == "group_comparison":
        main = build_main_results(analysis_type, result)
        highest = main.get("highest_group") or {}
        lowest = main.get("lowest_group") or {}
        if main.get("significant"):
            if (main.get("groups_count") or 0) == 2:
                summary = f"Между двумя группами обнаружены статистически значимые различия. Среднее значение выше в группе «{highest.get('label')}», ниже в группе «{lowest.get('label')}»."
            else:
                summary = f"Обнаружены статистически значимые различия между группами. Наибольшее среднее значение наблюдается в группе «{highest.get('label')}», наименьшее — в группе «{lowest.get('label')}»."
        else:
            summary = "Статистически значимые различия между группами не выявлены. Следует учитывать размер выборки, разброс внутри групп и размер эффекта."
        if effect_size.get("interpretation"):
            summary += f" Размер эффекта: {effect_size['interpretation']}."
        return {
            "summary": summary,
            "details": [
                "t-test и Mann–Whitney применяются для сравнения двух групп.",
                "ANOVA и Kruskal–Wallis применяются для сравнения трех и более групп.",
                "Размер эффекта показывает, насколько выражены различия между группами.",
                "Post-hoc сравнения помогают определить, между какими именно группами есть различия.",
            ],
            "limitations": [
                "Статистическая значимость не показывает величину различий; для этого используется размер эффекта.",
                "При малых или сильно несбалансированных группах результаты следует интерпретировать осторожно.",
                "Post-hoc сравнения увеличивают риск ложноположительных результатов, поэтому требуется поправка p-value.",
            ],
        }
    if analysis_type == "regression" and effect_size:
        return {
            "summary": f"Модель объясняет {effect_size['value'] * 100:.2f}% вариации целевой переменной. Коэффициенты показывают среднее изменение целевой переменной при изменении предиктора на одну единицу при прочих равных условиях. Регрессионная модель показывает статистическую связь, но сама по себе не доказывает причинное влияние.",
            "details": ["R² показывает долю вариации целевой переменной, объясняемую моделью.", "Adjusted R² учитывает количество предикторов.", "Стандартизированные коэффициенты помогают сравнивать относительную силу предикторов.", "VIF используется для проверки мультиколлинеарности.", "Диагностика остатков помогает оценить применимость линейной модели."],
            "limitations": ["Линейная регрессия предполагает приблизительно линейную связь.", "Регрессионная модель не доказывает причинно-следственную зависимость.", "При мультиколлинеарности коэффициенты могут быть нестабильными.", "При неоднородности дисперсии остатков стандартные ошибки и p-value могут быть ненадежными."],
        }
    if analysis_type == "logistic_regression":
        return {
            "summary": "Логистическая регрессия оценивает связь факторов с вероятностью наступления бинарного события. Odds ratio больше 1 соответствует увеличению шансов события, меньше 1 — уменьшению шансов при прочих равных условиях. Модель не доказывает причинно-следственную зависимость.",
            "details": ["Odds ratio показывает изменение шансов события при увеличении предиктора на одну единицу.", "ROC-AUC оценивает способность модели различать классы.", "Матрица ошибок показывает правильные и ошибочные классификации.", "Калибровка сопоставляет предсказанные вероятности с наблюдаемой частотой события."],
            "limitations": ["Логистическая регрессия показывает статистическую связь, но не доказывает причинность.", "При дисбалансе классов accuracy может быть завышенной.", "При малом числе событий на предиктор коэффициенты могут быть нестабильными."],
        }
    if analysis_type == "factor_analysis":
        kmo = (result.get("kmo") or {}).get("overall")
        bartlett = (result.get("bartlett") or {}).get("significant")
        variance = result.get("cumulative_explained_variance")
        summary = "Факторный анализ указывает на возможную скрытую структуру связей между выбранными переменными."
        if kmo is not None:
            summary += f" Общий KMO равен {kmo:.3f}."
        if bartlett is True:
            summary += " Критерий Бартлетта статистически значим."
        elif bartlett is False:
            summary += " Критерий Бартлетта незначим, поэтому решение следует интерпретировать осторожно."
        if variance is not None:
            summary += f" Выбранные факторы объясняют {variance * 100:.2f}% вариации."
        return {
            "summary": summary,
            "details": [
                "KMO оценивает пригодность данных для факторного анализа.",
                "Критерий Бартлетта проверяет, отличается ли корреляционная матрица от единичной.",
                "Factor loadings показывают связь переменных с факторами.",
                "Communality показывает, насколько хорошо переменная объясняется выделенными факторами.",
                "Parallel analysis сравнивает eigenvalues реальных данных со случайными данными.",
            ],
            "limitations": [
                "Факторный анализ не доказывает существование скрытых причин, а только выявляет структуру связей между переменными.",
                "Названия факторов должны задаваться исследователем на основе смысла вопросов с высокими нагрузками.",
                "При малой выборке или низком KMO факторное решение может быть нестабильным.",
                "Переменные с cross-loading могут затруднять интерпретацию факторов.",
            ],
        }
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
    warnings.extend(chi_square.get("warnings") or [])
    warnings.extend((result.get("kmo") or {}).get("warnings") or [])
    warnings.extend((result.get("bartlett") or {}).get("warnings") or [])
    warnings.extend((result.get("cluster_quality") or {}).get("warnings") or [])
    if "p_value" in chi_square and chi_square.get("p_value") is None:
        warnings.append("Для данного метода не удалось рассчитать p-value.")
    return warnings


def build_visualization_specs(analysis_type):
    specs = []
    for index, item in enumerate(VISUALIZATIONS.get(analysis_type, [])):
        if isinstance(item, dict):
            specs.append({**item, "recommended": item.get("recommended", index == 0)})
        else:
            chart_type, title = item
            specs.append({"type": chart_type, "title": title, "recommended": index == 0})
    return specs


def standardize_analysis_result(analysis_type, result, payload=None, dataset=None):
    raw_result = _clean_raw_result(result)
    data_quality = build_data_quality_summary(analysis_type, raw_result, payload, dataset)
    descriptive_profile = build_descriptive_profile(raw_result, payload, dataset, raw_result.get("survey_id"))
    warnings = collect_warnings(raw_result)
    warnings.extend(build_applicability_warnings(analysis_type, raw_result, payload, dataset, data_quality))
    warnings.extend(collect_descriptive_warnings(descriptive_profile))
    warnings = deduplicate_warnings(warnings)
    effect_size = build_effect_size_summary(analysis_type, raw_result)
    interpretation = build_interpretation(analysis_type, raw_result, effect_size, data_quality, warnings)
    recommendations = [
        *RECOMMENDATIONS.get(
            analysis_type,
            ["Интерпретируйте результат вместе с подробными таблицами и графиками метода."],
        ),
        *build_common_recommendations(analysis_type, interpretation, warnings),
        *build_descriptive_recommendations(descriptive_profile),
        *((raw_result.get("detailed_missing_analysis") or {}).get("recommendations") or []),
    ]
    standardized_result = {
        "analysis_type": analysis_type,
        "title": ANALYSIS_TITLES.get(analysis_type, analysis_type.replace("_", " ").title()),
        "purpose": ANALYSIS_PURPOSES.get(analysis_type, "Аналитический метод."),
        "input_summary": build_input_summary(raw_result, payload, dataset),
        "data_quality": data_quality,
        "descriptive_profile": descriptive_profile,
        "main_results": build_main_results(analysis_type, raw_result),
        "effect_size": effect_size,
        "interpretation": interpretation,
        "visualizations": build_visualization_specs(analysis_type),
        "warnings": warnings,
        "recommendations": deduplicate_warnings(recommendations),
        "raw_result": raw_result,
    }
    if analysis_type == "correlation":
        standardized_result["method_hint"] = build_correlation_method_hint(raw_result)
    return standardized_result
