from pydantic import BaseModel, Field


class Pagination(BaseModel):
    limit: int = Field(100, gt=0)
    offset: int = Field(0, ge=0)


class PaginationEntity(Pagination):
    pass


class PaginationTest(Pagination):
    pass
