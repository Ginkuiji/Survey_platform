from .advanced_analytics_dataset import build_analysis_dataset
from .analytics_result_format import standardize_analysis_result
from .advanced_analytics_methods import (
    clean_numeric_pairs,
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
    compute_missing_analysis,
    compute_scale_index,
    compute_time_analysis,
    get_column,
)
from .analytics import (
    _answer_has_value,
    build_detailed_missing_analysis,
    build_visibility_by_question,
    get_completed_normal_responses,
    get_question_answers,
    get_screened_out_responses,
    get_survey_conditions,
    get_survey_pages,
    get_survey_questions,
)
from .models import Response


def _with_metadata(survey_id: int, analysis_type: str, dataset, result: dict, payload=None) -> dict:
    full_result = {
        "survey_id": survey_id,
        "analysis_type": analysis_type,
        "dataset_size": len(dataset.rows),
        **result,
    }
    full_result["standardized_result"] = standardize_analysis_result(
        analysis_type,
        full_result,
        payload=payload,
        dataset=dataset,
    )
    return full_result


def _single_variable(dataset, role: str):
    if len(dataset.variables) != 1:
        raise ValueError(
            f"Переменная «{role}» должна давать ровно один столбец данных. "
            "Используйте порядковое, бинарное, числовое, ранговое или другое одностолбцовое кодирование."
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
    if len(dataset.variables) == 2:
        left, right = dataset.variables
        result["scatter_pairs"] = [
            {"x": x_value, "y": y_value}
            for x_value, y_value in clean_numeric_pairs(
                get_column(dataset.rows, left.code),
                get_column(dataset.rows, right.code),
            )[:500]
        ]
    return _with_metadata(survey_id, "correlation", dataset, result, payload)


def run_crosstab_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    dataset = build_analysis_dataset(survey_id, [payload["row"], payload["column"]])
    if len(dataset.variables) != 2:
        raise ValueError(
            "Crosstab row and column must each produce exactly one dataset column. "
            "For choice questions, use ordinal/category-style encoding instead of one_hot."
        )

    row_variable, column_variable = dataset.variables
    result = compute_crosstab(
        dataset.rows,
        row_variable.code,
        column_variable.code,
        row_variable=row_variable,
        column_variable=column_variable,
    )
    return _with_metadata(survey_id, "crosstab", dataset, {"crosstab": result}, payload)


def run_chi_square_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    dataset = build_analysis_dataset(survey_id, [payload["row"], payload["column"]])
    if len(dataset.variables) != 2:
        raise ValueError(
            "Chi-square row and column must each produce exactly one dataset column. "
            "For choice questions, use ordinal/category-style encoding instead of one_hot."
        )

    row_variable, column_variable = dataset.variables
    crosstab = compute_crosstab(
        dataset.rows,
        row_variable.code,
        column_variable.code,
        row_variable=row_variable,
        column_variable=column_variable,
    )
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
        payload,
    )


def run_correspondence_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    dataset = build_analysis_dataset(survey_id, [payload["row"], payload["column"]])
    if len(dataset.variables) != 2:
        raise ValueError(
            "Correspondence analysis row and column must each produce exactly one dataset column."
        )

    row_variable, column_variable = dataset.variables
    crosstab = compute_crosstab(
        dataset.rows,
        row_variable.code,
        column_variable.code,
        row_variable=row_variable,
        column_variable=column_variable,
    )
    result = compute_correspondence_analysis(
        crosstab,
        row_variable=row_variable,
        column_variable=column_variable,
        n_dimensions=payload.get("n_dimensions", 2),
    )
    return _with_metadata(survey_id, "correspondence_analysis", dataset, result, payload)


def run_regression_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    if payload["target"].get("encoding") == "matrix_multi_binary":
        raise ValueError("Матричный множественный выбор можно использовать только как предиктор регрессии, но не как зависимую переменную.")
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
    
    return _with_metadata(survey_id, "regression", dataset, result, payload)


