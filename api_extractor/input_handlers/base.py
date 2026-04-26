"""Base input handler interface."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseHandler(ABC):
    """Abstract base class for input handlers."""

    @abstractmethod
    def get_path(self, source: str) -> Optional[str]:
        """
        Get local path for the source.

        Args:
            source: Source identifier (local path or S3 URI)

        Returns:
            Local path to process, or None on error
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up any temporary resources."""
        pass

    @abstractmethod
    def is_valid_source(self, source: str) -> bool:
        """
        Check if source is valid for this handler.

        Args:
            source: Source identifier

        Returns:
            True if handler can process this source
        """
        pass
