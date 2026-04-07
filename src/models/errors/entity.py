from typing import Annotated

from pydantic import Field

from src.models.base import BaseEntityModel


class ErrorModel(BaseEntityModel):
    error_class: Annotated[
        str | None,
        Field(description="Error class name", alias="errorClass", default=None),
    ]
    type: Annotated[str, Field(description="Error type", default=None)]
    error_message: Annotated[
        str | None,
        Field(description="Error message", alias="errorMessage", default=None),
    ]
    field: Annotated[str | None, Field(description="Field name", default=None)]
    key: Annotated[str | None, Field(description="Key name", default=None)]
    args: Annotated[list | None, Field(description="Arguments", default=None)]


class ServiceErrorModel(BaseEntityModel):
    errors: Annotated[list[ErrorModel], Field(description="List of errors")]
