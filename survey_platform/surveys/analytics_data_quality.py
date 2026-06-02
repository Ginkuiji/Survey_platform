from collections import defaultdict
from statistics import median

try:
    import numpy as np
except ImportError:  # pragma: no cover - depends on deployment environment
    np = None

from .models import Response


HIGH_MISSING_RATE = 30.0
TOO_FAST_THRESHOLD_SECONDS = 30
VIF_WARNING_THRESHOLD = 5.0


def is_missing(value):
    return value is None or value == ""


def _percent(part, whole):
    return round(part / whole * 100, 2) if whole else 0.0


def _variable_dict(variable):
    return {
        "code": variable.code,
        "label": variable.label,
        "question_id": variable.question_id,
    }


def _dataset_rows(dataset):
    return getattr(dataset, "rows", None) or []


def _dataset_variables(dataset):
    return getattr(dataset, "variables", None) or []


def _infer_analysis_n(analysis_type, result, dataset_size):
    if result.get("n") is not None:
        return result["n"]
    if analysis_type == "scale_index" and result.get("n_scored") is not None:
        return result["n_scored"]
    if analysis_type == "missing_analysis":
        return (result.get("summary") or {}).get("total_completed_normal")
    if analysis_type in ("crosstab", "chi_square"):
        return (result.get("crosstab") or {}).get("total")
    if analysis_type == "correlation":
        pair_counts = [
            value
            for row_index, row in enumerate(result.get("n_matrix") or [])
            for column_index, value in enumerate(row)
            if row_index != column_index and value is not None
        ]
        return min(pair_counts) if pair_counts else dataset_size
    return dataset_size


def _build_survey_quality(result, payload, notes):
    survey = {
        "total_started": None,
        "total_finished": None,
        "total_completed": None,
        "total_screened_out": None,
        "total_active_unfinished": None,
        "completion_rate": None,
        "screenout_rate": None,
        "finish_rate": None,
    }
    time_quality = {
        "too_fast_responses_count": None,
        "too_fast_threshold_seconds": TOO_FAST_THRESHOLD_SECONDS,
        "median_completion_time_seconds": None,
    }
    survey_id = result.get("survey_id") or (payload or {}).get("survey_id")
    if not survey_id:
        notes.append("Сводные показатели опроса недоступны: не указан идентификатор опроса.")
        return survey, time_quality

    try:
        started = list(Response.objects.filter(survey_id=survey_id, status="active"))
    except Exception:  # pragma: no cover - protects analytics if optional quality query fails
        notes.append("Сводные показатели опроса временно недоступны.")
        return survey, time_quality

    completed = [
        response for response in started
        if response.is_complete and not response.screened_out and response.complete_reason == "completed"
    ]
    finished = [response for response in started if response.finished_at is not None]
    screened_out = [response for response in started if response.is_complete and response.screened_out]
    active_unfinished = [
        response for response in started
        if not response.is_complete and response.finished_at is None
    ]
    survey.update({
        "total_started": len(started),
        "total_finished": len(finished),
        "total_completed": len(completed),
        "total_screened_out": len(screened_out),
        "total_active_unfinished": len(active_unfinished),
        "completion_rate": _percent(len(completed), len(started)),
        "screenout_rate": _percent(len(screened_out), len(started)),
        "finish_rate": _percent(len(finished), len(started)),
    })

    durations = [
        (response.finished_at - response.started_at).total_seconds()
        for response in completed
        if response.started_at and response.finished_at
    ]
    if durations:
        time_quality["too_fast_responses_count"] = sum(
            duration < TOO_FAST_THRESHOLD_SECONDS for duration in durations
        )
        time_quality["median_completion_time_seconds"] = round(median(durations), 2)
    else:
        time_quality["too_fast_responses_count"] = 0
        notes.append("Невозможно оценить слишком быстрые прохождения: отсутствуют данные о времени начала или завершения.")
    return survey, time_quality


