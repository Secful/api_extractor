"""Request and response schemas for API endpoints."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request schema for analyze endpoint."""

    path: str = Field(..., description="Path to codebase (local directory or S3 URI)")
    s3: bool = Field(False, description="Whether path is an S3 URI")
    title: str = Field("Extracted API", description="API title for OpenAPI spec")
    version: str = Field("1.0.0", description="API version for OpenAPI spec")
    description: Optional[str] = Field(None, description="API description for OpenAPI spec")

    class Config:
        json_schema_extra = {
            "example": {
                "path": "/app/code",
                "s3": False,
                "title": "My API",
                "version": "1.0.0",
                "description": "My REST API",
            }
        }


class AnalyzeResponse(BaseModel):
    """Response schema for analyze endpoint."""

    success: bool = Field(..., description="Whether extraction was successful")
    openapi_spec: Optional[Dict[str, Any]] = Field(None, description="Generated OpenAPI specification")
    endpoints_count: int = Field(0, description="Number of endpoints found")
    frameworks_detected: List[str] = Field([], description="Frameworks detected/used")
    errors: List[str] = Field([], description="Errors encountered during extraction")
    warnings: List[str] = Field([], description="Warnings encountered during extraction")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "openapi_spec": {"openapi": "3.0.0", "info": {"title": "My API", "version": "1.0.0"}},
                "endpoints_count": 5,
                "frameworks_detected": ["fastapi"],
                "errors": [],
                "warnings": [],
                "metadata": {"source_path": "/app/code", "is_s3": False, "frameworks_used": ["fastapi"]},
            }
        }


class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Service version")

    class Config:
        json_schema_extra = {"example": {"status": "healthy", "version": "0.1.0"}}


class InfoResponse(BaseModel):
    """Response schema for info endpoint."""

    version: str = Field(..., description="Service version")
    supported_frameworks: List[str] = Field(..., description="List of supported frameworks")
    features: Dict[str, bool] = Field(..., description="Available features")

    class Config:
        json_schema_extra = {
            "example": {
                "version": "0.1.0",
                "supported_frameworks": ["fastapi", "flask", "django_rest", "express", "nestjs", "fastify"],
                "features": {"s3_support": True, "auto_detection": True, "multiple_frameworks": True},
            }
        }


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str = Field(..., description="Human-readable error message")
    error_type: str = Field(..., description="Type of error")

    class Config:
        json_schema_extra = {"example": {"detail": "Path not found", "error_type": "ValidationError"}}
