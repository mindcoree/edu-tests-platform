import uuid
from typing import Any

from fastapi import HTTPException, status


class ExceptionTeacher(HTTPException):
    """Базовое исключение приложения."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

    class NotFoundUuid(HTTPException):
        def __init__(self, uuid_model: uuid.UUID, model: str):
            super().__init__(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model} not found by UUID: {uuid_model}",
            )

    class AlreadyExists(HTTPException):
        def __init__(self, field_name: str, value_field, model: str):
            super().__init__(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{model} with field:{field_name}={value_field} already exists",
            )

    class InvalidData(HTTPException):
        def __init__(self, reason: str):
            super().__init__(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=reason,
            )
