"""Fastify framework extractor."""

import re
from typing import List, Optional
from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.models import (
    Route,
    Parameter,
    HTTPMethod,
    FrameworkType,
)


class FastifyExtractor(BaseExtractor):
    """Extract API routes from Fastify applications."""

    # HTTP methods
    HTTP_METHODS = ["get", "post", "put", "delete", "patch", "head", "options"]

    def __init__(self) -> None:
        """Initialize Fastify extractor."""
        super().__init__(FrameworkType.FASTIFY)

    def get_file_extensions(self) -> List[str]:
        """Get JavaScript/TypeScript file extensions."""
        return [".js", ".ts"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a Fastify file.

        Args:
            file_path: Path to JavaScript/TypeScript file

        Returns:
            List of Route objects
        """
        routes = []

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Determine language
        language = "javascript" if file_path.endswith(".js") else "typescript"

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, language)
        if not tree:
            return routes

        # Query for route method calls: fastify.get(), app.post(), etc.
        route_query = """
        (expression_statement
          (call_expression
            function: (member_expression
              object: (identifier) @obj_name
              property: (property_identifier) @method_name)
            arguments: (arguments) @args))
        """

        route_matches = self.parser.query(tree, route_query, language)

        for match in route_matches:
            method_name_node = match.get("method_name")
            args_node = match.get("args")
            obj_name_node = match.get("obj_name")

            if not method_name_node or not args_node or not obj_name_node:
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)

            # Check if it's a valid HTTP method
            if method_name not in self.HTTP_METHODS:
                continue

            # Extract path from first argument
            arg_nodes = [
                child
                for child in args_node.children
                if child.type not in (",", "(", ")", "comment")
            ]

            if not arg_nodes:
                continue

            path_node = arg_nodes[0]
            if path_node.type != "string":
                continue

            path = self.parser.extract_string_value(path_node, source_code)
            if not path:
                continue

            # Get location
            location = self.parser.get_node_location(obj_name_node)

            # Create route
            http_method = HTTPMethod[method_name.upper()]
            route = Route(
                path=path,
                methods=[http_method],
                handler_name=None,
                framework=self.framework,
                raw_path=path,
                source_file=file_path,
                source_line=location["start_line"],
            )
            routes.append(route)

        return routes

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from Fastify path.

        Fastify uses :paramName syntax.

        Args:
            path: Route path

        Returns:
            List of Parameter objects
        """
        parameters = []

        # Find all :param patterns
        pattern = r":([a-zA-Z_][a-zA-Z0-9_]*)"
        matches = re.finditer(pattern, path)

        for match in matches:
            param_name = match.group(1)

            param = self._create_parameter(
                name=param_name,
                location="path",
                param_type="string",
                required=True,
            )
            parameters.append(param)

        return parameters

    def _normalize_path(self, path: str) -> str:
        """
        Normalize Fastify path to OpenAPI format.

        Convert :param to {param}.

        Args:
            path: Fastify path

        Returns:
            Normalized path
        """
        # Replace :param with {param}
        normalized = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", path)
        return normalized
