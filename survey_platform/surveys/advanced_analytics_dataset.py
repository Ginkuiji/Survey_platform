from dataclasses import dataclass
from typing import Any

from .analytics import (
    build_visibility_by_question,
    get_completed_normal_responses,
    get_survey_conditions,
    get_survey_pages,
)
from .models import Answer, Question


@dataclass
class AnalysisVariable:
    code: str
    label: str
    question_id: int
    qtype: str
    measure: str
    encoding: str


@dataclass
class AnalysisDataset:
    rows: list[dict[str, Any]]
    variables: list[AnalysisVariable]
    response_ids: list[int]


def _ordered_options(question: Question):
    return list(question.options.all().order_by("order", "id"))


def _ordered_matrix_rows(question: Question):
    return list(question.matrix_rows.all().order_by("order", "id"))


def _ordered_matrix_columns(question: Question):
    return list(question.matrix_columns.all().order_by("order", "id"))


def _question_label(question: Question) -> str:
    return question.short_label or question.text


def _unsupported(question: Question, encoding: str) -> ValueError:
    return ValueError(
        f"Unsupported advanced analytics encoding '{encoding}' "
        f"for question {question.id} ({question.qtype})."
    )


def _variables_for_spec(question: Question, encoding: str, measure: str) -> list[AnalysisVariable]:
    base_label = _question_label(question)

    if question.qtype in (Question.NUMBER, Question.SCALE) and encoding == "numeric":
        return [AnalysisVariable(f"q_{question.id}", base_label, question.id, question.qtype, measure, encoding)]

    if question.qtype == Question.YESNO and encoding == "binary":
        return [AnalysisVariable(f"q_{question.id}", base_label, question.id, question.qtype, measure, encoding)]

    if question.qtype in (Question.SINGLE, Question.DROPDOWN):
        if encoding == "ordinal":
            return [AnalysisVariable(f"q_{question.id}", base_label, question.id, question.qtype, measure, encoding)]
        if encoding == "one_hot":
            return [
                AnalysisVariable(
                    f"q_{question.id}_opt_{option.id}",
                    f"{base_label}: {option.text}",
                    question.id,
                    question.qtype,
                    measure,
                    encoding,
                )
                for option in _ordered_options(question)
            ]

    if question.qtype == Question.MULTI and encoding == "one_hot":
        return [
            AnalysisVariable(
                f"q_{question.id}_opt_{option.id}",
                f"{base_label}: {option.text}",
                question.id,
                question.qtype,
                measure,
                encoding,
            )
            for option in _ordered_options(question)
        ]

    if question.qtype == Question.RANKING and encoding == "rank":
        return [
            AnalysisVariable(
                f"q_{question.id}_rank_{option.id}",
                f"{base_label}: {option.text} rank",
                question.id,
                question.qtype,
                measure,
                encoding,
            )
            for option in _ordered_options(question)
        ]

    if question.qtype == Question.MATRIX_SINGLE and encoding == "matrix_ordinal":
        return [
            AnalysisVariable(
                f"q_{question.id}_row_{row.id}",
                f"{base_label}: {row.text}",
                question.id,
                question.qtype,
                measure,
                encoding,
            )
            for row in _ordered_matrix_rows(question)
        ]

    if question.qtype == Question.MATRIX_MULTI and encoding == "matrix_multi_binary":
        rows = _ordered_matrix_rows(question)
        columns = _ordered_matrix_columns(question)
        if not rows or not columns:
            return []
        return [
            AnalysisVariable(
                f"q_{question.id}_row_{row.id}_col_{column.id}",
                f"{base_label}: {row.text} -> {column.text}",
                question.id,
                question.qtype,
                measure,
                encoding,
            )
            for row in rows
            for column in columns
        ]

    raise _unsupported(question, encoding)


def _selected_option_ids(answer: Answer | None) -> set[int]:
    if not answer:
        return set()
    return {option.id for option in answer.selected_options.all()}


def _selected_first_option_id(answer: Answer | None) -> int | None:
    if not answer:
        return None
    selected = list(answer.selected_options.all())
    return selected[0].id if selected else None


