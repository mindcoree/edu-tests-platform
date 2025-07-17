import uuid
from typing import Sequence
from common.paginations import PaginationTest
from fastapi import APIRouter, Depends, status, Query
from .schemas import (
    TestIn,
    TestOut,
    SearchTest,
    EditTest,
    QuestionCreate,
    QuestionWithAnswerOut,
    QuestionEdit,
    TestWithQuestionsOut,
    StudentTestResultOut,
    TestAnalyticsOut,
    StudentInfo,
    StudentResultForTeacherOut,
    SearchStudent,
)
from .dependencies import TeacherServicesDep, RestrictTeacherDep
from common.enums import TestStatus


router = APIRouter(prefix="/teacher", tags=["TEACHER ENDPOINTS"])


@router.post(
    "/tests/test/add",
    status_code=status.HTTP_201_CREATED,
    response_model=TestOut,
)
async def create_test(
    services: TeacherServicesDep,
    test_in: TestIn,
    restrict: RestrictTeacherDep,
) -> TestOut:
    teacher_id = int(restrict.sub)
    return await services.create_test(test_data=test_in, teacher_id=teacher_id)


@router.get("/tests/show", response_model=Sequence[TestOut])
async def show_tests(
    restrict: RestrictTeacherDep,
    services: TeacherServicesDep,
    search_test: SearchTest = Depends(),
    pagination: PaginationTest = Depends(),
    status_: TestStatus | None = None,
) -> Sequence[TestOut]:
    teacher_id = int(restrict.sub)

    return await services.list_tests(
        search_test=search_test,
        pagination=pagination,
        status_=status_,
        teacher_id=teacher_id,
    )


@router.delete(
    "/tests/test/delete/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_test(
    test_id: uuid.UUID, restrict: RestrictTeacherDep, services: TeacherServicesDep
) -> None:
    teacher_id = int(restrict.sub)

    return await services.delete_test(test_id=test_id, teacher_id=teacher_id)


@router.patch(
    "/tests/test/edit/{test_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TestOut,
)
async def edit_test(
    test_id: uuid.UUID,
    restrict: RestrictTeacherDep,
    test_edit_data: EditTest,
    services: TeacherServicesDep,
) -> TestOut:
    teacher_id = int(restrict.sub)

    return await services.edit_test(
        test_id=test_id, edit_data=test_edit_data, teacher_id=teacher_id
    )


@router.post(
    "/tests/{test_id}/questions/add",
    status_code=status.HTTP_201_CREATED,
    response_model=QuestionWithAnswerOut,
)
async def create_question_with_answers(
    test_id: uuid.UUID,
    restrict: RestrictTeacherDep,
    services: TeacherServicesDep,
    question_in: QuestionCreate,
) -> QuestionWithAnswerOut:
    teacher_id = int(restrict.sub)

    question = await services.create_question_with_answers(
        test_id=test_id, question_data=question_in, teacher_id=teacher_id
    )
    return question


@router.delete("/tests/delete/all", status_code=status.HTTP_200_OK)
async def delete_all_tests(
    restrict: RestrictTeacherDep,
    services: TeacherServicesDep,
) -> dict[str, str]:
    teacher_id = int(restrict.sub)

    return await services.delete_all_tests(teacher_id=teacher_id)


@router.delete("/tests/{test_id}/questions/delete/all", status_code=status.HTTP_200_OK)
async def delete_all_questions_by_test_id(
    restrict: RestrictTeacherDep, test_id: uuid.UUID, services: TeacherServicesDep
) -> dict[str, str]:
    teacher_id = int(restrict.sub)

    return await services.delete_all_questions_by_test_id(
        test_id=test_id, teacher_id=teacher_id
    )


@router.delete(
    "/tests/{test_id}/questions/delete/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_question(
    test_id: uuid.UUID,
    restrict: RestrictTeacherDep,
    question_id: uuid.UUID,
    services: TeacherServicesDep,
) -> None:
    teacher_id = int(restrict.sub)

    return await services.delete_question(
        test_id=test_id, question_id=question_id, teacher_id=teacher_id
    )


@router.post("/tests/{test_id}/duplicate", response_model=TestWithQuestionsOut)
async def duplicate_test(
    test_id: uuid.UUID, restrict: RestrictTeacherDep, services: TeacherServicesDep
) -> TestWithQuestionsOut:
    teacher_id = int(restrict.sub)

    return await services.duplicate_test(test_id=test_id, teacher_id=teacher_id)


