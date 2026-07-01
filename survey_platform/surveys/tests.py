from django.test import SimpleTestCase
from django.utils import timezone
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from rest_framework.test import APITestCase

from survey_analytics.analytics import classify_question_response_state
from survey_analytics.analytics_result_format import standardize_analysis_result
from survey_analytics.analytics_descriptive_profile import describe_numeric_values
from survey_analytics.advanced_analytics_methods import compute_chi_square, compute_cramers_v, compute_factor_analysis, compute_group_comparison, compute_kmeans_clustering, compute_linear_regression, compute_logistic_regression, compute_cronbach_alpha, compute_scale_index, compute_time_analysis
from surveys.models import Question, Response, Survey


class AnonymousSurveySubmissionTests(APITestCase):
    def create_response_with_text_question(self, is_anonymous):
        survey = Survey.objects.create(
            title="Public survey" if is_anonymous else "Private survey",
            status="active",
            starts_at=timezone.now() - timedelta(days=1),
            is_anonymous=is_anonymous,
        )
        question = Question.objects.create(
            survey=survey,
            text="Comment",
            qtype=Question.TEXT,
            required=False,
        )
        response = Response.objects.create(
            survey=survey,
            session_token=f"token-{survey.id}",
        )
        return response, question

    def test_anonymous_survey_can_be_submitted_without_authentication(self):
        response, question = self.create_response_with_text_question(is_anonymous=True)

        result = self.client.post(
            "/api/surveys/submit/",
            {
                "response_token": response.session_token,
                "answers": [{"question": question.id, "text": ""}],
            },
            format="json",
        )

        self.assertEqual(result.status_code, 200)
        response.refresh_from_db()
        self.assertTrue(response.is_complete)
        self.assertIsNone(response.user)

    def test_non_anonymous_survey_still_requires_authentication_on_submit(self):
        response, question = self.create_response_with_text_question(is_anonymous=False)

        result = self.client.post(
            "/api/surveys/submit/",
            {
                "response_token": response.session_token,
                "answers": [{"question": question.id, "text": ""}],
            },
            format="json",
        )

        self.assertIn(result.status_code, (401, 403))
        self.assertIn("Authentication credentials", str(result.data.get("detail", "")))
        response.refresh_from_db()
        self.assertFalse(response.is_complete)