def run_logistic_regression_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    target_spec = payload["target"]
    feature_specs = payload["features"]

    if target_spec.get("encoding") not in ("binary", "ordinal"):
        raise ValueError("Зависимая переменная логистической регрессии должна использовать бинарное кодирование или бинарное порядковое кодирование.")
    if target_spec.get("encoding") == "matrix_multi_binary":
        raise ValueError("Матричный множественный выбор не поддерживается как зависимая переменная логистической регрессии.")

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
        raise ValueError("Для логистической регрессии требуется хотя бы один столбец-предиктор.")

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

    return _with_metadata(survey_id, "logistic_regression", dataset, result, payload)


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
        raise ValueError("Факторный анализ не поддерживает кодирования one_hot и matrix_multi.")

    dataset = build_analysis_dataset(survey_id, variable_specs)
    if len(dataset.variables) < 3:
        raise ValueError("Для факторного анализа требуется не менее трех развернутых переменных.")
    if payload.get("n_factors", 2) >= len(dataset.variables):
        raise ValueError("Число факторов должно быть меньше числа развернутых переменных.")

    result = compute_factor_analysis(
        dataset.rows,
        dataset.variables,
        n_factors=payload.get("n_factors", 2),
        rotation=payload.get("rotation", "varimax"),
        standardize=payload.get("standardize", True),
        include_factor_scores=payload.get("include_factor_scores", False),
        parallel_analysis=payload.get("parallel_analysis", True),
        parallel_iterations=payload.get("parallel_iterations", 100),
        parallel_percentile=payload.get("parallel_percentile", 95),
    )
    return _with_metadata(survey_id, "factor_analysis", dataset, result, payload)


def run_cluster_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    dataset = build_analysis_dataset(survey_id, payload["variables"])
    if len(dataset.variables) < 2:
        raise ValueError("Для кластерного анализа требуется не менее двух развернутых переменных.")

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
    return _with_metadata(survey_id, "cluster_analysis", dataset, result, payload)


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
        raise ValueError("Для сравнения групп каждая выбранная переменная должна давать ровно один столбец данных.")

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
    return _with_metadata(survey_id, "group_comparison", dataset, result, payload)


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
    full_result = {
        "survey_id": survey_id,
        "analysis_type": "time_analysis",
        "dataset_size": result.get("n", len(response_items)),
        **result,
    }
    full_result["standardized_result"] = standardize_analysis_result("time_analysis", full_result, payload=payload)
    return full_result


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
        raise ValueError("Анализ надежности не поддерживает кодирования one_hot и matrix_multi.")

    dataset = build_analysis_dataset(survey_id, variable_specs)
    if len(dataset.variables) < 2:
        raise ValueError("Для расчета α Кронбаха требуется не менее двух развернутых переменных.")

    result = compute_cronbach_alpha(
        dataset.rows,
        dataset.variables,
        standardize=payload.get("standardize", False),
    )
    return _with_metadata(survey_id, "reliability_analysis", dataset, result, payload)


def run_scale_index_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]
    item_specs = payload["items"]
    variable_specs = [
        {
            "question_id": item["question_id"],
            "encoding": item["encoding"],
            "measure": item["measure"],
        }
        for item in item_specs
    ]

    unsupported_encodings = {"one_hot", "rank", "matrix_multi_binary"}
    invalid_specs = [
        spec.get("encoding")
        for spec in variable_specs
        if spec.get("encoding") in unsupported_encodings
    ]
    if invalid_specs:
        raise ValueError("Индекс шкалы не поддерживает кодирования one_hot, rank и matrix_multi.")

    dataset = build_analysis_dataset(survey_id, variable_specs)
    if len(dataset.variables) < 2:
        raise ValueError("Для индекса шкалы требуется не менее двух развернутых переменных.")

    min_answered_items = payload.get("min_answered_items", 1)
    if min_answered_items > len(dataset.variables):
        raise ValueError("min_answered_items не может быть больше числа развернутых пунктов.")

    result = compute_scale_index(
        rows=dataset.rows,
        variables=dataset.variables,
        item_configs=item_specs,
        title=payload.get("title", "Индекс шкалы"),
        method=payload.get("method", "mean"),
        min_answered_items=min_answered_items,
        include_cronbach_alpha=payload.get("include_cronbach_alpha", True),
    )

    return _with_metadata(survey_id, "scale_index", dataset, result, payload)


