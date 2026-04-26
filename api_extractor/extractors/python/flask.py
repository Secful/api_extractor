"""Flask framework extractor."""

import re
from typing import List, Optional, Dict, Set
from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.models import (
    Route,
    Parameter,
    HTTPMethod,
    FrameworkType,
)


class FlaskExtractor(BaseExtractor):
    """Extract API routes from Flask applications."""

    # HTTP method shortcuts
    HTTP_METHOD_SHORTCUTS = ["get", "post", "put", "delete", "patch"]

    def __init__(self) -> None:
        """Initialize Flask extractor."""
        super().__init__(FrameworkType.FLASK)
        self.blueprints: Dict[str, str] = {}  # blueprint_var -> url_prefix

    def get_file_extensions(self) -> List[str]:
        """Get Python file extensions."""
        return [".py"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a Flask file.

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

        # First pass: Find Blueprint definitions using query
        self._extract_blueprints_query(tree, source_code)

        # Second pass: Find route decorators using query
        # Query for @app.route() or @blueprint.route() or @app.get/post/etc
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

            if not obj_name_node or not method_name_node or not func_name_node:
                continue

            obj_name = self.parser.get_node_text(obj_name_node, source_code)
            method_name = self.parser.get_node_text(method_name_node, source_code)
            func_name = self.parser.get_node_text(func_name_node, source_code)

            # Check if it's a route decorator
            if method_name == "route":
                # Extract path and methods from arguments
                if not args_node:
                    continue

                path = self._extract_path_from_arguments(args_node, source_code)
                if not path:
                    continue

                methods = self._extract_methods_from_arguments(args_node, source_code)
                if not methods:
                    methods = [HTTPMethod.GET]  # Default to GET

                # Add blueprint prefix if applicable
                if obj_name in self.blueprints:
                    prefix = self.blueprints[obj_name]
                    path = prefix + path

                location = self.parser.get_node_location(func_name_node)

                route = Route(
                    path=path,
                    methods=methods,
                    handler_name=func_name,
                    framework=self.framework,
                    raw_path=path,
                    source_file=file_path,
                    source_line=location["start_line"],
                )
                routes.append(route)

            # Check for method shortcuts (@app.get, @app.post, etc.)
            elif method_name in self.HTTP_METHOD_SHORTCUTS:
                if not args_node:
                    continue

                path = self._extract_path_from_arguments(args_node, source_code)
                if not path:
                    continue

                http_method = HTTPMethod[method_name.upper()]

                # Add blueprint prefix if applicable
                if obj_name in self.blueprints:
                    prefix = self.blueprints[obj_name]
                    path = prefix + path

                location = self.parser.get_node_location(func_name_node)

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

    def _extract_blueprints_query(self, tree, source_code: bytes) -> None:
        """
        Extract Blueprint definitions and their url_prefix using queries.

        Args:
            tree: Syntax tree
            source_code: Source code bytes
        """
        # Query for Blueprint assignments: var_name = Blueprint(...)
        blueprint_query = """
        (expression_statement
          (assignment
            left: (identifier) @var_name
            right: (call
              function: (identifier) @func_name
              arguments: (argument_list) @args)))
        """

        blueprint_matches = self.parser.query(tree, blueprint_query, "python")

        for match in blueprint_matches:
            var_name_node = match.get("var_name")
            func_name_node = match.get("func_name")
            args_node = match.get("args")

            if not var_name_node or not func_name_node:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)
            if func_name != "Blueprint":
                continue

            var_name = self.parser.get_node_text(var_name_node, source_code)

            # Extract url_prefix from arguments
            url_prefix = None
            if args_node:
                url_prefix = self._extract_url_prefix(args_node, source_code)

            self.blueprints[var_name] = url_prefix or ""

    def _extract_url_prefix(self, args_node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract url_prefix from Blueprint arguments.

        Args:
            args_node: argument_list node
            source_code: Source code bytes

        Returns:
            URL prefix or None
        """
        # Look for url_prefix keyword argument
        for child in args_node.children:
            if child.type == "keyword_argument":
                name_node = self.parser.find_child_by_field(child, "name")
                if not name_node:
                    continue

                name = self.parser.get_node_text(name_node, source_code)
                if name == "url_prefix":
                    value_node = self.parser.find_child_by_field(child, "value")
                    if value_node and value_node.type == "string":
                        return self.parser.extract_string_value(value_node, source_code)

        return None

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

        return None

    def _extract_methods_from_arguments(
        self, args_node: Node, source_code: bytes
    ) -> List[HTTPMethod]:
        """
        Extract HTTP methods from methods= argument.

        Args:
            args_node: argument_list node
            source_code: Source code bytes

        Returns:
            List of HTTPMethod
        """
        methods = []

        # Look for methods keyword argument
        for child in args_node.children:
            if child.type == "keyword_argument":
                name_node = self.parser.find_child_by_field(child, "name")
                if not name_node:
                    continue

                name = self.parser.get_node_text(name_node, source_code)
                if name == "methods":
                    value_node = self.parser.find_child_by_field(child, "value")
                    if value_node and value_node.type == "list":
                        # Extract strings from list
                        for list_child in value_node.children:
                            if list_child.type == "string":
                                method_str = self.parser.extract_string_value(
                                    list_child, source_code
                                )
                                if method_str:
                                    try:
                                        methods.append(HTTPMethod[method_str.upper()])
                                    except KeyError:
                                        pass

        return methods

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from Flask path.

        Flask uses <type:param_name> or <param_name> syntax.

        Args:
            path: Route path

        Returns:
            List of Parameter objects
        """
        parameters = []

        # Find all <param> patterns
        pattern = r"<(?:([^:>]+):)?([^>]+)>"
        matches = re.finditer(pattern, path)

        for match in matches:
            param_type = match.group(1) if match.group(1) else "string"
            param_name = match.group(2)

            # Map Flask types to OpenAPI types
            type_map = {
                "int": "integer",
                "float": "number",
                "string": "string",
                "path": "string",
                "uuid": "string",
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
        Normalize Flask path to OpenAPI format.

        Convert <type:param> to {param}.

        Args:
            path: Flask path

        Returns:
            Normalized path
        """
        # Replace <type:param> or <param> with {param}
        normalized = re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", path)
        return normalized