@router.post("/tests/{test_id}/publish", response_model=TestOut)
async def publish_test(
    test_id: uuid.UUID, restrict: RestrictTeacherDep, services: TeacherServicesDep
) -> TestOut:
    teacher_id = int(restrict.sub)

    return await services.update_test_status(
        test_id=test_id, status_=TestStatus.PUBLISHED, teacher_id=teacher_id
    )


@router.post("/tests/{test_id}/archive", response_model=TestOut)
async def archive_test(
    test_id: uuid.UUID, restrict: RestrictTeacherDep, services: TeacherServicesDep
) -> TestOut:
    teacher_id = int(restrict.sub)

    return await services.update_test_status(
        test_id=test_id, status_=TestStatus.ARCHIVED, teacher_id=teacher_id
    )


@router.get(
    "/tests/{test_id}/questions/{question_id}", response_model=QuestionWithAnswerOut
)
async def get_question_by_id(
    test_id: uuid.UUID,
    question_id: uuid.UUID,
    restrict: RestrictTeacherDep,
    services: TeacherServicesDep,
) -> QuestionWithAnswerOut:
    teacher_id = int(restrict.sub)

    return await services.get_question_by_id(
        test_id=test_id, question_id=question_id, teacher_id=teacher_id
    )


@router.get("/tests/students", response_model=Sequence[StudentInfo])
async def get_students_by_teacher(
    restrict: RestrictTeacherDep,
    services: TeacherServicesDep,
    pagination: PaginationTest = Depends(),
    search_query: SearchStudent = Depends(),
) -> Sequence[StudentInfo]:
    teacher_id = int(restrict.sub)
    return await services.get_students_by_teacher(
        teacher_id=teacher_id, pagination=pagination, search_query=search_query
    )


@router.get("/tests/{test_id}", response_model=TestWithQuestionsOut)
async def get_test_by_id(
    test_id: uuid.UUID, restrict: RestrictTeacherDep, services: TeacherServicesDep
) -> TestWithQuestionsOut:
    teacher_id = int(restrict.sub)

    return await services.get_test_by_id(test_id=test_id, teacher_id=teacher_id)


@router.patch(
    "/tests/{test_id}/questions/edit/{question_id}",
    status_code=status.HTTP_200_OK,
    response_model=QuestionWithAnswerOut,
)
async def edit_question(
    test_id: uuid.UUID,
    question_id: uuid.UUID,
    edit_data: QuestionEdit,
    restrict: RestrictTeacherDep,
    services: TeacherServicesDep,
) -> QuestionWithAnswerOut:
    teacher_id = int(restrict.sub)

    return await services.edit_question_with_answers(
        test_id=test_id,
        question_id=question_id,
        edit_data=edit_data,
        teacher_id=teacher_id,
    )


@router.get("/tests/{test_id}/results", response_model=Sequence[StudentTestResultOut])
async def get_test_results(
    test_id: uuid.UUID,
    restrict: RestrictTeacherDep,
    services: TeacherServicesDep,
    pagination: PaginationTest = Depends(),
) -> Sequence[StudentTestResultOut]:
    teacher_id = int(restrict.sub)
    return await services.get_test_results(
        test_id=test_id, teacher_id=teacher_id, pagination=pagination
    )


@router.get("/tests/{test_id}/analytics", response_model=TestAnalyticsOut)
async def get_test_analytics(
    test_id: uuid.UUID,
    restrict: RestrictTeacherDep,
    services: TeacherServicesDep,
    search: str | None = Query(None, alias="search"),
) -> TestAnalyticsOut:
    teacher_id = int(restrict.sub)
    return await services.get_test_analytics(
        test_id=test_id, teacher_id=teacher_id, search_query=search
    )


@router.get(
    "/tests/students/{student_id}/results",
    response_model=Sequence[StudentResultForTeacherOut],
)
async def get_student_results_by_teacher(
    student_id: int,
    restrict: RestrictTeacherDep,
    services: TeacherServicesDep,
    pagination: PaginationTest = Depends(),
) -> Sequence[StudentResultForTeacherOut]:
    teacher_id = int(restrict.sub)
    return await services.get_student_results_by_teacher(
        student_id=student_id, teacher_id=teacher_id, pagination=pagination
    )
