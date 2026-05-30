from .answer_services import (
    CHOICE_QTYPES,
    MATRIX_QTYPES,
    MULTI_CHOICE_QTYPES,
    NUMERIC_QTYPES,
    RANKING_QTYPES,
    TEXT_QTYPES,
    answer_has_value,
)

def extract_answer_value(question, answer_data):
    if not answer_data:
        return None
    if question.qtype in CHOICE_QTYPES:
        selected_options = answer_data.get("selected_options") or []
        return selected_options[0] if selected_options else None
    if question.qtype in MULTI_CHOICE_QTYPES:
        return answer_data.get("selected_options") or []
    if question.qtype in TEXT_QTYPES:
        return (answer_data.get("text") or "").strip()
    if question.qtype in NUMERIC_QTYPES:
        return answer_data.get("num")
    if question.qtype in MATRIX_QTYPES:
        return answer_data.get("matrix_cells") or []
    if question.qtype in RANKING_QTYPES:
        return answer_data.get("ranking_items") or []
    return None


def condition_matches(condition, source_question, answer_data):
    operator = condition.operator

    if operator == "is_answered":
        return bool(answer_data) and answer_has_value(source_question, answer_data)
    if operator == "not_answered":
        return not answer_data or not answer_has_value(source_question, answer_data)

    value = extract_answer_value(source_question, answer_data)

    if operator == "contains_option":
        if not condition.option_id:
            return False
        if source_question.qtype in CHOICE_QTYPES:
            return value == condition.option_id
        if source_question.qtype in MULTI_CHOICE_QTYPES:
            return condition.option_id in value
        return False

    if operator in ("contains_matrix_cell", "matrix_row_equals", "matrix_row_not_equals"):
        if source_question.qtype not in MATRIX_QTYPES or not condition.matrix_row_id or not condition.matrix_column_id:
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


def evaluate_conditions(conditions, answers_by_question, questions_by_id):
    groups = {}
    for index, condition in enumerate(conditions):
        group_key = condition.group_id or f"__condition_{condition.id or index}"
        groups.setdefault(group_key, []).append(condition)

    matched_conditions = []
    for group_conditions in groups.values():
        group_results = []
        for condition in group_conditions:
            source_question = questions_by_id.get(condition.source_question_id)
            if not source_question:
                group_results.append((condition, False))
                continue

            answer_data = answers_by_question.get(condition.source_question_id)
            group_results.append((
                condition,
                condition_matches(condition, source_question, answer_data),
            ))

        group = group_conditions[0].group
        group_logic = group.logic if group else "all"
        if group_logic == "any":
            matched_conditions.extend(
                condition for condition, matches in group_results if matches
            )
        elif all(matches for _, matches in group_results):
            matched_conditions.extend(group_conditions)

    return matched_conditions
