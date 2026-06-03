from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
MAX_DIAGNOSTIC_POINTS = 500


def _complete_regression_cases(rows, target_code, feature_codes):
    y_values = []
    x_values = []
    response_ids = []
    for row in rows:
        values = [row.get(target_code)] + [row.get(code) for code in feature_codes]
        if all(_is_numeric(value) for value in values):
            y_values.append(_as_float(values[0]))
            x_values.append([_as_float(value) for value in values[1:]])
            response_ids.append(row.get("response_id"))
    return response_ids, y_values, x_values


def _diagnostic_sample(items, notes):
    if len(items) <= MAX_DIAGNOSTIC_POINTS:
        return items
    notes.append("Для диагностических графиков сохранена ограниченная выборка наблюдений.")
    indexes = np.linspace(0, len(items) - 1, MAX_DIAGNOSTIC_POINTS, dtype=int)
    return [items[index] for index in indexes]


def _numeric_summary(values):
    if not len(values):
        return {}
    q1, median_value, q3 = (float(np.percentile(values, percentile)) for percentile in (25, 50, 75))
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outliers_count = int(np.sum((values < lower_fence) | (values > upper_fence)))
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=1)) if len(values) > 1 else None,
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "q1": q1,
        "median": median_value,
        "q3": q3,
        "iqr": iqr,
        "outliers_count": outliers_count,
        "outliers_rate": round(outliers_count / len(values) * 100, 2),
    }


def _vif_diagnostics(x_matrix, feature_codes):
    if len(feature_codes) < 2:
        return {"vif": [], "max_vif": None, "high_vif_variables": [], "notes": ["VIF не рассчитывается для модели с одним предиктором."]}
    items = []
    for index, name in enumerate(feature_codes):
        target = x_matrix[:, index]
        predictors = np.delete(x_matrix, index, axis=1)
        predictors = np.column_stack([np.ones(len(predictors)), predictors])
        coefficients, _, _, _ = np.linalg.lstsq(predictors, target, rcond=None)
        residual = target - predictors @ coefficients
        total = float(np.sum((target - np.mean(target)) ** 2))
        r2 = 1 - float(np.sum(residual ** 2)) / total if total else 1
        vif = None if r2 >= 1 else float(1 / (1 - r2))
        if vif is None:
            interpretation = "Не удалось рассчитать"
        elif vif < 5:
            interpretation = "Приемлемый уровень"
        elif vif < 10:
            interpretation = "Возможная мультиколлинеарность"
        else:
            interpretation = "Выраженная мультиколлинеарность"
        items.append({"name": name, "vif": vif, "interpretation": interpretation})
    valid = [item["vif"] for item in items if item["vif"] is not None]
    return {
        "vif": items,
        "max_vif": max(valid) if valid else None,
        "high_vif_variables": [item["name"] for item in items if item["vif"] is None or item["vif"] >= 5],
        "notes": [],
    }


def _residual_normality(residuals):
    if stats is None or len(residuals) < 3:
        return {"method": None, "statistic": None, "p_value": None, "likely_normal": None, "interpretation": "Проверка нормальности остатков недоступна."}
    result = stats.shapiro(residuals) if len(residuals) <= 5000 else stats.normaltest(residuals)
    p_value = _finite_or_none(result.pvalue)
    return {
        "method": "shapiro" if len(residuals) <= 5000 else "dagostino_k2",
        "statistic": _finite_or_none(result.statistic),
        "p_value": p_value,
        "likely_normal": p_value is not None and p_value >= 0.05,
        "interpretation": "Распределение остатков не показывает заметного отклонения от нормального." if p_value is not None and p_value >= 0.05 else "Распределение остатков может отличаться от нормального.",
    }


def _heteroscedasticity_diagnostics(predicted, residuals):
    if len(predicted) < 2 or float(np.std(predicted)) == 0 or float(np.std(np.abs(residuals))) == 0:
        correlation = None
    else:
        correlation = float(np.corrcoef(predicted, np.abs(residuals))[0, 1])
    warning = correlation is not None and abs(correlation) >= 0.3
    return {
        "method": "correlation_abs_residuals_predicted",
        "correlation": correlation,
        "warning": warning,
        "interpretation": "Разброс остатков может зависеть от предсказанного значения." if warning else "Явных признаков зависимости разброса остатков от предсказанных значений не обнаружено.",
    }


