"""FastAPI framework extractor."""

import re
from typing import List, Optional, Dict, Any
from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.models import (
    Route,
    Parameter,
    HTTPMethod,
    FrameworkType,
)


class FastAPIExtractor(BaseExtractor):
    """Extract API routes from FastAPI applications."""

    # HTTP method decorators
    HTTP_METHODS = ["get", "post", "put", "delete", "patch", "head", "options"]

    def __init__(self) -> None:
        """Initialize FastAPI extractor."""
        super().__init__(FrameworkType.FASTAPI)

    def get_file_extensions(self) -> List[str]:
        """Get Python file extensions."""
        return [".py"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a FastAPI file.

        Args:
            file_path: Path to Python file

        Returns:
            List of Route objects
        """
        routes = []

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, "python")
        if not tree:
            return routes

        # Query for FastAPI route decorators: @app.get(), @router.post(), etc.
        route_query = """
        (decorated_definition
          (decorator
            (call
              function: (attribute
                object: (identifier) @obj_name
                attribute: (identifier) @method_name)
              arguments: (argument_list) @args))
          definition: (function_definition
            name: (identifier) @func_name))
        """

        route_matches = self.parser.query(tree, route_query, "python")

        for match in route_matches:
            obj_name_node = match.get("obj_name")
            method_name_node = match.get("method_name")
            args_node = match.get("args")
            func_name_node = match.get("func_name")

            if not method_name_node or not func_name_node:
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)

            # Check if it's a valid HTTP method
            if method_name not in self.HTTP_METHODS:
                continue

            # Extract path from arguments
            path = None
            if args_node:
                path = self._extract_path_from_arguments(args_node, source_code)

            if not path:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)
            location = self.parser.get_node_location(func_name_node)

            # Convert method name to HTTPMethod enum
            http_method = HTTPMethod[method_name.upper()]

            route = Route(
                path=path,
                methods=[http_method],
                handler_name=func_name,
                framework=self.framework,
                raw_path=path,
                source_file=file_path,
                source_line=location["start_line"],
            )
            routes.append(route)

        return routes

    def _extract_path_from_arguments(self, args_node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract path string from arguments node.

        Args:
            args_node: argument_list node
            source_code: Source code bytes

        Returns:
            Path string or None
        """
        # First argument should be the path
        for child in args_node.children:
            if child.type == "string":
                return self.parser.extract_string_value(child, source_code)
            elif child.type == "identifier":
                # Could be a variable reference - for now skip
                continue

        return None

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from FastAPI path.

        FastAPI uses {param_name} or {param_name:type} syntax.

        Args:
            path: Route path

        Returns:
            List of Parameter objects
        """
        parameters = []

        # Find all {param} patterns
        pattern = r"\{([^}:]+)(?::([^}]+))?\}"
        matches = re.finditer(pattern, path)

        for match in matches:
            param_name = match.group(1)
            param_type = match.group(2) if match.group(2) else "string"

            # Map FastAPI types to OpenAPI types
            type_map = {
                "int": "integer",
                "float": "number",
                "str": "string",
                "bool": "boolean",
                "path": "string",
            }

            openapi_type = type_map.get(param_type, "string")

            param = self._create_parameter(
                name=param_name,
                location="path",
                param_type=openapi_type,
                required=True,
            )
            parameters.append(param)

        return parameters

    def _normalize_path(self, path: str) -> str:
        """
        Normalize FastAPI path to OpenAPI format.

        FastAPI uses {param} which is already OpenAPI format.

        Args:
            path: FastAPI path

        Returns:
            Normalized path
        """
        # FastAPI already uses OpenAPI format
        return path