def _build_variable_quality(dataset):
    rows = _dataset_rows(dataset)
    variables = _dataset_variables(dataset)
    variable_items = []
    zero_variance = []
    high_missing = []
    question_missing = defaultdict(list)
    question_labels = {}

    for variable in variables:
        values = [row.get(variable.code) for row in rows]
        non_missing_values = [value for value in values if not is_missing(value)]
        missing_count = len(values) - len(non_missing_values)
        missing_rate = _percent(missing_count, len(values))
        item = {
            **_variable_dict(variable),
            "missing_count": missing_count,
            "missing_rate": missing_rate,
            "non_missing_count": len(non_missing_values),
        }
        variable_items.append(item)
        question_missing[variable.question_id].append(missing_rate)
        question_labels.setdefault(variable.question_id, variable.label)
        if missing_rate >= HIGH_MISSING_RATE:
            high_missing.append(item)
        if len(set(non_missing_values)) < 2:
            zero_variance.append({
                **_variable_dict(variable),
                "non_missing_count": len(non_missing_values),
                "unique_values_count": len(set(non_missing_values)),
            })

    high_missing_questions = []
    for question_id, rates in question_missing.items():
        missing_rate = round(sum(rates) / len(rates), 2)
        if missing_rate >= HIGH_MISSING_RATE:
            high_missing_questions.append({
                "question_id": question_id,
                "label": question_labels.get(question_id),
                "missing_rate": missing_rate,
                "variables_count": len(rates),
            })

    row_completeness = []
    if variables:
        for row in rows:
            answered = sum(not is_missing(row.get(variable.code)) for variable in variables)
            row_completeness.append(answered / len(variables))

    return {
        "answers": {
            "average_completeness_rate": round(sum(row_completeness) / len(row_completeness) * 100, 2) if row_completeness else None,
            "high_missing_questions_count": len(high_missing_questions),
            "high_missing_questions": high_missing_questions,
        },
        "variables": {
            "variables_count": len(variables),
            "zero_variance_variables_count": len(zero_variance),
            "zero_variance_variables": zero_variance,
            "high_missing_variables_count": len(high_missing),
            "high_missing_variables": high_missing,
            "items": variable_items,
        },
    }


def compute_vif_for_dataset(rows, feature_codes):
    if np is None or len(feature_codes) < 2:
        return []
    complete_rows = [
        [row.get(code) for code in feature_codes]
        for row in rows
        if all(not is_missing(row.get(code)) for code in feature_codes)
    ]
    try:
        matrix = np.asarray(complete_rows, dtype=float)
    except (TypeError, ValueError):
        return []
    if matrix.shape[0] <= len(feature_codes):
        return []

    result = []
    for index, code in enumerate(feature_codes):
        target = matrix[:, index]
        predictors = np.delete(matrix, index, axis=1)
        if np.var(target) == 0:
            result.append({"code": code, "vif": None})
            continue
        predictors = np.column_stack([np.ones(len(predictors)), predictors])
        coefficients, _, _, _ = np.linalg.lstsq(predictors, target, rcond=None)
        predicted = predictors @ coefficients
        total = np.sum((target - np.mean(target)) ** 2)
        residual = np.sum((target - predicted) ** 2)
        r2 = 1 - residual / total if total else 1
        vif = None if r2 >= 1 else float(1 / (1 - r2))
        result.append({"code": code, "vif": vif})
    return result


def _expected_checks(result):
    chi_square = result.get("chi_square") or {}
    diagnostics = chi_square.get("expected_diagnostics")
    if diagnostics:
        return {
            "expected_cells_count": diagnostics.get("cells_count"),
            "expected_below_5_count": diagnostics.get("below_5_count"),
            "expected_below_5_rate": diagnostics.get("below_5_rate"),
            "expected_below_1_count": diagnostics.get("below_1_count"),
            "min_expected": diagnostics.get("min_expected"),
            "assumption_warning": diagnostics.get("assumption_warning"),
        }
    expected = chi_square.get("expected") or []
    values = [value for row in expected for value in row if value is not None]
    below_five = [value for value in values if value < 5]
    return {
        "expected_cells_count": len(values),
        "expected_below_5_count": len(below_five),
        "expected_below_5_rate": _percent(len(below_five), len(values)),
        "expected_below_1_count": len([value for value in values if value < 1]),
        "min_expected": min(values) if values else None,
    }