def compute_linear_regression(rows, target_code, feature_codes, include_intercept=True) -> dict:
    if not feature_codes:
        raise ValueError("Для линейной регрессии требуется хотя бы один предиктор.")
    if np is None:
        raise ValueError("Для линейной регрессии требуется установленный пакет numpy.")

    response_ids, y_values, x_values = _complete_regression_cases(rows, target_code, feature_codes)
    n = len(y_values)
    feature_count = len(feature_codes)
    parameter_count = feature_count + (1 if include_intercept else 0)

    if n <= parameter_count:
        raise ValueError("Недостаточно полных наблюдений для линейной регрессии.")

    x_matrix = np.array(x_values, dtype=float)
    if include_intercept:
        x_matrix = np.column_stack([np.ones(n), x_matrix])
    y_vector = np.array(y_values, dtype=float)

    warnings = []
    notes = []
    coefficients, _, rank, _ = np.linalg.lstsq(x_matrix, y_vector, rcond=None)
    if rank < parameter_count:
        warnings.append("Матрица признаков близка к вырожденной; стандартные ошибки и p-value могут быть нестабильными.")

    predicted = x_matrix @ coefficients
    residual_sum_squares = float(np.sum((y_vector - predicted) ** 2))
    total_sum_squares = float(np.sum((y_vector - np.mean(y_vector)) ** 2))
    r2 = 1.0 if total_sum_squares == 0 else 1 - residual_sum_squares / total_sum_squares
    degrees_of_freedom = n - parameter_count
    adjusted_r2 = 1 - (1 - r2) * (n - 1) / degrees_of_freedom if degrees_of_freedom > 0 else None
    residuals = y_vector - predicted
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mae = float(np.mean(np.abs(residuals)))
    residual_standard_error = float(np.sqrt(residual_sum_squares / degrees_of_freedom)) if degrees_of_freedom > 0 else None
    inverse_xtx = np.linalg.pinv(x_matrix.T @ x_matrix)
    covariance = inverse_xtx * (residual_sum_squares / degrees_of_freedom)
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0))
    critical = float(stats.t.ppf(0.975, degrees_of_freedom)) if stats is not None else 1.96
    if stats is None:
        warnings.append("Пакет scipy недоступен; p-value коэффициентов линейной регрессии не рассчитаны.")
    feature_matrix = np.array(x_values, dtype=float)
    target_std = float(np.std(y_vector, ddof=1))

    names = ["intercept"] + feature_codes if include_intercept else feature_codes
    coefficient_items = []
    for index, (name, value) in enumerate(zip(names, coefficients)):
        standard_error = float(standard_errors[index])
        t_statistic = float(value / standard_error) if standard_error else None
        p_value = float(2 * stats.t.sf(abs(t_statistic), degrees_of_freedom)) if stats is not None and t_statistic is not None else None
        feature_index = index - 1 if include_intercept else index
        standardized = None
        if name != "intercept" and target_std:
            feature_std = float(np.std(feature_matrix[:, feature_index], ddof=1))
            standardized = float(value * feature_std / target_std) if feature_std else None
        direction = "увеличивается" if value > 0 else "уменьшается"
        interpretation = "Свободный член модели." if name == "intercept" else f"При увеличении переменной на одну единицу целевая переменная в среднем {direction} на {abs(float(value)):.4f} при прочих равных условиях."
        coefficient_items.append({
            "name": name,
            "value": float(value),
            "standard_error": standard_error,
            "t_statistic": t_statistic,
            "p_value": p_value,
            "confidence_interval_95": {"low": float(value - critical * standard_error), "high": float(value + critical * standard_error)},
            "standardized_coefficient": standardized,
            "interpretation": interpretation,
        })
    observed_vs_predicted = [
        {"response_id": response_id, "observed": float(observed), "predicted": float(prediction), "residual": float(residual)}
        for response_id, observed, prediction, residual in zip(response_ids, y_vector, predicted, residuals)
    ]
    sampled_points = _diagnostic_sample(observed_vs_predicted, notes)
    residual_summary = _numeric_summary(residuals)
    normality = _residual_normality(residuals)
    heteroscedasticity = _heteroscedasticity_diagnostics(predicted, residuals)
    leverage = np.diag(x_matrix @ inverse_xtx @ x_matrix.T)
    standardized_residuals = residuals / (residual_standard_error * np.sqrt(np.maximum(1 - leverage, 1e-12))) if residual_standard_error else np.full(n, np.nan)
    cooks_distance = standardized_residuals ** 2 * leverage / (parameter_count * np.maximum(1 - leverage, 1e-12))
    leverage_threshold = 2 * parameter_count / n
    cooks_threshold = 4 / n
    influential = sorted([
        {**point, "standardized_residual": _finite_or_none(std_residual), "leverage": float(item_leverage), "cooks_distance": _finite_or_none(cooks)}
        for point, std_residual, item_leverage, cooks in zip(observed_vs_predicted, standardized_residuals, leverage, cooks_distance)
    ], key=lambda item: item.get("cooks_distance") or 0, reverse=True)
    multicollinearity = _vif_diagnostics(feature_matrix, feature_codes)
    if residual_summary.get("outliers_rate", 0) >= 5:
        warnings.append("Обнаружены выбросы по остаткам; отдельные наблюдения могут заметно влиять на модель.")
    if abs(residual_summary.get("mean", 0)) > max((residual_summary.get("std") or 0) * 0.1, 1e-9):
        warnings.append("Среднее остатков заметно отличается от нуля; модель может быть смещена.")
    if normality.get("likely_normal") is False:
        warnings.append("Остатки модели могут отличаться от нормального распределения; p-value коэффициентов следует интерпретировать осторожно.")
    if heteroscedasticity["warning"]:
        warnings.append("Обнаружены признаки неоднородности дисперсии остатков; стандартные ошибки и p-value могут быть нестабильными.")
    if multicollinearity["high_vif_variables"]:
        warnings.append("Обнаружена возможная мультиколлинеарность между предикторами; коэффициенты модели могут быть нестабильными.")
    if any(item["leverage"] > leverage_threshold or (item["cooks_distance"] or 0) > cooks_threshold for item in influential):
        warnings.append("Обнаружены потенциально влияющие наблюдения; рекомендуется проверить выбросы и качество ответов.")
    if r2 < 0.1:
        warnings.append("R² низкий; модель объясняет небольшую долю вариации целевой переменной.")
    return {
        "model": "linear",
        "target": target_code,
        "features": feature_codes,
        "coefficients": coefficient_items,
        "feature_count": feature_count,
        "include_intercept": include_intercept,
        "r2": float(r2),
        "adjusted_r2": float(adjusted_r2) if adjusted_r2 is not None else None,
        "rmse": rmse,
        "mae": mae,
        "residual_standard_error": residual_standard_error,
        "degrees_of_freedom": degrees_of_freedom,
        "diagnostics": {
            "residuals": [float(value) for value in residuals[:MAX_DIAGNOSTIC_POINTS]],
            "predictions": [float(value) for value in predicted[:MAX_DIAGNOSTIC_POINTS]],
            "observed_vs_predicted": sampled_points,
            "residual_summary": residual_summary,
            "normality": normality,
            "heteroscedasticity": heteroscedasticity,
            "multicollinearity": multicollinearity,
            "influential_points": {
                "high_leverage_count": sum(item["leverage"] > leverage_threshold for item in influential),
                "large_cooks_distance_count": sum((item["cooks_distance"] or 0) > cooks_threshold for item in influential),
                "thresholds": {"leverage": leverage_threshold, "cooks_distance": cooks_threshold},
                "top_points": influential[:10],
            },
        },
        "n": n,
        "warnings": warnings,
        "notes": notes,
    }


