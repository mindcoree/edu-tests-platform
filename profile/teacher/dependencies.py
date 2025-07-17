from typing import Annotated
from common.db_helper import SessionDep
from auth.schemas import AccessTokenPayload
from fastapi import Depends
from common.enums import Role
from auth.dependencies import PayloadEntity, restrict_to_entity
from .repository import TeacherRepository
from .services import TeacherServices


async def get_services(session: SessionDep) -> TeacherServices:
    return TeacherServices(repository=TeacherRepository(session=session))


TeacherServicesDep = Annotated[TeacherServices, Depends(get_services)]


async def restrict_to_teacher(payload: PayloadEntity) -> AccessTokenPayload:
    return await restrict_to_entity(payload=payload, role_entity=Role.TEACHER)


RestrictTeacherDep = Annotated[AccessTokenPayload, Depends(restrict_to_teacher)]
