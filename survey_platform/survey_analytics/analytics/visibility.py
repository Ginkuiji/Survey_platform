from . import common as _common
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})

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

    if operator in ("contains_matrix_cell", "matrix_row_equals", "matrix_row_not_equals"):
        if source_question.qtype not in (Question.MATRIX_SINGLE, Question.MATRIX_MULTI):
            return False
        if not condition.matrix_row_id or not condition.matrix_column_id:
            return False
        cells = value or []
        row_matches = [
            cell
            for cell in cells
            if cell.get("row") == condition.matrix_row_id
        ]
        has_cell = any(cell.get("column") == condition.matrix_column_id for cell in row_matches)
        if operator == "contains_matrix_cell":
            return has_cell
        return has_cell if operator == "matrix_row_equals" else bool(row_matches) and not has_cell

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
        group_key = condition.group_id or f"__condition_{condition.id or index}"
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

        group = group_conditions[0].group
        group_logic = group.logic if group else "all"
        if group_logic == "any":
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


def classify_question_response_state(
    response: Response,
    question: Question,
    pages,
    conditions,
    answers_by_question=None,
    seen_question_ids=None,
) -> str:
    if answers_by_question is None:
        answers_by_question = {
            answer.question_id: answer
            for answer in response.answers.all()
        }
    answer = answers_by_question.get(question.id)
    if answer is not None and _answer_has_value(question, answer):
        return "answered"

    seen_question_ids = (
        set(seen_question_ids)
        if seen_question_ids is not None
        else _response_seen_question_ids(response, pages, conditions)
    )
    if question.id in seen_question_ids:
        return "skipped_after_shown"
    if response.screened_out:
        return "screened_out"
    if not response.is_complete:
        return "not_reached"
    return "not_shown_by_branching"


def _detailed_missing_interpretation(counts, rates) -> str:
    if rates["real_missing_rate"] >= 30:
        return "Высокая доля реальных пропусков среди респондентов, которым вопрос был показан."
    if rates["not_reached_rate"] >= 20:
        return "Заметная часть начавших опрос не дошла до вопроса."
    if rates["not_shown_by_branching_rate"] >= 50:
        return "Вопрос часто не показывается из-за логики ветвления; это не следует считать обычным пропуском."
    if counts["screened_out"]:
        return "Часть респондентов не дошла до вопроса из-за корректного отсева."
    return "Критичных особенностей заполнения вопроса не обнаружено."


def build_detailed_missing_analysis(survey_id: int, questions=None, pages=None, conditions=None) -> Dict[str, Any]:
    responses = list(
        get_started_responses(survey_id)
        .prefetch_related(
            "answers",
            "answers__selected_options",
            "answers__matrix_cells__row",
            "answers__matrix_cells__column",
            "answers__ranking_items",
        )
        .order_by("id")
    )
    questions = questions or list(get_survey_questions(survey_id).select_related("page"))
    pages = pages or get_survey_pages(survey_id)
    conditions = conditions or get_survey_conditions(survey_id)
    response_contexts = []
    for response in responses:
        response_contexts.append({
            "response": response,
            "answers": {answer.question_id: answer for answer in response.answers.all()},
            "seen_question_ids": _response_seen_question_ids(response, pages, conditions),
        })

    question_items = []
    warnings = []
    for question in questions:
        counts = Counter({
            "answered": 0,
            "skipped_after_shown": 0,
            "not_shown_by_branching": 0,
            "not_reached": 0,
            "screened_out": 0,
        })
        for context in response_contexts:
            state = classify_question_response_state(
                context["response"],
                question,
                pages,
                conditions,
                answers_by_question=context["answers"],
                seen_question_ids=context["seen_question_ids"],
            )
            counts[state] += 1

        shown_count = counts["answered"] + counts["skipped_after_shown"]
        count_payload = dict(counts)
        rates = {
            "answered_rate": percent(counts["answered"], len(responses)),
            "real_missing_rate": percent(counts["skipped_after_shown"], shown_count),
            "not_shown_by_branching_rate": percent(counts["not_shown_by_branching"], len(responses)),
            "not_reached_rate": percent(counts["not_reached"], len(responses)),
            "screened_out_rate": percent(counts["screened_out"], len(responses)),
        }
        if rates["real_missing_rate"] >= 30:
            warnings.append(f"У вопроса «{question.text}» высокая доля реальных пропусков: {rates['real_missing_rate']}%.")
        if rates["not_reached_rate"] >= 20:
            warnings.append(f"До вопроса «{question.text}» не дошли {rates['not_reached_rate']}% начавших опрос.")
        if rates["not_shown_by_branching_rate"] >= 50:
            warnings.append(f"Вопрос «{question.text}» часто скрывается ветвлением: {rates['not_shown_by_branching_rate']}%.")

        question_items.append({
            "question_id": question.id,
            "label": question.text,
            "qtype": question.qtype,
            "required": question.required,
            "page_id": question.page_id,
            "page_title": getattr(getattr(question, "page", None), "title", None),
            "base": len(responses),
            "shown_count": shown_count,
            "counts": count_payload,
            "rates": rates,
            "interpretation": _detailed_missing_interpretation(count_payload, rates),
        })

    summary = {
        "total_started": len(responses),
        "total_completed_normal": sum(response.is_complete and not response.screened_out for response in responses),
        "total_screened_out": sum(response.screened_out for response in responses),
        "total_active_unfinished": sum(not response.is_complete for response in responses),
        "questions_count": len(question_items),
        "questions_with_high_real_missing": sum(item["rates"]["real_missing_rate"] >= 30 for item in question_items),
        "questions_with_high_not_reached": sum(item["rates"]["not_reached_rate"] >= 20 for item in question_items),
        "questions_mostly_hidden_by_branching": sum(item["rates"]["not_shown_by_branching_rate"] >= 50 for item in question_items),
    }
    recommendations = []
    if summary["questions_with_high_real_missing"]:
        recommendations.append("Проверьте формулировки и обязательность вопросов с высокой долей реальных пропусков.")
    if summary["questions_with_high_not_reached"]:
        recommendations.append("Проверьте длину анкеты и точки выхода: часть респондентов не доходит до поздних вопросов.")
    if summary["questions_mostly_hidden_by_branching"]:
        recommendations.append("Сверьте условия ветвления для часто скрытых вопросов; структурные пропуски не являются ошибкой заполнения.")

    return {
        "summary": summary,
        "questions": question_items,
        "warnings": warnings,
        "recommendations": recommendations,
        "note": "Реальными пропусками считаются только пропуски после показа вопроса. Ветвление, незавершенное прохождение и отсев учитываются отдельно.",
    }


# ---- Question type analysis layer ----------------------------------------

