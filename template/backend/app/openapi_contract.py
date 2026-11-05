from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import JsonValue

from app.rate_limit_middleware import UNLIMITED_PATHS
from app.shared.schemas import ErrorResponse

ERROR_RESPONSE_SCHEMA_NAME = "ErrorResponse"
ERROR_RESPONSE_CONTENT: dict[str, JsonValue] = {
    "application/json": {"schema": {"$ref": f"#/components/schemas/{ERROR_RESPONSE_SCHEMA_NAME}"}}
}
SHARED_ERROR_RESPONSES: dict[str, JsonValue] = {
    "ValidationFailed": {
        "description": "The path, query or body is not valid; code `validation_error`.",
        "content": ERROR_RESPONSE_CONTENT,
    },
    "RateLimited": {
        "description": "Over a request budget; code `rate_limited`, with `Retry-After`.",
        "headers": {"Retry-After": {"schema": {"type": "integer"}}},
        "content": ERROR_RESPONSE_CONTENT,
    },
    "ApiError": {
        "description": "Any refusal: `{error: {code, message}}`.",
        "content": ERROR_RESPONSE_CONTENT,
    },
}


def name_operation_after_handler(route: APIRoute) -> str:
    return route.name


def strip_titles_below(node: JsonValue) -> None:
    match node:
        case dict():
            match node.get("title"):
                case str():
                    del node["title"]
                case _:
                    pass
            for key, value in node.items():
                match (key, value):
                    case ("properties", dict()):
                        for property_schema in value.values():
                            strip_titles_below(property_schema)
                    case _:
                        strip_titles_below(value)
        case list():
            for item in node:
                strip_titles_below(item)
        case _:
            pass


def reference_shared_response(response_name: str) -> dict[str, JsonValue]:
    return {"$ref": f"#/components/responses/{response_name}"}


def document_operation_errors(operation: JsonValue, *, path: str) -> None:
    match operation:
        case {"responses": dict() as responses}:
            if responses.pop("422", None) is not None:
                responses.setdefault("400", reference_shared_response("ValidationFailed"))
            if path not in UNLIMITED_PATHS:
                responses.setdefault("429", reference_shared_response("RateLimited"))
            responses.setdefault("default", reference_shared_response("ApiError"))
        case _:
            pass


def read_object_member(container: dict[str, JsonValue], *, member_name: str) -> dict[str, JsonValue]:
    match container.setdefault(member_name, {}):
        case dict() as member:
            return member
        case _:
            return {}


def add_error_components(components: dict[str, JsonValue]) -> None:
    component_schemas = read_object_member(components, member_name="schemas")
    component_schemas.pop("HTTPValidationError", None)
    component_schemas.pop("ValidationError", None)
    error_response_schema: dict[str, JsonValue] = ErrorResponse.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    component_schemas.update(read_object_member(error_response_schema, member_name="$defs"))
    error_response_schema.pop("$defs")
    component_schemas[ERROR_RESPONSE_SCHEMA_NAME] = error_response_schema
    read_object_member(components, member_name="responses").update(SHARED_ERROR_RESPONSES)


def document_path_errors(path_item: JsonValue, *, path: str) -> None:
    match path_item:
        case dict():
            for operation in path_item.values():
                document_operation_errors(operation, path=path)
        case _:
            pass


def build_contract_openapi(openapi_schema: dict[str, JsonValue]) -> dict[str, JsonValue]:
    add_error_components(read_object_member(openapi_schema, member_name="components"))
    for path, path_item in read_object_member(openapi_schema, member_name="paths").items():
        document_path_errors(path_item, path=path)
    for section_name in ("paths", "components"):
        strip_titles_below(openapi_schema.get(section_name))
    return openapi_schema


def install_openapi_contract(application: FastAPI) -> None:
    generate_default_openapi = application.openapi

    def generate_contract_openapi() -> dict[str, JsonValue]:
        if application.openapi_schema is None:
            application.openapi_schema = build_contract_openapi(generate_default_openapi())
        return application.openapi_schema

    application.openapi = generate_contract_openapi  # ty: ignore[invalid-assignment]  # FastAPI's override point
