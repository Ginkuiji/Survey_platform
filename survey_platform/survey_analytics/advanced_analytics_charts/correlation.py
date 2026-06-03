from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def build_correlation_chart(report, config, result, chart_type):
    specs = config.get("variables") or _question_specs(report.survey_id, config.get("questionIds"), "correlation")
    if len(specs) < 2:
        raise ValueError("Correlation chart requires at least two variables.")
    dataset = build_analysis_dataset(report.survey_id, specs)
    if chart_type in {"network", "correlation_network"}:
        raise ValueError("Сетевой граф корреляций доступен в JSON-результате отчета; PNG-визуализация для него пока не поддерживается.")
    if chart_type in {"heatmap", "correlation_heatmap"}:
        matrix = result.get("matrix")
        labels = [item.get("label") or item.get("code") for item in result.get("variables", [])]
        if not matrix or not labels:
            raise ValueError("Correlation matrix is not available for heatmap.")
        return _matrix_heatmap(matrix, labels, labels, "Correlation heatmap", vmin=-1, vmax=1, cmap="coolwarm")

    if len(dataset.variables) == 2:
        left, right = dataset.variables
        pairs = clean_numeric_pairs(get_column(dataset.rows, left.code), get_column(dataset.rows, right.code))
        if not pairs:
            raise ValueError("Not enough numeric pairs for correlation scatter plot.")
        x_values, y_values = map(list, zip(*pairs))
        is_ranked = chart_type in {"ranked_scatterplot", "ranked_scatter_plot"}
        if is_ranked:
            x_values = _rank_values(x_values)
            y_values = _rank_values(y_values)
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(x_values, y_values, alpha=0.72)
        trend = _linear_trend(x_values, y_values)
        if trend:
            slope, intercept = trend
            x_min, x_max = min(x_values), max(x_values)
            ax.plot([x_min, x_max], [intercept + slope * x_min, intercept + slope * x_max], color="#d62728", label="Trend line")
            ax.legend()
        ax.set_xlabel(_truncate(left.label))
        ax.set_ylabel(_truncate(right.label))
        coefficient = (result.get("matrix") or [[None, None], [None, None]])[0][1]
        p_value = (result.get("p_values") or [[None, None], [None, None]])[0][1]
        n = (result.get("n_matrix") or [[None, None], [None, None]])[0][1]
        title = "Ranked correlation scatter plot" if is_ranked else "Correlation scatter plot"
        ax.set_title(f"{title}\nr={_numeric(coefficient)}, p={_numeric(p_value)}, n={n}")
        ax.grid(alpha=0.25)
        return figure_to_png(fig)

    if chart_type in {"scatterplot", "correlation_scatterplot", "ranked_scatterplot", "ranked_scatter_plot"}:
        raise ValueError("Scatter plot requires exactly two expanded correlation variables.")
    matrix = result.get("matrix")
    labels = [item.get("label") or item.get("code") for item in result.get("variables", [])]
    if not matrix or not labels:
        raise ValueError("Correlation matrix is not available for heatmap.")
    return _matrix_heatmap(matrix, labels, labels, "Correlation heatmap", vmin=-1, vmax=1, cmap="coolwarm")