def _cluster_sizes(result):
    sizes = []
    for cluster in result.get("clusters") or []:
        size = cluster.get("size", cluster.get("n", cluster.get("count")))
        if size is not None:
            sizes.append(size)
    return sizes


def _method_specific_checks(analysis_type, result, dataset):
    if analysis_type == "chi_square":
        return _expected_checks(result)
    if analysis_type in ("regression", "logistic_regression"):
        features = result.get("features") or []
        vif = compute_vif_for_dataset(_dataset_rows(dataset), features)
        checks = {
            "features_count": len(features),
            "cases_per_feature": round(result.get("n", 0) / len(features), 2) if features else None,
            "vif": vif,
            "high_vif_variables": [item for item in vif if item["vif"] is not None and item["vif"] >= VIF_WARNING_THRESHOLD],
        }
        if analysis_type == "logistic_regression":
            positive = result.get("positive_class_count")
            negative = result.get("negative_class_count")
            n = result.get("n")
            minority = min(positive, negative) if positive is not None and negative is not None else None
            checks.update({
                "positive_class_count": positive,
                "negative_class_count": negative,
                "minority_class_rate": _percent(minority, n) if minority is not None and n else None,
                "events_per_variable": round(minority / len(features), 2) if minority is not None and features else None,
            })
        return checks
    if analysis_type == "factor_analysis":
        kmo = result.get("kmo") or {}
        bartlett = result.get("bartlett") or {}
        n_variables = result.get("n_variables")
        n = result.get("n")
        return {
            "n": n,
            "n_variables": n_variables,
            "cases_per_variable": round(n / n_variables, 2) if n is not None and n_variables else None,
            "kmo_overall": kmo.get("overall"),
            "bartlett_p_value": bartlett.get("p_value"),
            "low_kmo_variables": [
                item for item in (kmo.get("per_variable") or kmo.get("variables") or [])
                if item.get("kmo") is not None and item["kmo"] < 0.6
            ],
            "low_communality_variables": [
                item for item in result.get("communalities") or []
                if item.get("communality") is not None and item["communality"] < 0.3
            ],
            "cross_loading_variables": result.get("cross_loading_variables") or [],
            "weak_variables": result.get("weak_variables") or [],
            "cumulative_explained_variance": result.get("cumulative_explained_variance"),
        }
    if analysis_type == "cluster_analysis":
        sizes = _cluster_sizes(result)
        return {
            "n_clusters": result.get("n_clusters"),
            "silhouette_score": result.get("silhouette_score"),
            "min_cluster_size": min(sizes) if sizes else None,
            "max_cluster_size": max(sizes) if sizes else None,
            "cluster_size_ratio": round(max(sizes) / min(sizes), 2) if sizes and min(sizes) else None,
            "largest_cluster_rate": round(max(sizes) / sum(sizes) * 100, 2) if sizes and sum(sizes) else None,
            "weak_profile_clusters": [
                item for item in result.get("cluster_profiles") or []
                if not item.get("top_distinguishing_features")
            ],
        }
    if analysis_type == "group_comparison":
        sizes = [group.get("n") for group in result.get("groups") or [] if group.get("n") is not None]
        return {
            "groups_count": len(sizes),
            "min_group_size": min(sizes) if sizes else None,
            "max_group_size": max(sizes) if sizes else None,
        }
    if analysis_type == "reliability_analysis":
        return {"n_items": result.get("n_items"), "alpha": result.get("alpha")}
    if analysis_type == "scale_index":
        return {"n_items": result.get("n_items"), "min_answered_items": result.get("min_answered_items")}
    return {}


