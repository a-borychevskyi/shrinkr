from typing import Annotated

from pydantic import Field

from src.models.base import BaseEntityModel


class ErrorModel(BaseEntityModel):
    error_class: Annotated[
        str | None,
        Field(description="Error class name", alias="errorClass"),
    ] = None
    type: Annotated[str, Field(description="Error type")] = None
    error_message: Annotated[
        str | None,
        Field(description="Error message", alias="errorMessage"),
    ] = None
    field: Annotated[str | None, Field(description="Field name")] = None
    key: Annotated[str | None, Field(description="Key name")] = None
    args: Annotated[list | None, Field(description="Arguments")] = None


class ServiceErrorModel(BaseEntityModel):
    errors: Annotated[list[ErrorModel], Field(description="List of errors")]
