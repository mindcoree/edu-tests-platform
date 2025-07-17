from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, model_validator, Field
import uuid
from common.enums import TestStatus, TestAttemptStatus


class AnswerOptionCreate(BaseModel):
    answer_text: Optional[str] = None
    image_url: Optional[str] = None
    is_correct: bool = False

    @classmethod
    @model_validator(mode="before")
    def check_text_or_image(cls, data):
        if isinstance(data, dict):
            if not data.get("answer_text") and not data.get("image_url"):
                raise ValueError("Either answer_text or image_url must be provided")
        elif hasattr(data, "answer_text") and hasattr(data, "image_url"):
            if not data.answer_text and not data.image_url:
                raise ValueError("Either answer_text or image_url must be provided")
        return data


class QuestionIn(BaseModel):
    question_text: str
    image_url: Optional[str] = None
    order: Optional[int] = None
    points: Optional[int] = Field(default=1, ge=0)
    answer_options: List[AnswerOptionCreate] = []


class TestIn(BaseModel):
    title: str = Field(max_length=255)
    description: Optional[str] = None
    image_url: Optional[str] = None


class SearchTest(BaseModel):
    title: str | None = Field(max_length=255, default=None)
    description: str | None = None


class EditTest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class TestOut(TestIn):
    test_id: uuid.UUID
    status: TestStatus


class AnswerOptionOut(AnswerOptionCreate):
    answer_id: uuid.UUID


class AnswerOptionEdit(BaseModel):
    answer_id: Optional[uuid.UUID] = None
    answer_text: Optional[str] = None
    image_url: Optional[str] = None
    is_correct: Optional[bool] = None


class QuestionEdit(BaseModel):
    question_text: Optional[str] = None
    image_url: Optional[str] = None
    order: Optional[int] = None
    points: Optional[int] = Field(default=None, ge=0)
    answer_options: Optional[List[AnswerOptionEdit]] = None
    answer_ids_to_delete: Optional[List[uuid.UUID]] = None


class QuestionCreate(BaseModel):
    question_text: str
    image_url: Optional[str] = None
    order: Optional[int] = None
    points: Optional[int] = Field(default=1, ge=0)
    answer_options: List[AnswerOptionCreate] = []


class QuestionWithAnswerOut(BaseModel):
    question_id: uuid.UUID
    test_id: uuid.UUID
    question_text: str
    image_url: Optional[str] = None
    order: Optional[int] = None
    points: int
    answer_options: List[AnswerOptionOut] = []


class QuestionOut(BaseModel):
    question_id: uuid.UUID
    test_id: uuid.UUID
    question_text: str
    image_url: Optional[str] = None
    order: Optional[int] = None
    points: int


class TestWithQuestionsOut(TestOut):
    questions: List[QuestionOut] = []


class StudentInfo(BaseModel):
    id: int
    email: str
    login: str


class StudentTestResultOut(BaseModel):
    attempt_id: uuid.UUID
    student: StudentInfo
    status: TestAttemptStatus
    score: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class QuestionAnalyticsOut(BaseModel):
    question_id: uuid.UUID
    question_text: str
    correct_answer_percentage: float


class TestAnalyticsOut(BaseModel):
    total_attempts: int
    average_score: Optional[float]
    question_analytics: List[QuestionAnalyticsOut]


class SearchStudent(BaseModel):
    login: Optional[str] = None


class TestInfoForStudentResults(BaseModel):
    test_id: uuid.UUID
    title: str


class StudentResultForTeacherOut(BaseModel):
    attempt_id: uuid.UUID
    test: TestInfoForStudentResults
    status: TestAttemptStatus
    score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