def _complete_logistic_cases(rows, target_code, feature_codes):
    y_values = []
    x_values = []
    response_ids = []

    for row in rows:
        values = [row.get(target_code)] + [row.get(code) for code in feature_codes]
        if any(_is_missing(value) for value in values):
            continue
        if not all(_is_numeric(value) for value in values):
            raise ValueError("Для логистической регрессии зависимая переменная и предикторы должны быть числовыми.")

        y_values.append(_as_float(values[0]))
        x_values.append([_as_float(value) for value in values[1:]])
        response_ids.append(row.get("response_id"))

    return response_ids, y_values, x_values


def _sigmoid(values):
    clipped = np.clip(values, -500, 500)
    return 1 / (1 + np.exp(-clipped))


def _safe_odds_ratio(coefficient):
    try:
        value = math.exp(float(coefficient))
    except (OverflowError, TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


def _interpret_odds_ratio(value):
    if value is None:
        return "—"
    if value > 1:
        return "Увеличивает шансы события"
    if value < 1:
        return "Уменьшает шансы события"
    return "Не меняет шансы события"


def _fit_sklearn_logistic(
    x_matrix,
    y_vector,
    include_intercept,
    max_iter,
    regularization,
    lambda_,
):
    from sklearn.linear_model import LogisticRegression

    if regularization == "l2":
        model = LogisticRegression(
            penalty="l2",
            C=(1 / lambda_) if lambda_ > 0 else 1e12,
            fit_intercept=include_intercept,
            max_iter=max_iter,
            solver="lbfgs",
        )
        model.fit(x_matrix, y_vector)
    else:
        try:
            model = LogisticRegression(
                penalty=None,
                fit_intercept=include_intercept,
                max_iter=max_iter,
                solver="lbfgs",
            )
            model.fit(x_matrix, y_vector)
        except (TypeError, ValueError):
            model = LogisticRegression(
                penalty="none",
                fit_intercept=include_intercept,
                max_iter=max_iter,
                solver="lbfgs",
            )
            model.fit(x_matrix, y_vector)

    coefficient_values = []
    if include_intercept:
        coefficient_values.append(float(model.intercept_[0]))
    coefficient_values.extend(float(value) for value in model.coef_[0])
    probabilities = model.predict_proba(x_matrix)[:, 1]
    return coefficient_values, probabilities


def _fit_numpy_logistic(
    x_matrix,
    y_vector,
    include_intercept,
    max_iter,
    learning_rate,
    regularization,
    lambda_,
):
    n = x_matrix.shape[0]
    design_matrix = x_matrix
    if include_intercept:
        design_matrix = np.column_stack([np.ones(n), x_matrix])

    beta = np.zeros(design_matrix.shape[1], dtype=float)
    for _ in range(max_iter):
        probabilities = _sigmoid(design_matrix @ beta)
        gradient = (design_matrix.T @ (probabilities - y_vector)) / n
        if regularization == "l2" and lambda_ > 0:
            penalty = (lambda_ * beta) / n
            if include_intercept:
                penalty[0] = 0.0
            gradient = gradient + penalty

        beta -= learning_rate * gradient
        if float(np.linalg.norm(gradient)) < 1e-6:
            break

    return [float(value) for value in beta], _sigmoid(design_matrix @ beta)


def _classification_metrics(actual, probabilities, threshold):
    predicted = probabilities >= threshold
    tp = int(np.sum((predicted == 1) & (actual == 1)))
    tn = int(np.sum((predicted == 0) & (actual == 0)))
    fp = int(np.sum((predicted == 1) & (actual == 0)))
    fn = int(np.sum((predicted == 0) & (actual == 1)))
    accuracy = (tp + tn) / len(actual)
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    specificity = tn / (tn + fp) if (tn + fp) else None
    f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and (precision + recall) else None
    balanced_accuracy = (recall + specificity) / 2 if recall is not None and specificity is not None else None
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy),
        "precision": float(precision) if precision is not None else None,
        "recall": float(recall) if recall is not None else None,
        "specificity": float(specificity) if specificity is not None else None,
        "f1": float(f1) if f1 is not None else None,
        "balanced_accuracy": float(balanced_accuracy) if balanced_accuracy is not None else None,
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