def _fill_question_values(row: dict[str, Any], question: Question, encoding: str, answer: Answer | None, shown: bool):
    variables = _variables_for_spec(question, encoding, measure="")
    if not shown:
        for variable in variables:
            row[variable.code] = None
        return

    if question.qtype in (Question.NUMBER, Question.SCALE) and encoding == "numeric":
        row[f"q_{question.id}"] = answer.num if answer else None
        return

    if question.qtype == Question.YESNO and encoding == "binary":
        options = _ordered_options(question)
        selected_id = _selected_first_option_id(answer)
        if not selected_id or len(options) < 2:
            row[f"q_{question.id}"] = None
        elif selected_id == options[0].id:
            row[f"q_{question.id}"] = 1
        elif selected_id == options[1].id:
            row[f"q_{question.id}"] = 0
        else:
            row[f"q_{question.id}"] = None
        return

    if question.qtype in (Question.SINGLE, Question.DROPDOWN) and encoding == "ordinal":
        option_index = {option.id: index for index, option in enumerate(_ordered_options(question), start=1)}
        selected_id = _selected_first_option_id(answer)
        row[f"q_{question.id}"] = option_index.get(selected_id) if selected_id else None
        return

    if question.qtype in (Question.SINGLE, Question.DROPDOWN, Question.MULTI) and encoding == "one_hot":
        selected_ids = _selected_option_ids(answer)
        for option in _ordered_options(question):
            row[f"q_{question.id}_opt_{option.id}"] = 1 if option.id in selected_ids else 0
        return

    if question.qtype == Question.RANKING and encoding == "rank":
        ranks = {}
        if answer:
            ranks = {item.option_id: item.rank for item in answer.ranking_items.all()}
        for option in _ordered_options(question):
            row[f"q_{question.id}_rank_{option.id}"] = ranks.get(option.id)
        return

    if question.qtype == Question.MATRIX_SINGLE and encoding == "matrix_ordinal":
        column_index = {column.id: index for index, column in enumerate(_ordered_matrix_columns(question), start=1)}
        values_by_row = {}
        if answer:
            for cell in answer.matrix_cells.all():
                values_by_row[cell.row_id] = column_index.get(cell.column_id)
        for matrix_row in _ordered_matrix_rows(question):
            row[f"q_{question.id}_row_{matrix_row.id}"] = values_by_row.get(matrix_row.id)
        return

    if question.qtype == Question.MATRIX_MULTI and encoding == "matrix_multi_binary":
        matrix_rows = _ordered_matrix_rows(question)
        matrix_columns = _ordered_matrix_columns(question)
        selected_cells = set()
        if answer:
            selected_cells = {
                (cell.row_id, cell.column_id)
                for cell in answer.matrix_cells.all()
            }
        for matrix_row in matrix_rows:
            for matrix_column in matrix_columns:
                row[f"q_{question.id}_row_{matrix_row.id}_col_{matrix_column.id}"] = (
                    1 if (matrix_row.id, matrix_column.id) in selected_cells else 0
                )
        return

    raise _unsupported(question, encoding)


def build_analysis_dataset(survey_id: int, variable_specs: list[dict]) -> AnalysisDataset:
    if not variable_specs:
        raise ValueError("At least one variable spec is required.")

    question_ids = [spec.get("question_id") for spec in variable_specs]
    if any(question_id is None for question_id in question_ids):
        raise ValueError("Each variable spec must include question_id.")

    questions_by_id = {
        question.id: question
        for question in (
            Question.objects
            .filter(survey_id=survey_id, id__in=question_ids)
            .prefetch_related("options", "matrix_rows", "matrix_columns")
        )
    }
    missing_question_ids = sorted(set(question_ids) - set(questions_by_id))
    if missing_question_ids:
        raise ValueError(f"Questions do not belong to survey or do not exist: {missing_question_ids}.")

    completed_responses = list(
        get_completed_normal_responses(survey_id)
        .prefetch_related(
            "answers",
            "answers__selected_options",
            "answers__matrix_cells__row",
            "answers__matrix_cells__column",
            "answers__ranking_items",
        )
    )
    response_ids = [response.id for response in completed_responses]
    answers = (
        Answer.objects
        .filter(response_id__in=response_ids, question_id__in=question_ids)
        .select_related("question", "response")
        .prefetch_related(
            "selected_options",
            "matrix_cells__row",
            "matrix_cells__column",
            "ranking_items",
        )
    )
    answers_by_response_question = {
        (answer.response_id, answer.question_id): answer
        for answer in answers
    }

    pages = get_survey_pages(survey_id)
    conditions = get_survey_conditions(survey_id)
    visibility_by_question = build_visibility_by_question(completed_responses, pages, conditions)

    variables = []
    normalized_specs = []
    for spec in variable_specs:
        question = questions_by_id[spec["question_id"]]
        encoding = spec.get("encoding")
        measure = spec.get("measure")
        if not encoding or not measure:
            raise ValueError("Each variable spec must include encoding and measure.")
        spec_variables = _variables_for_spec(question, encoding, measure)
        variables.extend(spec_variables)
        normalized_specs.append((question, encoding))

    rows = []
    for response in completed_responses:
        row = {"response_id": response.id}
        for question, encoding in normalized_specs:
            shown = response.id in visibility_by_question.get(question.id, set())
            answer = answers_by_response_question.get((response.id, question.id))
            _fill_question_values(row, question, encoding, answer, shown)
        rows.append(row)

    return AnalysisDataset(rows=rows, variables=variables, response_ids=response_ids)