def run_missing_analysis(payload: dict) -> dict:
    survey_id = payload["survey_id"]

    completed_responses = list(
        get_completed_normal_responses(survey_id)
        .prefetch_related(
            "answers",
            "answers__selected_options",
            "answers__matrix_cells__row",
            "answers__matrix_cells__column",
            "answers__ranking_items",
        )
    )
    completed_response_ids = [response.id for response in completed_responses]
    questions = list(get_survey_questions(survey_id).select_related("page"))
    pages = get_survey_pages(survey_id)
    conditions = get_survey_conditions(survey_id)
    visibility_by_question = build_visibility_by_question(
        completed_responses,
        pages,
        conditions,
    )

    answers_by_question = {}
    for question in questions:
        answers = get_question_answers(question.id, completed_response_ids=completed_response_ids)
        answers_by_question[question.id] = {
            answer.response_id
            for answer in answers
            if _answer_has_value(question, answer)
        }

    group_rows = None
    group_variable = None
    group_by = payload.get("group_by")
    if group_by:
        if group_by.get("encoding") not in ("binary", "ordinal"):
            raise ValueError("Группировка в анализе пропусков поддерживает только бинарные или порядковые категориальные переменные.")
        group_dataset = build_analysis_dataset(survey_id, [group_by])
        group_variable = _single_variable(group_dataset, "Missing analysis group_by")
        if group_variable.qtype not in ("yesno", "single", "dropdown"):
            raise ValueError("Группировка в анализе пропусков поддерживает только вопросы типов да/нет, одиночный выбор или выпадающий список.")
        group_rows = group_dataset.rows

    result = compute_missing_analysis(
        questions=questions,
        completed_responses=completed_responses,
        visibility_by_question=visibility_by_question,
        answers_by_question=answers_by_question,
        group_rows=group_rows,
        group_variable=group_variable,
        include_group_breakdown=payload.get("include_group_breakdown", False),
    )
    result["detailed_missing_analysis"] = build_detailed_missing_analysis(
        survey_id,
        questions=questions,
        pages=pages,
        conditions=conditions,
    )
    result["warnings"] = [
        *(result.get("warnings") or []),
        *(result["detailed_missing_analysis"].get("warnings") or []),
    ]

    if payload.get("include_screened_out", False):
        screened_out_responses = list(
            get_screened_out_responses(survey_id)
            .prefetch_related(
                "answers",
                "answers__selected_options",
                "answers__matrix_cells__row",
                "answers__matrix_cells__column",
                "answers__ranking_items",
            )
        )
        context = {
            "total_screened_out": len(screened_out_responses),
            "note": (
                "Screened out responses are excluded from main missing analysis. "
                "They are shown separately because respondents intentionally left the questionnaire due to screening logic."
            ),
        }
        if screened_out_responses:
            screened_visibility = build_visibility_by_question(screened_out_responses, pages, conditions)
            seen_counts_by_response = {response.id: 0 for response in screened_out_responses}
            for response_ids in screened_visibility.values():
                for response_id in response_ids:
                    if response_id in seen_counts_by_response:
                        seen_counts_by_response[response_id] += 1
            context["average_seen_questions_before_screenout"] = round(
                sum(seen_counts_by_response.values()) / len(seen_counts_by_response),
                2,
            )
        result["screened_out_context"] = context

    full_result = {
        "survey_id": survey_id,
        "analysis_type": "missing_analysis",
        "dataset_size": len(completed_responses),
        **result,
    }
    full_result["standardized_result"] = standardize_analysis_result("missing_analysis", full_result, payload=payload)
    return full_result
