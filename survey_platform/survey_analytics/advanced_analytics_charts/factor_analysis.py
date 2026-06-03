from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def build_factor_analysis_chart(report, config, result, chart_type):
    if chart_type in {"loadings", "loadings_heatmap", "factor_loadings_heatmap"}:
        return _factor_loadings_heatmap(result)
    if chart_type in {"parallel_analysis", "parallel_analysis_plot"}:
        components = (result.get("parallel_analysis") or {}).get("components") or []
        if not components:
            raise ValueError("Parallel analysis недоступен для этого результата.")
        labels = [str(item.get("component")) for item in components]
        real = [_numeric(item.get("real_eigenvalue")) or 0 for item in components]
        random_threshold = [_numeric(item.get("random_percentile_eigenvalue")) or 0 for item in components]
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.plot(labels, real, marker="o", label="Реальные eigenvalues")
        ax.plot(labels, random_threshold, marker="o", linestyle="--", label="Случайный порог")
        ax.set_title("Parallel analysis")
        ax.legend()
        ax.grid(alpha=0.25)
        return figure_to_png(fig)
    if chart_type in {"explained_variance", "explained_variance_bar"}:
        explained = result.get("explained_variance") or []
        if not explained:
            raise ValueError("Данные объясненной дисперсии недоступны.")
        labels = [item.get("factor") for item in explained]
        values = [(_numeric(item.get("explained_variance")) if item.get("explained_variance") is not None else _numeric(item.get("value"))) or 0 for item in explained]
        return _bar_chart(labels, values, "Объясненная дисперсия", "Доля дисперсии")
    if chart_type in {"communalities", "communalities_bar"}:
        communalities = result.get("communalities") or []
        if not communalities:
            raise ValueError("Communalities недоступны для этого результата.")
        labels = [_truncate(item.get("label") or item.get("variable"), 20) for item in communalities]
        values = [_numeric(item.get("communality")) or 0 for item in communalities]
        return _bar_chart(labels, values, "Communalities", "Communality")
    if chart_type in {"factor_scores", "factor_score_scatterplot", "biplot", "pca_biplot"}:
        scores = result.get("factor_scores") or []
        points = [
            (
                _numeric(item.get("Фактор 1")) if item.get("Фактор 1") is not None else _numeric((item.get("scores") or [{}, {}])[0].get("value")),
                _numeric(item.get("Фактор 2")) if item.get("Фактор 2") is not None else _numeric((item.get("scores") or [{}, {}])[1].get("value")),
            )
            for item in scores
            if len(item.get("scores") or []) >= 2 or (item.get("Фактор 1") is not None and item.get("Фактор 2") is not None)
        ]
        points = [(x, y) for x, y in points if x is not None and y is not None]
        if not points:
            raise ValueError("Для biplot требуется не менее двух факторов и сохраненные factor scores.")
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter([item[0] for item in points], [item[1] for item in points], alpha=0.55)
        ax.set_xlabel("Фактор 1")
        ax.set_ylabel("Фактор 2")
        ax.set_title("PCA biplot" if chart_type in {"biplot", "pca_biplot"} else "Факторные значения")
        ax.grid(alpha=0.25)
        return figure_to_png(fig)
    scree = result.get("scree") or []
    if scree:
        labels = [str(item.get("component")) for item in scree]
        eigenvalues = [_numeric(item.get("eigenvalue")) for item in scree]
    else:
        eigenvalues = [_numeric(value) for value in result.get("eigenvalues", [])]
        labels = [f"C{index + 1}" for index in range(len(eigenvalues))]
    points = [(label, value) for label, value in zip(labels, eigenvalues) if value is not None]
    if not points:
        return _factor_loadings_heatmap(result)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot([label for label, _ in points], [value for _, value in points], marker="o")
    ax.axhline(1, color="#666", linestyle="--", linewidth=1)
    ax.set_title("Scree plot")
    ax.set_ylabel("Eigenvalue")
    ax.grid(alpha=0.25)
    return figure_to_png(fig)


def _factor_loadings_heatmap(result):
    loadings = result.get("loadings") or []
    if not loadings:
        raise ValueError("Factor analysis data is not available for chart.")
    factors = [item.get("factor") for item in loadings[0].get("factors", [])]
    matrix = []
    labels = []
    for item in loadings:
        by_factor = {factor.get("factor"): _numeric(factor.get("loading")) for factor in item.get("factors", [])}
        matrix.append([by_factor.get(factor) or 0 for factor in factors])
        labels.append(item.get("label") or item.get("variable"))
    return _matrix_heatmap(matrix, factors, labels, "Factor loadings", vmin=-1, vmax=1, cmap="coolwarm")


