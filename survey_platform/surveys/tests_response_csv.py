import csv
import io

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import (
    Answer,
    MatrixAnswerCell,
    MatrixColumn,
    MatrixRow,
    Option,
    Question,
    RankingAnswerItem,
    Response,
    Survey,
)
from .response_csv_export import build_responses_csv


class ResponsesCsvExportTests(TestCase):
    def test_builds_wide_machine_readable_dataset(self):
        user = get_user_model().objects.create_user(
            username="respondent",
            email="respondent@example.com",
            password="password",
        )
        survey = Survey.objects.create(title="Export survey")

        number = Question.objects.create(
            survey=survey,
            text="Возраст",
            qtype=Question.NUMBER,
            order=0,
        )
        multi = Question.objects.create(
            survey=survey,
            text="Каналы связи",
            qtype=Question.MULTI,
            order=1,
        )
        email_option = Option.objects.create(
            question=multi,
            text="Email",
            value="email",
            order=0,
        )
        phone_option = Option.objects.create(
            question=multi,
            text="Телефон",
            value="phone",
            order=1,
        )
        matrix = Question.objects.create(
            survey=survey,
            text="Оценка",
            qtype=Question.MATRIX_MULTI,
            order=2,
        )
        matrix_row = MatrixRow.objects.create(
            question=matrix,
            text="Сервис",
            value="service",
            order=0,
        )
        matrix_column = MatrixColumn.objects.create(
            question=matrix,
            text="Хорошо",
            value="good",
            order=0,
        )
        ranking = Question.objects.create(
            survey=survey,
            text="Приоритет",
            qtype=Question.RANKING,
            order=3,
        )
        ranking_option = Option.objects.create(
            question=ranking,
            text="Цена",
            value="price",
            order=0,
        )

        response = Response.objects.create(
            survey=survey,
            user=user,
            session_token="csv-export-test",
            is_complete=True,
            complete_reason="completed",
            finished_at="2026-06-18T10:00:00Z",
        )
        Answer.objects.create(response=response, question=number, num=32)
        multi_answer = Answer.objects.create(response=response, question=multi)
        multi_answer.selected_options.add(email_option)
        matrix_answer = Answer.objects.create(response=response, question=matrix)
        MatrixAnswerCell.objects.create(
            answer=matrix_answer,
            row=matrix_row,
            column=matrix_column,
        )
        ranking_answer = Answer.objects.create(response=response, question=ranking)
        RankingAnswerItem.objects.create(
            answer=ranking_answer,
            option=ranking_option,
            rank=1,
        )

        responses = (
            Response.objects
            .filter(survey=survey)
            .select_related("user")
            .prefetch_related(
                "answers__selected_options",
                "answers__matrix_cells__row",
                "answers__matrix_cells__column",
                "answers__ranking_items__option",
            )
        )
        csv_bytes = build_responses_csv(survey, responses)
        rows = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"))))

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["response_id"], str(response.id))
        self.assertEqual(row["user_email"], "respondent@example.com")
        self.assertEqual(row["completion_type"], "completed")
        self.assertEqual(row[f"q_{number.id}__Возраст"], "32.0")
        self.assertEqual(row[f"q_{multi.id}__Каналы_связи__option_{email_option.id}__Email"], "1")
        self.assertEqual(row[f"q_{multi.id}__Каналы_связи__option_{phone_option.id}__Телефон"], "0")
        self.assertEqual(
            row[
                f"q_{matrix.id}__Оценка__row_{matrix_row.id}__Сервис"
                f"__column_{matrix_column.id}__Хорошо"
            ],
            "1",
        )
        self.assertEqual(
            row[f"q_{ranking.id}__Приоритет__option_{ranking_option.id}__Цена__rank"],
            "1",
        )
