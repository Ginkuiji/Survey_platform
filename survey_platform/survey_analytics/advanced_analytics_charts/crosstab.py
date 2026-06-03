from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def build_crosstab_chart(report, config, result, chart_type):
    crosstab = result.get("crosstab")
    if not crosstab:
        raise ValueError("Crosstab data is not available for chart.")
    rows = crosstab.get("rows") or []
    if not rows:
        raise ValueError("Crosstab rows are empty.")
    x_labels = [str(column.get("value")) for column in rows[0].get("columns", [])]
    y_labels = [str(row.get("label") or row.get("value")) for row in rows]
    chi_square = result.get("chi_square") or {}
    if chart_type in {"standardized_residual_heatmap", "residual_heatmap"}:
        matrix = chi_square.get("standardized_residuals")
        if not matrix:
            raise ValueError("Стандартизированные остатки недоступны для этого отчета.")
        return _matrix_heatmap(matrix, x_labels, y_labels, "Стандартизированные остатки χ²", vmin=-3, vmax=3, cmap="coolwarm")
    if chart_type == "chi_square_contribution_heatmap":
        matrix = chi_square.get("cell_contributions")
        if not matrix:
            raise ValueError("Вклады ячеек в χ² недоступны для этого отчета.")
        return _matrix_heatmap(matrix, x_labels, y_labels, "Вклад ячеек в χ²", cmap="YlOrRd")
    if chart_type == "mosaic_plot":
        raise ValueError("Mosaic plot пока недоступен для серверного построения.")
    matrix = [[column.get("count", 0) for column in row.get("columns", [])] for row in rows]
    return _matrix_heatmap(matrix, x_labels, y_labels, "Crosstab heatmap", cmap="YlGnBu")


