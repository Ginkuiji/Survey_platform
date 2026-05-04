# surveys/analytics.py
from collections import Counter
from statistics import median
from typing import Any, Callable, Dict, Iterable, Optional

from .models import AnalyticResults, Answer, MatrixAnswerCell, MatrixColumn, MatrixRow, Option, Question, QuestionCondition, Response, Survey, SurveyPage


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
        .select_related("source_question", "question", "page", "target_page", "option")
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
    }


def percent(part: int, whole: int) -> float:
    return round(part / whole * 100, 2) if whole else 0


def _answer_to_condition_data(answer: Answer) -> Dict[str, Any]:
    data = {
        "selected_options": [option.id for option in answer.selected_options.all()],
        "text": answer.text or "",
        "num": answer.num,
        "matrix_cells": [
            {"row": cell.row_id, "column": cell.column_id}
            for cell in answer.matrix_cells.all()
        ],
        "ranking_items": [
            {"option": item.option_id, "rank": item.rank}
            for item in answer.ranking_items.all()
        ],
    }
    return data


def _condition_answer_has_value(question: Question, answer_data: Optional[Dict[str, Any]]) -> bool:
    if not answer_data:
        return False
    if question.qtype in (Question.SINGLE, Question.MULTI, Question.DROPDOWN, Question.YESNO):
        return bool(answer_data.get("selected_options"))
    if question.qtype in (Question.TEXT, Question.DATE):
        return bool((answer_data.get("text") or "").strip())
    if question.qtype in (Question.SCALE, Question.NUMBER):
        return answer_data.get("num") is not None
    if question.qtype in (Question.MATRIX_SINGLE, Question.MATRIX_MULTI):
        return bool(answer_data.get("matrix_cells"))
    if question.qtype == Question.RANKING:
        return bool(answer_data.get("ranking_items"))
    return False


def _extract_condition_answer_value(question: Question, answer_data: Optional[Dict[str, Any]]):
    if not answer_data:
        return None
    if question.qtype in (Question.SINGLE, Question.DROPDOWN, Question.YESNO):
        selected_options = answer_data.get("selected_options") or []
        return selected_options[0] if selected_options else None
    if question.qtype == Question.MULTI:
        return answer_data.get("selected_options") or []
    if question.qtype in (Question.TEXT, Question.DATE):
        return (answer_data.get("text") or "").strip()
    if question.qtype in (Question.SCALE, Question.NUMBER):
        return answer_data.get("num")
    if question.qtype in (Question.MATRIX_SINGLE, Question.MATRIX_MULTI):
        return answer_data.get("matrix_cells") or []
    if question.qtype == Question.RANKING:
        return answer_data.get("ranking_items") or []
    return None


def _condition_matches(condition: QuestionCondition, answer_data: Optional[Dict[str, Any]]) -> bool:
    source_question = condition.source_question
    operator = condition.operator

    if operator == "is_answered":
        return _condition_answer_has_value(source_question, answer_data)
    if operator == "not_answered":
        return not _condition_answer_has_value(source_question, answer_data)

    value = _extract_condition_answer_value(source_question, answer_data)

    if operator == "contains_option":
        if not condition.option_id:
            return False
        if source_question.qtype in (Question.SINGLE, Question.DROPDOWN, Question.YESNO):
            return value == condition.option_id
        if source_question.qtype == Question.MULTI:
            return condition.option_id in value
        return False

    if operator in ("equals", "not_equals"):
        if condition.option_id:
            expected = condition.option_id
        elif condition.value_number is not None:
            expected = condition.value_number
        else:
            expected = condition.value_text
        result = value == expected
        return result if operator == "equals" else not result

    if operator in ("gt", "lt", "gte", "lte"):
        if value is None or condition.value_number is None:
            return False
        try:
            value = float(value)
        except (TypeError, ValueError):
            return False
        if operator == "gt":
            return value > condition.value_number
        if operator == "lt":
            return value < condition.value_number
        if operator == "gte":
            return value >= condition.value_number
        if operator == "lte":
            return value <= condition.value_number

    return False


