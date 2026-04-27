"""Gin framework extractor for Go."""

from __future__ import annotations

import re
from typing import List, Optional, Dict, Any

from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.models import (
    Route,
    Parameter,
    HTTPMethod,
    FrameworkType,
    ParameterLocation,
)


class GinExtractor(BaseExtractor):
    """Extract API routes from Gin applications."""

    # HTTP methods - Gin uses uppercase
    HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

    def __init__(self) -> None:
        """Initialize Gin extractor."""
        super().__init__(FrameworkType.GIN)
        self.router_groups: Dict[str, str] = {}  # var_name -> mount_path

    def get_file_extensions(self) -> List[str]:
        """Get Go file extensions."""
        return [".go"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a Gin file.

        Args:
            file_path: Path to Go file

        Returns:
            List of Route objects
        """
        routes = []

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, "go")
        if not tree:
            return routes

        # Reset router groups for this file
        self.router_groups = {}

        # First pass: Find RouterGroup creation using queries
        self._extract_router_groups(tree, source_code)

        # Second pass: Find route definitions using queries
        routes.extend(self._extract_routes_query(tree, source_code, file_path))

        return routes

    def _extract_router_groups(self, tree, source_code: bytes) -> None:
        """
        Extract RouterGroup creation and mounting.

        Finds patterns like: users := router.Group("/api")
        """
        # Query for RouterGroup creation
        group_query = """
        (short_var_declaration
          left: (expression_list (identifier) @var_name)
          right: (expression_list
            (call_expression
              function: (selector_expression
                field: (field_identifier) @method_name)
              arguments: (argument_list) @args)))
        """

        matches = self.parser.query(tree, group_query, "go")

        for match in matches:
            method_name_node = match.get("method_name")
            if not method_name_node:
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)

            # Check if it's Group() call
            if method_name == "Group":
                var_name_node = match.get("var_name")
                args_node = match.get("args")

                if var_name_node and args_node:
                    var_name = self.parser.get_node_text(var_name_node, source_code)
                    path = self._extract_path_from_args(args_node, source_code)

                    if var_name and path is not None:
                        self.router_groups[var_name] = path

    def _extract_routes_query(self, tree, source_code: bytes, file_path: str) -> List[Route]:
        """
        Extract router method calls using tree-sitter queries.

        Finds patterns like: router.GET("/path", handler)
        """
        routes = []

        # Query for method calls: router.GET("/path", handler)
        route_query = """
        (call_expression
          function: (selector_expression
            operand: (identifier) @router_var
            field: (field_identifier) @method_name)
          arguments: (argument_list) @args)
        """

        matches = self.parser.query(tree, route_query, "go")

        for match in matches:
            router_var_node = match.get("router_var")
            method_name_node = match.get("method_name")
            args_node = match.get("args")

            if not router_var_node or not method_name_node or not args_node:
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)

            # Gin uses uppercase: GET, POST, etc.
            if method_name not in self.HTTP_METHODS:
                continue

            # Extract path from first argument (string literal)
            path = self._extract_path_from_args(args_node, source_code)
            if path is None:
                continue

            # Extract handler name from second argument
            handler_name = self._extract_handler_from_args(args_node, source_code)

            # Apply router group prefix if applicable
            router_var = self.parser.get_node_text(router_var_node, source_code)
            if router_var in self.router_groups:
                prefix = self.router_groups[router_var]
                path = self._compose_paths(prefix, path)

            # Normalize path
            normalized_path = self._normalize_path(path)

            # Extract path parameters
            parameters = self._extract_path_parameters(normalized_path)

            # Create route
            route = Route(
                path=normalized_path,
                methods=[HTTPMethod[method_name]],
                handler_name=handler_name,
                framework=FrameworkType.GIN,
                raw_path=path,
                source_file=file_path,
                source_line=method_name_node.start_point[0] + 1,
                metadata={"parameters": [p.model_dump() for p in parameters]},
            )
            routes.append(route)

        return routes

    def _extract_path_from_args(self, args_node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract path string from argument list.

        Args:
            args_node: Argument list node
            source_code: Source code bytes

        Returns:
            Path string or None
        """
        # Get first argument (skip parentheses and commas)
        for child in args_node.children:
            if child.type in ("interpreted_string_literal", "raw_string_literal"):
                # Go string literals: "path" or `path`
                text = self.parser.get_node_text(child, source_code)
                # Remove quotes
                if text.startswith('"') and text.endswith('"'):
                    return text[1:-1]
                elif text.startswith('`') and text.endswith('`'):
                    return text[1:-1]
        return None

    def _extract_handler_from_args(self, args_node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract handler function name from arguments.

        Args:
            args_node: Argument list node
            source_code: Source code bytes

        Returns:
            Handler name or None
        """
        # Get second argument (handler function)
        arg_count = 0
        for child in args_node.children:
            if child.type not in ("(", ")", ","):
                arg_count += 1
                if arg_count == 2:  # Second argument
                    if child.type == "identifier":
                        return self.parser.get_node_text(child, source_code)
                    # Could also be a function literal
                    elif child.type == "func_literal":
                        return "<anonymous>"
        return None

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from Gin path.

        Gin uses :paramName syntax (identical to Express).

        Args:
            path: Route path

        Returns:
            List of Parameter objects
        """
        parameters = []

        # Find all :param patterns (same as Express!)
        pattern = r":([a-zA-Z_][a-zA-Z0-9_]*)"
        matches = re.finditer(pattern, path)

        for match in matches:
            param_name = match.group(1)

            param = Parameter(
                name=param_name,
                location=ParameterLocation.PATH,
                type="string",
                required=True,
            )
            parameters.append(param)

        return parameters

    def _normalize_path(self, path: str) -> str:
        """
        Normalize Gin path to OpenAPI format.

        Convert :param to {param} (same as Express).

        Args:
            path: Gin path

        Returns:
            Normalized path
        """
        # Replace :param with {param}
        normalized = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", path)
        return normalized

    def _compose_paths(self, prefix: str, path: str) -> str:
        """
        Compose prefix and path, handling edge cases like double slashes.

        Args:
            prefix: Mount prefix (e.g., '/api', '/')
            path: Route path (e.g., '/users', '/')

        Returns:
            Composed path without double slashes
        """
        # Handle empty prefix
        if not prefix:
            return path

        # Handle root prefix '/' specially
        if prefix == '/':
            return path

        # Ensure prefix doesn't end with '/' unless it's root
        if prefix.endswith('/'):
            prefix = prefix.rstrip('/')

        # Ensure path starts with '/'
        if not path.startswith('/'):
            path = '/' + path

        return prefix + path
