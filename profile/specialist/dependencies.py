from typing import Annotated

from auth.schemas import AccessTokenPayload
from fastapi import Depends
from common.enums import Role
from auth.dependencies import PayloadEntity, restrict_to_entity


async def restrict_to_specialist(payload: PayloadEntity) -> AccessTokenPayload:
    return await restrict_to_entity(payload=payload, role_entity=Role.SPECIALIST)


RestrictSpecialistDep = Annotated[AccessTokenPayload, Depends(restrict_to_specialist)]