def _evaluate_conditions(conditions, answers_by_question: Dict[int, Dict[str, Any]]):
    groups = {}
    for index, condition in enumerate(conditions):
        group_key = condition.group_key or f"__condition_{condition.id or index}"
        groups.setdefault(group_key, []).append(condition)

    matched_conditions = []
    for group_conditions in groups.values():
        group_results = [
            (
                condition,
                _condition_matches(condition, answers_by_question.get(condition.source_question_id)),
            )
            for condition in group_conditions
        ]

        if group_conditions[0].group_logic == "any":
            matched_conditions.extend(
                condition for condition, matches in group_results if matches
            )
        elif all(matches for _, matches in group_results):
            matched_conditions.extend(group_conditions)

    return matched_conditions


def _question_is_visible(question: Question, conditions, matched_condition_ids) -> bool:
    incoming = [
        condition
        for condition in conditions
        if condition.action == "show_question" and condition.question_id == question.id
    ]
    return not incoming or any(condition.id in matched_condition_ids for condition in incoming)


def _page_is_visible(page_id: Optional[int], conditions, matched_condition_ids) -> bool:
    if page_id is None:
        return True
    incoming = [
        condition
        for condition in conditions
        if condition.action == "show_page" and condition.page_id == page_id
    ]
    return not incoming or any(condition.id in matched_condition_ids for condition in incoming)


def _response_seen_question_ids(response: Response, pages, conditions) -> set[int]:
    answers = list(
        response.answers
        .select_related("question")
        .prefetch_related("selected_options", "matrix_cells", "ranking_items")
        .all()
    )
    answers_by_question = {
        answer.question_id: _answer_to_condition_data(answer)
        for answer in answers
    }
    seen_answers = {}
    seen_question_ids = set()
    page_index_by_id = {
        page["id"]: index
        for index, page in enumerate(pages)
        if page["id"] is not None
    }

    page_index = 0
    visited_pages = set()
    while 0 <= page_index < len(pages) and page_index not in visited_pages:
        visited_pages.add(page_index)
        page = pages[page_index]
        matched_before_page = _evaluate_conditions(conditions, seen_answers)
        matched_before_ids = {condition.id for condition in matched_before_page}

        if not _page_is_visible(page["id"], conditions, matched_before_ids):
            page_index += 1
            continue

        matched_for_questions = _evaluate_conditions(conditions, answers_by_question)
        matched_question_ids = {condition.id for condition in matched_for_questions}

        visible_page_questions = []
        for question in page["questions"]:
            if _question_is_visible(question, conditions, matched_question_ids):
                seen_question_ids.add(question.id)
                visible_page_questions.append(question)

        for question in visible_page_questions:
            if question.id in answers_by_question:
                seen_answers[question.id] = answers_by_question[question.id]

        matched_after_page = _evaluate_conditions(conditions, seen_answers)
        if any(condition.action == "terminate" for condition in matched_after_page):
            break

        jump_condition = next(
            (
                condition
                for condition in matched_after_page
                if condition.action == "jump_to_page" and condition.target_page_id
            ),
            None,
        )
        if jump_condition and jump_condition.target_page_id in page_index_by_id:
            page_index = page_index_by_id[jump_condition.target_page_id]
        else:
            page_index += 1

    return seen_question_ids


def build_visibility_by_question(completed_responses, pages, conditions) -> Dict[int, set[int]]:
    visibility_by_question: Dict[int, set[int]] = {}
    for response in completed_responses:
        for question_id in _response_seen_question_ids(response, pages, conditions):
            visibility_by_question.setdefault(question_id, set()).add(response.id)
    return visibility_by_question


# ---- Question type analysis layer ----------------------------------------

def _option_payload(option: Option, count: int, base: Dict[str, int]) -> Dict[str, Any]:
    return {
        "id": option.id,
        "text": option.text,
        "value": option.value,
        "count": count,
        "percent_answered": percent(count, base["answered_count"]),
        "percent_total": percent(count, base["total_completed"]),
    }


def analyze_single_choice(question: Question, answers, base: Dict[str, int]) -> Dict[str, Any]:
    counts = Counter()
    for answer in answers:
        selected = list(answer.selected_options.all())
        if selected:
            counts[selected[0].id] += 1

    options = [
        _option_payload(option, counts[option.id], base)
        for option in question.options.all()
    ]
    return {"options": options}


def analyze_multi_choice(question: Question, answers, base: Dict[str, int]) -> Dict[str, Any]:
    counts = Counter()
    total_choices = 0
    for answer in answers:
        selected = list(answer.selected_options.all())
        total_choices += len(selected)
        for option in selected:
            counts[option.id] += 1

    options = [
        _option_payload(option, counts[option.id], base)
        for option in question.options.all()
    ]
    return {
        "options": options,
        "total_choices": total_choices,
    }


