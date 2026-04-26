"""API routes for API Extractor HTTP server."""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, status

from api_extractor.core.models import FrameworkType
from api_extractor.service import ExtractionService
from api_extractor.server.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    InfoResponse,
    ErrorResponse,
)
from api_extractor.server.security import validate_path, check_path_exists
from api_extractor.server.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["monitoring"],
    summary="Health check",
    description="Check if the service is healthy and responsive",
)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(status="healthy", version=settings.api_version)


@router.get(
    "/info",
    response_model=InfoResponse,
    tags=["information"],
    summary="Service information",
    description="Get information about the service capabilities and supported frameworks",
)
def service_info() -> InfoResponse:
    """Service information endpoint."""
    settings = get_settings()
    return InfoResponse(
        version=settings.api_version,
        supported_frameworks=[f.value for f in FrameworkType],
        features={
            "s3_support": settings.enable_s3,
            "auto_detection": True,
            "multiple_frameworks": True,
        },
    )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    tags=["extraction"],
    summary="Analyze codebase",
    description="Extract REST API definitions from source code and generate OpenAPI specification",
    responses={
        200: {"description": "Successful extraction"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        403: {"model": ErrorResponse, "description": "Forbidden path"},
        404: {"model": ErrorResponse, "description": "Path not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def analyze_codebase(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze codebase and extract API definitions.

    This endpoint accepts a path to source code (local or S3) and extracts
    REST API definitions, generating an OpenAPI specification.
    """
    settings = get_settings()

    try:
        # Security validation
        logger.info(f"Analyzing path: {request.path}, S3: {request.s3}")

        # Check if S3 is enabled
        if request.s3 and not settings.enable_s3:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="S3 support is disabled",
            )

        # Validate path
        try:
            validate_path(
                request.path,
                request.s3,
                settings.allowed_path_prefixes if settings.allowed_path_prefixes else None,
            )
        except PermissionError as e:
            logger.warning(f"Permission denied for path {request.path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        except ValueError as e:
            logger.warning(f"Invalid path {request.path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Check if path exists (local only)
        if not request.s3:
            try:
                check_path_exists(request.path, request.s3)
            except FileNotFoundError as e:
                logger.warning(f"Path not found: {request.path}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                )
            except ValueError as e:
                logger.warning(f"Invalid path: {request.path}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

        # Perform extraction
        service = ExtractionService()
        result = service.extract_api(
            path=request.path,
            frameworks=None,
            s3=request.s3,
            title=request.title,
            version=request.version,
            description=request.description,
        )

        # Convert OpenAPISpec to dict for JSON response
        openapi_dict = None
        if result.openapi_spec:
            openapi_dict = result.openapi_spec.model_dump(exclude_none=True)

        # Build response
        response = AnalyzeResponse(
            success=result.success,
            openapi_spec=openapi_dict,
            endpoints_count=result.endpoints_count,
            frameworks_detected=[f.value for f in result.frameworks_detected],
            errors=result.errors,
            warnings=result.warnings,
            metadata=result.metadata,
        )

        if not result.success:
            # Return 200 with success=false and errors in response body
            # This allows clients to see what went wrong
            logger.warning(f"Extraction failed: {result.errors}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during extraction")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