def _roc_curve_points(actual, probabilities):
    thresholds = sorted({1.0, 0.0, *[float(value) for value in probabilities]}, reverse=True)
    points = []
    positives = int(np.sum(actual == 1))
    negatives = int(np.sum(actual == 0))
    for threshold in thresholds:
        predicted = probabilities >= threshold
        tp = int(np.sum((predicted == 1) & (actual == 1)))
        fp = int(np.sum((predicted == 1) & (actual == 0)))
        points.append({"threshold": threshold, "tpr": tp / positives if positives else None, "fpr": fp / negatives if negatives else None})
    points.sort(key=lambda item: (item["fpr"], item["tpr"]))
    auc = float(np.trapezoid([item["tpr"] for item in points], [item["fpr"] for item in points])) if points else None
    return points, auc


def _calibration_bins(actual, probabilities, bins_count=10):
    bins = []
    for index in range(bins_count):
        low = index / bins_count
        high = (index + 1) / bins_count
        mask = (probabilities >= low) & ((probabilities < high) | ((index == bins_count - 1) & (probabilities <= high)))
        if not np.any(mask):
            continue
        bins.append({
            "low": low,
            "high": high,
            "n": int(np.sum(mask)),
            "mean_predicted_probability": float(np.mean(probabilities[mask])),
            "observed_event_rate": float(np.mean(actual[mask])),
        })
    return bins


