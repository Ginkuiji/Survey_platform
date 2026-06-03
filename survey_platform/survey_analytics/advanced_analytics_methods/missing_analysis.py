from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
HIGH_SKIP_RATE = 30
MODERATE_SKIP_RATE = 10
LOW_VISIBILITY_RATE = 50


def _response_id(response):
    if isinstance(response, dict):
        return response.get("id") or response.get("response_id")
    return response.id


def _question_value(question, name, default=None):
    if isinstance(question, dict):
        return question.get(name, default)
    return getattr(question, name, default)


def _question_label(question):
    return _question_value(question, "short_label") or _question_value(question, "text") or str(_question_value(question, "id"))


def _question_page_id(question):
    return _question_value(question, "page_id")


def _question_page_title(question):
    if isinstance(question, dict):
        return question.get("page_title")
    page = getattr(question, "page", None)
    return getattr(page, "title", "") if page else ""


def classify_missing_item(shown_count, skipped_count, visibility_rate, skip_rate_shown):
    if shown_count == 0:
        return "not_shown"
    if skipped_count == 0:
        return "no_missing"
    if visibility_rate < LOW_VISIBILITY_RATE and (skip_rate_shown or 0) < MODERATE_SKIP_RATE:
        return "branching_limited"
    if (skip_rate_shown or 0) >= HIGH_SKIP_RATE:
        return "high_missing"
    if (skip_rate_shown or 0) >= MODERATE_SKIP_RATE:
        return "moderate_missing"
    return "low_missing"


def interpret_missing_item(item) -> str:
    shown_count = item.get("shown_count") or 0
    skipped_count = item.get("skipped_count") or 0
    visibility_rate = item.get("visibility_rate") or 0
    skip_rate_shown = item.get("skip_rate_shown")

    if shown_count == 0:
        return "Вопрос не был показан ни одному респонденту. Проверьте условия ветвления."
    if visibility_rate < LOW_VISIBILITY_RATE and (skip_rate_shown or 0) < MODERATE_SKIP_RATE:
        return "Вопрос показан только части респондентов из-за ветвления; это не является обычным пропуском."
    if skip_rate_shown is not None and skip_rate_shown >= HIGH_SKIP_RATE:
        return "Высокая доля реальных пропусков среди респондентов, которым вопрос был показан."
    if skipped_count == 0:
        return "Все респонденты, которым был показан вопрос, дали ответ."
    return "Доля пропусков находится в допустимых пределах."


def _missing_question_short_item(item):
    return {
        "question_id": item.get("question_id"),
        "label": item.get("label"),
        "shown_count": item.get("shown_count"),
        "skipped_count": item.get("skipped_count"),
        "skip_rate_shown": item.get("skip_rate_shown"),
        "visibility_rate": item.get("visibility_rate"),
        "missing_type_code": item.get("missing_type_code"),
        "missing_type": item.get("missing_type"),
    }


def _missing_group_label(value, value_labels):
    if value_labels is None:
        return str(value)
    if value in value_labels:
        return value_labels[value]
    try:
        int_value = int(value)
        if int_value in value_labels:
            return value_labels[int_value]
    except (TypeError, ValueError):
        pass
    return str(value)


