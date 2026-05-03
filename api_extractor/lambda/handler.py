"""AWS Lambda handler for API extraction from S3-mounted source code."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from api_extractor.service import ExtractionService

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# S3 mount point (configured via S3 Files)
S3_MOUNT_PATH = os.environ.get("S3_MOUNT_PATH", "/mnt/s3")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Lambda handler for API extraction.

    Expected input (JSON body):
        {
            "folder": "my-project",           # Required: folder name in mounted S3
            "title": "My API",                 # Optional: OpenAPI title
            "version": "1.0.0",                # Optional: API version
            "description": "API description"   # Optional: API description
        }

    Returns:
        {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": JSON-serialized OpenAPI 3.1.0 spec
        }
    """
    try:
        # Parse input
        body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
        folder = body.get("folder")

        if not folder:
            return error_response(400, "Missing required field: 'folder'")

        # Construct path from mounted S3 filesystem
        # All project folders are under /lambda/ prefix in S3
        code_path = Path(S3_MOUNT_PATH) / "lambda" / folder
        logger.info(f"Processing: {code_path}")

        # Verify mount point exists
        if not Path(S3_MOUNT_PATH).exists():
            logger.error(f"S3 mount point not found: {S3_MOUNT_PATH}")
            return error_response(500, f"S3 filesystem not mounted at {S3_MOUNT_PATH}")

        # Verify folder exists
        if not code_path.exists():
            logger.warning(f"Folder not found: {folder}")
            return error_response(404, f"Folder not found: {folder}")

        if not code_path.is_dir():
            logger.warning(f"Path is not a directory: {folder}")
            return error_response(400, f"Path is not a directory: {folder}")

        logger.info(f"Extracting API from: {code_path}")

        # Extract API using api_extractor service
        service = ExtractionService()
        result = service.extract_api(
            path=str(code_path),
            title=body.get("title", "Extracted API"),
            version=body.get("version", "1.0.0"),
            description=body.get("description"),
        )

        if not result.success:
            logger.warning(f"Extraction failed: {result.errors}")
            return error_response(
                422,
                "Extraction failed",
                {
                    "errors": result.errors,
                    "warnings": result.warnings,
                },
            )

        # Return OpenAPI spec as JSON
        openapi_spec = result.openapi_spec.model_dump(exclude_none=True, by_alias=True)

        logger.info(
            f"Successfully extracted {result.endpoints_count} endpoints "
            f"from frameworks: {', '.join(f.value for f in result.frameworks_detected)}"
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Endpoints-Count": str(result.endpoints_count),
                "X-Frameworks": ",".join(f.value for f in result.frameworks_detected),
            },
            "body": json.dumps(openapi_spec),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        return error_response(400, f"Invalid JSON: {str(e)}")

    except Exception as e:
        logger.exception("Unexpected error during extraction")
        return error_response(500, f"Internal error: {str(e)}")


def error_response(
    status_code: int, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build error response."""
    body: dict[str, Any] = {"error": message}
    if details:
        body.update(details)

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
