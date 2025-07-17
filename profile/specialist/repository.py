from sqlalchemy.ext.asyncio import AsyncSession


class SpecialistRepository:

    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session
