"""Express framework extractor."""

import re
from typing import List, Optional, Dict
from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.models import (
    Route,
    Parameter,
    HTTPMethod,
    FrameworkType,
)


class ExpressExtractor(BaseExtractor):
    """Extract API routes from Express applications."""

    # HTTP methods
    HTTP_METHODS = ["get", "post", "put", "delete", "patch", "head", "options"]

    def __init__(self) -> None:
        """Initialize Express extractor."""
        super().__init__(FrameworkType.EXPRESS)
        self.routers: Dict[str, str] = {}  # router_var -> mount_path

    def get_file_extensions(self) -> List[str]:
        """Get JavaScript file extensions."""
        return [".js", ".ts"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from an Express file.

        Args:
            file_path: Path to JavaScript file

        Returns:
            List of Route objects
        """
        routes = []

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Determine language (JavaScript or TypeScript)
        language = "javascript" if file_path.endswith(".js") else "typescript"

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, language)
        if not tree:
            return routes

        # First pass: Find router creation and mounting using queries
        self._extract_routers_query(tree, source_code, language)

        # Second pass: Find route definitions using queries
        # Query for route method calls: app.get(), router.post(), etc.
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
            obj_name_node = match.get("obj_name")
            method_name_node = match.get("method_name")
            args_node = match.get("args")

            if not obj_name_node or not method_name_node or not args_node:
                continue

            obj_name = self.parser.get_node_text(obj_name_node, source_code)
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

            # Add router prefix if applicable
            if obj_name in self.routers:
                prefix = self.routers[obj_name]
                path = self._compose_paths(prefix, path)

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

    def _extract_routers_query(self, tree, source_code: bytes, language: str) -> None:
        """
        Extract Router creation and mounting using queries.

        Args:
            tree: Syntax tree
            source_code: Source code bytes
            language: Language (javascript or typescript)
        """
        # Query 1: Find Router creation - const router = express.Router()
        router_creation_query = """
        (variable_declarator
          name: (identifier) @var_name
          value: (call_expression
            function: (member_expression) @func))
        """

        router_matches = self.parser.query(tree, router_creation_query, language)

        for match in router_matches:
            var_name_node = match.get("var_name")
            func_node = match.get("func")

            if not var_name_node or not func_node:
                continue

            func_text = self.parser.get_node_text(func_node, source_code)

            # Check if it's express.Router()
            if "Router" in func_text:
                var_name = self.parser.get_node_text(var_name_node, source_code)
                self.routers[var_name] = ""  # Will be set by app.use()

        # Query 2: Find app.use() calls to get mount paths
        use_query = """
        (expression_statement
          (call_expression
            function: (member_expression
              object: (identifier) @obj_name
              property: (property_identifier) @method_name)
            arguments: (arguments) @args))
        """

        use_matches = self.parser.query(tree, use_query, language)

        for match in use_matches:
            method_name_node = match.get("method_name")
            args_node = match.get("args")

            if not method_name_node or not args_node:
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)
            if method_name != "use":
                continue

            # Extract arguments (path and router)
            arg_nodes = [
                child for child in args_node.children if child.type not in (",", "(", ")", "comment")
            ]

            if len(arg_nodes) >= 2:
                # First arg is path, second is router
                path_node = arg_nodes[0]
                router_node = arg_nodes[1]

                if path_node.type == "string" and router_node.type == "identifier":
                    path = self.parser.extract_string_value(path_node, source_code)
                    router_var = self.parser.get_node_text(router_node, source_code)

                    if router_var in self.routers:
                        self.routers[router_var] = path or ""

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from Express path.

        Express uses :paramName syntax.

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
        Normalize Express path to OpenAPI format.

        Convert :param to {param}.

        Args:
            path: Express path

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
