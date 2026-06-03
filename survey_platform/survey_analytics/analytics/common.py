# surveys/analytics.py
from collections import Counter
from statistics import median, stdev
from typing import Any, Callable, Dict, Iterable, Optional

from surveys.models import AnalyticResults, Answer, MatrixAnswerCell, MatrixColumn, MatrixRow, Option, Question, QuestionCondition, Response, Survey, SurveyPage


# ---- Data access layer ----------------------------------------------------

def get_finished_responses(survey_id: int):
    return Response.objects.filter(
        survey_id=survey_id,
        is_complete=True,
        status="active",
    ).order_by("id")


def get_completed_normal_responses(survey_id: int):
    return Response.objects.filter(
        survey_id=survey_id,
        is_complete=True,
        screened_out=False,
        status="active",
    ).order_by("id")


def get_screened_out_responses(survey_id: int):
    return Response.objects.filter(
        survey_id=survey_id,
        is_complete=True,
        screened_out=True,
        status="active",
    ).order_by("id")


def get_started_responses(survey_id: int):
    return Response.objects.filter(survey_id=survey_id, status="active")


def get_survey_questions(survey_id: int):
    return (
        Question.objects
        .filter(survey_id=survey_id)
        .prefetch_related("options", "matrix_rows", "matrix_columns")
        .order_by("order", "id")
    )


def get_survey_pages(survey_id: int):
    pages = list(
        SurveyPage.objects
        .filter(survey_id=survey_id)
        .prefetch_related("question_page__options", "question_page__matrix_rows", "question_page__matrix_columns")
        .order_by("order", "id")
    )
    if pages:
        return [
            {
                "id": page.id,
                "questions": list(page.question_page.all().order_by("order", "id")),
            }
            for page in pages
        ]

    return [
        {
            "id": None,
            "questions": list(get_survey_questions(survey_id)),
        }
    ]


def get_survey_conditions(survey_id: int):
    return list(
        QuestionCondition.objects
        .filter(source_question__survey_id=survey_id, is_active=True)
        .select_related("source_question", "question", "page", "target_page", "option", "matrix_row", "matrix_column", "group")
        .order_by("priority", "id")
    )


def get_question_answers(question_id: int, completed_response_ids: Optional[Iterable[int]] = None):
    qs = (
        Answer.objects
        .filter(question_id=question_id, response__is_complete=True, response__status="active")
        .select_related("response", "question")
        .prefetch_related("selected_options", "matrix_cells__row", "matrix_cells__column", "ranking_items__option")
        .order_by("id")
    )
    if completed_response_ids is not None:
        qs = qs.filter(response_id__in=completed_response_ids)
    return qs


# ---- Analysis base layer --------------------------------------------------

def _answer_has_value(question: Question, answer: Answer) -> bool:
    if question.qtype in (Question.SINGLE, Question.MULTI, Question.DROPDOWN, Question.YESNO):
        return bool(list(answer.selected_options.all()))
    if question.qtype in (Question.TEXT, Question.DATE):
        return bool((answer.text or "").strip())
    if question.qtype in (Question.SCALE, Question.NUMBER):
        return _extract_scale_value(answer) is not None
    if question.qtype in (Question.MATRIX_SINGLE, Question.MATRIX_MULTI):
        return answer.matrix_cells.exists()
    if question.qtype == Question.RANKING:
        return answer.ranking_items.exists()
    return True


def build_question_base(question: Question, completed_responses, answers, shown_response_ids=None) -> Dict[str, int]:
    total_completed = len(completed_responses)
    answered_response_ids = {
        answer.response_id
        for answer in answers
        if _answer_has_value(question, answer)
    }
    shown_response_ids = set(shown_response_ids or [])
    shown_count = len(shown_response_ids)
    shown_answered_response_ids = answered_response_ids & shown_response_ids

    return {
        "total_completed": total_completed,
        "answered_count": len(shown_answered_response_ids),
        "shown_count": shown_count,
        "skipped_count": max(shown_count - len(shown_answered_response_ids), 0),
        "not_shown_count": max(total_completed - shown_count, 0),
        "shown_rate_completed": percent(shown_count, total_completed),
    }


def percent(part: int, whole: int) -> float:
    return round(part / whole * 100, 2) if whole else 0


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def describe_numeric_answers(values, total_count):
    q1 = _percentile(values, 0.25)
    q3 = _percentile(values, 0.75)
    iqr = q3 - q1 if q1 is not None and q3 is not None else None
    lower_fence = q1 - 1.5 * iqr if iqr is not None else None
    upper_fence = q3 + 1.5 * iqr if iqr is not None else None
    outliers_count = sum(value < lower_fence or value > upper_fence for value in values) if values else 0
    missing_count = max(total_count - len(values), 0)
    return {
        "answered_count": len(values),
        "n": len(values),
        "missing_count": missing_count,
        "missing_rate": percent(missing_count, total_count),
        "average": round(sum(values) / len(values), 2) if values else None,
        "median": median(values) if values else None,
        "std": round(stdev(values), 2) if len(values) > 1 else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "outliers": {
            "method": "iqr",
            "lower_fence": lower_fence,
            "upper_fence": upper_fence,
            "count": outliers_count,
            "rate": percent(outliers_count, len(values)),
        },
    }


