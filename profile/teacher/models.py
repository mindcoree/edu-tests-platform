from common.base import Base
from common.enums import TestStatus
from common.mixins import TimestampMix
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, ForeignKey, Text, text, Enum


class Test(TimestampMix, Base):
    __tablename__ = "tests"

    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("auth_entity.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TestStatus] = mapped_column(
        Enum(TestStatus),
        nullable=False,
        default=TestStatus.DRAFT,
        server_default=TestStatus.DRAFT.value,
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="test", cascade="all,delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tests.test_id", ondelete="CASCADE"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    order: Mapped[int | None]
    points: Mapped[int] = mapped_column(default=1, server_default="1")
    test: Mapped["Test"] = relationship(back_populates="questions")
    answer_options: Mapped[list["AnswerOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class AnswerOption(Base):
    __tablename__ = "answer_options"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_text: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool]
    question: Mapped["Question"] = relationship(back_populates="answer_options")
