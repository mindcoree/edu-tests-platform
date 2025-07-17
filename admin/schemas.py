from pydantic import BaseModel, Field, EmailStr
from common.enums import Role


class ChangeRoleEntity(BaseModel):
    entity_id: int = Field(..., gt=0)
    new_role: Role


class SearchEntity(BaseModel):
    login: str | None = None
    email: str | None = None
    role: Role | None = None


class AdminIn(BaseModel):

    login: str
    password: str
    email: EmailStr
    role: Role = Role.ADMIN


class AdminOut(BaseModel):
    id: int
    login: str
    email: EmailStr
    role: Role
