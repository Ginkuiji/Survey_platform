from collections import defaultdict
from statistics import median

try:
    import numpy as np
except ImportError:  # pragma: no cover - depends on deployment environment
    np = None

from surveys.models import Response


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


