from typing import Annotated

from auth.schemas import AccessTokenPayload
from fastapi import Depends
from common.enums import Role
from auth.dependencies import PayloadEntity, restrict_to_entity
from common.db_helper import SessionDep
from .repository import StudentRepository
from .services import StudentServices


async def get_services_student(session: SessionDep) -> StudentServices:
    return StudentServices(StudentRepository(session))


StudentServicesDep = Annotated[StudentServices, Depends(get_services_student)]


async def restrict_to_student(payload: PayloadEntity) -> AccessTokenPayload:
    return await restrict_to_entity(payload=payload, role_entity=Role.STUDENT)


RestrictStudentDep = Annotated[AccessTokenPayload, Depends(restrict_to_student)]
