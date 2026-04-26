"""Service layer result models."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from api_extractor.core.models import FrameworkType
from api_extractor.openapi.models import OpenAPISpec


class ExtractionServiceResult(BaseModel):
    """Result of extraction service operation."""

    success: bool
    openapi_spec: Optional[OpenAPISpec] = None
    endpoints_count: int = 0
    frameworks_detected: List[FrameworkType] = []
    errors: List[str] = []
    warnings: List[str] = []
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True
