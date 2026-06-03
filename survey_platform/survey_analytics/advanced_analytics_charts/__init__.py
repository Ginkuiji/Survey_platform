from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
from .correlation import *  # noqa: F401,F403
from .regression import *  # noqa: F401,F403
from .group_comparison import *  # noqa: F401,F403
from .factor_analysis import *  # noqa: F401,F403
from .cluster_analysis import *  # noqa: F401,F403
from .logistic_regression import *  # noqa: F401,F403
from .crosstab import *  # noqa: F401,F403
from .time_analysis import *  # noqa: F401,F403
from .other import *  # noqa: F401,F403

def build_report_section_chart(report, section_id, chart_type=None) -> BytesIO:
    if MATPLOTLIB_IMPORT_ERROR is not None:
        raise ValueError("Matplotlib is not installed on the server.")

    payload = get_report_payload(report)
    sections = payload.get("sections") or []
    section = next((item for item in sections if str(item.get("id")) == str(section_id)), None)
    if not section:
        raise ValueError("Report section not found.")
    if section.get("error"):
        raise ValueError("Cannot build chart for a section with analysis error.")

    section_type = section.get("type")
    config = section.get("config") or section
    result = section.get("result") or {}
    chart_type = chart_type or "auto"

    builders = {
        "correlation": build_correlation_chart,
        "regression": build_regression_chart,
        "group_comparison": build_group_comparison_chart,
        "factor_analysis": build_factor_analysis_chart,
        "cluster_analysis": build_cluster_analysis_chart,
        "logistic_regression": build_logistic_regression_chart,
        "chi_square": build_crosstab_chart,
        "crosstab": build_crosstab_chart,
        "correspondence_analysis": build_crosstab_chart,
        "time_analysis": build_time_analysis_chart,
        "missing_analysis": build_missing_analysis_chart,
        "reliability_analysis": build_reliability_chart,
        "scale_index": build_scale_index_chart,
    }
    builder = builders.get(section_type)
    if not builder:
        raise ValueError(f"Matplotlib chart is not available for analysis type '{section_type}'.")
    return builder(report, config, result, chart_type)