def build_data_quality_summary(analysis_type, result, payload=None, dataset=None):
    notes = []
    rows = _dataset_rows(dataset)
    dataset_size = result.get("dataset_size")
    if dataset_size is None and dataset is not None:
        dataset_size = len(rows)
    analysis_n = _infer_analysis_n(analysis_type, result, dataset_size)
    excluded_cases = dataset_size - analysis_n if dataset_size is not None and analysis_n is not None else None
    missing_rate = _percent(excluded_cases, dataset_size) if excluded_cases is not None and dataset_size else None
    if analysis_n is None:
        notes.append("Не удалось определить число наблюдений, фактически вошедших в расчет.")

    survey, time_quality = _build_survey_quality(result, payload, notes)
    variable_quality = _build_variable_quality(dataset)
    variables = variable_quality["variables"]
    method_checks = {
        "sample_size_ok": analysis_n is None or analysis_n >= 30,
        "missing_rate_ok": missing_rate is None or missing_rate < HIGH_MISSING_RATE,
        "zero_variance_ok": variables["zero_variance_variables_count"] == 0,
        "method_specific": _method_specific_checks(analysis_type, result, dataset),
    }
    return {
        "survey": survey,
        "dataset": {
            "dataset_size": dataset_size,
            "analysis_n": analysis_n,
            "complete_cases": analysis_n,
            "excluded_cases": excluded_cases,
            "missing_rate": missing_rate,
        },
        "answers": variable_quality["answers"],
        "variables": variables,
        "time": time_quality,
        "method_checks": method_checks,
        "notes": notes,
    }


def _crosstab_shape(result):
    crosstab = result.get("crosstab") or {}
    rows = crosstab.get("rows") or []
    columns = rows[0].get("columns") or [] if rows else []
    return len(rows), len(columns), [
        column.get("count", 0)
        for row in rows
        for column in row.get("columns") or []
    ]


