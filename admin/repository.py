from typing import Sequence

from sqlalchemy import delete, select, update, Result
from sqlalchemy.ext.asyncio import AsyncSession
from auth.models import AuthEntity
from auth.repository import AuthRepository
from common.enums import Role


class AdminRepository(AuthRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        super().__init__(session)

    async def change_entity_role(
        self, entity_id: int, new_role: Role
    ) -> AuthEntity | None:

        stmt = (
            update(AuthEntity)
            .where(AuthEntity.id == entity_id)
            .values(role=new_role)
            .returning(AuthEntity)
        )

        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def change_role_entity(
        self,
        entity_id: int,
        change_role: Role,
    ) -> AuthEntity | None:
        stmt = (
            update(AuthEntity)
            .where(AuthEntity.id == entity_id)
            .values(role=change_role)
            .returning(AuthEntity)
        )
        result: Result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_all_entities(
        self,
        login: str | None,
        email: str | None,
        role: Role | None,
        offset: int,
        limit: int,
    ) -> Sequence[AuthEntity]:
        stmt = select(AuthEntity)
        if login:
            stmt = stmt.where(AuthEntity.login.ilike(f"%{login}%"))
        if email:
            stmt = stmt.where(AuthEntity.email.ilike(f"%{email}%"))
        if role:
            stmt = stmt.where(AuthEntity.role == role)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_entity_by_id(self, entity_id: int) -> AuthEntity | None:
        stmt = select(AuthEntity).where(AuthEntity.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_entity_by_id(self, entity_id: int) -> bool:
        stmt = (
            delete(AuthEntity)
            .where(AuthEntity.id == entity_id)
            .returning(AuthEntity.id)
        )
        result: Result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()
