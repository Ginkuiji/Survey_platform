from .constants import *  # noqa: F401,F403
from . import helpers as _helpers

globals().update({name: getattr(_helpers, name) for name in dir(_helpers) if not name.startswith("__")})

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
    if analysis_type == "time_analysis":
        summary = result.get("summary") or {}
        duration = result.get("duration_summary") or {}
        quality = result.get("quality_flags") or {}
        dropout = result.get("dropout") or {}
        return {
            **summary,
            "median_duration_seconds": duration.get("median_seconds", summary.get("median_completion_time_seconds")),
            "p25_duration_seconds": duration.get("p25_seconds"),
            "p75_duration_seconds": duration.get("p75_seconds"),
            "iqr_duration_seconds": duration.get("iqr_seconds"),
            "too_fast_rate": (quality.get("too_fast") or {}).get("rate"),
            "possibly_low_quality_rate": quality.get("possibly_low_quality_rate"),
            "highest_dropout_page": dropout.get("highest_dropout_page"),
        }
    if analysis_type == "scale_index":
        groups = (result.get("groups") or {}).get("items") or []
        high = next((item for item in groups if item.get("group") == "high"), {})
        reliability = result.get("reliability") or {}
        return {
            "method": result.get("calculation", result.get("method")),
            "index_title": result.get("index_title", result.get("title")),
            "n": result.get("n", result.get("n_scored")),
            "items_count": result.get("items_count", result.get("n_items")),
            "mean_score": (result.get("score_summary") or {}).get("mean"),
            "mean_normalized_score": (result.get("normalized_score_summary") or {}).get("mean"),
            "cronbach_alpha": reliability.get("cronbach_alpha", reliability.get("alpha")),
            "high_group_percent": high.get("percent"),
        }
    if analysis_type == "reliability_analysis":
        return {
            "method": result.get("method"),
            "n": result.get("n"),
            "items_count": result.get("items_count", result.get("n_items")),
            "cronbach_alpha": result.get("cronbach_alpha", result.get("alpha")),
            "average_inter_item_correlation": result.get("average_inter_item_correlation", result.get("mean_inter_item_correlation")),
            "problematic_items_count": len(result.get("problematic_items") or []),
            "items_improving_alpha_count": sum(bool(item.get("improves_alpha")) for item in result.get("alpha_if_item_deleted") or []),
        }
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
            return {"name": "V Крамера", "value": value, "interpretation": interpret_cramers_v(value), "description": "Показывает силу связи между категориальными переменными."}
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
    if analysis_type == "time_analysis":
        value = (result.get("summary") or {}).get("completion_rate")
        if value is not None:
            interpretation = "высокая доля завершений" if value >= 80 else "умеренная доля завершений" if value >= 60 else "низкая доля завершений"
            return {"name": "Доля полных завершений", "value": value, "interpretation": interpretation, "description": "Показывает долю начавших опрос респондентов, которые полностью завершили его."}
    if analysis_type == "reliability_analysis" and result.get("alpha") is not None:
        return {"name": "Cronbach’s alpha", "value": result["alpha"], "interpretation": interpret_cronbach_alpha(result["alpha"]), "description": "Показывает внутреннюю согласованность пунктов шкалы."}
    if analysis_type == "scale_index":
        value = (result.get("reliability") or {}).get("alpha")
        if value is not None:
            return {"name": "Cronbach’s alpha", "value": value, "interpretation": interpret_cronbach_alpha(value), "description": "Показывает внутреннюю согласованность пунктов индекса."}
    return {}

