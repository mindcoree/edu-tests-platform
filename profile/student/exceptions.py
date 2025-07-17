import uuid
from fastapi import HTTPException, status


class ExceptionStudent(HTTPException):
    """Базовое исключение для студенческого раздела."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

    class TestNotFound(HTTPException):
        def __init__(self, test_id: uuid.UUID):
            super().__init__(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test with id {test_id} not found or not published.",
            )

    class AttemptNotFound(HTTPException):
        def __init__(self, attempt_id: uuid.UUID):
            super().__init__(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test attempt with id {attempt_id} not found.",
            )

    class AttemptAlreadyFinished(HTTPException):
        def __init__(self, attempt_id: uuid.UUID):
            super().__init__(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Test attempt {attempt_id} is already completed.",
            )

    class QuestionNotFoundInTest(HTTPException):
        def __init__(self, question_id: uuid.UUID, test_id: uuid.UUID):
            super().__init__(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question {question_id} not found in test {test_id}.",
            )

    class AnswerOptionNotFound(HTTPException):
        def __init__(self, answer_option_id: uuid.UUID):
            super().__init__(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Answer option {answer_option_id} not found.",
            )

    class ActiveTestAttemptExists(HTTPException):
        def __init__(self):
            super().__init__(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У вас уже есть активный тест. Завершите его, прежде чем начинать новый.",
            )
