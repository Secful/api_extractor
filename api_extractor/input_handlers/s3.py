"""S3 input handler."""

import os
import tempfile
import shutil
from typing import Optional
from urllib.parse import urlparse

from api_extractor.input_handlers.base import BaseHandler


class S3Handler(BaseHandler):
    """Handle S3 URIs by downloading to temporary directory."""

    def __init__(self) -> None:
        """Initialize handler."""
        self.temp_dir: Optional[str] = None
        self._s3_client = None

    def _get_s3_client(self):
        """Lazy load boto3 S3 client."""
        if self._s3_client is None:
            try:
                import boto3

                self._s3_client = boto3.client("s3")
            except ImportError:
                raise ImportError(
                    "boto3 is required for S3 support. Install with: pip install boto3"
                )
        return self._s3_client

    def get_path(self, source: str) -> Optional[str]:
        """
        Download S3 content to temporary directory.

        Args:
            source: S3 URI (s3://bucket/path/)

        Returns:
            Local temporary path or None on error
        """
        if not self.is_valid_source(source):
            return None

        try:
            # Parse S3 URI
            parsed = urlparse(source)
            bucket = parsed.netloc
            prefix = parsed.path.lstrip("/")

            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="api_extractor_")

            # Download S3 content
            s3_client = self._get_s3_client()

            # List objects with prefix
            paginator = s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

            for page in pages:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    key = obj["Key"]

                    # Skip if it's just the prefix (directory marker)
                    if key == prefix or key.endswith("/"):
                        continue

                    # Calculate local path
                    relative_path = key[len(prefix) :].lstrip("/")
                    local_path = os.path.join(self.temp_dir, relative_path)

                    # Create directory if needed
                    local_dir = os.path.dirname(local_path)
                    os.makedirs(local_dir, exist_ok=True)

                    # Download file
                    s3_client.download_file(bucket, key, local_path)

            return self.temp_dir

        except Exception as e:
            # Clean up on error
            self.cleanup()
            raise RuntimeError(f"Error downloading from S3: {str(e)}")

    def cleanup(self) -> None:
        """Remove temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
            finally:
                self.temp_dir = None

    def is_valid_source(self, source: str) -> bool:
        """
        Check if source is a valid S3 URI.

        Args:
            source: Source to check

        Returns:
            True if source is S3 URI
        """
        return source.startswith("s3://")

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.cleanup()
