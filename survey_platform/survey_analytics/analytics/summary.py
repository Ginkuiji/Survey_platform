from . import common as _common
from . import visibility as _visibility
from . import question_types as _question_types
globals().update({name: getattr(_common, name) for name in dir(_common) if not name.startswith("__")})
globals().update({name: getattr(_visibility, name) for name in dir(_visibility) if not name.startswith("__")})
globals().update({name: getattr(_question_types, name) for name in dir(_question_types) if not name.startswith("__")})

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
