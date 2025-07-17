import uuid
from typing import Sequence

from auth.models import AuthEntity
from utils.s3 import s3_client
from .exceptions import ExceptionTeacher
from fastapi import HTTPException, status
from .repository import TeacherRepository
from sqlalchemy.exc import IntegrityError
from .schemas import (
    TestIn,
    SearchTest,
    EditTest,
    QuestionCreate,
    QuestionEdit,
    TestAnalyticsOut,
    QuestionAnalyticsOut,
    SearchStudent,
)
from .models import Test, Question, AnswerOption
from profile.student.models import TestAttempt
from common.paginations import PaginationTest
from common.enums import TestStatus


class TeacherServices:
    def __init__(self, repository: TeacherRepository):
        self.repo = repository

    async def create_test(self, test_data: TestIn, teacher_id: int) -> Test:
        try:
            data = test_data.model_dump()
            data["teacher_id"] = teacher_id
            test = await self.repo.create_test(data)
        except IntegrityError:
            raise ExceptionTeacher.AlreadyExists(
                model="Test", field_name="title", value_field=test_data.title
            )

        return test

    async def list_tests(
        self,
        teacher_id: int,
        search_test: SearchTest,
        pagination: PaginationTest,
        status_: TestStatus | None = None,
    ) -> Sequence[Test]:
        list_tests = await self.repo.show_tests(
            search_test=search_test,
            offset=pagination.offset,
            limit=pagination.limit,
            status_=status_,
            teacher_id=teacher_id,
        )
        return list_tests

    async def get_test_by_id(self, test_id: uuid.UUID, teacher_id: int) -> Test:
        test = await self.repo.get_test_by_id(test_id=test_id, teacher_id=teacher_id)
        if not test:
            raise ExceptionTeacher.NotFoundUuid(model="Test", uuid_model=test_id)
        return test

    async def _generate_unique_title(self, base_title: str, teacher_id: int) -> str:
        # Получаем все названия тестов, начинающиеся с base_title для учителя
        existing_titles = [
            t.title
            for t in await self.repo.get_tests_by_title_prefix(
                base_title, teacher_id=teacher_id
            )
        ]
        if base_title not in existing_titles:
            return base_title
        i = 1
        while True:
            new_title = f"{base_title} (копия {i})"
            if new_title not in existing_titles:
                return new_title
            i += 1

    async def duplicate_test(self, test_id: uuid.UUID, teacher_id: int) -> Test:
        original_test = await self.get_test_by_id(
            test_id=test_id, teacher_id=teacher_id
        )
        base_title = f"{original_test.title}"
        attempt = 0
        max_attempts = 10
        while attempt < max_attempts:
            unique_title = await self._generate_unique_title(
                base_title, teacher_id=teacher_id
            )
            new_test = Test(
                title=unique_title,
                description=original_test.description,
                image_url=original_test.image_url,
                status=TestStatus.DRAFT,
                questions=[],
                teacher_id=teacher_id,
            )

            for original_question in original_test.questions:
                new_question = Question(
                    question_text=original_question.question_text,
                    image_url=original_question.image_url,
                    order=original_question.order,
                    answer_options=[],
                )
                for original_answer in original_question.answer_options:
                    new_answer = AnswerOption(
                        answer_text=original_answer.answer_text,
                        image_url=original_answer.image_url,
                        is_correct=original_answer.is_correct,
                    )
                    new_question.answer_options.append(new_answer)
                new_test.questions.append(new_question)
            try:
                new_duplicate_test = await self.repo.add_test(new_test)
                return new_duplicate_test
            except IntegrityError:
                attempt += 1
                base_title = unique_title  # чтобы следующий вариант был (копия 2) (копия 3) и т.д.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create a duplicate for test with title '{base_title}' after {max_attempts} attempts.",
        )

    async def get_student_results_by_teacher(
        self, student_id: int, teacher_id: int, pagination: PaginationTest
    ) -> Sequence[TestAttempt]:
        return await self.repo.get_student_results_by_teacher(
            student_id=student_id, teacher_id=teacher_id, pagination=pagination
        )

    async def get_students_by_teacher(
        self,
        teacher_id: int,
        search_query: SearchStudent,
        pagination: PaginationTest,
    ) -> Sequence[AuthEntity]:
        return await self.repo.get_students_by_teacher(
            teacher_id=teacher_id, search_query=search_query, pagination=pagination
        )

    async def get_test_analytics(
        self, test_id: uuid.UUID, teacher_id: int, search_query: str | None = None
    ) -> TestAnalyticsOut:
        (
            total_attempts,
            average_score,
            question_data,
        ) = await self.repo.get_test_analytics_data(
            test_id=test_id, teacher_id=teacher_id, search_query=search_query
        )

        question_analytics = [
            QuestionAnalyticsOut(
                question_id=q_id,
                question_text=q_text,
                correct_answer_percentage=percentage,
            )
            for q_id, q_text, percentage in question_data
        ]

        return TestAnalyticsOut(
            total_attempts=total_attempts or 0,
            average_score=average_score,
            question_analytics=question_analytics,
        )

    async def get_test_results(
        self, test_id: uuid.UUID, teacher_id: int, pagination: PaginationTest
    ) -> Sequence[TestAttempt]:
        results = await self.repo.get_test_results(
            test_id=test_id, teacher_id=teacher_id, pagination=pagination
        )
        return results

    async def update_test_status(
        self, test_id: uuid.UUID, status_: TestStatus, teacher_id: int
    ) -> Test:
        test = await self.repo.update_test_status(
            test_id=test_id, status_=status_, teacher_id=teacher_id
        )
        if not test:
            raise ExceptionTeacher.NotFoundUuid(model="Test", uuid_model=test_id)
        return test

    async def delete_test(self, test_id: uuid.UUID, teacher_id: int) -> None:
        # First, fetch the test with its related questions and answers to get image_urls
        test_to_delete = await self.get_test_by_id(
            test_id=test_id, teacher_id=teacher_id
        )

        # Delete associated images from S3
        if test_to_delete.image_url:
            if object_key := s3_client.get_key_from_url(test_to_delete.image_url):
                s3_client.delete_file(object_key)

        for question in test_to_delete.questions:
            if question.image_url:
                if object_key := s3_client.get_key_from_url(question.image_url):
                    s3_client.delete_file(object_key)
            for answer in question.answer_options:
                if answer.image_url:
                    if object_key := s3_client.get_key_from_url(answer.image_url):
                        s3_client.delete_file(object_key)

        # Now, delete the test from the database. Cascade will handle questions and answers.
        deleted_test_id = await self.repo.delete_test_by_id(
            test_id, teacher_id=teacher_id
        )
        if deleted_test_id is None:
            raise ExceptionTeacher.NotFoundUuid(model="Test", uuid_model=test_id)

    async def delete_all_tests(self, teacher_id: int) -> dict[str, str]:
        # 1. First, fetch all tests with all nested data eagerly loaded.
        all_tests = await self.repo.get_all_tests_by_teacher(teacher_id=teacher_id)

        # 2. Iterate through the fetched objects and delete images from S3.
        for test in all_tests:
            if test.image_url:
                if object_key := s3_client.get_key_from_url(test.image_url):
                    s3_client.delete_file(object_key)
            for question in test.questions:
                if question.image_url:
                    if object_key := s3_client.get_key_from_url(question.image_url):
                        s3_client.delete_file(object_key)
                for answer in question.answer_options:
                    if answer.image_url:
                        if object_key := s3_client.get_key_from_url(answer.image_url):
                            s3_client.delete_file(object_key)

        # 3. Only now, delete the records from the database.
        deleted_count = await self.repo.delete_all_tests(teacher_id=teacher_id)
        return {"message": f"Successfully deleted {deleted_count} tests."}

    async def delete_all_questions_by_test_id(
        self, test_id: uuid.UUID, teacher_id: int
    ) -> dict[str, str]:
        # 1. First, fetch the test and all its questions with answers.
        test = await self.get_test_by_id(test_id=test_id, teacher_id=teacher_id)

        # 2. Iterate through the questions and delete associated images from S3.
        for question in test.questions:
            if question.image_url:
                if object_key := s3_client.get_key_from_url(question.image_url):
                    s3_client.delete_file(object_key)
            for answer in question.answer_options:
                if answer.image_url:
                    if object_key := s3_client.get_key_from_url(answer.image_url):
                        s3_client.delete_file(object_key)

        # 3. Only now, delete the records from the database.
        deleted_count = await self.repo.delete_all_questions_by_test_id(test_id=test_id)
        return {"message": f"Successfully deleted {deleted_count} questions."}

    async def edit_test(
        self, edit_data: EditTest, test_id: uuid.UUID, teacher_id: int
    ) -> Test:
        # First, get the current state of the test
        current_test = await self.get_test_by_id(test_id=test_id, teacher_id=teacher_id)
        if not current_test:
            raise ExceptionTeacher.NotFoundUuid(model="Test", uuid_model=test_id)

        update_data = edit_data.model_dump(exclude_unset=True)

        # Check if the image is being updated or removed.
        # This logic triggers only if 'image_url' is explicitly in the request payload.
        if "image_url" in update_data and current_test.image_url:
            if update_data["image_url"] != current_test.image_url:
                if object_key := s3_client.get_key_from_url(current_test.image_url):
                    s3_client.delete_file(object_key)

        try:
            edit_test = await self.repo.edit_test(
                test_data=update_data,
                test_id=test_id,
                teacher_id=teacher_id,
            )
        except IntegrityError:
            raise ExceptionTeacher.AlreadyExists(
                model="Test", field_name="title", value_field=edit_data.title
            )

        if edit_test is None:
            raise ExceptionTeacher.NotFoundUuid(model="Test", uuid_model=test_id)

        return edit_test

    async def edit_question_with_answers(
        self,
        test_id: uuid.UUID,
        question_id: uuid.UUID,
        edit_data: QuestionEdit,
        teacher_id: int,
    ) -> Question:
        # Get the current state of the question to check old image URLs
        current_question = await self.get_question_by_id(
            test_id=test_id, question_id=question_id, teacher_id=teacher_id
        )
        if not current_question:
            raise ExceptionTeacher.NotFoundUuid(
                model="Question", uuid_model=question_id
            )

        edit_data_dict = edit_data.model_dump(exclude_unset=True)

        # Handle question image update or removal
        if "image_url" in edit_data_dict and current_question.image_url:
            if edit_data_dict["image_url"] != current_question.image_url:
                if object_key := s3_client.get_key_from_url(current_question.image_url):
                    s3_client.delete_file(object_key)

        # Handle answer options updates and image deletions/removals
        answer_options_data = edit_data_dict.get("answer_options")
        if answer_options_data:
            current_answers_map = {
                ans.answer_id: ans for ans in current_question.answer_options
            }
            for answer_data in answer_options_data:
                answer_id = answer_data.get("answer_id")
                # Scenario: An existing answer is being edited.
                if answer_id in current_answers_map:
                    # Check if the 'image_url' key was sent in the request for this answer.
                    # This indicates an intent to change or remove the image.
                    if "image_url" in answer_data:
                        current_answer = current_answers_map[answer_id]
                        # If there was an old image and the new URL is different, delete the old file.
                        if (
                            current_answer.image_url
                            and answer_data["image_url"] != current_answer.image_url
                        ):
                            if object_key := s3_client.get_key_from_url(
                                current_answer.image_url
                            ):
                                s3_client.delete_file(object_key)

        answer_ids_to_delete = edit_data_dict.pop("answer_ids_to_delete", None)

        # Handle deletion of images for answers that are being deleted
        if answer_ids_to_delete:
            answers_to_delete = await self.repo.get_answers_by_ids(answer_ids_to_delete)
            for answer in answers_to_delete:
                if answer.image_url:
                    if object_key := s3_client.get_key_from_url(answer.image_url):
                        s3_client.delete_file(object_key)

        edited_question = await self.repo.edit_question_with_answers(
            test_id=test_id,
            question_id=question_id,
            question_data=edit_data_dict,
            answer_options_data=answer_options_data,
            answer_ids_to_delete=answer_ids_to_delete,
        )

        if edited_question is None:
            raise ExceptionTeacher.NotFoundUuid(
                model="Question", uuid_model=question_id
            )

        return edited_question

    async def get_question_by_id(
        self, test_id: uuid.UUID, question_id: uuid.UUID, teacher_id: int
    ) -> Question:
        # ensure teacher owns the test
        await self.get_test_by_id(test_id=test_id, teacher_id=teacher_id)
        question = await self.repo.get_question_by_id(
            test_id=test_id, question_id=question_id
        )
        if not question:
            raise ExceptionTeacher.NotFoundUuid(
                model="Question", uuid_model=question_id
            )
        return question

    async def create_question_with_answers(
        self, test_id: uuid.UUID, question_data: QuestionCreate, teacher_id: int
    ) -> Question:
        # ensure teacher owns the test
        await self.get_test_by_id(test_id=test_id, teacher_id=teacher_id)
        question_dict = question_data.model_dump(exclude={"answer_options"})
        question_dict["test_id"] = test_id
        try:
            question = await self.repo.create_question_with_answers(
                question_data=question_dict,
                answer_options=[
                    answer.model_dump() for answer in question_data.answer_options
                ],
            )
        except IntegrityError as e:
            raise HTTPException(
                status_code=500, detail=f"Error creating question: {str(e)}"
            )
        return question

    async def delete_question(
        self, test_id: uuid.UUID, question_id: uuid.UUID, teacher_id: int
    ) -> None:
        # First, fetch the question to get image_urls
        question_to_delete = await self.get_question_by_id(
            test_id=test_id, question_id=question_id, teacher_id=teacher_id
        )

        # Delete associated images from S3
        if question_to_delete.image_url:
            if object_key := s3_client.get_key_from_url(question_to_delete.image_url):
                s3_client.delete_file(object_key)
        for answer in question_to_delete.answer_options:
            if answer.image_url:
                if object_key := s3_client.get_key_from_url(answer.image_url):
                    s3_client.delete_file(object_key)

        # Now, delete the question from the database
        deleted_question_id = await self.repo.delete_question_by_id(
            test_id=test_id, question_id=question_id
        )
        if deleted_question_id is None:
            raise ExceptionTeacher.NotFoundUuid(
                model="Question", uuid_model=question_id
            )
