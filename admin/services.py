from typing import Sequence
from admin.repository import AdminRepository
from admin.schemas import ChangeRoleEntity, SearchEntity
from auth.models import AuthEntity
from fastapi import HTTPException, status
from .schemas import AdminIn
from utils import auth
from sqlalchemy.exc import IntegrityError
from common.paginations import PaginationEntity


class AdminServices:
    def __init__(self, repository: AdminRepository):
        self.repo = repository

    async def create_admin(self, admin_info: AdminIn) -> AuthEntity:
        hashed_password = await auth.hash_password(admin_info.password)
        admin_data = admin_info.model_dump(exclude={"password"})
        admin_data["hash_password"] = hashed_password
        try:
            return await self.repo.create_entity(admin_data)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entity with this email or login already exists",
            )

    async def change_role(self, entity_info: ChangeRoleEntity) -> AuthEntity:
        entity = await self.repo.change_role_entity(
            entity_id=entity_info.entity_id, change_role=entity_info.new_role
        )
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found by ID: {entity_info.entity_id}",
            )

        return entity

    async def get_all_entity(
        self,
        search_entity: SearchEntity,
        pagination: PaginationEntity,
    ) -> Sequence[AuthEntity]:
        return await self.repo.get_all_entities(
            login=search_entity.login,
            email=search_entity.email,
            role=search_entity.role,
            offset=pagination.offset,
            limit=pagination.limit,
        )

    async def get_entity_by_id(self, entity_id: int) -> AuthEntity:
        entity = await self.repo.get_entity_by_id(entity_id=entity_id)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found by ID: {entity_id}",
            )
        return entity

    async def delete_entity_by_id(self, entity_id: int):
        deleted = await self.repo.delete_entity_by_id(entity_id=entity_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found by ID: {entity_id}",
            )
