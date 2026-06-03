from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

def _option_payload(option: Option, count: int, base: Dict[str, int]) -> Dict[str, Any]:
    return {
        "id": option.id,
        "text": option.text,
        "value": option.value,
        "count": count,
        "percent_answered": percent(count, base["answered_count"]),
        "percent_shown": percent(count, base["shown_count"]),
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
        "average_selected_options": round(total_choices / base["answered_count"], 2) if base["answered_count"] else 0,
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
        **describe_numeric_answers(values, base["shown_count"]),
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
                        "percent_answered_row": percent(counts[(row.id, column.id)], row_answer_counts[row.id]),
                        "percent_shown": percent(counts[(row.id, column.id)], base["shown_count"]),
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
                "percent_answered_row": percent(count, len(row_respondents[row.id])),
                "percent_shown": percent(count, base["shown_count"]),
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
    last_place_counts = Counter()

    for answer in answers:
        for item in answer.ranking_items.all():
            ranks_by_option.setdefault(item.option_id, []).append(item.rank)
            rank_distribution.setdefault(item.option_id, Counter())[item.rank] += 1
            if item.rank == 1:
                first_place_counts[item.option_id] += 1
            if item.rank == len(ranks_by_option):
                last_place_counts[item.option_id] += 1

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
                "last_place_count": last_place_counts[option.id],
                "median_rank": median(ranks_by_option[option.id]) if ranks_by_option[option.id] else None,
                "min_rank": min(ranks_by_option[option.id]) if ranks_by_option[option.id] else None,
                "max_rank": max(ranks_by_option[option.id]) if ranks_by_option[option.id] else None,
                "rank_distribution": [
                    {
                        "rank": rank,
                        "count": count,
                        "percent_answered": percent(count, base["answered_count"]),
                        "percent_shown": percent(count, base["shown_count"]),
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