def compute_missing_analysis(
    questions,
    completed_responses,
    visibility_by_question,
    answers_by_question,
    group_rows=None,
    group_variable=None,
    include_group_breakdown=False,
) -> dict:
    response_ids = [_response_id(response) for response in completed_responses]
    response_id_set = set(response_ids)
    total_completed_normal = len(response_ids)
    questions_count = len(questions)
    question_items = []

    for question in questions:
        question_id = _question_value(question, "id")
        shown_response_ids = set(visibility_by_question.get(question_id) or set()) & response_id_set
        answered_response_ids = set(answers_by_question.get(question_id) or set()) & shown_response_ids
        shown_count = len(shown_response_ids)
        answered_count = len(answered_response_ids)
        skipped_count = max(shown_count - answered_count, 0)
        not_shown_count = max(total_completed_normal - shown_count, 0)
        visibility_rate = round(shown_count / total_completed_normal * 100, 2) if total_completed_normal else 0
        answer_rate_shown = round(answered_count / shown_count * 100, 2) if shown_count else None
        skip_rate_shown = round(skipped_count / shown_count * 100, 2) if shown_count else None
        answer_rate_total = round(answered_count / total_completed_normal * 100, 2) if total_completed_normal else 0
        missing_type_code = classify_missing_item(shown_count, skipped_count, visibility_rate, skip_rate_shown)
        qtype = _question_value(question, "qtype")

        item = {
            "question_id": question_id,
            "label": _question_label(question),
            "qtype_code": qtype,
            "qtype": _question_type_label(qtype),
            "required": bool(_question_value(question, "required", False)),
            "page_id": _question_page_id(question),
            "page_title": _question_page_title(question),
            "total_completed_normal": total_completed_normal,
            "shown_count": shown_count,
            "not_shown_count": not_shown_count,
            "answered_count": answered_count,
            "skipped_count": skipped_count,
            "visibility_rate": visibility_rate,
            "answer_rate_shown": answer_rate_shown,
            "skip_rate_shown": skip_rate_shown,
            "answer_rate_total": answer_rate_total,
            "missing_type_code": missing_type_code,
            "missing_type": _missing_type_label(missing_type_code),
        }
        item["interpretation"] = interpret_missing_item(item)
        question_items.append(item)

    total_shown_slots = sum(item["shown_count"] for item in question_items)
    total_answered_slots = sum(item["answered_count"] for item in question_items)
    total_skipped_slots = sum(item["skipped_count"] for item in question_items)
    total_not_shown_slots = sum(item["not_shown_count"] for item in question_items)
    total_possible_slots = total_completed_normal * questions_count

    top_skipped_questions = [
        _missing_question_short_item(item)
        for item in sorted(
            [item for item in question_items if item["shown_count"] > 0 and item["skipped_count"] > 0],
            key=lambda item: (item["skip_rate_shown"] or 0, item["skipped_count"]),
            reverse=True,
        )
    ]
    low_visibility_questions = [
        _missing_question_short_item(item)
        for item in sorted(
            [item for item in question_items if item["visibility_rate"] < LOW_VISIBILITY_RATE],
            key=lambda item: item["visibility_rate"],
        )
    ]
    never_shown_questions = [
        _missing_question_short_item(item)
        for item in question_items
        if item["shown_count"] == 0
    ]
    required_questions_with_missing = [
        _missing_question_short_item(item)
        for item in question_items
        if item["required"] and item["skipped_count"] > 0
    ]

    groups = []
    if include_group_breakdown and group_rows is not None and group_variable is not None:
        group_by_response = {
            row.get("response_id"): row.get(group_variable.code)
            for row in group_rows
            if not _is_missing(row.get(group_variable.code))
        }
        group_totals = {}
        for item in question_items:
            question_id = item["question_id"]
            shown_ids = set(visibility_by_question.get(question_id) or set()) & response_id_set
            answered_ids = set(answers_by_question.get(question_id) or set()) & shown_ids
            for response_id in shown_ids:
                group_value = group_by_response.get(response_id)
                if group_value is None:
                    continue
                bucket = group_totals.setdefault(group_value, {
                    "group": group_value,
                    "group_label": _missing_group_label(group_value, group_variable.value_labels),
                    "total_shown_slots": 0,
                    "total_answered_slots": 0,
                    "total_skipped_slots": 0,
                })
                bucket["total_shown_slots"] += 1
                if response_id in answered_ids:
                    bucket["total_answered_slots"] += 1
                else:
                    bucket["total_skipped_slots"] += 1
        for group in sorted(group_totals.values(), key=lambda item: str(item["group_label"])):
            shown_slots = group["total_shown_slots"]
            group["overall_skip_rate_shown"] = round(group["total_skipped_slots"] / shown_slots * 100, 2) if shown_slots else None
            groups.append(group)

    return {
        "method": "missing_analysis",
        "summary": {
            "total_completed_normal": total_completed_normal,
            "questions_count": questions_count,
            "total_shown_slots": total_shown_slots,
            "total_answered_slots": total_answered_slots,
            "total_skipped_slots": total_skipped_slots,
            "total_not_shown_slots": total_not_shown_slots,
            "overall_skip_rate_shown": round(total_skipped_slots / total_shown_slots * 100, 2) if total_shown_slots else None,
            "overall_visibility_rate": round(total_shown_slots / total_possible_slots * 100, 2) if total_possible_slots else 0,
            "questions_with_high_missing": sum(1 for item in question_items if item["missing_type_code"] == "high_missing"),
            "questions_with_moderate_missing": sum(1 for item in question_items if item["missing_type_code"] == "moderate_missing"),
            "questions_with_low_visibility": sum(1 for item in question_items if item["visibility_rate"] < LOW_VISIBILITY_RATE),
        },
        "questions": question_items,
        "top_skipped_questions": top_skipped_questions,
        "low_visibility_questions": low_visibility_questions,
        "never_shown_questions": never_shown_questions,
        "required_questions_with_missing": required_questions_with_missing,
        "groups": groups,
        "warnings": [],
    }


