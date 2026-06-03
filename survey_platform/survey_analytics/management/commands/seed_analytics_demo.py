import random
import secrets
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from surveys.models import (
    Survey,
    SurveyPage,
    Question,
    Option,
    Response,
    Answer,
    MatrixRow,
    MatrixColumn,
    MatrixAnswerCell,
    RankingAnswerItem,
)


class Command(BaseCommand):
    help = "Create demo survey data for analytics testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--responses",
            type=int,
            default=120,
            help="Number of normally completed responses to create",
        )
        parser.add_argument(
            "--screened-out",
            type=int,
            default=25,
            help="Number of screened out responses to create",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previous demo survey before creating a new one",
        )

    def handle(self, *args, **options):
        responses_count = options["responses"]
        screened_out_count = options["screened_out"]

        with transaction.atomic():
            if options["clear"]:
                Survey.objects.filter(title="Демо: аналитика удовлетворенности сервисом").delete()

            survey = Survey.objects.create(
                title="Демо: аналитика удовлетворенности сервисом",
                description=(
                    "Тестовый опрос для проверки описательной аналитики, "
                    "корреляции, χ², таблиц сопряженности и линейной регрессии."
                ),
                status="active",
                starts_at=timezone.now() - timedelta(days=1),
                ends_at=timezone.now() + timedelta(days=30),
                is_anonymous=True,
                randomize_pages=False,
            )

            pages = self.create_pages(survey)
            questions = self.create_questions(survey, pages)

            self.create_completed_responses(survey, questions, responses_count)
            self.create_screened_out_responses(survey, screened_out_count)

        self.stdout.write(self.style.SUCCESS("Demo analytics survey created successfully."))
        self.stdout.write(f"Survey id: {survey.id}")
        self.stdout.write(f"Normal completed responses: {responses_count}")
        self.stdout.write(f"Screened out responses: {screened_out_count}")

        self.stdout.write("")
        self.stdout.write("Question ids for manual API tests:")
        for key, question in questions.items():
            self.stdout.write(f"{key}: id={question.id}, type={question.qtype}, text={question.text}")

    def create_pages(self, survey):
        page1 = SurveyPage.objects.create(
            survey=survey,
            title="Профиль респондента",
            description="Базовые сведения о респонденте.",
            order=0,
        )
        page2 = SurveyPage.objects.create(
            survey=survey,
            title="Оценка сервиса",
            description="Оценка опыта использования сервиса.",
            order=1,
        )
        page3 = SurveyPage.objects.create(
            survey=survey,
            title="Приоритеты и характеристики",
            description="Ранжирование факторов и матричная оценка.",
            order=2,
        )
        return {
            "profile": page1,
            "evaluation": page2,
            "details": page3,
        }

    def create_question(self, survey, page, text, qtype, order, required=True, qsettings=None, short_label=""):
        return Question.objects.create(
            survey=survey,
            page=page,
            text=text,
            short_label=short_label,
            qtype=qtype,
            order=order,
            required=required,
            qsettings=qsettings or {},
        )

    def create_options(self, question, values):
        options = []
        for index, item in enumerate(values):
            if isinstance(item, tuple):
                text, value = item
            else:
                text, value = item, ""
            options.append(
                Option.objects.create(
                    question=question,
                    text=text,
                    value=value,
                    order=index,
                )
            )
        return options

    def create_matrix_rows(self, question, values):
        rows = []
        for index, text in enumerate(values):
            rows.append(
                MatrixRow.objects.create(
                    question=question,
                    text=text,
                    value=str(index + 1),
                    order=index,
                )
            )
        return rows

    def create_matrix_columns(self, question, values):
        columns = []
        for index, text in enumerate(values):
            columns.append(
                MatrixColumn.objects.create(
                    question=question,
                    text=text,
                    value=str(index + 1),
                    order=index,
                )
            )
        return columns

    def create_questions(self, survey, pages):
        q_gender = self.create_question(
            survey, pages["profile"], "Пол", Question.SINGLE, 0, short_label="Пол"
        )
        self.create_options(q_gender, [("Женский", "female"), ("Мужской", "male")])

        q_age = self.create_question(
            survey,
            pages["profile"],
            "Возраст",
            Question.NUMBER,
            1,
            qsettings={"min": 14, "max": 70, "integer": True},
            short_label="Возраст",
        )

        q_group = self.create_question(
            survey,
            pages["profile"],
            "Группа пользователя",
            Question.DROPDOWN,
            2,
            short_label="Группа",
        )
        self.create_options(q_group, [
            ("Студент", "student"),
            ("Сотрудник", "employee"),
            ("Руководитель", "manager"),
        ])

        q_experience = self.create_question(
            survey,
            pages["profile"],
            "Есть опыт использования аналогичных сервисов?",
            Question.YESNO,
            3,
            short_label="Опыт",
        )
        self.create_options(q_experience, [("Да", "yes"), ("Нет", "no")])

        q_usage = self.create_question(
            survey,
            pages["evaluation"],
            "Как часто вы используете сервис?",
            Question.SCALE,
            0,
            qsettings={"min": 1, "max": 5, "step": 1},
            short_label="Частота",
        )

        q_satisfaction = self.create_question(
            survey,
            pages["evaluation"],
            "Насколько вы удовлетворены сервисом?",
            Question.SCALE,
            1,
            qsettings={"min": 1, "max": 5, "step": 1},
            short_label="Удовлетворенность",
        )

        q_recommend = self.create_question(
            survey,
            pages["evaluation"],
            "Насколько вероятно, что вы порекомендуете сервис?",
            Question.SCALE,
            2,
            qsettings={"min": 1, "max": 10, "step": 1},
            short_label="Рекомендация",
        )

        q_features = self.create_question(
            survey,
            pages["evaluation"],
            "Какие функции для вас наиболее важны?",
            Question.MULTI,
            3,
            short_label="Важные функции",
        )
        self.create_options(q_features, [
            ("Удобный интерфейс", "ui"),
            ("Быстрая работа", "speed"),
            ("Гибкая аналитика", "analytics"),
            ("Экспорт отчетов", "export"),
            ("Настройка ветвления", "branching"),
        ])

        q_ranking = self.create_question(
            survey,
            pages["details"],
            "Расставьте факторы выбора сервиса по важности",
            Question.RANKING,
            0,
            qsettings={"full_ranking": True},
            short_label="Приоритет факторов",
        )
        self.create_options(q_ranking, [
            ("Цена", "price"),
            ("Функциональность", "features"),
            ("Удобство", "usability"),
            ("Надежность", "reliability"),
        ])

        q_matrix = self.create_question(
            survey,
            pages["details"],
            "Оцените характеристики сервиса",
            Question.MATRIX_SINGLE,
            1,
            short_label="Матрица оценки",
        )
        self.create_matrix_rows(q_matrix, [
            "Интерфейс",
            "Скорость работы",
            "Качество аналитики",
            "Удобство настройки",
        ])
        self.create_matrix_columns(q_matrix, [
            "Плохо",
            "Удовлетворительно",
            "Хорошо",
            "Отлично",
        ])

        return {
            "gender": q_gender,
            "age": q_age,
            "group": q_group,
            "experience": q_experience,
            "usage": q_usage,
            "satisfaction": q_satisfaction,
            "recommend": q_recommend,
            "features": q_features,
            "ranking": q_ranking,
            "matrix": q_matrix,
        }

    def add_selected_answer(self, response, question, option):
        answer = Answer.objects.create(response=response, question=question)
        answer.selected_options.set([option])
        return answer

    def add_multi_answer(self, response, question, options):
        answer = Answer.objects.create(response=response, question=question)
        answer.selected_options.set(options)
        return answer

    def add_num_answer(self, response, question, value):
        return Answer.objects.create(
            response=response,
            question=question,
            num=value,
        )

    def add_ranking_answer(self, response, question, preferred_order):
        answer = Answer.objects.create(response=response, question=question)
        for rank, option in enumerate(preferred_order, start=1):
            RankingAnswerItem.objects.create(
                answer=answer,
                option=option,
                rank=rank,
            )
        return answer

    def add_matrix_single_answer(self, response, question, satisfaction):
        answer = Answer.objects.create(response=response, question=question)
        rows = list(question.matrix_rows.all().order_by("order", "id"))
        columns = list(question.matrix_columns.all().order_by("order", "id"))

        # satisfaction 1..5 переводим в оценку 1..4
        base_column_index = max(0, min(3, round(satisfaction) - 1))

        for row in rows:
            noisy_index = max(0, min(3, base_column_index + random.choice([-1, 0, 0, 1])))
            MatrixAnswerCell.objects.create(
                answer=answer,
                row=row,
                column=columns[noisy_index],
            )

        return answer

    def create_completed_responses(self, survey, questions, count):
        gender_options = list(questions["gender"].options.all().order_by("order", "id"))
        group_options = list(questions["group"].options.all().order_by("order", "id"))
        yesno_options = list(questions["experience"].options.all().order_by("order", "id"))
        feature_options = list(questions["features"].options.all().order_by("order", "id"))
        ranking_options = list(questions["ranking"].options.all().order_by("order", "id"))

        now = timezone.now()

        for index in range(count):
            started_at = now - timedelta(days=random.randint(0, 14), minutes=random.randint(1, 300))
            finished_at = started_at + timedelta(minutes=random.randint(3, 18))

            response = Response.objects.create(
                survey=survey,
                session_token=secrets.token_urlsafe(24),
                started_at=started_at,
                is_complete=True,
                finished_at=finished_at,
                status="active",
                complete_reason="completed",
                client_meta={"seed": "analytics_demo"},
            )

            # Так как started_at auto_now_add, обновляем вручную после create
            Response.objects.filter(id=response.id).update(
                started_at=started_at,
                finished_at=finished_at,
            )
            response.started_at = started_at
            response.finished_at = finished_at

            age = random.randint(18, 60)
            gender = random.choice(gender_options)
            group = random.choices(group_options, weights=[0.55, 0.3, 0.15], k=1)[0]
            has_experience = random.random() < 0.72
            experience_option = yesno_options[0] if has_experience else yesno_options[1]

            usage = random.choices([1, 2, 3, 4, 5], weights=[8, 14, 25, 32, 21], k=1)[0]

            # Искусственная зависимость: опыт и частота повышают удовлетворенность
            satisfaction_raw = (
                1.2
                + usage * 0.65
                + (0.45 if has_experience else -0.15)
                + random.uniform(-0.8, 0.8)
            )
            satisfaction = int(round(max(1, min(5, satisfaction_raw))))

            # Рекомендация зависит от удовлетворенности и частоты
            recommend_raw = (
                satisfaction * 1.45
                + usage * 0.45
                + random.uniform(-1.2, 1.2)
            )
            recommend = int(round(max(1, min(10, recommend_raw))))

            self.add_selected_answer(response, questions["gender"], gender)
            self.add_num_answer(response, questions["age"], age)
            self.add_selected_answer(response, questions["group"], group)
            self.add_selected_answer(response, questions["experience"], experience_option)
            self.add_num_answer(response, questions["usage"], usage)
            self.add_num_answer(response, questions["satisfaction"], satisfaction)
            self.add_num_answer(response, questions["recommend"], recommend)

            feature_weights = {
                "ui": 0.60 + satisfaction * 0.04,
                "speed": 0.55 + usage * 0.05,
                "analytics": 0.35 + (0.20 if group.value in ("employee", "manager") else 0.05),
                "export": 0.28 + (0.25 if group.value == "manager" else 0.08),
                "branching": 0.30 + (0.20 if has_experience else 0.00),
            }
            selected_features = [
                option
                for option in feature_options
                if random.random() < min(feature_weights.get(option.value, 0.4), 0.9)
            ]
            if not selected_features:
                selected_features = [random.choice(feature_options)]
            self.add_multi_answer(response, questions["features"], selected_features)

            # Ранжирование: при высокой удовлетворенности чаще важны удобство и функциональность,
            # при низкой — цена.
            ranking_pool = ranking_options[:]
            if satisfaction >= 4:
                ranking_pool.sort(
                    key=lambda option: {
                        "usability": 0,
                        "features": 1,
                        "reliability": 2,
                        "price": 3,
                    }.get(option.value, 10)
                )
            elif satisfaction <= 2:
                ranking_pool.sort(
                    key=lambda option: {
                        "price": 0,
                        "reliability": 1,
                        "features": 2,
                        "usability": 3,
                    }.get(option.value, 10)
                )
            else:
                random.shuffle(ranking_pool)

            # Немного случайности в порядке
            if random.random() < 0.25:
                a, b = random.sample(range(len(ranking_pool)), 2)
                ranking_pool[a], ranking_pool[b] = ranking_pool[b], ranking_pool[a]

            self.add_ranking_answer(response, questions["ranking"], ranking_pool)
            self.add_matrix_single_answer(response, questions["matrix"], satisfaction)

    def create_screened_out_responses(self, survey, count):
        reasons = [
            "Не подходит по возрасту",
            "Нет опыта использования аналогичных сервисов",
            "Не входит в целевую группу исследования",
        ]

        now = timezone.now()

        for _ in range(count):
            started_at = now - timedelta(days=random.randint(0, 14), minutes=random.randint(1, 300))
            screened_out_at = started_at + timedelta(minutes=random.randint(1, 4))
            reason = random.choices(reasons, weights=[0.45, 0.35, 0.20], k=1)[0]

            response = Response.objects.create(
                survey=survey,
                session_token=secrets.token_urlsafe(24),
                is_complete=True,
                finished_at=screened_out_at,
                screened_out=True,
                screened_out_at=screened_out_at,
                screened_out_reason=reason,
                complete_reason="screened_out",
                status="active",
                client_meta={"seed": "analytics_demo", "screened_out": True},
            )

            Response.objects.filter(id=response.id).update(
                started_at=started_at,
                finished_at=screened_out_at,
                screened_out_at=screened_out_at,
            )