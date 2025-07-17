from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from common.enums import Role, DesiredRole
from typing import Optional
from .models import RoleRequestStatus


class AuthEntitySchema(BaseModel):
    id: int
    login: str
    role: Role


class AuthEntityIn(BaseModel):
    """Схема для данных, необходимых при регистрации новой сущности."""

    email: EmailStr
    login: str = Field(min_length=8)
    password: str = Field(min_length=8)
    desired_role: DesiredRole = DesiredRole.STUDENT


class AuthEntityOut(BaseModel):
    """Схема для данных, возвращаемых после успешной регистрации."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    email: EmailStr
    role: Role


class AuthCredentials(BaseModel):
    """Схема для учетных данных, передаваемых при входе в систему."""

    login: str
    password: str


class TokenInfo(BaseModel):
    """Схема для возврата пары access и refresh токенов."""

    access: str
    refresh: str


class AccessTokenPayload(BaseModel):
    """Схема для полезной нагрузки (payload) access-токена."""

    sub: str
    login: str
    role: Role


class RoleRequestCreate(BaseModel):
    requested__desired_role: DesiredRole
    # entity_id будет определяться из текущего пользователя (автоматически)


class RoleRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: int
    requested_role: Role
    status: RoleRequestStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RoleRequestListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    items: list[RoleRequestOut]


class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)
    repeat_password: str = Field(min_length=8)

class PasswordResetResponse(BaseModel):
    detail: str
