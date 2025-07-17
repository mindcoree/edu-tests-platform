from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    STUDENT = "student"
    TEACHER = "teacher"


class RoleRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DesiredRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    SPECIALIST = "specialist"


class TestStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class TestAttemptStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
