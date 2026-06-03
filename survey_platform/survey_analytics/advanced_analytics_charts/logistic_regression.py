from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def build_logistic_regression_chart(report, config, result, chart_type):
    if chart_type in {"probabilities", "probability_histogram"}:
        probabilities = [_numeric(item.get("probability")) for item in result.get("predictions", [])]
        probabilities = [value for value in probabilities if value is not None]
        if not probabilities:
            raise ValueError("Predicted probabilities are not available.")
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.hist(probabilities, bins=10, range=(0, 1), color="#1f77b4", edgecolor="white")
        ax.set_title("Predicted probability distribution")
        ax.set_xlabel("Probability")
        ax.set_ylabel("Count")
        return figure_to_png(fig)
    if chart_type in {"odds_ratio", "odds_ratio_forest", "odds_ratio_forest_plot"}:
        coefficients = [item for item in result.get("coefficients", []) if item.get("name") != "intercept" and _numeric(item.get("odds_ratio")) is not None]
        if not coefficients:
            raise ValueError("Для построения графика недостаточно данных в сохраненном результате.")
        labels = [_truncate(result.get("variables_by_code", {}).get(item.get("name"), {}).get("label") or item.get("name")) for item in coefficients]
        values = [_numeric(item.get("odds_ratio")) for item in coefficients]
        fig, ax = plt.subplots(figsize=(max(7, len(labels) * 0.7), 5))
        ax.bar(range(len(values)), values, color="#1f77b4")
        ax.axhline(1, color="#666", linestyle="--")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.set_title("Odds ratio по факторам")
        return figure_to_png(fig)
    if chart_type == "roc_curve":
        points = result.get("roc_curve") or []
        if not points:
            raise ValueError("Для построения графика недостаточно данных в сохраненном результате.")
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.plot([item.get("fpr") for item in points], [item.get("tpr") for item in points])
        ax.plot([0, 1], [0, 1], linestyle="--", color="#666")
        ax.set_title("ROC-кривая")
        ax.set_xlabel("False positive rate")
        ax.set_ylabel("True positive rate")
        return figure_to_png(fig)

    matrix = result.get("confusion_matrix") or {}
    values = [
        [matrix.get("tn", 0), matrix.get("fp", 0)],
        [matrix.get("fn", 0), matrix.get("tp", 0)],
    ]
    return _matrix_heatmap(values, ["Predicted 0", "Predicted 1"], ["Actual 0", "Actual 1"], "Confusion matrix", cmap="Blues")


