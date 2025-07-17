import uuid
from typing import Sequence

from common.enums import TestAttemptStatus
from common.paginations import PaginationTest
from .exceptions import ExceptionStudent
from .models import TestAttempt
from .repository import StudentRepository
from .schemas import (
    StudentAnswerIn,
    TestResultOut,
    AttemptHistoryItemOut,
    StudentStatsOut,
)
from profile.teacher.models import Test


class StudentServices:
    def __init__(self, repository: StudentRepository):
        self.repo = repository

    async def list_available_tests(
        self, pagination: PaginationTest, search_test
    ) -> Sequence[Test]:
        """Возвращает список опубликованных тестов."""
        return await self.repo.get_published_tests(
            offset=pagination.offset, limit=pagination.limit, search_test=search_test
        )

    async def get_student_stats(self, student_id: int) -> StudentStatsOut:
        """Возвращает статистику по попыткам студента."""
        stats_data = await self.repo.get_student_stats(student_id=student_id)
        return StudentStatsOut(**stats_data)

    async def get_attempt_history(
        self, student_id: int, pagination: PaginationTest
    ) -> list[AttemptHistoryItemOut]:
        """Возвращает историю попыток студента."""
        attempts = await self.repo.get_attempts_by_student_id(
            student_id=student_id,
            offset=pagination.offset,
            limit=pagination.limit,
        )
        # Преобразуем данные из моделей SQLAlchemy в Pydantic схемы
        return [
            AttemptHistoryItemOut(
                attempt_id=attempt.attempt_id,
                status=attempt.status,
                score=attempt.score,
                started_at=attempt.created_at,
                completed_at=(
                    attempt.updated_at
                    if attempt.status == TestAttemptStatus.COMPLETED
                    else None
                ),
                test_title=attempt.test.title,
            )
            for attempt in attempts
        ]

    async def get_test_for_passing(self, test_id: uuid.UUID) -> Test:
        """
        Возвращает один тест со всеми вопросами и вариантами ответов
        (без флагов is_correct) для прохождения студентом.
        """
        test = await self.repo.get_test_for_student_by_id(test_id=test_id)
        if not test:
            raise ExceptionStudent.TestNotFound(test_id=test_id)
        return test

    async def start_test(self, student_id: int, test_id: uuid.UUID) -> TestAttempt:
        """Начинает новую попытку прохождения теста."""
        # Проверяем, есть ли у студента уже активная попытка
        if await self.repo.has_active_attempt(student_id=student_id):
            raise ExceptionStudent.ActiveTestAttemptExists()

        # Проверяем, существует ли тест и опубликован ли он
        test = await self.repo.get_test_for_student_by_id(test_id=test_id)
        if not test:
            raise ExceptionStudent.TestNotFound(test_id=test_id)

        # Создаем попытку
        attempt = await self.repo.create_test_attempt(
            student_id=student_id, test_id=test_id
        )
        return attempt

    async def submit_answer(
        self, attempt_id: uuid.UUID, answer_data: StudentAnswerIn
    ) -> dict:
        """
        Принимает и проверяет ответ студента.
        Поддерживает вопросы с несколькими правильными ответами.
        """
        # 1. Проверяем, существует ли попытка и не завершена ли она
        attempt = await self.repo.get_attempt_with_results(attempt_id=attempt_id)
        if not attempt:
            raise ExceptionStudent.AttemptNotFound(attempt_id=attempt_id)
        if attempt.status == TestAttemptStatus.COMPLETED:
            raise ExceptionStudent.AttemptAlreadyFinished(attempt_id=attempt_id)

        # 2. Находим все правильные варианты ответа для данного вопроса
        correct_answers = await self.repo.get_correct_answers_for_question(
            question_id=answer_data.question_id
        )
        correct_answer_ids = {ans.answer_id for ans in correct_answers}

        # 3. Проверяем, что для вопроса существуют правильные ответы
        # (проверка на корректность составления теста)
        question_exists_in_test = any(
            q.question_id == answer_data.question_id for q in attempt.test.questions
        )
        if not question_exists_in_test:
            raise ExceptionStudent.QuestionNotFoundInTest(
                question_id=answer_data.question_id, test_id=attempt.test_id
            )

        # 4. Сравниваем набор ответов студента с набором правильных ответов
        chosen_ids = set(answer_data.chosen_answer_option_ids)
        is_correct = chosen_ids == correct_answer_ids

        # 5. Сохраняем ответ студента
        await self.repo.save_student_answer(
            attempt_id=attempt_id,
            question_id=answer_data.question_id,
            chosen_option_ids=answer_data.chosen_answer_option_ids,
            is_correct=is_correct,
        )

        # 6. Возвращаем результат
        return {
            "is_correct": is_correct,
            "correct_answer_option_ids": list(correct_answer_ids),
        }

    async def finish_test(self, attempt_id: uuid.UUID):
        """Завершает попытку и рассчитывает результат."""
        attempt = await self.repo.get_attempt_with_results(attempt_id=attempt_id)
        if not attempt:
            raise ExceptionStudent.AttemptNotFound(attempt_id=attempt_id)
        if attempt.status == TestAttemptStatus.COMPLETED:
            raise ExceptionStudent.AttemptAlreadyFinished(attempt_id=attempt_id)

        total_possible_points = sum(q.points for q in attempt.test.questions)
        earned_points = sum(
            ans.question.points for ans in attempt.student_answers if ans.is_correct
        )

        score_percentage = (
            (earned_points / total_possible_points) * 100
            if total_possible_points > 0
            else 0
        )

        test_attempt = await self.repo.update_test_attempt(
            attempt_id=attempt_id,
            status=TestAttemptStatus.COMPLETED,
            score=score_percentage,
        )

        result = TestResultOut(
            attempt_id=attempt_id,
            test_id=attempt.test_id,
            status=TestAttemptStatus.COMPLETED,
            score=score_percentage,
            total_possible_points=total_possible_points,
            earned_points=earned_points,
            started_at=test_attempt.created_at,
            completed_at=test_attempt.updated_at,
        )
        return result
