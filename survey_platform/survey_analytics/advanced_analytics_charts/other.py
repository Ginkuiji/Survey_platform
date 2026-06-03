from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def build_missing_analysis_chart(report, config, result, chart_type):
    questions = result.get("top_skipped_questions") or result.get("questions") or []
    questions = questions[:15]
    if not questions:
        raise ValueError("Missing analysis questions are not available.")
    labels = [_truncate(item.get("label") or item.get("question_id"), 24) for item in questions]
    values = [
        _numeric(item.get("skip_rate_shown")) if item.get("skip_rate_shown") is not None else _numeric(item.get("skipped_count")) or 0
        for item in questions
    ]
    return _bar_chart(labels, values, "Top skipped questions", "Skip rate among shown, %")


def build_reliability_chart(report, config, result, chart_type):
    if chart_type in {"inter_item_correlation_heatmap", "items_correlation_heatmap"}:
        correlations = result.get("inter_item_correlations") or {}
        matrix = correlations.get("matrix") or result.get("inter_item_correlation_matrix") or []
        variables = correlations.get("variables") or result.get("variables") or []
        if not matrix or not variables:
            raise ValueError("Для построения графика недостаточно данных в сохраненном результате.")
        labels = [item.get("label") or item.get("code") for item in variables]
        return _matrix_heatmap(matrix, labels, labels, "Межпунктовые корреляции", vmin=-1, vmax=1, cmap="coolwarm")
    items = result.get("item_statistics") or []
    if not items:
        raise ValueError("Reliability item statistics are not available.")
    labels = [_truncate(item.get("label") or item.get("code"), 24) for item in items[:20]]
    if chart_type == "alpha_if_deleted":
        values = [_numeric(item.get("alpha_if_deleted")) or 0 for item in items[:20]]
        return _bar_chart(labels, values, "Alpha if item deleted", "Alpha")
    values = [_numeric(item.get("item_total_correlation")) or 0 for item in items[:20]]
    return _bar_chart(labels, values, "Item-total correlation", "Correlation")


def build_scale_index_chart(report, config, result, chart_type):
    if chart_type in {"items_correlation_heatmap", "scale_items_correlation_heatmap"}:
        return build_reliability_chart(report, config, result.get("reliability") or {}, "inter_item_correlation_heatmap")
    if chart_type == "boxplot":
        scores = [_numeric(item.get("normalized_score")) if item.get("normalized_score") is not None else _numeric(item.get("score")) for item in result.get("scores") or []]
        scores = [value for value in scores if value is not None]
        if not scores:
            raise ValueError("Для построения графика недостаточно данных в сохраненном результате.")
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.boxplot(scores, patch_artist=True)
        ax.set_title("Boxplot индекса шкалы")
        ax.set_ylabel("Значение индекса")
        ax.grid(axis="y", alpha=0.25)
        return figure_to_png(fig)
    if chart_type == "groups":
        rows = (result.get("groups") or {}).get("items") or []
        if not rows:
            raise ValueError("Для построения графика недостаточно данных в сохраненном результате.")
        return _bar_chart([item.get("label") for item in rows], [_numeric(item.get("count")) or 0 for item in rows], "Группы уровней индекса", "Респонденты")
    if chart_type == "score_card":
        summary = result.get("normalized_score_summary") or result.get("score_summary") or {}
        if summary.get("mean") is None:
            raise ValueError("Для построения графика недостаточно данных в сохраненном результате.")
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.axis("off")
        ax.text(0.5, 0.6, f"{summary.get('mean'):.2f}", ha="center", va="center", fontsize=32)
        ax.text(0.5, 0.35, "Среднее значение индекса", ha="center", va="center")
        return figure_to_png(fig)
    rows = result.get("distribution") or result.get("score_distribution") or []
    if not rows:
        raise ValueError("Scale index score distribution is not available.")
    labels = [item.get("label") for item in rows]
    values = [_numeric(item.get("count")) or 0 for item in rows]
    return _bar_chart(labels, values, "Scale score distribution", "Responses")


