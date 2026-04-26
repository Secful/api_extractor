"""Input source handlers."""

from api_extractor.input_handlers.base import BaseHandler
from api_extractor.input_handlers.local import LocalHandler
from api_extractor.input_handlers.s3 import S3Handler

__all__ = ["BaseHandler", "LocalHandler", "S3Handler"]
