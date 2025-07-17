from typing import Annotated
from common.db_helper import SessionDep
from common.enums import Role
from .schemas import AccessTokenPayload
from .repository import RoleRequestRepository, AuthRepository
from .services import RoleRequestService, AuthServices


from fastapi import (
    Depends,
    Request,
    Response,
    HTTPException,
    status,
)


async def get_auth_service(session: SessionDep) -> AuthServices:
    return AuthServices(
        repository=AuthRepository(session=session),
        role_request_repo=RoleRequestRepository(session=session),
    )


AuthServiceDep = Annotated[AuthServices, Depends(get_auth_service)]


async def get_payload(
    request: Request,
    response: Response,
    service: AuthServiceDep,
):
    return await service.access_token_payload(request, response)


PayloadEntity = Annotated[AccessTokenPayload, Depends(get_payload)]


async def restrict_to_entity(
    payload: PayloadEntity,
    role_entity: Role,
) -> AccessTokenPayload:
    role = payload.role

    if role == "admin":
        return payload
    elif role != role_entity:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden auth",
        )
    return payload


async def get_role_request_service(session: SessionDep) -> RoleRequestService:
    return RoleRequestService(
        repo=RoleRequestRepository(session=session),
        entity_repo=AuthRepository(session=session),
    )


RoleRequestServiceDep = Annotated[RoleRequestService, Depends(get_role_request_service)]
