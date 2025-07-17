import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from common.enums import TestAttemptStatus


# --- Схемы для отображения тестов студенту ---


class TestListViewOut(BaseModel):
    """Схема для отображения теста в общем списке."""

    test_id: uuid.UUID
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    # Дополнительно можно добавить количество вопросов, если нужно
    # total_questions: int


class AnswerOptionForStudentOut(BaseModel):
    """Вариант ответа, как его видит студент (без флага is_correct)."""

    answer_id: uuid.UUID
    answer_text: Optional[str] = None
    image_url: Optional[str] = None


class QuestionForStudentOut(BaseModel):
    """Вопрос, как его видит студент (без правильных ответов)."""

    question_id: uuid.UUID
    question_text: str
    image_url: Optional[str] = None
    order: Optional[int] = None
    points: int
    answer_options: List[AnswerOptionForStudentOut] = []


class TestDetailViewOut(TestListViewOut):
    """Полная схема теста для прохождения студентом."""

    questions: List[QuestionForStudentOut] = []


# --- Схемы для процесса прохождения теста ---


class TestAttemptStartOut(BaseModel):
    """Результат старта теста."""

    attempt_id: uuid.UUID
    test_id: uuid.UUID
    student_id: int
    score: Optional[float] = None
    status: TestAttemptStatus
    created_at: datetime


# --- Схемы для отображения результатов ---


class TestResultOut(BaseModel):
    """Итоговый результат прохождения теста."""

    attempt_id: uuid.UUID
    test_id: uuid.UUID
    status: TestAttemptStatus
    score: float  # Итоговый балл в процентах (например, 85.5)
    total_possible_points: int
    earned_points: int
    started_at: datetime
    completed_at: datetime
    # Можно добавить список ответов для детального разбора
    # answers: List[DetailedAnswerResult]


class AttemptHistoryItemOut(BaseModel):
    """Схема для отображения одной попытки в истории."""

    model_config = ConfigDict(from_attributes=True)

    attempt_id: uuid.UUID
    status: TestAttemptStatus
    score: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    test_title: str


class StudentAnswerIn(BaseModel):
    """Схема для отправки ответа студентом."""

    question_id: uuid.UUID
    chosen_answer_option_ids: List[uuid.UUID]


class StudentAnswerResultOut(BaseModel):
    """Результат проверки ответа студента."""

    is_correct: bool
    correct_answer_option_ids: List[uuid.UUID]


class StudentStatsOut(BaseModel):
    """Схема для вывода статистики по студенту."""

    total_tests_completed: int
    average_score: Optional[float] = None
    in_progress_count: int
