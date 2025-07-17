import uuid
from typing import Sequence, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    select,
    Result,
    delete,
    update,
    func,
    cast,
    Float,
    case,
    Row,
)
from sqlalchemy.orm import selectinload, joinedload
from common.paginations import PaginationTest
from .models import Test, Question, AnswerOption
from .schemas import SearchTest, SearchStudent
from common.enums import TestStatus, TestAttemptStatus
from profile.student.models import TestAttempt, StudentAnswer
from auth.models import AuthEntity


class TeacherRepository:
    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session

    async def create_test(self, test_data: dict) -> Test:
        new_test = Test(**test_data)
        self.session.add(new_test)
        await self.session.commit()
        await self.session.refresh(new_test)
        return new_test

    async def add_test(self, test: Test) -> Test:
        self.session.add(test)
        await self.session.commit()

        # Re-fetch the object with relationships eagerly loaded to prevent
        stmt = (
            select(Test)
            .where(Test.test_id == test.test_id)
            .options(selectinload(Test.questions).selectinload(Question.answer_options))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_all_tests_by_teacher(self, teacher_id: int) -> Sequence[Test]:
        stmt = (
            select(Test)
            .where(Test.teacher_id == teacher_id)
            .options(selectinload(Test.questions).selectinload(Question.answer_options))
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def show_tests(
        self,
        search_test: SearchTest,
        offset: int,
        limit: int,
        teacher_id: int,
        status_: TestStatus | None = None,
    ) -> Sequence[Test]:
        stmt = select(Test)
        # filter by teacher
        stmt = stmt.where(Test.teacher_id == teacher_id)

        if search_test.title:
            stmt = stmt.where(Test.title.ilike(f"%{search_test.title}%"))
        if search_test.description:
            stmt = stmt.where(Test.description.ilike(f"%{search_test.description}%"))
        if status_:
            stmt = stmt.where(Test.status == status_)

        stmt = stmt.offset(offset).limit(limit)
        result: Result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_test_by_id(self, test_id: uuid.UUID, teacher_id: int) -> Test | None:
        stmt = (
            select(Test)
            .where(Test.test_id == test_id, Test.teacher_id == teacher_id)
            .options(selectinload(Test.questions).selectinload(Question.answer_options))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_test_by_id(
        self, test_id: uuid.UUID, teacher_id: int
    ) -> uuid.UUID | None:
        # delete only tests owned by teacher
        stmt = (
            delete(Test)
            .where(Test.test_id == test_id, Test.teacher_id == teacher_id)
            .returning(Test.test_id)
        )
        result: Result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_all_tests(self, teacher_id: int) -> int:
        # delete all tests for this teacher
        stmt = delete(Test).where(Test.teacher_id == teacher_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def edit_test(
        self, test_data: dict, test_id: uuid.UUID, teacher_id: int
    ) -> Test | None:
        # update only tests owned by teacher
        stmt = (
            update(Test)
            .where(Test.test_id == test_id, Test.teacher_id == teacher_id)
            .values(**test_data)
            .returning(Test)
        )
        result: Result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_answers_by_ids(
        self, answer_ids: list[uuid.UUID]
    ) -> Sequence[AnswerOption]:
        stmt = select(AnswerOption).where(AnswerOption.answer_id.in_(answer_ids))
        return (await self.session.execute(stmt)).scalars().all()

    async def create_question_with_answers(
        self, question_data: dict, answer_options: list[dict]
    ) -> Question:
        new_question = Question(**question_data)
        self.session.add(new_question)

        # flush to get the ID of the new_question
        await self.session.flush()

        answer_objs = []
        for answer in answer_options:
            new_answer = AnswerOption(
                question_id=new_question.question_id,
                **answer,
            )
            answer_objs.append(new_answer)

        self.session.add_all(answer_objs)

        await self.session.commit()
        await self.session.refresh(new_question, attribute_names=["answer_options"])
        return new_question

    async def edit_question_with_answers(
        self,
        test_id: uuid.UUID,
        question_id: uuid.UUID,
        question_data: dict,
        answer_options_data: list[dict] | None,
        answer_ids_to_delete: list[uuid.UUID] | None,
    ) -> Question | None:
        """
        Редактирует вопрос и его ответы, используя пря��ые UPDATE-запросы
        для максимальной производительности.
        """
        # 1. прямое обновление вопроса в БД
        if question_data:
            stmt = (
                update(Question)
                .where(Question.question_id == question_id, Question.test_id == test_id)
                .values(**question_data)
            )
            result = await self.session.execute(stmt)
            if result.rowcount == 0:
                return None  # Вопрос не найден ��ли не принадлежит тесту

        # 2. Удаление ответов
        if answer_ids_to_delete:
            stmt = delete(AnswerOption).where(
                AnswerOption.answer_id.in_(answer_ids_to_delete)
            )
            await self.session.execute(stmt)

        # 3. Обновление существующих и добавление новых ответов
        if answer_options_data is not None:
            new_answers_to_add = []
            for answer_data in answer_options_data:
                answer_id = answer_data.pop("answer_id", None)
                if answer_id:
                    stmt = (
                        update(AnswerOption)
                        .where(AnswerOption.answer_id == answer_id)
                        .values(**answer_data)
                    )
                    await self.session.execute(stmt)
                else:
                    # Это новый ответ, создаем объект для добавления
                    new_answer = AnswerOption(question_id=question_id, **answer_data)
                    new_answers_to_add.append(new_answer)

            if new_answers_to_add:
                self.session.add_all(new_answers_to_add)

        # Сохраняем все UPDATE-запросы и новые добавления
        await self.session.commit()

        # Явно обновляем объекты в сессии, чтобы получить актуальные связанные ответы
        self.session.expire_all()

        # 4. Загружаем и возвращаем финальное состояние объекта
        # Это необходимо, так как UPDATE не обновляет объекты в сессии
        final_stmt = (
            select(Question)
            .where(Question.question_id == question_id)
            .options(selectinload(Question.answer_options))
        )
        result = await self.session.execute(final_stmt)
        return result.scalar_one_or_none()

    async def get_question_by_id(
        self, test_id: uuid.UUID, question_id: uuid.UUID
    ) -> Question | None:
        stmt = (
            select(Question)
            .where(Question.question_id == question_id, Question.test_id == test_id)
            .options(selectinload(Question.answer_options))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_question_by_id(
        self, test_id: uuid.UUID, question_id: uuid.UUID
    ) -> uuid.UUID | None:
        stmt = (
            delete(Question)
            .where(Question.question_id == question_id, Question.test_id == test_id)
            .returning(Question.question_id)
        )
        result: Result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_all_questions_by_test_id(self, test_id: uuid.UUID) -> int:
        stmt = delete(Question).where(Question.test_id == test_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def update_test_status(
        self, test_id: uuid.UUID, status_: TestStatus, teacher_id: int
    ) -> Test | None:
        # update only tests owned by teacher
        stmt = (
            update(Test)
            .where(Test.test_id == test_id, Test.teacher_id == teacher_id)
            .values(status=status_)
            .returning(Test)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_tests_by_title_prefix(
        self, title_prefix: str, teacher_id: int
    ) -> Sequence[Test]:
        # fetch tests by title prefix scoped to teacher
        stmt = select(Test).where(
            Test.teacher_id == teacher_id, Test.title.ilike(f"{title_prefix}%")
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_test_results(
        self, test_id: uuid.UUID, teacher_id: int, pagination: PaginationTest
    ) -> Sequence[TestAttempt]:
        stmt = (
            select(TestAttempt)
            .join(Test, TestAttempt.test_id == Test.test_id)
            .where(TestAttempt.test_id == test_id, Test.teacher_id == teacher_id)
            .options(joinedload(TestAttempt.student))
            .order_by(TestAttempt.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    async def get_students_by_teacher(
        self,
        teacher_id: int,
        search_query: SearchStudent,
        pagination: PaginationTest,
    ) -> Sequence[AuthEntity]:
        stmt = (
            select(AuthEntity)
            .distinct()
            .join(TestAttempt, AuthEntity.id == TestAttempt.student_id)
            .join(Test, TestAttempt.test_id == Test.test_id)
            .where(Test.teacher_id == teacher_id)
        )
        if search_query.login:
            stmt = stmt.where(AuthEntity.login.ilike(f"%{search_query.login}%"))

        stmt = (
            stmt.order_by(AuthEntity.login)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_student_results_by_teacher(
        self, student_id: int, teacher_id: int, pagination: PaginationTest
    ) -> Sequence[TestAttempt]:
        stmt = (
            select(TestAttempt)
            .join(Test, TestAttempt.test_id == Test.test_id)
            .where(Test.teacher_id == teacher_id, TestAttempt.student_id == student_id)
            .options(joinedload(TestAttempt.test))
            .order_by(TestAttempt.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    async def get_test_analytics_data(
        self, test_id: uuid.UUID, teacher_id: int, search_query: str | None = None
    ) -> (
        tuple[int, None, list[Any]]
        | tuple[Any, Any, Sequence[Row[tuple[uuid.UUID, str, Any]]]]
    ):
        # Query to get total attempts and average score
        attempts_stmt = (
            select(
                func.count(TestAttempt.attempt_id),
                func.avg(TestAttempt.score),
            )
            .join(Test, TestAttempt.test_id == Test.test_id)
            .where(
                Test.test_id == test_id,
                Test.teacher_id == teacher_id,
                TestAttempt.status == TestAttemptStatus.COMPLETED,
            )
        )
        attempts_result = await self.session.execute(attempts_stmt)
        total_attempts, average_score = attempts_result.one()

        if total_attempts == 0:
            return 0, None, []

        # Query to get question analytics with percentage calculation in the DB
        correct_answers = func.count().filter(StudentAnswer.is_correct).label("correct")
        total_answers = func.count(StudentAnswer.student_answer_id).label("total")

        percentage_correct = case(
            (total_answers > 0, (cast(correct_answers, Float) / total_answers) * 100),
            else_=0.0,
        ).label("correct_answer_percentage")

        questions_stmt = (
            select(
                Question.question_id,
                Question.question_text,
                percentage_correct,
            )
            .select_from(StudentAnswer)
            .join(Question, StudentAnswer.question_id == Question.question_id)
            .join(TestAttempt, StudentAnswer.attempt_id == TestAttempt.attempt_id)
            .join(Test, TestAttempt.test_id == Test.test_id)
            .where(
                Test.test_id == test_id,
                Test.teacher_id == teacher_id,
                TestAttempt.status == TestAttemptStatus.COMPLETED,
            )
        )
        if search_query:
            questions_stmt = questions_stmt.where(
                func.lower(Question.question_text).like(f"%{search_query.lower()}%")
            )

        questions_stmt = questions_stmt.group_by(
            Question.question_id, Question.question_text
        ).order_by(Question.order)
        questions_result = await self.session.execute(questions_stmt)
        question_analytics_data = questions_result.all()

        return total_attempts, average_score, question_analytics_data