def build_applicability_warnings(analysis_type, result, payload=None, dataset=None, data_quality=None):
    quality = data_quality or {}
    dataset_quality = quality.get("dataset") or {}
    variables = quality.get("variables") or {}
    time_quality = quality.get("time") or {}
    checks = (quality.get("method_checks") or {}).get("method_specific") or {}
    warnings = []

    if dataset_quality.get("analysis_n") is not None and dataset_quality["analysis_n"] < 30:
        warnings.append("Размер выборки меньше 30 наблюдений, результаты следует интерпретировать осторожно.")
    if dataset_quality.get("missing_rate") is not None and dataset_quality["missing_rate"] >= HIGH_MISSING_RATE:
        warnings.append("В анализ не вошла значительная часть наблюдений из-за пропусков.")
    if variables.get("zero_variance_variables_count", 0) > 0:
        warnings.append("В одной или нескольких выбранных переменных нет вариативности; такие переменные могут искажать или блокировать расчет.")
    if variables.get("high_missing_variables_count", 0) > 0:
        warnings.append("В одной или нескольких выбранных переменных высокий уровень пропусков.")
    if (time_quality.get("too_fast_responses_count") or 0) > 0:
        warnings.append("Обнаружены слишком быстрые прохождения; они могут снижать качество данных.")

    if analysis_type == "correlation":
        variables_count = len(result.get("variables") or [])
        n_matrix = result.get("n_matrix") or []
        p_values = result.get("p_values") or []
        pair_ns = [
            n_matrix[row_index][column_index]
            for row_index in range(len(n_matrix))
            for column_index in range(row_index + 1, len(n_matrix[row_index]))
            if n_matrix[row_index][column_index] is not None
        ]
        pair_p_values = [
            p_values[row_index][column_index]
            for row_index in range(len(p_values))
            for column_index in range(row_index + 1, len(p_values[row_index]))
        ]
        if variables_count < 2:
            warnings.append("Для корреляционного анализа требуется не менее двух переменных.")
        if any(value < 3 for value in pair_ns):
            warnings.append("Для части пар переменных недостаточно полных наблюдений для надежной оценки корреляции.")
        if any(3 <= value < 30 for value in pair_ns):
            warnings.append("Для части пар переменных меньше 30 совместных наблюдений; оценки корреляции могут быть нестабильными.")
        if any(value is None for value in pair_p_values):
            warnings.append("Для части корреляций p-value недоступен.")
        if any(
            row_index < len(n_matrix[row_index])
            and any(
                n_matrix[row_index][column_index] < min(n_matrix[row_index][row_index], n_matrix[column_index][column_index])
                for column_index in range(row_index + 1, len(n_matrix[row_index]))
            )
            for row_index in range(len(n_matrix))
        ):
            warnings.append("Для части пар применено попарное исключение наблюдений с пропусками; значения n различаются между корреляциями.")
    elif analysis_type == "crosstab":
        rows, columns, counts = _crosstab_shape(result)
        if rows < 2 or columns < 2:
            warnings.append("Таблица имеет менее двух строк или двух столбцов, анализ связи между категориями невозможен.")
        if any(count < 5 for count in counts):
            warnings.append("Таблица сопряженности содержит малые частоты в ячейках; интерпретация распределения требует осторожности.")
    elif analysis_type == "chi_square":
        if checks.get("expected_below_5_count", 0) > 0:
            warnings.append("Для χ²-критерия часть ожидаемых частот меньше 5; результат следует интерпретировать осторожно.")
        if checks.get("expected_below_5_rate", 0) > 20:
            warnings.append("Более 20% ожидаемых частот меньше 5; χ²-критерий может быть ненадежен.")
        if checks.get("expected_below_1_count", 0) > 0:
            warnings.append("В таблице есть ожидаемые частоты меньше 1; χ²-критерий может быть неприменим.")
        rows, columns, _ = _crosstab_shape(result)
        if rows == 2 and columns == 2 and checks.get("expected_below_5_count", 0):
            warnings.append("Для таблицы 2x2 при малых частотах рекомендуется использовать точный критерий Фишера.")
    elif analysis_type == "correspondence_analysis":
        if (result.get("n_rows") or 0) < 2 or (result.get("n_columns") or 0) < 2:
            warnings.append("Анализ соответствий требует таблицу сопряженности размером не менее 2x2.")
        masses = [
            item.get("mass")
            for item in [*(result.get("row_coordinates") or []), *(result.get("column_coordinates") or [])]
            if item.get("mass") is not None
        ]
        if any(mass < 0.05 for mass in masses):
            warnings.append("Часть категорий имеет очень малую массу, координаты таких категорий могут быть нестабильными.")
    elif analysis_type in ("regression", "logistic_regression"):
        if checks.get("cases_per_feature") is not None and checks["cases_per_feature"] < 10:
            warnings.append("Для регрессии мало наблюдений относительно числа предикторов.")
        if checks.get("high_vif_variables"):
            warnings.append("Обнаружена мультиколлинеарность между предикторами; коэффициенты модели могут быть нестабильными.")
        diagnostics = result.get("diagnostics") or {}
        multicollinearity = diagnostics.get("multicollinearity") or {}
        if multicollinearity.get("high_vif_variables"):
            warnings.append("Обнаружена возможная мультиколлинеарность между предикторами; коэффициенты модели могут быть нестабильными.")
        if analysis_type == "regression":
            residual_summary = diagnostics.get("residual_summary") or {}
            if (result.get("r2") is not None and result["r2"] < 0.1):
                warnings.append("R² низкий; модель объясняет небольшую долю вариации целевой переменной.")
            if (residual_summary.get("outliers_rate") or 0) >= 5:
                warnings.append("Обнаружены выбросы по остаткам; отдельные наблюдения могут заметно влиять на модель.")
            if (diagnostics.get("heteroscedasticity") or {}).get("warning"):
                warnings.append("Обнаружены признаки неоднородности дисперсии остатков; стандартные ошибки и p-value могут быть нестабильными.")
            if (diagnostics.get("normality") or {}).get("likely_normal") is False:
                warnings.append("Остатки модели могут отличаться от нормального распределения; p-value коэффициентов следует интерпретировать осторожно.")
            influential = diagnostics.get("influential_points") or {}
            if (influential.get("high_leverage_count") or 0) or (influential.get("large_cooks_distance_count") or 0):
                warnings.append("Обнаружены потенциально влияющие наблюдения; рекомендуется проверить выбросы и качество ответов.")
        if analysis_type == "logistic_regression":
            if checks.get("minority_class_rate") is not None and checks["minority_class_rate"] < 10:
                warnings.append("Целевая переменная сильно несбалансирована; метрики accuracy могут быть малоинформативны.")
            if checks.get("events_per_variable") is not None and checks["events_per_variable"] < 10:
                warnings.append("Для логистической регрессии мало событий на один предиктор; коэффициенты могут быть нестабильными.")
            metrics = result.get("metrics") or {}
            if metrics.get("roc_auc") is not None and metrics["roc_auc"] < 0.7:
                warnings.append("ROC-AUC низкий; модель слабо различает классы.")
            if (metrics.get("precision") is not None and metrics["precision"] < 0.5) or (metrics.get("recall") is not None and metrics["recall"] < 0.5):
                warnings.append("Precision или recall низкие; модель может плохо находить один из классов.")
    elif analysis_type == "factor_analysis":
        if (checks.get("n_variables") or 0) < 3:
            warnings.append("Для факторного анализа выбрано менее трех переменных.")
        if checks.get("cases_per_variable") is not None and checks["cases_per_variable"] < 5:
            warnings.append("Размер выборки мал относительно числа переменных; факторное решение может быть нестабильным.")
        if checks.get("kmo_overall") is not None and checks["kmo_overall"] < 0.6:
            warnings.append("KMO ниже 0.6, данные могут быть плохо пригодны для факторного анализа.")
        if checks.get("bartlett_p_value") is not None and checks["bartlett_p_value"] >= 0.05:
            warnings.append("Критерий Бартлетта незначим, факторный анализ может быть неинформативен.")
        if checks.get("low_kmo_variables"):
            warnings.append("У отдельных переменных низкий KMO; они могут плохо согласовываться с общей факторной структурой.")
        if checks.get("low_communality_variables"):
            warnings.append("Некоторые переменные имеют низкую communality; они плохо объясняются выделенными факторами.")
        if checks.get("cross_loading_variables"):
            warnings.append("Некоторые переменные имеют высокие нагрузки сразу на несколько факторов; их интерпретация может быть неоднозначной.")
        if checks.get("weak_variables"):
            warnings.append("Некоторые переменные не имеют существенных нагрузок ни на один фактор.")
        if checks.get("cumulative_explained_variance") is not None and checks["cumulative_explained_variance"] < 0.5:
            warnings.append("Выбранные факторы объясняют небольшую долю дисперсии; факторное решение может быть слабым.")
    elif analysis_type == "cluster_analysis":
        if checks.get("silhouette_score") is not None and checks["silhouette_score"] < 0.25:
            warnings.append("Silhouette score низкий, кластеры могут быть плохо разделены.")
        if checks.get("min_cluster_size") is not None and checks["min_cluster_size"] < 5:
            warnings.append("Один или несколько кластеров содержат мало респондентов.")
        if checks.get("n_clusters") and result.get("n") is not None and result["n"] < checks["n_clusters"] * 10:
            warnings.append("Количество кластеров слишком велико для доступного числа наблюдений.")
        if checks.get("cluster_size_ratio") is not None and checks["cluster_size_ratio"] >= 10:
            warnings.append("Размеры кластеров сильно различаются; сегментацию следует интерпретировать осторожно.")
        if checks.get("largest_cluster_rate") is not None and checks["largest_cluster_rate"] > 70:
            warnings.append("Один кластер содержит большую часть выборки, поэтому структура сегментов может быть слабой.")
        if checks.get("weak_profile_clusters"):
            warnings.append("Профили некоторых кластеров выражены слабо; отличающие признаки почти не выделяются.")
    elif analysis_type == "group_comparison":
        if checks.get("min_group_size") is not None and checks["min_group_size"] < 5:
            warnings.append("В одной или нескольких группах меньше 5 наблюдений; сравнение групп может быть ненадежным.")
        if checks.get("min_group_size") and checks.get("max_group_size", 0) / checks["min_group_size"] >= 3:
            warnings.append("Размеры групп сильно различаются; результаты следует интерпретировать осторожно.")
        if (result.get("post_hoc") or {}).get("enabled"):
            warnings.append("Для множественных сравнений важно учитывать поправку p-value.")
    elif analysis_type == "time_analysis":
        summary = result.get("summary") or {}
        minimum = summary.get("min_completion_time_seconds")
        maximum = summary.get("max_completion_time_seconds")
        median_value = summary.get("median_completion_time_seconds")
        if minimum is not None and minimum < TOO_FAST_THRESHOLD_SECONDS:
            warnings.append("Обнаружены слишком быстрые прохождения; возможно, часть ответов была дана невнимательно.")
        if maximum is not None and median_value and maximum > max(3600, median_value * 5):
            warnings.append("Обнаружены аномально длинные прохождения; они могут быть связаны с перерывами при заполнении анкеты.")
    elif analysis_type == "reliability_analysis":
        if (result.get("n_items") or 0) < 3:
            warnings.append("Для оценки надежности шкалы желательно использовать не менее трех пунктов.")
        if result.get("alpha") is not None and result["alpha"] < 0.7:
            warnings.append("Cronbach’s alpha ниже 0.7, внутренняя согласованность шкалы может быть недостаточной.")
        if any((item.get("item_total_correlation") or 0) < 0.3 for item in result.get("item_statistics") or []):
            warnings.append("Некоторые пункты слабо связаны с общей шкалой.")
        if any(item.get("improves_alpha") for item in result.get("alpha_if_item_deleted") or []):
            warnings.append("Удаление одного или нескольких пунктов может повысить Cronbach’s alpha; эти пункты стоит проверить содержательно.")
    elif analysis_type == "scale_index":
        if (result.get("n_items") or 0) < 3:
            warnings.append("Индекс шкалы построен по малому числу пунктов; интерпретация может быть ограниченной.")
        if any(item.get("reverse") and (item.get("min_value") is None or item.get("max_value") is None) for item in result.get("items") or []):
            warnings.append("Для обратного кодирования необходимо корректно задать минимальное и максимальное значения шкалы.")
        reliability = result.get("reliability") or {}
        if reliability.get("alpha") is not None and reliability["alpha"] < 0.7:
            warnings.append("Надежность пунктов индекса ограничена; интерпретируйте composite score с осторожностью.")
    elif analysis_type == "missing_analysis":
        if result.get("low_visibility_questions"):
            warnings.append("В опросе используется ветвление, поэтому вопросы, не показанные респонденту, не следует трактовать как обычные пропуски.")
        if result.get("top_skipped_questions"):
            warnings.append("Обнаружены вопросы с высоким уровнем пропусков среди тех, кому они были показаны.")
        if not (payload or {}).get("include_screened_out", False):
            warnings.append("Отсеченные респонденты не включены в анализ пропусков.")
    return warnings


def deduplicate_warnings(warnings):
    result = []
    seen = set()
    for warning in warnings:
        normalized = str(warning).strip() if warning is not None else ""
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
