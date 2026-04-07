from pydantic import BaseModel, Field


class BaseSchema(BaseModel):
    pass


class BaseResponse(BaseModel):
    pass


class BasePayloadResponse[T](BaseSchema):
    payload: T | list[T] = Field(..., description="The payload of the response")


class BaseRequest(BaseModel):
    pass
