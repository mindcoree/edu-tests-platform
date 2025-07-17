from typing import Annotated

from sqlalchemy.orm import mapped_column
from sqlalchemy import JSON
from pydantic import Field, StringConstraints, BaseModel


JSON = Annotated[dict, mapped_column(JSON)]


login = Annotated[
    str,
    Field(
        min_length=8,
        max_length=40,
        description="Login must be between 8 and 40 characters.",
        examples=["mindcore"],
    ),
]

password = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=40,
        pattern=r"^[A-Za-z\d@$!%*#?&]+$",
    ),
]
