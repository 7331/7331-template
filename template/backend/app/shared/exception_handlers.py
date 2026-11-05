from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.utils import is_body_allowed_for_status_code
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.errors import AppError, InvalidInputError
from app.shared.schemas import ErrorBody, ErrorResponse

NO_STORE_HEADERS: dict[str, str] = {"Cache-Control": "no-store"}
UNNAMED_HTTP_ERROR_CODE = "http_error"


def build_error_json_response(status_code: int, *, code: str, message: str, headers: dict[str, str]) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"), headers=headers)


def build_app_error_response(error: AppError) -> JSONResponse:
    headers = dict(NO_STORE_HEADERS) | dict(error.response_headers)
    if error.retry_after_seconds is not None:
        headers["Retry-After"] = str(error.retry_after_seconds)
    return build_error_json_response(error.status, code=error.code, message=error.message, headers=headers)


def name_http_error_code(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase.lower().replace(" ", "_").replace("-", "_")
    except ValueError:
        return UNNAMED_HTTP_ERROR_CODE


def build_http_exception_response(error: StarletteHTTPException) -> Response:
    headers = dict(NO_STORE_HEADERS) | dict(error.headers or {})
    if not is_body_allowed_for_status_code(error.status_code):
        return Response(status_code=error.status_code, headers=headers)
    return build_error_json_response(
        error.status_code,
        code=name_http_error_code(error.status_code),
        message=str(error.detail).lower(),
        headers=headers,
    )


def describe_validation_error(error: RequestValidationError) -> str:
    validation_errors = error.errors()
    if not validation_errors:
        return "invalid request"
    location = validation_errors[0]["loc"]
    field_name = str(location[1] if len(location) > 1 else location[0]) if location else ""
    return f"{field_name}: invalid value" if field_name else "invalid request"


def register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(AppError)
    async def handle_app_error(_request: Request, error: AppError) -> JSONResponse:
        return build_app_error_response(error)

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_request: Request, error: StarletteHTTPException) -> Response:
        return build_http_exception_response(error)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        return build_app_error_response(InvalidInputError(describe_validation_error(error)))
