"""Pydantic models for OpenAPI 3.1 specification."""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class Contact(BaseModel):
    """Contact information."""

    name: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None


class License(BaseModel):
    """License information."""

    name: str
    url: Optional[str] = None


class Info(BaseModel):
    """API information."""

    title: str
    version: str
    description: Optional[str] = None
    terms_of_service: Optional[str] = Field(None, alias="termsOfService")
    contact: Optional[Contact] = None
    license: Optional[License] = None


class Server(BaseModel):
    """Server information."""

    url: str
    description: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None


class SchemaObject(BaseModel):
    """JSON Schema object."""

    type: Optional[str] = None
    format: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    default: Optional[Any] = None
    example: Optional[Any] = None
    properties: Optional[Dict[str, "SchemaObject"]] = None
    required: Optional[List[str]] = None
    items: Optional["SchemaObject"] = None
    enum: Optional[List[Any]] = None
    ref: Optional[str] = Field(None, alias="$ref")
    additional_properties: Optional[Union[bool, "SchemaObject"]] = Field(
        None, alias="additionalProperties"
    )


class ParameterObject(BaseModel):
    """Parameter object."""

    model_config = {"populate_by_name": True}

    name: str
    in_: str = Field(..., alias="in")
    description: Optional[str] = None
    required: Optional[bool] = False
    deprecated: Optional[bool] = False
    schema_: Optional[SchemaObject] = Field(None, alias="schema")
    example: Optional[Any] = None


class MediaType(BaseModel):
    """Media type object."""

    model_config = {"populate_by_name": True}

    schema_: Optional[SchemaObject] = Field(None, alias="schema")
    example: Optional[Any] = None
    examples: Optional[Dict[str, Any]] = None


class RequestBody(BaseModel):
    """Request body object."""

    description: Optional[str] = None
    content: Dict[str, MediaType]
    required: Optional[bool] = False


class Response(BaseModel):
    """Response object."""

    description: str
    content: Optional[Dict[str, MediaType]] = None
    headers: Optional[Dict[str, Any]] = None


class Operation(BaseModel):
    """Operation object."""

    model_config = {"populate_by_name": True}

    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    operation_id: Optional[str] = Field(None, alias="operationId")
    parameters: Optional[List[ParameterObject]] = None
    request_body: Optional[RequestBody] = Field(None, alias="requestBody")
    responses: Dict[str, Response]
    deprecated: Optional[bool] = False
    security: Optional[List[Dict[str, List[str]]]] = None


class PathItem(BaseModel):
    """Path item object."""

    summary: Optional[str] = None
    description: Optional[str] = None
    get: Optional[Operation] = None
    put: Optional[Operation] = None
    post: Optional[Operation] = None
    delete: Optional[Operation] = None
    options: Optional[Operation] = None
    head: Optional[Operation] = None
    patch: Optional[Operation] = None
    parameters: Optional[List[ParameterObject]] = None


class Tag(BaseModel):
    """Tag object."""

    name: str
    description: Optional[str] = None


class OpenAPISpec(BaseModel):
    """OpenAPI 3.1 Specification."""

    model_config = {"populate_by_name": True}

    openapi: str = "3.1.0"
    info: Info
    servers: Optional[List[Server]] = Field(default_factory=list)
    paths: Dict[str, PathItem] = Field(default_factory=dict)
    components: Optional[Dict[str, Any]] = None
    security: Optional[List[Dict[str, List[str]]]] = None
    tags: Optional[List[Tag]] = None
