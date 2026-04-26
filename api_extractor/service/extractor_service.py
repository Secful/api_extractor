"""Core extraction service for API Extractor."""

import logging
from typing import List, Optional
from pathlib import Path

from api_extractor.core.detector import FrameworkDetector
from api_extractor.core.models import FrameworkType
from api_extractor.openapi.builder import OpenAPIBuilder
from api_extractor.input_handlers.local import LocalHandler
from api_extractor.input_handlers.s3 import S3Handler
from api_extractor.service.models import ExtractionServiceResult

logger = logging.getLogger(__name__)


def get_extractor(framework: FrameworkType):
    """
    Get extractor instance for framework.

    Args:
        framework: Framework type

    Returns:
        Extractor instance or None
    """
    if framework == FrameworkType.FASTAPI:
        from api_extractor.extractors.python.fastapi import FastAPIExtractor
        return FastAPIExtractor()
    elif framework == FrameworkType.FLASK:
        from api_extractor.extractors.python.flask import FlaskExtractor
        return FlaskExtractor()
    elif framework == FrameworkType.DJANGO_REST:
        from api_extractor.extractors.python.django_rest import DjangoRESTExtractor
        return DjangoRESTExtractor()
    elif framework == FrameworkType.EXPRESS:
        from api_extractor.extractors.javascript.express import ExpressExtractor
        return ExpressExtractor()
    elif framework == FrameworkType.NESTJS:
        from api_extractor.extractors.javascript.nestjs import NestJSExtractor
        return NestJSExtractor()
    elif framework == FrameworkType.FASTIFY:
        from api_extractor.extractors.javascript.fastify import FastifyExtractor
        return FastifyExtractor()
    else:
        return None


class ExtractionService:
    """Service for extracting API definitions from source code."""

    def extract_api(
        self,
        path: str,
        frameworks: Optional[List[FrameworkType]] = None,
        s3: bool = False,
        title: str = "Extracted API",
        version: str = "1.0.0",
        description: Optional[str] = None,
    ) -> ExtractionServiceResult:
        """
        Extract API definitions from source code.

        Args:
            path: Path to codebase (local directory or S3 URI)
            frameworks: List of frameworks to extract from (None for auto-detect)
            s3: Whether path is an S3 URI
            title: API title for OpenAPI spec
            version: API version for OpenAPI spec
            description: API description for OpenAPI spec

        Returns:
            ExtractionServiceResult with extraction results
        """
        result = ExtractionServiceResult(success=False)
        handler = None

        try:
            # Determine input handler
            if s3:
                handler = S3Handler()
                logger.info("Using S3 handler")
            else:
                handler = LocalHandler()
                logger.info("Using local filesystem handler")

            # Validate source
            if not handler.is_valid_source(path):
                if s3:
                    result.errors.append(f"Invalid S3 URI: {path}")
                else:
                    result.errors.append(f"Path not found or not a directory: {path}")
                return result

            # Get local path
            local_path = handler.get_path(path)
            if not local_path:
                result.errors.append(f"Failed to access source: {path}")
                return result

            logger.info(f"Processing: {local_path}")

            # Detect or use specified frameworks
            detected_frameworks: Optional[List[FrameworkType]] = None

            if frameworks:
                # Manual framework specification
                detected_frameworks = frameworks
                logger.info(f"Using manually specified frameworks: {', '.join(f.value for f in frameworks)}")
            else:
                # Automatic detection
                logger.info("Detecting frameworks...")
                detector = FrameworkDetector()
                detected_frameworks = detector.detect(local_path)

                if detected_frameworks is None:
                    result.errors.append("Unable to detect any supported frameworks")
                    result.warnings.append("Use manual framework specification if detection fails")
                    return result

                logger.info(f"Detected frameworks: {', '.join(f.value for f in detected_frameworks)}")

            result.frameworks_detected = detected_frameworks

            # Extract routes from each framework
            logger.info("Extracting routes...")
            all_endpoints = []
            all_errors = []
            all_warnings = []

            for fw in detected_frameworks:
                extractor = get_extractor(fw)
                if not extractor:
                    logger.warning(f"Skipping {fw.value}: extractor not yet implemented")
                    result.warnings.append(f"Extractor not implemented for {fw.value}")
                    continue

                extraction_result = extractor.extract(local_path)

                if extraction_result.success:
                    all_endpoints.extend(extraction_result.endpoints)
                    logger.info(f"{fw.value}: {len(extraction_result.endpoints)} endpoints found")
                else:
                    logger.warning(f"{fw.value}: No endpoints found")

                all_errors.extend(extraction_result.errors)
                all_warnings.extend(extraction_result.warnings)

            # Check if we found any endpoints
            if not all_endpoints:
                result.errors.append("No API endpoints found")
                result.errors.extend(all_errors[:5])  # Include first 5 extraction errors
                result.warnings.extend(all_warnings[:10])
                return result

            result.endpoints_count = len(all_endpoints)

            # Generate OpenAPI spec
            logger.info("Generating OpenAPI spec...")
            builder = OpenAPIBuilder(title=title, version=version, description=description)
            spec = builder.build(all_endpoints)

            result.openapi_spec = spec
            result.errors = all_errors
            result.warnings = all_warnings
            result.success = True

            # Add metadata
            result.metadata = {
                "source_path": path,
                "is_s3": s3,
                "frameworks_used": [f.value for f in detected_frameworks],
            }

            return result

        except Exception as e:
            logger.exception("Extraction failed with exception")
            result.errors.append(f"Extraction failed: {str(e)}")
            return result

        finally:
            # Cleanup
            if handler:
                try:
                    handler.cleanup()
                except Exception as e:
                    logger.warning(f"Cleanup failed: {e}")
