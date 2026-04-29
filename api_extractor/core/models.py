"""Core data models for API extraction."""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class FrameworkType(str, Enum):
    """Supported framework types."""

    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO_REST = "django_rest"
    EXPRESS = "express"
    NESTJS = "nestjs"
    FASTIFY = "fastify"
    SPRING_BOOT = "spring_boot"
    NEXTJS = "nextjs"
    ASPNET_CORE = "aspnet_core"
    GIN = "gin"


class ParameterLocation(str, Enum):
    """Parameter location in request."""

    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"
    BODY = "body"


class HTTPMethod(str, Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class Schema(BaseModel):
    """Schema definition for request/response."""

    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    example: Optional[Any] = None
    ref: Optional[str] = None  # Reference to a reusable schema
    items: Optional[Any] = None  # For array type schemas


class Parameter(BaseModel):
    """API parameter definition."""

    model_config = {"populate_by_name": True}

    name: str
    location: ParameterLocation
    type: str = "string"
    required: bool = False
    description: Optional[str] = None
    default: Optional[Any] = None
    param_schema: Optional[Schema] = Field(None, alias="schema")


class Response(BaseModel):
    """API response definition."""

    model_config = {"populate_by_name": True}

    status_code: str = "200"
    description: str = "Success"
    response_schema: Optional[Schema] = Field(None, alias="schema")
    content_type: str = "application/json"


class Endpoint(BaseModel):
    """API endpoint definition."""

    path: str
    method: HTTPMethod
    parameters: List[Parameter] = Field(default_factory=list)
    request_body: Optional[Schema] = None
    responses: List[Response] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    description: Optional[str] = None
    operation_id: Optional[str] = None
    source_file: Optional[str] = None
    source_line: Optional[int] = None


class Route(BaseModel):
    """Internal route representation before OpenAPI conversion."""

    path: str
    methods: List[HTTPMethod]
    handler_name: Optional[str] = None
    framework: FrameworkType
    raw_path: str  # Original path with framework-specific syntax
    source_file: str
    source_line: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    """Result of API extraction."""

    success: bool
    endpoints: List[Endpoint] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    frameworks_detected: List[FrameworkType] = Field(default_factory=list)
