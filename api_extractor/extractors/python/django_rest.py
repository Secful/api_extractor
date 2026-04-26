"""Django REST Framework extractor."""

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


class DjangoRESTExtractor(BaseExtractor):
    """Extract API routes from Django REST Framework applications."""

    # ViewSet method to HTTP method mapping
    VIEWSET_METHODS = {
        "list": HTTPMethod.GET,
        "retrieve": HTTPMethod.GET,
        "create": HTTPMethod.POST,
        "update": HTTPMethod.PUT,
        "partial_update": HTTPMethod.PATCH,
        "destroy": HTTPMethod.DELETE,
    }

    def __init__(self) -> None:
        """Initialize Django REST extractor."""
        super().__init__(FrameworkType.DJANGO_REST)

    def get_file_extensions(self) -> List[str]:
        """Get Python file extensions."""
        return [".py"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a Django REST Framework file.

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

        # Query 1: Find ViewSet/APIView classes with base classes
        class_query = """
        (class_definition
          name: (identifier) @class_name
          superclasses: (argument_list) @superclasses
          body: (block) @body)
        """

        class_matches = self.parser.query(tree, class_query, "python")
        for match in class_matches:
            class_name_node = match.get("class_name")
            superclasses_node = match.get("superclasses")
            body_node = match.get("body")

            if not class_name_node or not body_node:
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)

            # Get base classes
            bases = []
            if superclasses_node:
                for child in superclasses_node.children:
                    if child.type in ("identifier", "attribute"):
                        base_name = self.parser.get_node_text(child, source_code)
                        bases.append(base_name)

            # Check if it's a ViewSet or APIView
            is_viewset = any("ViewSet" in base for base in bases)
            is_apiview = any("APIView" in base for base in bases)

            if not is_viewset and not is_apiview:
                continue

            # Extract routes from this class
            base_path = self._generate_path_from_class_name(class_name)
            location = self.parser.get_node_location(class_name_node)

            if is_viewset:
                routes.extend(
                    self._extract_viewset_routes_query(
                        body_node, source_code, file_path, base_path, location, tree
                    )
                )
            elif is_apiview:
                routes.extend(
                    self._extract_apiview_routes_query(
                        body_node, source_code, file_path, base_path, location, tree
                    )
                )

        # Query 2: Find function-based views with @api_view decorator
        api_view_query = """
        (decorated_definition
          (decorator
            (call
              function: (identifier) @decorator_name
              arguments: (argument_list
                (list) @methods_list)))
          definition: (function_definition
            name: (identifier) @func_name))
        """

        api_view_matches = self.parser.query(tree, api_view_query, "python")
        for match in api_view_matches:
            decorator_name_node = match.get("decorator_name")
            if not decorator_name_node:
                continue

            decorator_name = self.parser.get_node_text(decorator_name_node, source_code)
            if decorator_name != "api_view":
                continue

            func_name_node = match.get("func_name")
            methods_list_node = match.get("methods_list")

            if not func_name_node:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)

            # Extract HTTP methods from list
            http_methods = []
            if methods_list_node:
                for child in methods_list_node.children:
                    if child.type == "string":
                        method_str = self.parser.extract_string_value(child, source_code)
                        if method_str:
                            try:
                                http_methods.append(HTTPMethod[method_str.upper()])
                            except KeyError:
                                pass

            # Default to GET if no methods specified
            if not http_methods:
                http_methods = [HTTPMethod.GET]

            # Generate path from function name
            path = f"/{func_name.replace('_', '-')}"
            location = self.parser.get_node_location(func_name_node)

            route = Route(
                path=path,
                methods=http_methods,
                handler_name=func_name,
                framework=self.framework,
                raw_path=path,
                source_file=file_path,
                source_line=location["start_line"],
            )
            routes.append(route)

        return routes


    def _generate_path_from_class_name(self, class_name: str) -> str:
        """
        Generate REST path from class name.

        UserViewSet -> /users
        ItemAPIView -> /items

        Args:
            class_name: Class name

        Returns:
            Generated path
        """
        # Remove ViewSet/APIView suffix
        name = re.sub(r"(ViewSet|APIView)$", "", class_name)

        # Convert CamelCase to snake_case
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

        # Pluralize (simple approach)
        if not name.endswith("s"):
            name += "s"

        return f"/{name}"

    def _extract_viewset_routes_query(
        self,
        body_node: Node,
        source_code: bytes,
        file_path: str,
        base_path: str,
        location: Dict,
        tree,
    ) -> List[Route]:
        """
        Extract routes from ViewSet class using queries.

        Args:
            body_node: class body node
            source_code: Source code bytes
            file_path: Path to source file
            base_path: Base path for this ViewSet
            location: Source location info
            tree: Full syntax tree

        Returns:
            List of Route objects
        """
        routes = []

        # Query for standard ViewSet methods
        viewset_method_query = """
        (function_definition
          name: (identifier) @method_name)
        """

        # Execute query within the class body
        method_matches = self.parser.query(tree, viewset_method_query, "python")

        for match in method_matches:
            method_name_node = match.get("method_name")
            if not method_name_node:
                continue

            # Check if this node is within our body_node
            if not self._is_node_within(method_name_node, body_node):
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)

            # Check if it's a standard ViewSet method
            if method_name in self.VIEWSET_METHODS:
                http_method = self.VIEWSET_METHODS[method_name]

                # Determine path (list vs detail)
                if method_name in ["list", "create"]:
                    path = base_path
                else:
                    path = f"{base_path}/{{pk}}"

                route = Route(
                    path=path,
                    methods=[http_method],
                    handler_name=method_name,
                    framework=self.framework,
                    raw_path=path,
                    source_file=file_path,
                    source_line=location["start_line"],
                )
                routes.append(route)

        # Query for @action decorated methods
        action_query = """
        (decorated_definition
          (decorator
            (call
              function: (identifier) @decorator_name
              arguments: (argument_list) @args))
          definition: (function_definition
            name: (identifier) @func_name))
        """

        action_matches = self.parser.query(tree, action_query, "python")
        for match in action_matches:
            decorator_name_node = match.get("decorator_name")
            if not decorator_name_node:
                continue

            # Check if within body
            if not self._is_node_within(decorator_name_node, body_node):
                continue

            decorator_name = self.parser.get_node_text(decorator_name_node, source_code)
            if decorator_name != "action":
                continue

            func_name_node = match.get("func_name")
            args_node = match.get("args")

            if not func_name_node:
                continue

            method_name = self.parser.get_node_text(func_name_node, source_code)

            # Parse @action arguments
            is_detail = False
            http_methods = [HTTPMethod.GET]  # Default

            if args_node:
                for arg in args_node.children:
                    if arg.type == "keyword_argument":
                        name_node = self.parser.find_child_by_field(arg, "name")
                        value_node = self.parser.find_child_by_field(arg, "value")

                        if name_node and value_node:
                            arg_name = self.parser.get_node_text(name_node, source_code)

                            if arg_name == "detail":
                                value_text = self.parser.get_node_text(value_node, source_code)
                                is_detail = value_text == "True"

                            elif arg_name == "methods":
                                if value_node.type == "list":
                                    http_methods = []
                                    for list_child in value_node.children:
                                        if list_child.type == "string":
                                            method_str = self.parser.extract_string_value(
                                                list_child, source_code
                                            )
                                            if method_str:
                                                try:
                                                    http_methods.append(
                                                        HTTPMethod[method_str.upper()]
                                                    )
                                                except KeyError:
                                                    pass

            # Build path
            if is_detail:
                path = f"{base_path}/{{pk}}/{method_name}"
            else:
                path = f"{base_path}/{method_name}"

            for http_method in http_methods:
                route = Route(
                    path=path,
                    methods=[http_method],
                    handler_name=method_name,
                    framework=self.framework,
                    raw_path=path,
                    source_file=file_path,
                    source_line=location["start_line"],
                )
                routes.append(route)

        return routes

    def _extract_apiview_routes_query(
        self,
        body_node: Node,
        source_code: bytes,
        file_path: str,
        base_path: str,
        location: Dict,
        tree,
    ) -> List[Route]:
        """
        Extract routes from APIView class using queries.

        Args:
            body_node: class body node
            source_code: Source code bytes
            file_path: Path to source file
            base_path: Base path for this view
            location: Source location info
            tree: Full syntax tree

        Returns:
            List of Route objects
        """
        routes = []

        # Query for HTTP method handlers
        method_query = """
        (function_definition
          name: (identifier) @method_name)
        """

        http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
        method_matches = self.parser.query(tree, method_query, "python")

        for match in method_matches:
            method_name_node = match.get("method_name")
            if not method_name_node:
                continue

            # Check if within body
            if not self._is_node_within(method_name_node, body_node):
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)

            if method_name.lower() in http_method_names:
                try:
                    http_method = HTTPMethod[method_name.upper()]

                    route = Route(
                        path=base_path,
                        methods=[http_method],
                        handler_name=method_name,
                        framework=self.framework,
                        raw_path=base_path,
                        source_file=file_path,
                        source_line=location["start_line"],
                    )
                    routes.append(route)
                except KeyError:
                    pass

        return routes

    def _is_node_within(self, child_node: Node, parent_node: Node) -> bool:
        """
        Check if child_node is within parent_node's range.

        Args:
            child_node: Potential child node
            parent_node: Parent node

        Returns:
            True if child is within parent
        """
        return (
            child_node.start_byte >= parent_node.start_byte
            and child_node.end_byte <= parent_node.end_byte
        )


    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from Django REST path.

        Uses {param} syntax.

        Args:
            path: Route path

        Returns:
            List of Parameter objects
        """
        parameters = []

        # Find all {param} patterns
        pattern = r"\{([^}]+)\}"
        matches = re.finditer(pattern, path)

        for match in matches:
            param_name = match.group(1)

            # pk is typically an integer
            param_type = "integer" if param_name == "pk" else "string"

            param = self._create_parameter(
                name=param_name,
                location="path",
                param_type=param_type,
                required=True,
            )
            parameters.append(param)

        return parameters

    def _normalize_path(self, path: str) -> str:
        """
        Normalize Django REST path to OpenAPI format.

        Already uses {param} format which is OpenAPI compatible.

        Args:
            path: Django REST path

        Returns:
            Normalized path
        """
        return path
