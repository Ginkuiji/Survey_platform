from .models import MatrixColumn, MatrixRow, Option, Question

YESNO_DEFAULT_OPTIONS = (
    {"text": "Да", "value": "yes", "order": 0},
    {"text": "Нет", "value": "no", "order": 1},
)


def create_question_items(question, question_data):
    options = question_data.get("options", [])
    if question.qtype == Question.YESNO and not options:
        options = YESNO_DEFAULT_OPTIONS

    for opt_order, opt in enumerate(options):
        Option.objects.create(
            question=question,
            text=opt["text"],
            value=opt.get("value", ""),
            order=opt.get("order", opt_order),
        )

    for row_order, row in enumerate(question_data.get("matrix_rows", [])):
        MatrixRow.objects.create(
            question=question,
            text=row["text"],
            value=row.get("value", ""),
            order=row.get("order", row_order),
        )

    for column_order, column in enumerate(question_data.get("matrix_columns", [])):
        MatrixColumn.objects.create(
            question=question,
            text=column["text"],
            value=column.get("value", ""),
            order=column.get("order", column_order),
        )
