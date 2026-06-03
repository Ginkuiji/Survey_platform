from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

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


