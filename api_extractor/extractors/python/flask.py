"""Flask framework extractor."""

import re
from typing import List, Optional, Dict, Set, Any
from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.models import (
    Route,
    Parameter,
    HTTPMethod,
    FrameworkType,
    Schema,
    Endpoint,
    Response,
    ParameterLocation,
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

        # Find Pydantic models (if any)
        pydantic_models = self._find_pydantic_models(tree, source_code)

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

                # Extract function parameters for schemas
                func_def_node = func_name_node.parent if func_name_node.parent else None
                metadata = self._extract_function_metadata(
                    func_def_node, source_code, pydantic_models
                ) if func_def_node else {}

                route = Route(
                    path=path,
                    methods=methods,
                    handler_name=func_name,
                    framework=self.framework,
                    raw_path=path,
                    source_file=file_path,
                    source_line=location["start_line"],
                    metadata=metadata,
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

                # Extract function parameters for schemas
                func_def_node = func_name_node.parent if func_name_node.parent else None
                metadata = self._extract_function_metadata(
                    func_def_node, source_code, pydantic_models
                ) if func_def_node else {}

                route = Route(
                    path=path,
                    methods=[http_method],
                    handler_name=func_name,
                    framework=self.framework,
                    raw_path=path,
                    source_file=file_path,
                    source_line=location["start_line"],
                    metadata=metadata,
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

    def _find_pydantic_models(self, tree, source_code: bytes) -> Dict[str, Schema]:
        """
        Find all Pydantic BaseModel classes (Flask can use Pydantic!).

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping model names to Schema objects
        """
        models = {}

        # Query for classes inheriting from BaseModel
        model_query = """
        (class_definition
          name: (identifier) @class_name
          superclasses: (argument_list) @superclasses
          body: (block) @class_body)
        """

        matches = self.parser.query(tree, model_query, "python")

        for match in matches:
            class_name_node = match.get("class_name")
            superclasses_node = match.get("superclasses")
            class_body_node = match.get("class_body")

            if not all([class_name_node, superclasses_node, class_body_node]):
                continue

            # Check if BaseModel is in superclasses
            superclasses_text = self.parser.get_node_text(superclasses_node, source_code)
            if "BaseModel" not in superclasses_text:
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)

            # Parse fields from class body (simplified version)
            schema = self._parse_pydantic_class(class_body_node, source_code)
            models[class_name] = schema

        return models

    def _parse_pydantic_class(self, class_body_node: Node, source_code: bytes) -> Schema:
        """
        Parse Pydantic model fields from class body.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        properties = {}
        required = []

        # Look for typed assignments
        for child in class_body_node.children:
            if child.type == "expression_statement":
                for expr_child in child.children:
                    if expr_child.type == "assignment":
                        # name: type = default
                        left = expr_child.child_by_field_name("left")
                        type_node = expr_child.child_by_field_name("type")
                        right = expr_child.child_by_field_name("right")

                        if left and left.type == "identifier":
                            field_name = self.parser.get_node_text(left, source_code)

                            field_type = "string"  # default
                            is_optional = False

                            if type_node:
                                type_text = self.parser.get_node_text(type_node, source_code)
                                is_optional = "Optional" in type_text
                                field_type = self._map_python_type(type_text)

                            has_default = right is not None
                            is_required = not is_optional and not has_default

                            properties[field_name] = {"type": field_type}
                            if is_required:
                                required.append(field_name)

        return Schema(
            type="object",
            properties=properties,
            required=required,
        )

    def _map_python_type(self, type_text: str) -> str:
        """Map Python type to OpenAPI type."""
        # Check for List first before checking for contained types
        if "list" in type_text.lower() or "List" in type_text:
            return "array"
        elif "str" in type_text:
            return "string"
        elif "int" in type_text:
            return "integer"
        elif "float" in type_text:
            return "number"
        elif "bool" in type_text:
            return "boolean"
        else:
            return "string"

    def _extract_function_metadata(
        self, func_def_node: Node, source_code: bytes, pydantic_models: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Extract metadata from function definition.

        Args:
            func_def_node: Function definition node
            source_code: Source code bytes
            pydantic_models: Dictionary of Pydantic models

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Get parameters node
        params_node = func_def_node.child_by_field_name("parameters")
        if params_node:
            # Check for Pydantic model parameters
            for param in params_node.children:
                if param.type in ("typed_parameter", "typed_default_parameter"):
                    # Get parameter type
                    name_node = None
                    type_node = None

                    for child in param.children:
                        if child.type == "identifier" and not name_node:
                            name_node = child
                        elif child.type == "type":
                            type_node = child

                    if type_node:
                        type_text = self.parser.get_node_text(type_node, source_code)
                        # Check if type is a Pydantic model
                        if type_text in pydantic_models:
                            metadata["request_body"] = pydantic_models[type_text]
                            break

        # Extract query parameters from function body (request.args.get calls)
        func_body = func_def_node.child_by_field_name("body")
        if func_body:
            query_params = self._extract_query_params_from_body(func_body, source_code)
            if query_params:
                metadata["query_params"] = query_params

        return metadata

    def _extract_query_params_from_body(
        self, body_node: Node, source_code: bytes
    ) -> List[Parameter]:
        """
        Extract query parameters from request.args.get() calls in function body.

        Args:
            body_node: Function body node
            source_code: Source code bytes

        Returns:
            List of Parameter objects
        """
        params = []
        seen_params = set()

        # Recursively search for request.args.get() calls
        def search_args_get(node):
            if node.type == "call":
                # Check if it's request.args.get(...)
                func = node.child_by_field_name("function")
                if func and func.type == "attribute":
                    func_text = self.parser.get_node_text(func, source_code)
                    if "request.args.get" in func_text:
                        # Extract parameter name from first argument
                        args = node.child_by_field_name("arguments")
                        if args:
                            for child in args.children:
                                if child.type == "string":
                                    param_name = self.parser.extract_string_value(child, source_code)
                                    if param_name and param_name not in seen_params:
                                        seen_params.add(param_name)
                                        params.append(
                                            Parameter(
                                                name=param_name,
                                                location=ParameterLocation.QUERY,
                                                type="string",
                                                required=False,
                                            )
                                        )
                                    break

            for child in node.children:
                search_args_get(child)

        search_args_get(body_node)
        return params

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects.

        Overridden to handle Pydantic models and query params.

        Args:
            route: Route object

        Returns:
            List of Endpoint objects (one per HTTP method)
        """
        endpoints = []

        for method in route.methods:
            # Parse path parameters
            parameters = self._extract_path_parameters(route.raw_path)

            # Add query parameters from metadata
            if "query_params" in route.metadata:
                parameters.extend(route.metadata["query_params"])

            # Get request body from metadata
            request_body = route.metadata.get("request_body")

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
                request_body=request_body,
                responses=responses,
                tags=[self.framework.value],
                operation_id=route.handler_name,
                source_file=route.source_file,
                source_line=route.source_line,
            )

            endpoints.append(endpoint)

        return endpoints