def analyze_text(question: Question, answers, base: Dict[str, int]) -> Dict[str, Any]:
    texts = [
        answer.text.strip()
        for answer in answers
        if answer.text and answer.text.strip()
    ]
    return {
        "total_text_answers": len(texts),
        "text_answers": texts,
    }


def _extract_scale_value(answer: Answer) -> Optional[float]:
    if answer.num is not None:
        return answer.num
    if answer.text in (None, ""):
        return None
    try:
        return float(answer.text)
    except (TypeError, ValueError):
        return None


def analyze_scale(question: Question, answers, base: Dict[str, int]) -> Dict[str, Any]:
    values = [
        value
        for value in (_extract_scale_value(answer) for answer in answers)
        if value is not None
    ]
    distribution = Counter(values)

    return {
        "answered_count": len(values),
        "average": round(sum(values) / len(values), 2) if values else None,
        "median": median(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "distribution": [
            {"value": value, "count": distribution[value]}
            for value in sorted(distribution)
        ],
    }


def analyze_matrix(question: Question, answers, base: Dict[str, int]) -> Dict[str, Any]:
    counts = Counter()
    row_answer_counts = Counter()

    for answer in answers:
        answered_rows = set()
        for cell in answer.matrix_cells.all():
            counts[(cell.row_id, cell.column_id)] += 1
            answered_rows.add(cell.row_id)
        for row_id in answered_rows:
            row_answer_counts[row_id] += 1

    columns = list(question.matrix_columns.all())
    return {
        "rows": [
            {
                "id": row.id,
                "text": row.text,
                "value": row.value,
                "answered_count": row_answer_counts[row.id],
                "columns": [
                    {
                        "id": column.id,
                        "text": column.text,
                        "value": column.value,
                        "count": counts[(row.id, column.id)],
                        "percent_answered": percent(counts[(row.id, column.id)], base["answered_count"]),
                        "percent_total": percent(counts[(row.id, column.id)], base["total_completed"]),
                    }
                    for column in columns
                ],
            }
            for row in question.matrix_rows.all()
        ],
    }


def matrix_multi_distribution(question: Question, responses, shown_response_ids=None) -> Dict[str, Any]:
    response_ids = [response.id for response in responses]
    answers = list(get_question_answers(question.id, response_ids))
    if shown_response_ids is None:
        shown_response_ids = response_ids
    base = build_question_base(question, responses, answers, shown_response_ids)
    rows = list(MatrixRow.objects.filter(question=question).order_by("order", "id"))
    columns = list(MatrixColumn.objects.filter(question=question).order_by("order", "id"))

    row_payloads = [
        {"id": row.id, "text": row.text, "value": row.value}
        for row in rows
    ]
    column_payloads = [
        {"id": column.id, "text": column.text, "value": column.value}
        for column in columns
    ]

    if not rows or not columns:
        return {
            "type": Question.MATRIX_MULTI,
            "base": base,
            "rows": row_payloads,
            "columns": column_payloads,
            "cells": [],
            "row_summary": [],
            "column_summary": [],
        }

    row_by_id = {row.id: row for row in rows}
    column_by_id = {column.id: column for column in columns}
    answer_ids = [answer.id for answer in answers]
    cells_qs = (
        MatrixAnswerCell.objects
        .filter(answer_id__in=answer_ids, row__question=question, column__question=question)
        .select_related("answer", "row", "column")
    )

    cell_counts = Counter()
    row_selected_totals = Counter()
    column_selected_totals = Counter()
    row_respondents: Dict[int, set[int]] = {row.id: set() for row in rows}
    column_respondents: Dict[int, set[int]] = {column.id: set() for column in columns}
    respondent_cells = set()

    for cell in cells_qs:
        if cell.row_id not in row_by_id or cell.column_id not in column_by_id:
            continue
        response_id = cell.answer.response_id
        key = (response_id, cell.row_id, cell.column_id)
        if key in respondent_cells:
            continue
        respondent_cells.add(key)
        cell_counts[(cell.row_id, cell.column_id)] += 1
        row_selected_totals[cell.row_id] += 1
        column_selected_totals[cell.column_id] += 1
        row_respondents[cell.row_id].add(response_id)
        column_respondents[cell.column_id].add(response_id)

    cells = []
    for row in rows:
        for column in columns:
            count = cell_counts[(row.id, column.id)]
            cells.append({
                "row_id": row.id,
                "row_text": row.text,
                "column_id": column.id,
                "column_text": column.text,
                "count": count,
                "percent_answered": percent(count, base["answered_count"]),
                "percent_total": percent(count, base["total_completed"]),
            })

    row_summary = []
    for row in rows:
        respondent_count = len(row_respondents[row.id])
        selected_total = row_selected_totals[row.id]
        row_summary.append({
            "row_id": row.id,
            "row_text": row.text,
            "selected_total": selected_total,
            "respondent_count": respondent_count,
            "respondent_share": percent(respondent_count, base["answered_count"]),
            "avg_selected_per_respondent": round(selected_total / respondent_count, 2) if respondent_count else 0,
        })

    column_summary = []
    for column in columns:
        respondent_count = len(column_respondents[column.id])
        column_summary.append({
            "column_id": column.id,
            "column_text": column.text,
            "selected_total": column_selected_totals[column.id],
            "respondent_count": respondent_count,
            "respondent_share": percent(respondent_count, base["answered_count"]),
        })

    return {
        "type": Question.MATRIX_MULTI,
        "base": base,
        "rows": row_payloads,
        "columns": column_payloads,
        "cells": cells,
        "row_summary": row_summary,
        "column_summary": column_summary,
    }


def analyze_ranking(question: Question, answers, base: Dict[str, int]) -> Dict[str, Any]:
    ranks_by_option: Dict[int, list[int]] = {option.id: [] for option in question.options.all()}
    rank_distribution: Dict[int, Counter] = {
        option.id: Counter()
        for option in question.options.all()
    }
    first_place_counts = Counter()

    for answer in answers:
        for item in answer.ranking_items.all():
            ranks_by_option.setdefault(item.option_id, []).append(item.rank)
            rank_distribution.setdefault(item.option_id, Counter())[item.rank] += 1
            if item.rank == 1:
                first_place_counts[item.option_id] += 1

    return {
        "options": [
            {
                "id": option.id,
                "text": option.text,
                "value": option.value,
                "average_rank": (
                    round(sum(ranks_by_option[option.id]) / len(ranks_by_option[option.id]), 2)
                    if ranks_by_option[option.id]
                    else None
                ),
                "first_place_count": first_place_counts[option.id],
                "rank_distribution": [
                    {
                        "rank": rank,
                        "count": count,
                        "percent_answered": percent(count, base["answered_count"]),
                        "percent_total": percent(count, base["total_completed"]),
                    }
                    for rank, count in sorted(rank_distribution[option.id].items())
                ],
            }
            for option in question.options.all()
        ],
    }


QUESTION_ANALYZERS: Dict[str, Callable[[Question, Any, Dict[str, int]], Dict[str, Any]]] = {
    Question.SINGLE: analyze_single_choice,
    Question.MULTI: analyze_multi_choice,
    Question.TEXT: analyze_text,
    Question.SCALE: analyze_scale,
    Question.DROPDOWN: analyze_single_choice,
    Question.YESNO: analyze_single_choice,
    Question.NUMBER: analyze_scale,
    Question.DATE: analyze_text,
    Question.MATRIX_SINGLE: analyze_matrix,
    Question.RANKING: analyze_ranking,
}


def analyze_question(question: Question, answers, base: Dict[str, int]) -> Dict[str, Any]:
    analyzer = QUESTION_ANALYZERS.get(question.qtype)
    if analyzer is None:
        return {
            "unsupported": True,
            "message": f"Question type '{question.qtype}' is not supported by analytics yet.",
        }
    return analyzer(question, answers, base)


# ---- Survey JSON assembly layer ------------------------------------------

def build_screening_summary(screened_out_responses) -> Dict[str, Any]:
    reasons = Counter(
        (response.screened_out_reason or "").strip() or "Без указания причины"
        for response in screened_out_responses
    )
    durations = [
        (response.screened_out_at - response.started_at).total_seconds()
        for response in screened_out_responses
        if response.screened_out_at and response.started_at
    ]

    return {
        "total_screened_out": len(screened_out_responses),
        "average_screenout_time": round(sum(durations) / len(durations), 2) if durations else None,
        "reasons": [
            {"reason": reason, "count": count}
            for reason, count in reasons.most_common()
        ],
    }


def build_survey_summary(
    survey_id: int,
    started_responses,
    completed_normal_responses,
    screened_out_responses,
) -> Dict[str, Any]:
    total_started = len(started_responses)
    total_completed = len(completed_normal_responses)
    total_screened_out = len(screened_out_responses)
    total_finished = total_completed + total_screened_out

    completion_durations = [
        (response.finished_at - response.started_at).total_seconds()
        for response in completed_normal_responses
        if response.finished_at and response.started_at
    ]
    screenout_durations = [
        (response.screened_out_at - response.started_at).total_seconds()
        for response in screened_out_responses
        if response.screened_out_at and response.started_at
    ]

    return {
        "total_started": total_started,
        "total_completed": total_completed,
        "total_screened_out": total_screened_out,
        "total_finished": total_finished,
        "completion_rate": percent(total_completed, total_started),
        "screenout_rate": percent(total_screened_out, total_started),
        "finish_rate": percent(total_finished, total_started),
        "average_completion_time": round(sum(completion_durations) / len(completion_durations), 2) if completion_durations else None,
        "average_screenout_time": round(sum(screenout_durations) / len(screenout_durations), 2) if screenout_durations else None,
        "questions_count": get_survey_questions(survey_id).count(),
    }


def build_question_result(question: Question, completed_normal_responses, shown_response_ids=None) -> Dict[str, Any]:
    completed_response_ids = [response.id for response in completed_normal_responses]
    answers = list(get_question_answers(question.id, completed_response_ids))
    base = build_question_base(question, completed_normal_responses, answers, shown_response_ids)
    result = (
        matrix_multi_distribution(question, completed_normal_responses, shown_response_ids)
        if question.qtype == Question.MATRIX_MULTI
        else analyze_question(question, answers, base)
    )

    return {
        "id": question.id,
        "text": question.text,
        "qtype": question.qtype,
        "base": base,
        "result": result,
    }


def analyze_survey(survey_id: int, save: bool = False) -> Dict[str, Any]:
    survey = Survey.objects.get(id=survey_id)
    started_responses = list(get_started_responses(survey_id))
    completed_normal_responses = list(
        get_completed_normal_responses(survey_id)
        .prefetch_related(
            "answers",
            "answers__selected_options",
            "answers__matrix_cells__row",
            "answers__matrix_cells__column",
            "answers__ranking_items",
        )
    )
    screened_out_responses = list(get_screened_out_responses(survey_id))
    questions = list(get_survey_questions(survey_id))
    pages = get_survey_pages(survey_id)
    conditions = get_survey_conditions(survey_id)
    visibility_by_question = build_visibility_by_question(completed_normal_responses, pages, conditions)

    result = {
        "survey": {
            "id": survey.id,
            "title": survey.title,
        },
        "summary": build_survey_summary(
            survey_id,
            started_responses,
            completed_normal_responses,
            screened_out_responses,
        ),
        "screening": build_screening_summary(screened_out_responses),
        "questions": [
            build_question_result(
                question,
                completed_normal_responses,
                visibility_by_question.get(question.id, set()),
            )
            for question in questions
        ],
    }

    if save:
        AnalyticResults.objects.create(
            survey=survey,
            title=f"Срез аналитики опроса {survey.id}",
            total_responses=result["summary"]["total_finished"],
            data=result,
        )

    return result


# ---- Backward-compatible public functions used by views -------------------

def question_distribution(question_id: int, save: bool = False) -> Dict[str, Any]:
    question = (
        Question.objects
        .select_related("survey")
        .prefetch_related("options", "matrix_rows", "matrix_columns")
        .get(id=question_id)
    )
    completed_normal_responses = list(
        get_completed_normal_responses(question.survey_id)
        .prefetch_related(
            "answers",
            "answers__selected_options",
            "answers__matrix_cells__row",
            "answers__matrix_cells__column",
            "answers__ranking_items",
        )
    )
    pages = get_survey_pages(question.survey_id)
    conditions = get_survey_conditions(question.survey_id)
    visibility_by_question = build_visibility_by_question(completed_normal_responses, pages, conditions)
    result = build_question_result(
        question,
        completed_normal_responses,
        visibility_by_question.get(question.id, set()),
    )

    if save:
        AnalyticResults.objects.create(
            survey=question.survey,
            title=f"Аналитика вопроса {question.id}",
            total_responses=result["base"]["answered_count"],
            data=result,
        )

    return result


def survey_distribution(survey_id: int, save: bool = False) -> Dict[str, Any]:
    return analyze_survey(survey_id, save=save)
