from .advanced_analytics_dataset import build_analysis_dataset
from .advanced_analytics_methods import (
    compute_chi_square,
    compute_correlation_matrix,
    compute_correspondence_analysis,
    compute_cramers_v,
    compute_cronbach_alpha,
    compute_crosstab,
    compute_factor_analysis,
    compute_group_comparison,
    compute_kmeans_clustering,
    compute_linear_regression,
    compute_logistic_regression,
    compute_time_analysis,
)
from .models import Response


def _with_metadata(survey_id: int, analysis_type: str, dataset, result: dict) -> dict:
    return {
        "survey_id": survey_id,
        "analysis_type": analysis_type,
        "dataset_size": len(dataset.rows),
        **result,
    }


def _single_variable(dataset, role: str):
    if len(dataset.variables) != 1:
        raise ValueError(
            f"{role} variable must produce exactly one dataset column. "
            "Use ordinal, binary, numeric, rank, or a specific single-column encoding."
        )
    return dataset.variables[0]


def run_correlation_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    dataset = build_analysis_dataset(survey_id, payload["variables"])
    result = compute_correlation_matrix(
        dataset.rows,
        dataset.variables,
        method=payload.get("method", "pearson"),
    )
    return _with_metadata(survey_id, "correlation", dataset, result)


def run_crosstab_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    dataset = build_analysis_dataset(survey_id, [payload["row"], payload["column"]])
    if len(dataset.variables) != 2:
        raise ValueError(
            "Crosstab row and column must each produce exactly one dataset column. "
            "For choice questions, use ordinal/category-style encoding instead of one_hot."
        )

    row_variable, column_variable = dataset.variables
    result = compute_crosstab(dataset.rows, row_variable.code, column_variable.code)
    return _with_metadata(survey_id, "crosstab", dataset, {"crosstab": result})


def run_chi_square_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    dataset = build_analysis_dataset(survey_id, [payload["row"], payload["column"]])
    if len(dataset.variables) != 2:
        raise ValueError(
            "Chi-square row and column must each produce exactly one dataset column. "
            "For choice questions, use ordinal/category-style encoding instead of one_hot."
        )

    row_variable, column_variable = dataset.variables
    crosstab = compute_crosstab(dataset.rows, row_variable.code, column_variable.code)
    chi_square = compute_chi_square(crosstab)
    cramers_v = compute_cramers_v(crosstab, chi_square)
    return _with_metadata(
        survey_id,
        "chi_square",
        dataset,
        {
            "crosstab": crosstab,
            "chi_square": chi_square,
            "cramers_v": cramers_v,
        },
    )


def run_correspondence_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    dataset = build_analysis_dataset(survey_id, [payload["row"], payload["column"]])
    if len(dataset.variables) != 2:
        raise ValueError(
            "Correspondence analysis row and column must each produce exactly one dataset column."
        )

    row_variable, column_variable = dataset.variables
    crosstab = compute_crosstab(dataset.rows, row_variable.code, column_variable.code)
    result = compute_correspondence_analysis(
        crosstab,
        row_variable=row_variable,
        column_variable=column_variable,
        n_dimensions=payload.get("n_dimensions", 2),
    )
    return _with_metadata(survey_id, "correspondence_analysis", dataset, result)


def run_regression_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    if payload["target"].get("encoding") == "matrix_multi_binary":
        raise ValueError("matrix_multi can be used only as a regression feature, not as a target.")
    specs = [payload["target"], *payload["features"]]
    dataset = build_analysis_dataset(survey_id, specs)

    variables_meta = {
        variable.code: {
            "code": variable.code,
            "label": variable.label,
            "question_id": variable.question_id,
            "qtype": variable.qtype,
            "encoding": variable.encoding,
            "measure": variable.measure,
        }
        for variable in dataset.variables
    }

    target_dataset = build_analysis_dataset(survey_id, [payload["target"]])
    target_variable = _single_variable(target_dataset, "Target")

    feature_codes = [
        variable.code
        for variable in dataset.variables
        if variable.code != target_variable.code
    ]
    result = compute_linear_regression(
        dataset.rows,
        target_variable.code,
        feature_codes,
        include_intercept=payload.get("include_intercept", True),
    )
    result["variables"] = list(variables_meta.values())
    result["variables_by_code"] = variables_meta
    
    return _with_metadata(survey_id, "regression", dataset, result)


def run_logistic_regression_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    target_spec = payload["target"]
    feature_specs = payload["features"]

    if target_spec.get("encoding") not in ("binary", "ordinal"):
        raise ValueError("Logistic regression target must use binary encoding or binary ordinal choice encoding.")
    if target_spec.get("encoding") == "matrix_multi_binary":
        raise ValueError("matrix_multi is not supported as logistic regression target in MVP.")

    specs = [target_spec, *feature_specs]
    dataset = build_analysis_dataset(survey_id, specs)
    target_dataset = build_analysis_dataset(survey_id, [target_spec])
    target_variable = _single_variable(target_dataset, "Target")

    feature_codes = [
        variable.code
        for variable in dataset.variables
        if variable.code != target_variable.code
    ]
    if not feature_codes:
        raise ValueError("Logistic regression requires at least one feature column.")

    variables_meta = {
        variable.code: {
            "code": variable.code,
            "label": variable.label,
            "question_id": variable.question_id,
            "qtype": variable.qtype,
            "encoding": variable.encoding,
            "measure": variable.measure,
        }
        for variable in dataset.variables
    }

    result = compute_logistic_regression(
        dataset.rows,
        target_variable.code,
        feature_codes,
        include_intercept=payload.get("include_intercept", True),
        threshold=payload.get("threshold", 0.5),
        max_iter=payload.get("max_iter", 1000),
        learning_rate=payload.get("learning_rate", 0.1),
        regularization=payload.get("regularization", "l2"),
        lambda_=payload.get("lambda_", 0.01),
    )
    result["variables"] = list(variables_meta.values())
    result["variables_by_code"] = variables_meta

    return _with_metadata(survey_id, "logistic_regression", dataset, result)


