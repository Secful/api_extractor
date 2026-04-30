"""Base extractor class for framework-specific extractors."""

import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path

from api_extractor.core.models import (
    Endpoint,
    Route,
    Parameter,
    Schema,
    Response,
    HTTPMethod,
    FrameworkType,
    ExtractionResult,
)
from api_extractor.core.parser import LanguageParser


class BaseExtractor(ABC):
    """Abstract base class for framework-specific extractors."""

    def __init__(self, framework: FrameworkType) -> None:
        """
        Initialize extractor.

        Args:
            framework: Framework type this extractor handles
        """
        self.framework = framework
        self.parser = LanguageParser()
        self.endpoints: List[Endpoint] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @abstractmethod
    def get_file_extensions(self) -> List[str]:
        """
        Get file extensions this extractor handles.

        Returns:
            List of file extensions (e.g., ['.py', '.js'])
        """
        pass

    @abstractmethod
    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a single file.

        Args:
            file_path: Path to source file

        Returns:
            List of Route objects
        """
        pass

    def extract(self, path: str) -> ExtractionResult:
        """
        Main entry point for extraction.

        Args:
            path: Path to codebase directory

        Returns:
            ExtractionResult with endpoints and any errors
        """
        self.endpoints = []
        self.errors = []
        self.warnings = []

        # Find all relevant files
        files = self._find_source_files(path)

        # Extract routes from each file
        all_routes: List[Route] = []
        for file_path in files:
            try:
                routes = self.extract_routes_from_file(file_path)
                all_routes.extend(routes)
            except Exception as e:
                self.errors.append(f"Error extracting from {file_path}: {str(e)}")

        # Convert routes to endpoints
        for route in all_routes:
            try:
                endpoints = self._route_to_endpoints(route)
                self.endpoints.extend(endpoints)
            except Exception as e:
                self.errors.append(f"Error converting route {route.path}: {str(e)}")

        # Validate OpenAPI spec if endpoints were extracted
        if self.endpoints:
            validation_errors = self._validate_openapi_spec()
            if validation_errors:
                self.errors.extend(validation_errors)

        return ExtractionResult(
            success=len(self.endpoints) > 0 and len(self.errors) == 0,
            endpoints=self.endpoints,
            errors=self.errors,
            warnings=self.warnings,
            frameworks_detected=[self.framework],
        )

    def _validate_openapi_spec(self) -> List[str]:
        """
        Validate the extracted endpoints against OpenAPI 3.1.0 specification.

        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            from openapi_spec_validator import validate
            from api_extractor.openapi.builder import OpenAPIBuilder

            # Generate OpenAPI spec from endpoints
            builder = OpenAPIBuilder(
                title=f"{self.framework.value} API",
                version="1.0.0",
                description="Extracted API"
            )
            spec = builder.build(self.endpoints)
            spec_dict = spec.model_dump(exclude_none=True, by_alias=True)

            # Validate the spec
            validate(spec_dict)
            return []

        except ImportError:
            # openapi-spec-validator not installed, skip validation
            return []
        except Exception as e:
            error_msg = str(e)
            return [f"OpenAPI validation failed: {error_msg}"]

    def _find_source_files(self, path: str) -> List[str]:
        """
        Find all source files in the given path.

        Args:
            path: Path to search

        Returns:
            List of file paths
        """
        extensions = self.get_file_extensions()
        files = []

        for root, _, filenames in os.walk(path):
            # Skip common ignore directories
            if any(
                skip in root
                for skip in [
                    "venv",
                    ".venv",
                    "env",
                    ".env",
                    "node_modules",
                    "__pycache__",
                    ".git",
                    "dist",
                    "build",
                    "coverage",
                ]
            ):
                continue

            for filename in filenames:
                if any(filename.endswith(ext) for ext in extensions):
                    files.append(os.path.join(root, filename))

        return files

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects.

        Args:
            route: Route object

        Returns:
            List of Endpoint objects (one per HTTP method)
        """
        endpoints = []

        for method in route.methods:
            # Parse path parameters
            parameters = self._extract_path_parameters(route.raw_path)

            # Create default response
            responses = [
                Response(
                    status_code="200",
                    description="Success",
                    content_type="application/json",
                )
            ]

            endpoint = Endpoint(
                path=self._normalize_path(route.raw_path),
                method=method,
                parameters=parameters,
                responses=responses,
                tags=[self.framework.value],
                operation_id=route.handler_name,
                source_file=route.source_file,
                source_line=route.source_line,
            )

            endpoints.append(endpoint)

        return endpoints

    @abstractmethod
    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from a route path.

        Args:
            path: Route path with framework-specific parameter syntax

        Returns:
            List of Parameter objects
        """
        pass

    @abstractmethod
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to OpenAPI format.

        Args:
            path: Route path with framework-specific syntax

        Returns:
            Normalized path (e.g., /users/{id})
        """
        pass

    def _read_file(self, file_path: str) -> Optional[bytes]:
        """
        Read file content as bytes.

        Args:
            file_path: Path to file

        Returns:
            File content as bytes or None on error
        """
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            self.errors.append(f"Error reading file {file_path}: {str(e)}")
            return None

    def _create_parameter(
        self,
        name: str,
        location: str,
        param_type: str = "string",
        required: bool = True,
        description: Optional[str] = None,
    ) -> Parameter:
        """
        Helper to create a Parameter object.

        Args:
            name: Parameter name
            location: Parameter location (path, query, header, etc.)
            param_type: Parameter type
            required: Whether parameter is required
            description: Optional description

        Returns:
            Parameter object
        """
        from api_extractor.core.models import ParameterLocation

        return Parameter(
            name=name,
            location=ParameterLocation(location),
            type=param_type,
            required=required,
            description=description,
        )
