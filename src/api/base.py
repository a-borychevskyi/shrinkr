from pydantic import BaseModel, Field


class BaseSchema(BaseModel):
    pass


class BaseResponse(BaseModel):
    pass


class BasePayloadResponse[T: BaseResponse](BaseSchema):
    payload: T = Field(..., description="The payload of the response")
    status_code: int = Field(200, description="The status code of the response")


class BaseRequest(BaseModel):
    pass
