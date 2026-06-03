from survey_analytics.analytics_data_quality import (
    build_applicability_warnings,
    build_data_quality_summary,
    deduplicate_warnings,
)
from survey_analytics.analytics_descriptive_profile import (
    build_descriptive_profile,
    build_descriptive_recommendations,
    collect_descriptive_warnings,
)
from .constants import *  # noqa: F401,F403
from . import helpers as _helpers
from . import main_results as _main_results
from . import interpretation as _interpretation

globals().update({name: getattr(_helpers, name) for name in dir(_helpers) if not name.startswith("__")})
globals().update({name: getattr(_main_results, name) for name in dir(_main_results) if not name.startswith("__")})
globals().update({name: getattr(_interpretation, name) for name in dir(_interpretation) if not name.startswith("__")})

from .interpretation import *  # noqa: F401,F403
def standardize_analysis_result(analysis_type, result, payload=None, dataset=None):
    raw_result = _clean_raw_result(result)
    data_quality = build_data_quality_summary(analysis_type, raw_result, payload, dataset)
    descriptive_profile = build_descriptive_profile(raw_result, payload, dataset, raw_result.get("survey_id"))
    warnings = collect_warnings(raw_result)
    warnings.extend(build_applicability_warnings(analysis_type, raw_result, payload, dataset, data_quality))
    warnings.extend(collect_descriptive_warnings(descriptive_profile))
    warnings = deduplicate_warnings(warnings)
    effect_size = build_effect_size_summary(analysis_type, raw_result)
    interpretation = build_interpretation(analysis_type, raw_result, effect_size, data_quality, warnings)
    recommendations = [
        *RECOMMENDATIONS.get(
            analysis_type,
            ["Интерпретируйте результат вместе с подробными таблицами и графиками метода."],
        ),
        *build_common_recommendations(analysis_type, interpretation, warnings),
        *build_descriptive_recommendations(descriptive_profile),
        *((raw_result.get("detailed_missing_analysis") or {}).get("recommendations") or []),
    ]
    standardized_result = {
        "analysis_type": analysis_type,
        "title": ANALYSIS_TITLES.get(analysis_type, analysis_type.replace("_", " ").title()),
        "purpose": ANALYSIS_PURPOSES.get(analysis_type, "Аналитический метод."),
        "input_summary": build_input_summary(raw_result, payload, dataset),
        "data_quality": data_quality,
        "descriptive_profile": descriptive_profile,
        "main_results": build_main_results(analysis_type, raw_result),
        "effect_size": effect_size,
        "interpretation": interpretation,
        "visualizations": build_visualization_specs(analysis_type),
        "warnings": warnings,
        "recommendations": deduplicate_warnings(recommendations),
        "raw_result": raw_result,
    }
    if analysis_type == "correlation":
        standardized_result["method_hint"] = build_correlation_method_hint(raw_result)
    return standardized_result
