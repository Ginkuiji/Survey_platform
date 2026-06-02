from django.test import SimpleTestCase
from types import SimpleNamespace
from unittest.mock import patch

from .analytics import classify_question_response_state
from .analytics_result_format import standardize_analysis_result
from .analytics_descriptive_profile import describe_numeric_values


class StandardizedAnalysisResultTests(SimpleTestCase):
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

    @patch("surveys.analytics._response_seen_question_ids", return_value=set())
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