def compute_logistic_regression(
    rows,
    target_code,
    feature_codes,
    include_intercept=True,
    threshold=0.5,
    max_iter=1000,
    learning_rate=0.1,
    regularization="l2",
    lambda_=0.01,
) -> dict:
    if np is None:
        raise ValueError("Для логистической регрессии требуется установленный пакет numpy.")
    if not feature_codes:
        raise ValueError("Для логистической регрессии требуется хотя бы один предиктор.")
    if regularization not in ("none", "l2"):
        raise ValueError("Параметр regularization должен быть 'none' или 'l2'.")

    response_ids, y_values, x_values = _complete_logistic_cases(rows, target_code, feature_codes)
    n = len(y_values)
    feature_count = len(feature_codes)
    parameter_count = feature_count + (1 if include_intercept else 0)
    if n <= parameter_count:
        raise ValueError("Недостаточно полных наблюдений для логистической регрессии.")

    unique_y = sorted(set(y_values))
    if unique_y != [0.0, 1.0]:
        raise ValueError("Зависимая переменная логистической регрессии должна быть бинарной (0/1) и содержать оба класса.")

    x_matrix = np.array(x_values, dtype=float)
    y_vector = np.array(y_values, dtype=float)
    if not np.all(np.isfinite(x_matrix)) or not np.all(np.isfinite(y_vector)):
        raise ValueError("Данные логистической регрессии содержат некорректные числовые значения.")

    feature_std = np.std(x_matrix, axis=0, ddof=1)
    zero_variance_indexes = np.where(feature_std == 0)[0]
    if len(zero_variance_indexes):
        labels = [feature_codes[index] for index in zero_variance_indexes]
        raise ValueError(f"Логистическая регрессия не может использовать предикторы с нулевой дисперсией: {', '.join(labels)}.")

    warnings = []
    try:
        coefficient_values, probabilities = _fit_sklearn_logistic(
            x_matrix,
            y_vector,
            include_intercept,
            max_iter,
            regularization,
            lambda_,
        )
        method = "sklearn_logistic_regression"
    except ImportError:
        coefficient_values, probabilities = _fit_numpy_logistic(
            x_matrix,
            y_vector,
            include_intercept,
            max_iter,
            learning_rate,
            regularization,
            lambda_,
        )
        method = "numpy_logistic_regression"
        warnings.append("Пакет sklearn не установлен; использован резервный расчет градиентным спуском на numpy.")

    probabilities = np.array(probabilities, dtype=float)
    actual = y_vector.astype(int)
    selected_metrics = _classification_metrics(actual, probabilities, threshold)

    eps = 1e-15
    clipped_probabilities = np.clip(probabilities, eps, 1 - eps)
    log_loss_model = float(-np.sum(y_vector * np.log(clipped_probabilities) + (1 - y_vector) * np.log(1 - clipped_probabilities)))
    base_rate = float(np.mean(y_vector))
    null_probabilities = np.clip(np.full(n, base_rate), eps, 1 - eps)
    log_loss_null = float(-np.sum(y_vector * np.log(null_probabilities) + (1 - y_vector) * np.log(1 - null_probabilities)))
    pseudo_r2 = 1 - (log_loss_model / log_loss_null) if log_loss_null > 0 else None
    roc_curve, roc_auc = _roc_curve_points(actual, probabilities)
    threshold_analysis = [_classification_metrics(actual, probabilities, value) for value in np.linspace(0.1, 0.9, 9)]
    brier_score = float(np.mean((probabilities - y_vector) ** 2))
    design_matrix = np.column_stack([np.ones(n), x_matrix]) if include_intercept else x_matrix
    weights = probabilities * (1 - probabilities)
    information = design_matrix.T @ (design_matrix * weights[:, None])
    if regularization == "l2" and lambda_ > 0:
        penalty = np.eye(information.shape[0]) * lambda_
        if include_intercept:
            penalty[0, 0] = 0
        information = information + penalty
    covariance = np.linalg.pinv(information)
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0))
    multicollinearity = _vif_diagnostics(x_matrix, feature_codes)
    positive_class_count = int(np.sum(actual == 1))
    negative_class_count = int(np.sum(actual == 0))
    minority_rate = min(positive_class_count, negative_class_count) / n * 100
    events_per_variable = min(positive_class_count, negative_class_count) / feature_count

    names = ["intercept"] + feature_codes if include_intercept else feature_codes
    coefficients = []
    for index, (name, coefficient) in enumerate(zip(names, coefficient_values)):
        odds_ratio = _safe_odds_ratio(coefficient)
        standard_error = float(standard_errors[index])
        z_statistic = float(coefficient / standard_error) if standard_error else None
        p_value = float(2 * stats.norm.sf(abs(z_statistic))) if stats is not None and z_statistic is not None else None
        low = float(coefficient - 1.96 * standard_error)
        high = float(coefficient + 1.96 * standard_error)
        coefficients.append({
            "name": name,
            "coefficient": float(coefficient),
            "standard_error": standard_error,
            "z_statistic": z_statistic,
            "p_value": p_value,
            "confidence_interval_95": {"low": low, "high": high},
            "odds_ratio": odds_ratio,
            "odds_ratio_confidence_interval_95": {"low": _safe_odds_ratio(low), "high": _safe_odds_ratio(high)},
            "interpretation": _interpret_odds_ratio(odds_ratio),
        })
    notes = []
    if regularization != "none":
        notes.append("Стандартные ошибки и p-value коэффициентов регуляризованной логистической регрессии являются приближенными.")
    if multicollinearity["high_vif_variables"]:
        warnings.append("Обнаружена возможная мультиколлинеарность между предикторами; коэффициенты модели могут быть нестабильными.")
    if minority_rate < 10:
        warnings.append("Целевая переменная сильно несбалансирована; accuracy может быть малоинформативной.")
    if events_per_variable < 10:
        warnings.append("Для логистической регрессии мало событий на один предиктор; коэффициенты могут быть нестабильными.")
    if roc_auc is not None and roc_auc < 0.7:
        warnings.append("ROC-AUC низкий; модель слабо различает классы.")
    if (selected_metrics["precision"] is not None and selected_metrics["precision"] < 0.5) or (selected_metrics["recall"] is not None and selected_metrics["recall"] < 0.5):
        warnings.append("Precision или recall низкие; модель может плохо находить один из классов.")
    prediction_items = [
        {
            "response_id": response_id,
            "actual": int(actual_value),
            "probability": float(probability),
            "predicted": int(probability >= threshold),
        }
        for response_id, actual_value, probability in zip(response_ids, actual, probabilities)
    ]
    prediction_items = _diagnostic_sample(prediction_items, notes)

    return {
        "model": "logistic",
        "method": method,
        "target": target_code,
        "features": feature_codes,
        "include_intercept": include_intercept,
        "threshold": threshold,
        "regularization": regularization,
        "lambda_": lambda_,
        "coefficients": coefficients,
        "n": n,
        "feature_count": feature_count,
        "positive_class_count": positive_class_count,
        "negative_class_count": negative_class_count,
        "base_rate": base_rate,
        "class_balance": {
            "positive_rate": round(positive_class_count / n * 100, 2),
            "negative_rate": round(negative_class_count / n * 100, 2),
            "minority_class_rate": round(minority_rate, 2),
            "is_imbalanced": minority_rate < 10,
        },
        "metrics": {
            **{key: selected_metrics[key] for key in ("accuracy", "precision", "recall", "specificity", "f1", "balanced_accuracy")},
            "roc_auc": roc_auc,
            "log_loss": log_loss_model,
            "null_log_loss": log_loss_null,
            "brier_score": brier_score,
            "mcfadden_r2": float(pseudo_r2) if pseudo_r2 is not None else None,
        },
        "confusion_matrix": selected_metrics["confusion_matrix"],
        "roc_curve": roc_curve,
        "threshold_analysis": threshold_analysis,
        "predictions": prediction_items,
        "diagnostics": {
            "multicollinearity": multicollinearity,
            "events_per_variable": events_per_variable,
            "calibration": {"bins": _calibration_bins(actual, probabilities), "brier_score": brier_score},
        },
        "warnings": warnings,
        "notes": notes,
    }


