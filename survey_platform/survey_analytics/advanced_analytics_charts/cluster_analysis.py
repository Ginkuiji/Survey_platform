from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def build_cluster_analysis_chart(report, config, result, chart_type):
    if chart_type in {"profile_heatmap", "cluster_profile_heatmap"}:
        rows = (result.get("profile_heatmap") or {}).get("rows") or []
        if not rows:
            raise ValueError("Профили кластеров недоступны для построения графика.")
        variables = rows[0].get("values") or []
        matrix = [[_numeric(item.get("standardized_value")) or 0 for item in row.get("values") or []] for row in rows]
        return _matrix_heatmap(matrix, [_truncate(item.get("label") or item.get("code"), 18) for item in variables], [row.get("cluster_label") for row in rows], "Профили кластеров", cmap="coolwarm")
    if chart_type in {"pca_scatter", "cluster_pca_scatterplot"}:
        points = (result.get("dimension_reduction") or {}).get("points") or []
        if not points:
            raise ValueError("Для двумерной визуализации кластеров недостаточно данных.")
        fig, ax = plt.subplots(figsize=(7, 5))
        for cluster in sorted(set(item.get("cluster") for item in points)):
            selected = [item for item in points if item.get("cluster") == cluster]
            ax.scatter([item.get("x") for item in selected], [item.get("y") for item in selected], label=f"Кластер {cluster}", alpha=0.6)
        ax.set_title("PCA-проекция кластеров")
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.legend()
        ax.grid(alpha=0.25)
        return figure_to_png(fig)
    if chart_type in {"silhouette", "silhouette_plot"}:
        rows = (result.get("silhouette") or {}).get("cluster_summary") or []
        if not rows:
            raise ValueError("Silhouette plot недоступен для этого результата.")
        return _bar_chart([item.get("label") for item in rows], [_numeric(item.get("mean_silhouette")) or 0 for item in rows], "Средний silhouette по кластерам", "Silhouette")
    if chart_type in {"elbow", "elbow_plot"}:
        points = (result.get("elbow") or {}).get("points") or []
        if not points:
            raise ValueError("Elbow plot недоступен для этого результата.")
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.plot([item.get("k") for item in points], [item.get("inertia") for item in points], marker="o")
        ax.set_title("Elbow plot")
        ax.set_xlabel("Число кластеров")
        ax.set_ylabel("Inertia")
        ax.grid(alpha=0.25)
        return figure_to_png(fig)
    if chart_type in {"distances", "cluster_distances"}:
        rows = (result.get("cluster_distances") or {}).get("summary") or []
        if not rows:
            raise ValueError("Расстояния до центроидов недоступны.")
        return _bar_chart([item.get("label") for item in rows], [_numeric(item.get("mean_distance_to_centroid")) or 0 for item in rows], "Расстояния до центроидов", "Среднее расстояние")
    if chart_type == "radar":
        raise ValueError("Radar chart пока недоступен для серверного построения.")
    clusters = result.get("clusters") or result.get("cluster_sizes") or []
    if not clusters:
        raise ValueError("Cluster sizes are not available for chart.")
    labels = [f"Cluster {item.get('cluster')}" for item in clusters]
    values = [_numeric(item.get("size")) if item.get("size") is not None else _numeric(item.get("count")) or 0 for item in clusters]
    return _bar_chart(labels, values, "Cluster sizes", "Responses")


