import csv
import io
import re

from .models import Question


METADATA_COLUMNS = [
    "response_id",
    "user_id",
    "user_email",
    "started_at",
    "finished_at",
    "duration_seconds",
    "is_complete",
    "completion_type",
    "status",
    "screened_out_reason",
]


def _column_label(value):
    label = re.sub(r"[^\w]+", "_", str(value or "").strip(), flags=re.UNICODE)
    return label.strip("_")[:80]


def _question_prefix(question):
    label = _column_label(question.short_label or question.text)
    return f"q_{question.id}" + (f"__{label}" if label else "")


def _coded_value(item):
    return item.value or item.text


def _build_question_columns(question):
    prefix = _question_prefix(question)

    if question.qtype == Question.MULTI:
        return [
            (f"{prefix}__option_{option.id}__{_column_label(option.text)}", ("option", option.id))
            for option in question.options.all()
        ]

    if question.qtype == Question.RANKING:
        return [
            (f"{prefix}__option_{option.id}__{_column_label(option.text)}__rank", ("rank", option.id))
            for option in question.options.all()
        ]

    if question.qtype == Question.MATRIX_SINGLE:
        return [
            (f"{prefix}__row_{row.id}__{_column_label(row.text)}", ("matrix_row", row.id))
            for row in question.matrix_rows.all()
        ]

    if question.qtype == Question.MATRIX_MULTI:
        return [
            (
                f"{prefix}__row_{row.id}__{_column_label(row.text)}"
                f"__column_{column.id}__{_column_label(column.text)}",
                ("matrix_cell", row.id, column.id),
            )
            for row in question.matrix_rows.all()
            for column in question.matrix_columns.all()
        ]

    return [(prefix, ("value",))]


def _answer_value(question, answer, descriptor):
    if answer is None:
        return ""

    kind = descriptor[0]
    selected_options = list(answer.selected_options.all())

    if kind == "option":
        selected_ids = {option.id for option in selected_options}
        return 1 if descriptor[1] in selected_ids else 0

    if kind == "rank":
        ranks = {item.option_id: item.rank for item in answer.ranking_items.all()}
        return ranks.get(descriptor[1], "")

    if kind == "matrix_row":
        cells = [cell for cell in answer.matrix_cells.all() if cell.row_id == descriptor[1]]
        return _coded_value(cells[0].column) if cells else ""

    if kind == "matrix_cell":
        selected_cells = {
            (cell.row_id, cell.column_id)
            for cell in answer.matrix_cells.all()
        }
        return 1 if (descriptor[1], descriptor[2]) in selected_cells else 0

    if question.qtype in {Question.SINGLE, Question.DROPDOWN, Question.YESNO}:
        return _coded_value(selected_options[0]) if selected_options else ""

    if question.qtype in {Question.SCALE, Question.NUMBER}:
        return answer.num if answer.num is not None else ""

    return answer.text or ""


def _completion_type(response):
    if response.screened_out or response.complete_reason == "screened_out":
        return "screened_out"
    if response.is_complete:
        return "completed"
    return "incomplete"


def _isoformat(value):
    return value.isoformat() if value else ""


def build_responses_csv(survey, responses) -> bytes:
    questions = list(
        survey.questions
        .prefetch_related("options", "matrix_rows", "matrix_columns")
        .order_by("page__order", "order", "id")
    )
    question_columns = [
        (question, column_name, descriptor)
        for question in questions
        for column_name, descriptor in _build_question_columns(question)
    ]

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(METADATA_COLUMNS + [column[1] for column in question_columns])

    for response in responses:
        answers = {answer.question_id: answer for answer in response.answers.all()}
        duration = ""
        if response.finished_at and response.started_at:
            duration = round((response.finished_at - response.started_at).total_seconds(), 3)

        row = [
            response.id,
            response.user_id or "",
            response.user.email if response.user else "",
            _isoformat(response.started_at),
            _isoformat(response.finished_at),
            duration,
            1 if response.is_complete else 0,
            _completion_type(response),
            response.status,
            response.screened_out_reason,
        ]
        row.extend(
            _answer_value(question, answers.get(question.id), descriptor)
            for question, _, descriptor in question_columns
        )
        writer.writerow(row)

    return ("\ufeff" + output.getvalue()).encode("utf-8")
