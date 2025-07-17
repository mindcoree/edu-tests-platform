from sqlalchemy import ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.enums import Role, DesiredRole
from common.mixins import TimestampMix
from common.base import Base
from common.enums import RoleRequestStatus


class RoleRequest(TimestampMix, Base):
    __tablename__ = "role_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("auth_entity.id", ondelete="CASCADE"), nullable=False
    )
    requested_role: Mapped[DesiredRole] = mapped_column(
        SAEnum(DesiredRole), nullable=False
    )
    status: Mapped[RoleRequestStatus] = mapped_column(
        SAEnum(RoleRequestStatus), default=RoleRequestStatus.PENDING, nullable=False
    )

    entity: Mapped["AuthEntity"] = relationship("AuthEntity", backref="role_requests")


class AuthEntity(TimestampMix, Base):
    """
    Модель SQLAlchemy, представляющая аутентифицируемую сущность.

    Хранит учетные данные, которые могут быть связаны с различными типами
    пользователей (студент, преподаватель, специалист).
    """

    __tablename__ = "auth_entity"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    login: Mapped[str] = mapped_column(nullable=False, unique=True)
    hash_password: Mapped[str] = mapped_column(nullable=False, unique=True)
    role: Mapped[Role] = mapped_column(default=Role.STUDENT)

    test_attempts: Mapped[list["TestAttempt"]] = relationship(back_populates="student")
