import uuid
from sqlalchemy import ForeignKey, text, Enum, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from common.base import Base
from common.enums import TestAttemptStatus
from common.mixins import TimestampMix
from profile.teacher.models import Test, Question, AnswerOption

if TYPE_CHECKING:
    from auth.models import AuthEntity


class TestAttempt(TimestampMix, Base):
    __tablename__ = "test_attempts"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("auth_entity.id", ondelete="CASCADE"), nullable=False
    )
    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tests.test_id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[TestAttemptStatus] = mapped_column(
        Enum(TestAttemptStatus),
        nullable=False,
        default=TestAttemptStatus.IN_PROGRESS,
        server_default=TestAttemptStatus.IN_PROGRESS.value,
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    test: Mapped["Test"] = relationship()
    student: Mapped["AuthEntity"] = relationship(back_populates="test_attempts")
    student_answers: Mapped[list["StudentAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class StudentAnswerSelectedOption(Base):
    __tablename__ = "student_answer_selected_options"

    student_answer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_answers.student_answer_id", ondelete="CASCADE"),
        primary_key=True,
    )
    answer_option_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("answer_options.answer_id", ondelete="CASCADE"),
        primary_key=True,
    )


class StudentAnswer(TimestampMix, Base):
    __tablename__ = "student_answers"

    student_answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_attempts.attempt_id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        nullable=False,
    )
    is_correct: Mapped[bool] = mapped_column(nullable=False)

    attempt: Mapped["TestAttempt"] = relationship(back_populates="student_answers")
    question: Mapped["Question"] = relationship()
    chosen_options: Mapped[list["AnswerOption"]] = relationship(
        secondary="student_answer_selected_options"
    )
