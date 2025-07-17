import uuid
from typing import Sequence

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from common.enums import TestStatus, TestAttemptStatus
from profile.student.models import TestAttempt, StudentAnswer
from profile.teacher.models import Test, AnswerOption, Question
from profile.teacher.schemas import SearchTest


class StudentRepository:
    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session

    async def get_published_tests(
        self, offset: int, limit: int, search_test: SearchTest
    ) -> Sequence[Test]:
        """
        Получает список опубликованных тестов.
        Поддерживает поиск по названию и описанию.
        """
        stmt = (
            select(Test)
            .where(Test.status == TestStatus.PUBLISHED)
            .order_by(Test.created_at.desc())
        )
        if search_test.title:
            stmt = stmt.where(Test.title.ilike(f"%{search_test.title}%"))
        if search_test.description:
            stmt = stmt.where(Test.description.ilike(f"%{search_test.description}%"))

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_test_for_student_by_id(self, test_id: uuid.UUID) -> Test | None:
        """
        Получает один тест со всеми его вопросами и вариантами ответов
        для прохождения студентом.
        """
        stmt = (
            select(Test)
            .where(Test.test_id == test_id, Test.status == TestStatus.PUBLISHED)
            .options(
                selectinload(Test.questions).options(
                    selectinload(Question.answer_options)
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def has_active_attempt(self, student_id: int) -> bool:
        """Проверяет, есть ли у студента активная (незавершенная) попытка."""
        stmt = select(TestAttempt.attempt_id).where(
            TestAttempt.student_id == student_id,
            TestAttempt.status == TestAttemptStatus.IN_PROGRESS,
        )
        result = await self.session.execute(select(stmt.exists()))
        return result.scalar()

    async def create_test_attempt(
        self, student_id: int, test_id: uuid.UUID
    ) -> TestAttempt:
        """Создает новую запись о попытке прохождения теста."""
        new_attempt = TestAttempt(student_id=student_id, test_id=test_id)
        self.session.add(new_attempt)
        await self.session.commit()
        await self.session.refresh(new_attempt)
        return new_attempt

    async def get_correct_answers_for_question(
        self, question_id: uuid.UUID
    ) -> Sequence[AnswerOption]:
        """Находит все правильные варианты ответа для указанного вопроса."""
        stmt = select(AnswerOption).where(
            AnswerOption.question_id == question_id, AnswerOption.is_correct.is_(True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def save_student_answer(
        self,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
        chosen_option_ids: list[uuid.UUID],
        is_correct: bool,
    ) -> StudentAnswer:
        """
        Сохраняет или обновляет ответ студента, включая несколько выбранных вариантов.
        """
        # Ищем существующий ответ на этот вопрос в данной попытке
        stmt = (
            select(StudentAnswer)
            .where(
                StudentAnswer.attempt_id == attempt_id,
                StudentAnswer.question_id == question_id,
            )
            .options(selectinload(StudentAnswer.chosen_options))
        )
        result = await self.session.execute(stmt)
        student_answer = result.scalar_one_or_none()

        # Получаем объекты выбранных вариантов ответа
        chosen_options_stmt = select(AnswerOption).where(
            AnswerOption.answer_id.in_(chosen_option_ids)
        )
        answer_options = await self.session.execute(chosen_options_stmt)
        chosen_options = answer_options.scalars().all()
        if student_answer:
            # Если ответ существует, обновляем его
            student_answer.is_correct = is_correct
            student_answer.chosen_options = chosen_options
        else:
            # Если ответа нет, создаем новый
            student_answer = StudentAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
                is_correct=is_correct,
                chosen_options=chosen_options,
            )
            self.session.add(student_answer)

        await self.session.commit()
        await self.session.refresh(student_answer)
        return student_answer

    async def get_attempt_with_results(
        self, attempt_id: uuid.UUID
    ) -> TestAttempt | None:
        """
        Получает попытку со всеми ответами студента и информацией о вопросах,
        чтобы можно было рассчитать итоговый балл.
        """
        stmt = (
            select(TestAttempt)
            .where(TestAttempt.attempt_id == attempt_id)
            .options(
                selectinload(TestAttempt.student_answers).joinedload(
                    StudentAnswer.question
                ),
                joinedload(TestAttempt.test).selectinload(Test.questions),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_test_attempt(self, attempt_id: uuid.UUID, **kwargs) -> TestAttempt:
        """Обновляет данные попытки (статус, итоговый балл)."""
        stmt = (
            update(TestAttempt)
            .where(TestAttempt.attempt_id == attempt_id)
            .values(**kwargs)
            .returning(TestAttempt)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_attempts_by_student_id(
        self, student_id: int, offset: int, limit: int
    ) -> Sequence[TestAttempt]:
        """Получает историю попыток для указанного студента."""
        stmt = (
            select(TestAttempt)
            .where(TestAttempt.student_id == student_id)
            .options(joinedload(TestAttempt.test))
            .order_by(TestAttempt.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_student_stats(self, student_id: int) -> dict:
        """Собирает статистику по попыткам для указанного студента."""
        stmt = select(
            func.count(TestAttempt.attempt_id)
            .filter(TestAttempt.status == TestAttemptStatus.COMPLETED)
            .label("total_tests_completed"),
            func.avg(TestAttempt.score)
            .filter(TestAttempt.status == TestAttemptStatus.COMPLETED)
            .label("average_score"),
            func.count(TestAttempt.attempt_id)
            .filter(TestAttempt.status == TestAttemptStatus.IN_PROGRESS)
            .label("in_progress_count"),
        ).where(TestAttempt.student_id == student_id)
        result = await self.session.execute(stmt)
        stats = result.one()
        return {
            "total_tests_completed": stats.total_tests_completed or 0,
            "average_score": stats.average_score,
            "in_progress_count": stats.in_progress_count or 0,
        }
