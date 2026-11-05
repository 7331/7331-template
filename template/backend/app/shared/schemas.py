from pydantic import BaseModel, ConfigDict


class ApiRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, json_schema_serialization_defaults_required=True)


class ErrorBody(ApiResponse):
    code: str
    message: str


class ErrorResponse(ApiResponse):
    error: ErrorBody


class HealthResponse(ApiResponse):
    status: str