class StandardizedAnalysisResultTests(SimpleTestCase):
    def test_legacy_analytics_imports_remain_available(self):
        from surveys import analytics as legacy_analytics
        from surveys.advanced_analytics_methods import compute_time_analysis as legacy_compute_time_analysis

        self.assertIs(legacy_compute_time_analysis, compute_time_analysis)
        self.assertTrue(callable(legacy_analytics._response_seen_question_ids))

    def test_answer_has_value_handles_scale_answers_after_analytics_split(self):
        from survey_analytics.analytics import _answer_has_value
        from surveys.models import Question

        question = SimpleNamespace(qtype=Question.SCALE)

        self.assertTrue(_answer_has_value(question, SimpleNamespace(num=5, text="")))
        self.assertTrue(_answer_has_value(question, SimpleNamespace(num=None, text="4")))
        self.assertTrue(_answer_has_value(question, SimpleNamespace(number=5, text="")))
        self.assertFalse(_answer_has_value(question, SimpleNamespace(num=None, text="not-a-number")))

    def test_correlation_contains_required_fields_and_small_sample_warning(self):
        result = {
            "dataset_size": 12,
            "method": "pearson",
            "variables": [{"code": "q_1"}, {"code": "q_2"}],
            "matrix": [[1, 0.53], [0.53, 1]],
            "p_values": [[0, 0.01], [0.01, 0]],
            "n_matrix": [[12, 11], [11, 12]],
        }

        standardized = standardize_analysis_result("correlation", result)

        self.assertEqual(
            set(standardized),
            {
                "analysis_type", "title", "purpose", "input_summary",
                "data_quality", "descriptive_profile", "main_results", "effect_size",
                "interpretation", "visualizations", "warnings",
                "recommendations", "raw_result", "method_hint",
            },
        )
        self.assertEqual(standardized["effect_size"]["value"], 0.53)
        self.assertTrue(any("Размер выборки меньше 30" in warning for warning in standardized["warnings"]))
        self.assertIn("dataset", standardized["data_quality"])
        relationship = standardized["main_results"]["strongest_relationships"][0]
        self.assertEqual(relationship["direction"], "положительная")
        self.assertEqual(relationship["strength"], "заметная связь")
        self.assertTrue(relationship["significant"])
        self.assertEqual(standardized["method_hint"]["method"], "pearson")
        self.assertEqual(len(standardized["main_results"]["network"]["edges"]), 1)

    def test_unknown_analysis_type_returns_base_format(self):
        standardized = standardize_analysis_result("custom_method", {"n": 50})

        self.assertEqual(standardized["analysis_type"], "custom_method")
        self.assertEqual(standardized["main_results"], {})

    def test_existing_warnings_are_preserved_and_raw_result_is_not_recursive(self):
        result = {"n": 50, "warnings": ["original"], "standardized_result": {"old": True}}

        standardized = standardize_analysis_result("custom_method", result)

        self.assertIn("original", standardized["warnings"])
        self.assertNotIn("standardized_result", standardized["raw_result"])

    def test_chi_square_extracts_statistics_and_effect_size(self):
        standardized = standardize_analysis_result(
            "chi_square",
            {
                "dataset_size": 130,
                "chi_square": {"chi2": 12.43, "p_value": 0.015, "dof": 4, "expected": [[3, 7], [4, 8]]},
                "cramers_v": {"cramers_v": 0.23},
                "crosstab": {"rows": [{"columns": [{"count": 3}, {"count": 7}]}, {"columns": [{"count": 4}, {"count": 8}]}]},
            },
        )

        self.assertEqual(standardized["main_results"]["chi2"], 12.43)
        self.assertTrue(standardized["main_results"]["significant"])
        self.assertEqual(standardized["effect_size"]["value"], 0.23)
        self.assertEqual(standardized["data_quality"]["method_checks"]["method_specific"]["expected_below_5_count"], 2)
        self.assertTrue(any("ожидаемых частот меньше 5" in warning for warning in standardized["warnings"]))

    def test_regression_and_factor_analysis_extract_effect_sizes(self):
        regression = standardize_analysis_result("regression", {"n": 115, "r2": 0.42, "adjusted_r2": 0.38})
        factor = standardize_analysis_result("factor_analysis", {"n": 100, "cumulative_explained_variance": 0.71})

        self.assertEqual(regression["main_results"]["adjusted_r2"], 0.38)
        self.assertEqual(regression["effect_size"]["value"], 0.42)
        self.assertEqual(factor["effect_size"]["value"], 0.71)

    def test_factor_analysis_contains_interpretation_diagnostics(self):
        variables = [
            SimpleNamespace(code="q_1", label="Качество"),
            SimpleNamespace(code="q_2", label="Скорость"),
            SimpleNamespace(code="q_3", label="Поддержка"),
            SimpleNamespace(code="q_4", label="Удобство"),
        ]
        rows = [
            {"response_id": index, "q_1": index, "q_2": index + (index % 3), "q_3": 20 - index, "q_4": 21 - index + (index % 2)}
            for index in range(1, 20)
        ]

        result = compute_factor_analysis(rows, variables, include_factor_scores=True, parallel_iterations=20)

        self.assertEqual(result["kmo"]["per_variable"], result["kmo"]["variables"])
        self.assertTrue(result["parallel_analysis"]["enabled"])
        self.assertIn("recommended_n_factors", result["factor_recommendations"])
        self.assertEqual(len(result["communalities"]), 4)
        self.assertEqual(len(result["uniquenesses"]), 4)
        self.assertEqual(len(result["factor_structure"]), 2)
        self.assertIn("Фактор 1", result["factor_scores"][0])
        self.assertTrue(result["biplot"]["available"])

    def test_cluster_analysis_contains_segment_diagnostics(self):
        variables = [
            SimpleNamespace(code="q_1", label="Удовлетворенность", encoding="numeric"),
            SimpleNamespace(code="q_2", label="Лояльность", encoding="numeric"),
        ]
        rows = [
            {"response_id": index, "q_1": index % 4, "q_2": index % 3}
            for index in range(1, 21)
        ] + [
            {"response_id": index, "q_1": 20 + index % 4, "q_2": 15 + index % 3}
            for index in range(21, 41)
        ]

        result = compute_kmeans_clustering(rows, variables, n_clusters=2, elbow_max_k=4)

        self.assertEqual(len(result["cluster_sizes"]), 2)
        self.assertEqual(len(result["cluster_centroids"]), 2)
        self.assertEqual(len(result["cluster_distances"]["summary"]), 2)
        self.assertEqual(len(result["cluster_profiles"]), 2)
        self.assertTrue(result["elbow"]["points"])
        self.assertTrue(result["dimension_reduction"]["available"])
        self.assertTrue(result["radar_profiles"])
        self.assertTrue(result["profile_heatmap"]["rows"])
        self.assertIn("cluster_quality", result)

    def test_cronbach_alpha_contains_item_diagnostics(self):
        variables = [
            SimpleNamespace(code="q_1", label="Качество", question_id=1, qtype="scale", encoding="numeric"),
            SimpleNamespace(code="q_2", label="Скорость", question_id=2, qtype="scale", encoding="numeric"),
            SimpleNamespace(code="q_3", label="Удобство", question_id=3, qtype="scale", encoding="numeric"),
        ]
        rows = [{"q_1": index, "q_2": index + index % 2, "q_3": index + index % 3} for index in range(1, 15)]

        result = compute_cronbach_alpha(rows, variables)

        self.assertEqual(result["items_count"], 3)
        self.assertEqual(result["cronbach_alpha"], result["alpha"])
        self.assertEqual(len(result["item_total_correlations"]), 3)
        self.assertEqual(len(result["alpha_if_item_deleted"]), 3)
        self.assertEqual(len(result["inter_item_correlations"]["matrix"]), 3)

    def test_scale_index_contains_normalized_scores_and_groups(self):
        variables = [
            SimpleNamespace(code="q_1", label="Качество", question_id=1),
            SimpleNamespace(code="q_2", label="Сложность", question_id=2),
        ]
        rows = [
            {"response_id": 1, "q_1": 1, "q_2": 5},
            {"response_id": 2, "q_1": 3, "q_2": 3},
            {"response_id": 3, "q_1": 5, "q_2": 1},
        ]
        configs = [
            {"question_id": 1, "reverse": False},
            {"question_id": 2, "reverse": True, "min_value": 1, "max_value": 5},
        ]

        result = compute_scale_index(rows, variables, configs)

        self.assertTrue(result["reverse_coding"]["applied"])
        self.assertEqual(result["scores"][0]["normalized_score"], 0)
        self.assertEqual(result["scores"][-1]["normalized_score"], 100)
        self.assertEqual(len(result["groups"]["items"]), 3)
        self.assertEqual(result["index_title"], "Индекс шкалы")

    def test_dataset_quality_detects_missing_values_and_zero_variance(self):
        variables = [
            SimpleNamespace(code="q_1", label="Возраст", question_id=1),
            SimpleNamespace(code="q_2", label="Константа", question_id=2),
        ]
        dataset = SimpleNamespace(
            variables=variables,
            rows=[
                {"q_1": 20, "q_2": 1},
                {"q_1": 21, "q_2": 1},
                {"q_1": None, "q_2": 1},
            ],
        )

        standardized = standardize_analysis_result(
            "regression",
            {"dataset_size": 3, "n": 1, "features": ["q_1", "q_2"], "r2": 0.2},
            dataset=dataset,
        )

        quality = standardized["data_quality"]
        self.assertEqual(quality["variables"]["zero_variance_variables_count"], 1)
        self.assertEqual(quality["variables"]["high_missing_variables_count"], 1)
        self.assertEqual(quality["answers"]["average_completeness_rate"], 83.33)

    def test_warnings_are_deduplicated(self):
        standardized = standardize_analysis_result(
            "custom_method",
            {"n": 10, "warnings": [" Повтор ", "Повтор", None]},
        )

        self.assertEqual(standardized["warnings"].count("Повтор"), 1)

    def test_significant_weak_effect_has_limited_practical_significance(self):
        standardized = standardize_analysis_result(
            "chi_square",
            {
                "dataset_size": 100,
                "chi_square": {"chi2": 5.0, "p_value": 0.02, "dof": 1, "expected": [[20, 30], [20, 30]]},
                "cramers_v": {"cramers_v": 0.15},
                "crosstab": {"rows": [{"columns": [{"count": 20}, {"count": 30}]}, {"columns": [{"count": 20}, {"count": 30}]}]},
            },
        )

        interpretation = standardized["interpretation"]
        self.assertTrue(interpretation["statistical_significance"]["is_significant"])
        self.assertEqual(interpretation["practical_significance"]["level"], "limited")
        self.assertTrue(any("слабый эффект" in item for item in standardized["recommendations"]))

    def test_non_significant_moderate_effect_is_interpreted_cautiously(self):
        standardized = standardize_analysis_result(
            "group_comparison",
            {
                "n": 80,
                "test": {"p_value": 0.08},
                "effect_size": {"name": "Cohen's d", "value": 0.55, "interpretation": "умеренный эффект"},
            },
        )

        interpretation = standardized["interpretation"]
        self.assertFalse(interpretation["statistical_significance"]["is_significant"])
        self.assertEqual(interpretation["practical_significance"]["level"], "unclear")
        self.assertTrue(any("размер выборки" in item for item in standardized["recommendations"]))

    def test_p_value_without_effect_size_adds_recommendation(self):
        standardized = standardize_analysis_result("custom_method", {"n": 100, "p_value": 0.01})

        self.assertFalse(standardized["interpretation"]["effect_interpretation"]["available"])
        self.assertTrue(any("оценкой размера эффекта" in item for item in standardized["recommendations"]))

    def test_quality_warnings_lower_confidence(self):
        standardized = standardize_analysis_result(
            "custom_method",
            {"n": 10, "dataset_size": 100, "warnings": ["Первое", "Второе", "Третье", "Четвертое"]},
        )

        self.assertEqual(standardized["interpretation"]["confidence"]["level"], "low")

    def test_numeric_descriptive_profile_contains_quartiles_and_outliers(self):
        profile = describe_numeric_values([1, 2, 2, 3, 100, None])

        self.assertEqual(profile["n"], 5)
        self.assertEqual(profile["missing_count"], 1)
        self.assertEqual(profile["median"], 2)
        self.assertEqual(profile["q1"], 2)
        self.assertEqual(profile["q3"], 3)
        self.assertEqual(profile["outliers"]["count"], 1)

    def test_standardized_result_contains_dataset_descriptive_profile(self):
        dataset = SimpleNamespace(
            variables=[
                SimpleNamespace(
                    code="q_1",
                    label="Оценка",
                    question_id=1,
                    qtype="scale",
                    encoding="numeric",
                    measure="interval",
                    value_labels=None,
                ),
            ],
            rows=[{"q_1": 1}, {"q_1": 2}, {"q_1": 5}, {"q_1": None}],
        )

        standardized = standardize_analysis_result("custom_method", {"dataset_size": 4}, dataset=dataset)
        variable = standardized["descriptive_profile"]["variables"][0]

        self.assertEqual(variable["kind"], "numeric")
        self.assertEqual(variable["missing_count"], 1)
        self.assertEqual(variable["outliers"]["method"], "iqr")

    @patch("survey_analytics.analytics._response_seen_question_ids", return_value=set())
    def test_missing_state_classifier_distinguishes_branching_progress_and_screenout(self, _seen):
        question = SimpleNamespace(id=1)
        pages = []
        conditions = []

        self.assertEqual(
            classify_question_response_state(
                SimpleNamespace(screened_out=False, is_complete=True),
                question,
                pages,
                conditions,
                answers_by_question={},
            ),
            "not_shown_by_branching",
        )
        self.assertEqual(
            classify_question_response_state(
                SimpleNamespace(screened_out=False, is_complete=False),
                question,
                pages,
                conditions,
                answers_by_question={},
            ),
            "not_reached",
        )
        self.assertEqual(
            classify_question_response_state(
                SimpleNamespace(screened_out=True, is_complete=True),
                question,
                pages,
                conditions,
                answers_by_question={},
            ),
            "screened_out",
        )

    def test_missing_state_classifier_marks_visible_unanswered_as_real_missing(self):
        self.assertEqual(
            classify_question_response_state(
                SimpleNamespace(screened_out=False, is_complete=True),
                SimpleNamespace(id=1),
                [],
                [],
                answers_by_question={},
                seen_question_ids={1},
            ),
            "skipped_after_shown",
        )

    def test_chi_square_contains_residuals_contributions_and_diagnostics(self):
        crosstab = {
            "rows": [
                {"raw_value": "A", "value": "A", "columns": [{"raw_value": "X", "value": "X", "count": 9}, {"raw_value": "Y", "value": "Y", "count": 1}]},
                {"raw_value": "B", "value": "B", "columns": [{"raw_value": "X", "value": "X", "count": 1}, {"raw_value": "Y", "value": "Y", "count": 9}]},
            ],
        }

        chi_square = compute_chi_square(crosstab)
        cramers_v = compute_cramers_v(crosstab, chi_square)

        self.assertEqual(chi_square["observed"], [[9, 1], [1, 9]])
        self.assertEqual(len(chi_square["standardized_residuals"]), 2)
        self.assertEqual(len(chi_square["cell_contributions"]), 2)
        self.assertEqual(chi_square["expected_diagnostics"]["cells_count"], 4)
        self.assertTrue(chi_square["top_contributing_cells"])
        self.assertIn("effect_size_description", cramers_v)

    def test_group_comparison_t_test_contains_profiles_differences_and_effect(self):
        group_var = SimpleNamespace(code="group", label="Группа", value_labels={1: "A", 2: "B"})
        value_var = SimpleNamespace(code="value", label="Оценка")
        rows = [
            *[{"group": 1, "value": value} for value in (4, 5, 5, 6, 7)],
            *[{"group": 2, "value": value} for value in (1, 2, 2, 3, 4)],
        ]

        result = compute_group_comparison(rows, group_var, value_var, method="t_test")

        self.assertEqual(result["groups_count"], 2)
        self.assertEqual(result["effect_size"]["name"], "Cohen’s d")
        self.assertIsNotNone(result["differences"]["confidence_interval_95"])
        self.assertIn("q1", result["groups"][0])
        self.assertIn("variance_diagnostics", result)

    def test_group_comparison_mann_whitney_contains_rank_biserial_effect(self):
        group_var = SimpleNamespace(code="group", label="Группа", value_labels={})
        value_var = SimpleNamespace(code="value", label="Оценка")
        rows = [
            *[{"group": 1, "value": value} for value in (1, 2, 2, 3)],
            *[{"group": 2, "value": value} for value in (4, 5, 5, 6)],
        ]

        result = compute_group_comparison(rows, group_var, value_var, method="mann_whitney")

        self.assertEqual(result["effect_size"]["name"], "Rank-biserial correlation")
        self.assertIn("median_difference", result["differences"])

    def test_linear_regression_contains_coefficients_and_residual_diagnostics(self):
        rows = [{"response_id": index, "target": 2 * index + 1, "x": index} for index in range(1, 21)]

        result = compute_linear_regression(rows, "target", ["x"])

        self.assertIn("rmse", result)
        self.assertIn("mae", result)
        self.assertIn("standard_error", result["coefficients"][1])
        self.assertIn("confidence_interval_95", result["coefficients"][1])
        self.assertIn("observed_vs_predicted", result["diagnostics"])
        self.assertIn("multicollinearity", result["diagnostics"])

    def test_logistic_regression_contains_roc_calibration_and_coefficient_statistics(self):
        rows = [
            {"response_id": index, "target": 1 if index >= 10 else 0, "x": index}
            for index in range(20)
        ]

        result = compute_logistic_regression(rows, "target", ["x"], regularization="none")

        self.assertIn("roc_auc", result["metrics"])
        self.assertIn("specificity", result["metrics"])
        self.assertIn("balanced_accuracy", result["metrics"])
        self.assertTrue(result["roc_curve"])
        self.assertTrue(result["threshold_analysis"])
        self.assertTrue(result["diagnostics"]["calibration"]["bins"])
        self.assertIn("odds_ratio_confidence_interval_95", result["coefficients"][1])

    def test_time_analysis_contains_dropout_quality_and_flow_contract(self):
        started_at = datetime(2026, 1, 1, 12, 0, 0)
        responses = [
            {"response_id": 1, "started_at": started_at, "finished_at": started_at + timedelta(seconds=20), "is_complete": True, "complete_reason": "completed", "screened_out": False, "answered_question_ids": [1, 2]},
            {"response_id": 2, "started_at": started_at, "finished_at": started_at + timedelta(seconds=120), "is_complete": True, "complete_reason": "completed", "screened_out": False, "answered_question_ids": [1, 2]},
            {"response_id": 3, "started_at": started_at, "finished_at": started_at + timedelta(seconds=180), "is_complete": True, "complete_reason": "completed", "screened_out": False, "answered_question_ids": [1, 2]},
            {"response_id": 4, "started_at": started_at, "finished_at": None, "is_complete": False, "complete_reason": None, "screened_out": False, "answered_question_ids": [1]},
            {"response_id": 5, "started_at": started_at, "finished_at": started_at + timedelta(seconds=45), "screened_out_at": started_at + timedelta(seconds=40), "is_complete": True, "complete_reason": "screened_out", "screened_out": True, "screened_out_reason": "Возраст", "answered_question_ids": [1]},
        ]

        result = compute_time_analysis(
            responses,
            page_items=[
                {"page_id": 1, "page_title": "Страница 1", "question_ids": [1]},
                {"page_id": 2, "page_title": "Страница 2", "question_ids": [2]},
            ],
            too_fast_threshold_seconds=30,
        )

        self.assertEqual(result["method"], "time_and_dropout_analysis")
        self.assertEqual(result["duration_summary"]["count"], 3)
        self.assertEqual(result["quality_flags"]["too_fast"]["count"], 1)
        self.assertEqual(result["dropout"]["by_page"][1]["dropout_count"], 2)
        self.assertEqual(result["page_funnel"]["steps"][0]["label"], "Начали опрос")
        self.assertTrue(result["retention_curve"]["points"])
        self.assertEqual(result["screenout"]["top_reason"]["reason"], "Возраст")
        self.assertTrue(result["flow"]["links"])
