"""Local filesystem input handler."""

import os
from typing import Optional
from api_extractor.input_handlers.base import BaseHandler


class LocalHandler(BaseHandler):
    """Handle local filesystem paths."""

    def get_path(self, source: str) -> Optional[str]:
        """
        Get local path.

        Args:
            source: Local filesystem path

        Returns:
            Absolute path if exists, None otherwise
        """
        if not os.path.exists(source):
            return None

        if not os.path.isdir(source):
            return None

        return os.path.abspath(source)

    def cleanup(self) -> None:
        """No cleanup needed for local paths."""
        pass

    def is_valid_source(self, source: str) -> bool:
        """
        Check if source is a valid local path.

        Args:
            source: Path to check

        Returns:
            True if path exists and is a directory
        """
        return os.path.exists(source) and os.path.isdir(source)
