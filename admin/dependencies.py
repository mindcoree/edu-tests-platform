from auth.schemas import AccessTokenPayload
from common.enums import Role
from common.db_helper import SessionDep
from .repository import AdminRepository
from typing import Annotated
from .services import AdminServices
from fastapi import Depends
from auth.dependencies import restrict_to_entity, PayloadEntity


async def get_admin_services(session: SessionDep) -> AdminServices:
    return AdminServices(repository=AdminRepository(session=session))


AdminServicesDep = Annotated[AdminServices, Depends(get_admin_services)]


async def restrict_to_specialist(payload: PayloadEntity) -> AccessTokenPayload:
    return await restrict_to_entity(payload=payload, role_entity=Role.ADMIN)


RestrictAdminDep = Annotated[AccessTokenPayload, Depends(restrict_to_specialist)]
