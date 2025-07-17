from typing import Sequence, Annotated

from fastapi import (
    APIRouter,
    Response,
    Depends,
    Form,
    Query,
    status,
    Path,
)

from auth.dependencies import RoleRequestServiceDep
from .dependencies import AdminServicesDep, RestrictAdminDep
from .schemas import AdminIn, AdminOut, ChangeRoleEntity, SearchEntity
from auth.schemas import AuthEntityOut, RoleRequestListOut, RoleRequestOut
from common.paginations import PaginationEntity
from common.enums import RoleRequestStatus

router = APIRouter(prefix="/admin", tags=["ADMIN ENDPOINTS"])


@router.post("/create")
async def create_admin(
    services: AdminServicesDep, admin_info: Annotated[AdminIn, Form()]
) -> AdminOut:
    return await services.create_admin(admin_info)


@router.patch("/change-role-entity")
async def change_role_entity(
    restrict_admin: RestrictAdminDep,
    change_entity: ChangeRoleEntity,
    services: AdminServicesDep,
) -> AuthEntityOut:
    return await services.change_role(entity_info=change_entity)


@router.get("/entities", response_model=Sequence[AuthEntityOut])
async def get_all_entity(
    restrict_admin: RestrictAdminDep,
    services: AdminServicesDep,
    search_entity: SearchEntity = Depends(),
    pagination: PaginationEntity = Depends(),
) -> Sequence[AuthEntityOut]:
    return await services.get_all_entity(
        search_entity=search_entity, pagination=pagination
    )


@router.get("/get/entity/{entity_id}", response_model=AuthEntityOut)
async def get_entity_by_id(
    entity_id: int,
    services: AdminServicesDep,
    restrict_admin: RestrictAdminDep,
):
    return await services.get_entity_by_id(entity_id=entity_id)


@router.delete("/delete/entity/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_id(
    entity_id: int,
    services: AdminServicesDep,
    restrict_admin: RestrictAdminDep,
):
    await services.delete_entity_by_id(entity_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/role-requests",
    response_model=RoleRequestListOut,
    status_code=status.HTTP_200_OK,
)
async def list_role_requests(
    restrict_admin: RestrictAdminDep,
    service: RoleRequestServiceDep,
    status_: RoleRequestStatus | None = Query(None, alias="status"),
    pagination: PaginationEntity = Depends(),
) -> RoleRequestListOut:
    """
    Получить список заявок на смену роли (только для админа).
    """
    total, items = await service.list_requests(
        status_, offset=pagination.offset, limit=pagination.limit
    )
    return RoleRequestListOut(total=total, items=items)


@router.post(
    "/role-request/{request_id}/approve",
    response_model=RoleRequestOut,
    status_code=status.HTTP_200_OK,
)
async def approve_role_request(
    restrict_admin: RestrictAdminDep,
    service: RoleRequestServiceDep,
    request_id: int = Path(..., gt=0),
) -> RoleRequestOut:
    """
    Одобрить заявку на смену роли (только для админа).
    """
    return await service.approve_request(request_id)


@router.post(
    "/role-request/{request_id}/reject",
    response_model=RoleRequestOut,
    status_code=status.HTTP_200_OK,
)
async def reject_role_request(
    restrict_admin: RestrictAdminDep,
    service: RoleRequestServiceDep,
    request_id: int = Path(..., gt=0),
) -> RoleRequestOut:
    """
    Отклонить заявку на смену роли (только для админа).
    """
    return await service.reject_request(request_id)