def run_factor_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    variable_specs = payload["variables"]
    unsupported_encodings = {"one_hot", "matrix_multi_binary"}
    invalid_specs = [
        spec.get("encoding")
        for spec in variable_specs
        if spec.get("encoding") in unsupported_encodings
    ]
    if invalid_specs:
        raise ValueError("Factor analysis does not support one_hot or matrix_multi encodings in MVP.")

    dataset = build_analysis_dataset(survey_id, variable_specs)
    if len(dataset.variables) < 3:
        raise ValueError("Factor analysis requires at least three expanded variables.")
    if payload.get("n_factors", 2) >= len(dataset.variables):
        raise ValueError("n_factors must be less than number of expanded variables.")

    result = compute_factor_analysis(
        dataset.rows,
        dataset.variables,
        n_factors=payload.get("n_factors", 2),
        rotation=payload.get("rotation", "varimax"),
        standardize=payload.get("standardize", True),
        include_factor_scores=payload.get("include_factor_scores", False),
    )
    return _with_metadata(survey_id, "factor_analysis", dataset, result)


def run_cluster_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    dataset = build_analysis_dataset(survey_id, payload["variables"])
    if len(dataset.variables) < 2:
        raise ValueError("Cluster analysis requires at least two expanded variables.")

    profile_specs = payload.get("profile_variables") or payload["variables"]
    profile_dataset = build_analysis_dataset(survey_id, profile_specs)

    result = compute_kmeans_clustering(
        dataset.rows,
        dataset.variables,
        n_clusters=payload.get("n_clusters", 3),
        standardize=payload.get("standardize", True),
        max_iter=payload.get("max_iter", 300),
        profile_rows=profile_dataset.rows,
        profile_variables=profile_dataset.variables,
        max_profile_features=payload.get("max_profile_features", 5),
    )
    result["profile_variables"] = [
        {
            "code": variable.code,
            "label": variable.label,
            "question_id": variable.question_id,
            "qtype": variable.qtype,
            "encoding": variable.encoding,
            "measure": variable.measure,
        }
        for variable in profile_dataset.variables
    ]
    return _with_metadata(survey_id, "cluster_analysis", dataset, result)


def run_group_comparison(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    group_spec = payload["group"]
    value_spec = payload["value"]
    dataset = build_analysis_dataset(survey_id, [group_spec, value_spec])

    group_variables = [
        variable
        for variable in dataset.variables
        if variable.question_id == group_spec["question_id"]
    ]
    value_variables = [
        variable
        for variable in dataset.variables
        if variable.question_id == value_spec["question_id"]
    ]
    if len(group_variables) != 1 or len(value_variables) != 1:
        raise ValueError("Group comparison currently requires variables that produce exactly one column.")

    result = compute_group_comparison(
        rows=dataset.rows,
        group_var=group_variables[0],
        value_var=value_variables[0],
        method=payload.get("method", "anova"),
        alpha=payload.get("alpha", 0.05),
        post_hoc=payload.get("post_hoc", False),
        post_hoc_method=payload.get("post_hoc_method", "auto"),
        p_adjust=payload.get("p_adjust", "bonferroni"),
    )
    return _with_metadata(survey_id, "group_comparison", dataset, result)


def run_time_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    responses = Response.objects.filter(
        survey_id=survey_id,
        status="active",
    ).order_by("id")
    response_items = [
        {
            "response_id": response.id,
            "started_at": response.started_at,
            "finished_at": response.finished_at,
            "screened_out": response.screened_out,
            "screened_out_at": response.screened_out_at,
            "screened_out_reason": response.screened_out_reason,
            "complete_reason": response.complete_reason,
            "is_complete": response.is_complete,
            "status": response.status,
        }
        for response in responses
    ]

    group_rows = None
    group_variable = None
    group_by = payload.get("group_by")
    if group_by:
        group_dataset = build_analysis_dataset(survey_id, [group_by])
        group_variable = _single_variable(group_dataset, "Time analysis group_by")
        group_rows = group_dataset.rows

    result = compute_time_analysis(
        response_items=response_items,
        group_rows=group_rows,
        group_variable=group_variable,
        bucket_size_seconds=payload.get("bucket_size_seconds", 60),
        max_buckets=payload.get("max_buckets", 30),
    )
    return {
        "survey_id": survey_id,
        "analysis_type": "time_analysis",
        "dataset_size": result.get("n", len(response_items)),
        **result,
    }


def run_reliability_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    variable_specs = payload["variables"]
    unsupported_encodings = {"one_hot", "matrix_multi_binary"}
    invalid_specs = [
        spec.get("encoding")
        for spec in variable_specs
        if spec.get("encoding") in unsupported_encodings
    ]
    if invalid_specs:
        raise ValueError("Reliability analysis does not support one_hot or matrix_multi encodings in MVP.")

    dataset = build_analysis_dataset(survey_id, variable_specs)
    if len(dataset.variables) < 2:
        raise ValueError("Cronbach's alpha requires at least two expanded variables.")

    result = compute_cronbach_alpha(
        dataset.rows,
        dataset.variables,
        standardize=payload.get("standardize", False),
    )
    return _with_metadata(survey_id, "reliability_analysis", dataset, result)
