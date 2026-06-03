from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def build_regression_chart(report, config, result, chart_type):
    target_spec = config.get("target") or _single_spec(report.survey_id, config.get("targetQuestionId"), "regression", "target")
    feature_specs = config.get("features") or _question_specs(report.survey_id, config.get("featureQuestionIds"), "regression", "feature")
    if not feature_specs:
        raise ValueError("Regression chart requires at least one feature.")
    dataset = build_analysis_dataset(report.survey_id, [target_spec, *feature_specs])
    target_variable = _find_variable_by_question(dataset, target_spec["question_id"])
    feature_variables = [variable for variable in dataset.variables if variable.code != target_variable.code]
    diagnostics = result.get("diagnostics") or {}
    points = diagnostics.get("observed_vs_predicted") or []
    if chart_type in {"observed_vs_predicted", "residual_plot"}:
        if not points:
            raise ValueError("Для построения графика недостаточно данных в сохраненном результате.")
        fig, ax = plt.subplots(figsize=(7, 5))
        if chart_type == "residual_plot":
            ax.scatter([item.get("predicted") for item in points], [item.get("residual") for item in points], alpha=0.72)
            ax.axhline(0, color="#666", linestyle="--")
            ax.set_xlabel("Предсказанное значение")
            ax.set_ylabel("Остаток")
            ax.set_title("График остатков")
        else:
            ax.scatter([item.get("observed") for item in points], [item.get("predicted") for item in points], alpha=0.72)
            ax.set_xlabel("Наблюдаемое значение")
            ax.set_ylabel("Предсказанное значение")
            ax.set_title("Наблюдаемые и предсказанные значения")
        ax.grid(alpha=0.25)
        return figure_to_png(fig)
    if chart_type == "residual_histogram":
        residuals = diagnostics.get("residuals") or []
        if not residuals:
            raise ValueError("Для построения графика недостаточно данных в сохраненном результате.")
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.hist(residuals, bins=12, color="#1f77b4", edgecolor="white")
        ax.set_title("Распределение остатков")
        return figure_to_png(fig)
    if chart_type in {"coefficients", "regression_coefficients", "coefficient_ci", "coefficient_confidence_intervals"}:
        coefficients = [item for item in result.get("coefficients", []) if item.get("name") != "intercept"]
        if not coefficients:
            raise ValueError("Для построения графика недостаточно данных в сохраненном результате.")
        labels = [_truncate(result.get("variables_by_code", {}).get(item.get("name"), {}).get("label") or item.get("name")) for item in coefficients]
        values = [_numeric(item.get("value")) or 0 for item in coefficients]
        if chart_type in {"coefficient_ci", "coefficient_confidence_intervals"}:
            if any(not item.get("confidence_interval_95") for item in coefficients):
                raise ValueError("Для построения графика недостаточно данных в сохраненном результате.")
            errors = [[value - item["confidence_interval_95"]["low"] for value, item in zip(values, coefficients)], [item["confidence_interval_95"]["high"] - value for value, item in zip(values, coefficients)]]
            fig, ax = plt.subplots(figsize=(max(7, len(labels) * 0.7), 5))
            ax.bar(range(len(values)), values, color="#1f77b4")
            ax.errorbar(range(len(values)), values, yerr=errors, fmt="none", ecolor="#222", capsize=4)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=30, ha="right")
            ax.set_title("Доверительные интервалы коэффициентов")
            return figure_to_png(fig)
        return _bar_chart(labels, values, "Коэффициенты регрессии", "Коэффициент")

    if len(feature_variables) == 1:
        feature = feature_variables[0]
        pairs = clean_numeric_pairs(get_column(dataset.rows, feature.code), get_column(dataset.rows, target_variable.code))
        if not pairs:
            raise ValueError("Not enough numeric pairs for regression scatter plot.")
        x_values, y_values = zip(*pairs)
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(x_values, y_values, alpha=0.72, label="Observed")
        coefficients = {item.get("name"): item.get("value") for item in result.get("coefficients", [])}
        intercept = _numeric(coefficients.get("intercept")) or 0
        slope = _numeric(coefficients.get(feature.code))
        if slope is not None:
            x_min, x_max = min(x_values), max(x_values)
            ax.plot([x_min, x_max], [intercept + slope * x_min, intercept + slope * x_max], color="#d62728", label="Regression line")
            ax.legend()
        ax.set_xlabel(_truncate(feature.label))
        ax.set_ylabel(_truncate(target_variable.label))
        ax.set_title("Linear regression")
        ax.grid(alpha=0.25)
        return figure_to_png(fig)

    coefficients = [
        (item.get("name"), _numeric(item.get("value")))
        for item in result.get("coefficients", [])
        if item.get("name") != "intercept"
    ]
    coefficients = [(name, value) for name, value in coefficients if value is not None]
    if not coefficients:
        raise ValueError("Regression coefficients are not available.")
    labels = [_truncate(result.get("variables_by_code", {}).get(name, {}).get("label") or name) for name, _ in coefficients]
    values = [value for _, value in coefficients]
    return _bar_chart(labels, values, "Regression coefficients", "Coefficient")


