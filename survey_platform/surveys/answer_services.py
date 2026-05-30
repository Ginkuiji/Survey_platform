from .models import MatrixAnswerCell, MatrixColumn, MatrixRow, Option, Question, RankingAnswerItem

MATRIX_QTYPES = {Question.MATRIX_SINGLE, Question.MATRIX_MULTI}
CHOICE_QTYPES = {Question.SINGLE, Question.DROPDOWN, Question.YESNO}
MULTI_CHOICE_QTYPES = {Question.MULTI}
TEXT_QTYPES = {Question.TEXT, Question.DATE}
NUMERIC_QTYPES = {Question.SCALE, Question.NUMBER}
RANKING_QTYPES = {Question.RANKING}

ANSWER_FIELDS = {"selected_options", "text", "num", "matrix_cells", "ranking_items"}
ALLOWED_ANSWER_FIELDS = {
    Question.SINGLE: {"selected_options"},
    Question.DROPDOWN: {"selected_options"},
    Question.YESNO: {"selected_options"},
    Question.MULTI: {"selected_options"},
    Question.TEXT: {"text"},
    Question.DATE: {"text"},
    Question.SCALE: {"num"},
    Question.NUMBER: {"num"},
    Question.MATRIX_SINGLE: {"matrix_cells"},
    Question.MATRIX_MULTI: {"matrix_cells"},
    Question.RANKING: {"ranking_items"},
}


def add_matrix_cells(answer, question, cells_data):
    if not isinstance(cells_data, list):
        return "matrix_cells must be a list"
    if any(not isinstance(cell, dict) for cell in cells_data):
        return "matrix_cells must contain objects"

    rows = {
        row.id: row
        for row in MatrixRow.objects.filter(question=question, id__in=[cell.get("row") for cell in cells_data])
    }
    columns = {
        column.id: column
        for column in MatrixColumn.objects.filter(question=question, id__in=[cell.get("column") for cell in cells_data])
    }

    seen_pairs = set()
    seen_rows = set()
    cells = []
    for cell in cells_data:
        row_id = cell.get("row")
        column_id = cell.get("column")
        if row_id not in rows or column_id not in columns:
            return "matrix row or column does not belong to question"

        pair = (row_id, column_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        if question.qtype == Question.MATRIX_SINGLE:
            if row_id in seen_rows:
                return "matrix_single allows only one column per row"
            seen_rows.add(row_id)

        cell_obj = MatrixAnswerCell(answer=answer, row=rows[row_id], column=columns[column_id])
        cell_obj.full_clean()
        cells.append(cell_obj)

    MatrixAnswerCell.objects.bulk_create(cells)
    return None


def is_full_ranking_question(question):
    return question.qsettings.get("full_ranking", True)


def add_ranking_items(answer, question, items_data):
    options = {
        option.id: option
        for option in Option.objects.filter(question=question, id__in=[item.get("option") for item in items_data])
    }

    ranking_items = []
    for item in items_data:
        option_id = item.get("option")
        if option_id not in options:
            return "ranking option does not belong to question"

        ranking_item = RankingAnswerItem(
            answer=answer,
            option=options[option_id],
            rank=item["rank"],
        )
        ranking_item.full_clean()
        ranking_items.append(ranking_item)

    RankingAnswerItem.objects.bulk_create(ranking_items)
    return None


def answer_has_value(question, answer_data):
    if question.qtype in CHOICE_QTYPES | MULTI_CHOICE_QTYPES:
        return bool(answer_data.get("selected_options"))
    if question.qtype in TEXT_QTYPES:
        return bool((answer_data.get("text") or "").strip())
    if question.qtype in NUMERIC_QTYPES:
        return answer_data.get("num") is not None
    if question.qtype in MATRIX_QTYPES:
        return bool(answer_data.get("matrix_cells"))
    if question.qtype in RANKING_QTYPES:
        return bool(answer_data.get("ranking_items"))
    return False


def validate_answer_payload(question, answer_data):
    present_fields = {field for field in ANSWER_FIELDS if field in answer_data}
    allowed_fields = ALLOWED_ANSWER_FIELDS.get(question.qtype, set())
    disallowed_fields = present_fields - allowed_fields

    if disallowed_fields:
        fields = ", ".join(sorted(disallowed_fields))
        return f"Question {question.id} ({question.qtype}) does not allow fields: {fields}"

    if question.required and not answer_has_value(question, answer_data):
        return f"Question {question.id} is required"

    if question.qtype in CHOICE_QTYPES:
        selected_options = answer_data.get("selected_options", [])
        if len(selected_options) > 1:
            return f"Question {question.id} allows only one selected option"

    if question.qtype in CHOICE_QTYPES | MULTI_CHOICE_QTYPES and "selected_options" in answer_data:
        selected_options = answer_data.get("selected_options") or []
        if len(selected_options) != len(set(selected_options)):
            return f"Question {question.id} contains duplicate selected options"

    if question.qtype in MATRIX_QTYPES and "matrix_cells" not in answer_data and question.required:
        return f"Question {question.id} is required"

    if question.qtype == Question.RANKING and "ranking_items" in answer_data:
        ranking_items = answer_data.get("ranking_items") or []
        option_ids = [item["option"] for item in ranking_items]
        ranks = [item["rank"] for item in ranking_items]

        if len(option_ids) != len(set(option_ids)):
            return f"Question {question.id} contains duplicate ranking options"
        if len(ranks) != len(set(ranks)):
            return f"Question {question.id} contains duplicate ranks"

        options_count = question.options.count()
        if is_full_ranking_question(question):
            if len(ranking_items) != options_count:
                return f"Question {question.id} requires ranking all options"
            if set(ranks) != set(range(1, options_count + 1)):
                return f"Question {question.id} requires ranks from 1 to {options_count}"

    return None
