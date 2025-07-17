from fastapi import APIRouter, Depends
from typing import List
import uuid

from profile.student.schemas import (
    TestListViewOut,
    TestDetailViewOut,
    TestAttemptStartOut,
    StudentAnswerIn,
    StudentAnswerResultOut,
    TestResultOut,
    AttemptHistoryItemOut,
    StudentStatsOut,
)
from common.paginations import PaginationTest
from .dependencies import StudentServicesDep, RestrictStudentDep
from profile.teacher.schemas import SearchTest


router = APIRouter(prefix="/student", tags=["STUDENT ENDPOINTS"])


@router.get("/tests", response_model=List[TestListViewOut])
async def list_tests(
    restrict: RestrictStudentDep,
    services: StudentServicesDep,
    pagination: PaginationTest = Depends(),
    search_test: SearchTest = Depends(),
) -> List[TestListViewOut]:
    """Получение списка доступных тестов."""
    return await services.list_available_tests(pagination, search_test=search_test)


@router.get("/attempts", response_model=List[AttemptHistoryItemOut])
async def get_attempt_history(
    services: StudentServicesDep,
    restrict: RestrictStudentDep,
    pagination: PaginationTest = Depends(),
) -> list[AttemptHistoryItemOut]:
    """Получение истории своих попыток (пройденных и текущих)."""
    student_id = int(restrict.sub)
    return await services.get_attempt_history(
        student_id=student_id, pagination=pagination
    )


@router.get("/stats", response_model=StudentStatsOut)
async def get_student_stats(
    services: StudentServicesDep,
    restrict: RestrictStudentDep,
) -> StudentStatsOut:
    """Получение общей статистики по своим тестам."""
    student_id = int(restrict.sub)
    return await services.get_student_stats(student_id=student_id)


@router.get("/tests/{test_id}", response_model=TestDetailViewOut)
async def get_test_for_passing(
    restrict: RestrictStudentDep,
    test_id: uuid.UUID,
    services: StudentServicesDep,
) -> TestDetailViewOut:
    """Получение детальной информации о тесте для его прохождения."""
    return await services.get_test_for_passing(test_id)


@router.post("/tests/{test_id}/start", response_model=TestAttemptStartOut)
async def start_test(
    test_id: uuid.UUID,
    services: StudentServicesDep,
    restrict: RestrictStudentDep,
) -> TestAttemptStartOut:
    """Начало новой попытки прохождения теста."""
    student_id = int(restrict.sub)
    return await services.start_test(student_id=student_id, test_id=test_id)


@router.post("/attempts/{attempt_id}/answer", response_model=StudentAnswerResultOut)
async def submit_answer(
    restrict: RestrictStudentDep,
    attempt_id: uuid.UUID,
    answer_data: StudentAnswerIn,
    services: StudentServicesDep,
) -> StudentAnswerResultOut:
    """Отправка ответа на вопрос в рамках попытки."""
    return await services.submit_answer(attempt_id=attempt_id, answer_data=answer_data)


@router.post("/attempts/{attempt_id}/finish", response_model=TestResultOut)
async def finish_test(
    attempt_id: uuid.UUID,
    restrict: RestrictStudentDep,
    services: StudentServicesDep,
) -> TestResultOut:
    """Завершение попытки и получение итогового результата."""
    return await services.finish_test(attempt_id=attempt_id)
