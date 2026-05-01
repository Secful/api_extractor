"""Express framework extractor."""

import re
from typing import List, Optional, Dict, Any
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
from api_extractor.extractors.javascript.validation import (
    JoiParser,
    JSONSchemaParser,
    ZodParser,
    ValidationSchema,
)


class ExpressExtractor(BaseExtractor):
    """Extract API routes from Express applications."""

    # HTTP methods
    HTTP_METHODS = ["get", "post", "put", "delete", "patch", "head", "options"]

    def __init__(self) -> None:
        """Initialize Express extractor."""
        super().__init__(FrameworkType.EXPRESS)
        self.routers: Dict[str, str] = {}  # router_var -> mount_path
        self.validation_schemas: Dict[str, ValidationSchema] = {}  # schema_name -> ValidationSchema
        self.joi_parser: Optional[JoiParser] = None
        self.zod_parser: Optional[ZodParser] = None
        self.json_schema_parser: Optional[JSONSchemaParser] = None

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
        is_typescript = language == "typescript"

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, language)
        if not tree:
            return routes

        # For TypeScript files, find interface definitions
        interfaces = {}
        if is_typescript:
            interfaces = self._find_interfaces(tree, source_code)

        # Extract validation schemas (Joi/Zod)
        self._detect_and_extract_validation_schemas(tree, source_code, language, file_path)

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

            # Extract metadata based on language
            metadata = {}
            if is_typescript:
                # Find handler function (last argument or second if no middleware)
                handler_node = self._find_handler_function(arg_nodes)
                if handler_node:
                    metadata = self._extract_typescript_metadata(
                        handler_node, source_code, interfaces
                    )
            else:
                # JavaScript: minimal extraction from function body
                handler_node = self._find_handler_function(arg_nodes)
                if handler_node:
                    metadata = self._extract_javascript_metadata(handler_node, source_code)

            # Extract validation schemas from middleware chain
            validation_metadata = self._extract_validation_from_middleware(
                arg_nodes, source_code
            )
            if validation_metadata:
                metadata.update(validation_metadata)

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
                metadata=metadata,
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
        Also handles {{param}} template syntax and {param} OpenAPI format.

        Args:
            route path

        Returns:
            List of Parameter objects
        """
        parameters = []
        seen_params = set()

        # Find all :param patterns (Express format)
        pattern = r":([a-zA-Z_][a-zA-Z0-9_]*)"
        matches = re.finditer(pattern, path)

        for match in matches:
            param_name = match.group(1)

            if param_name in seen_params:
                continue
            seen_params.add(param_name)

            param = self._create_parameter(
                name=param_name,
                location="path",
                param_type="string",
                required=True,
            )
            parameters.append(param)

        # Find all {{param}} patterns (template/mustache format)
        template_pattern = r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}"
        template_matches = re.finditer(template_pattern, path)

        for match in template_matches:
            param_name = match.group(1)

            if param_name in seen_params:
                continue
            seen_params.add(param_name)

            param = self._create_parameter(
                name=param_name,
                location="path",
                param_type="string",
                required=True,
            )
            parameters.append(param)

        # Find all {param} patterns (OpenAPI format)
        openapi_pattern = r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})"
        openapi_matches = re.finditer(openapi_pattern, path)

        for match in openapi_matches:
            param_name = match.group(1)

            if param_name in seen_params:
                continue
            seen_params.add(param_name)

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
        Convert {{param}} (template syntax) to {param}.
        Handle edge cases like wildcards, optional segments, and embedded braces.

        Args:
            path: Express path

        Returns:
            Normalized path
        """
        # Replace :param with {param}
        normalized = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", path)
        # Replace {{param}} (template/mustache syntax) with {param}
        normalized = re.sub(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}", r"{\1}", normalized)

        # Handle wildcard patterns: /*param or /{/*param} -> /{param}
        normalized = re.sub(r'/\*([a-zA-Z_][a-zA-Z0-9_]*)', r'/{\1}', normalized)
        normalized = re.sub(r'/\{/\*([a-zA-Z_][a-zA-Z0-9_]*)\}', r'/{\1}', normalized)

        # Handle optional segments with nested braces: /{name}{.{format}} -> /{name}/{format}
        normalized = re.sub(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}\{\.?\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', r'{\1}/{\2}', normalized)

        # Handle optional segments: /user{/{op}} -> /user/{op}
        normalized = re.sub(r'\{/\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', r'/{\1}', normalized)

        # Handle embedded braces: /user{s} -> /users (remove single char params embedded in text)
        # This handles patterns like /user{s} or /path{optional}
        normalized = re.sub(r'([a-z]+)\{([a-zA-Z0-9_]+)\}', r'\1\2', normalized)

        # Handle dots/special chars between params: /{from}..{to} -> /{from}/{to}
        normalized = re.sub(r'\}[.]+\{', '}/{', normalized)
        # Handle single dots between params: /{name}.{format} -> /{name}/{format}
        normalized = re.sub(r'\}\.\{', '}/{', normalized)

        # Unescape backslashes: \\( -> (
        normalized = normalized.replace('\\\\', '')

        # Remove any remaining regex-style patterns that aren't valid OpenAPI
        # Remove patterns like (text) that might be regex groups
        normalized = re.sub(r'\([^)]*\)', '', normalized)

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

    def _find_interfaces(self, tree, source_code: bytes) -> Dict[str, Schema]:
        """
        Find all TypeScript interface definitions.

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping interface names to Schema objects
        """
        interfaces = {}

        # Query for interface declarations
        interface_query = """
        (interface_declaration
          name: (type_identifier) @interface_name
          body: (interface_body) @interface_body)
        """

        matches = self.parser.query(tree, interface_query, "typescript")

        for match in matches:
            interface_name_node = match.get("interface_name")
            interface_body_node = match.get("interface_body")

            if not all([interface_name_node, interface_body_node]):
                continue

            interface_name = self.parser.get_node_text(interface_name_node, source_code)

            # Parse fields from interface body
            schema = self._parse_interface_body(interface_body_node, source_code)
            interfaces[interface_name] = schema

        return interfaces

    def _parse_interface_body(self, body_node: Node, source_code: bytes) -> Schema:
        """
        Parse TypeScript interface fields.

        Args:
            body_node: Interface body node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        properties = {}
        required = []

        # Look for property signatures
        for child in body_node.children:
            if child.type == "property_signature":
                field_name = None
                field_type = "string"
                is_optional = False

                for field_child in child.children:
                    if field_child.type == "property_identifier":
                        field_name = self.parser.get_node_text(field_child, source_code)
                    elif field_child.type == "?":
                        is_optional = True
                    elif field_child.type == "type_annotation":
                        # Extract type from type_annotation
                        for type_child in field_child.children:
                            if type_child.type in ("type_identifier", "predefined_type", "array_type"):
                                type_text = self.parser.get_node_text(type_child, source_code)
                                field_type = self._map_typescript_type(type_text)
                                break

                if field_name:
                    properties[field_name] = {"type": field_type}
                    if not is_optional:
                        required.append(field_name)

        return Schema(
            type="object",
            properties=properties,
            required=required,
        )

    def _map_typescript_type(self, type_text: str) -> str:
        """Map TypeScript type to OpenAPI type."""
        # Check for array first
        if "[]" in type_text or "Array<" in type_text:
            return "array"
        elif "string" in type_text:
            return "string"
        elif "number" in type_text:
            return "number"
        elif "boolean" in type_text:
            return "boolean"
        else:
            return "string"

    def _find_handler_function(self, arg_nodes: List[Node]) -> Optional[Node]:
        """
        Find the handler function in route arguments.

        The handler is typically the last argument, or second if no middleware.

        Args:
            arg_nodes: List of argument nodes

        Returns:
            Handler function node or None
        """
        # Look for arrow_function or function_expression
        for node in reversed(arg_nodes):
            if node.type in ("arrow_function", "function_expression"):
                return node
        return None

    def _extract_typescript_metadata(
        self, handler_node: Node, source_code: bytes, interfaces: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Extract metadata from TypeScript typed handler.

        Args:
            handler_node: Handler function node
            source_code: Source code bytes
            interfaces: Dictionary of interface schemas

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Get function parameters
        params_node = handler_node.child_by_field_name("parameters")
        if not params_node:
            return metadata

        # Look for req and res parameters with type annotations
        for param in params_node.children:
            if param.type == "required_parameter":
                param_name = None
                type_annotation_node = None

                for child in param.children:
                    if child.type == "identifier":
                        param_name = self.parser.get_node_text(child, source_code)
                    elif child.type == "type_annotation":
                        type_annotation_node = child

                if param_name == "req" and type_annotation_node:
                    # Extract TypedRequest<BodyType, ParamsType, QueryType>
                    metadata.update(self._parse_typed_request_node(type_annotation_node, source_code, interfaces))
                elif param_name == "res" and type_annotation_node:
                    # Extract TypedResponse<ResponseType>
                    response_schema = self._parse_typed_response_node(type_annotation_node, source_code, interfaces)
                    if response_schema:
                        metadata["response_schema"] = response_schema

        return metadata

    def _parse_typed_request_node(
        self, type_annotation_node: Node, source_code: bytes, interfaces: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Parse TypedRequest<BodyType, ParamsType, QueryType> from AST node.

        Args:
            type_annotation_node: Type annotation node
            source_code: Source code bytes
            interfaces: Dictionary of interface schemas

        Returns:
            Metadata dictionary with request_body and query_params
        """
        metadata = {}

        # Find generic_type node
        generic_type_node = None
        for child in type_annotation_node.children:
            if child.type == "generic_type":
                generic_type_node = child
                break

        if not generic_type_node:
            return metadata

        # Find type_arguments node
        type_args_node = None
        for child in generic_type_node.children:
            if child.type == "type_arguments":
                type_args_node = child
                break

        if not type_args_node:
            return metadata

        # Extract type arguments
        type_args = []
        for child in type_args_node.children:
            if child.type in ("type_identifier", "object_type", "predefined_type"):
                type_args.append(child)

        # First type arg is body type
        if len(type_args) >= 1:
            body_type_node = type_args[0]
            if body_type_node.type == "type_identifier":
                body_type = self.parser.get_node_text(body_type_node, source_code)
                if body_type != "void" and body_type in interfaces:
                    metadata["request_body"] = interfaces[body_type]

        # Third type arg is query type (if present)
        if len(type_args) >= 3:
            query_type_node = type_args[2]
            if query_type_node.type == "object_type":
                # Parse inline object type
                query_params = self._parse_inline_query_type_node(query_type_node, source_code)
                if query_params:
                    metadata["query_params"] = query_params

        return metadata

    def _parse_typed_request(self, type_text: str, interfaces: Dict[str, Schema]) -> Dict[str, Any]:
        """
        Parse TypedRequest<BodyType, ParamsType, QueryType>.

        Args:
            type_text: Type annotation text
            interfaces: Dictionary of interface schemas

        Returns:
            Metadata dictionary with request_body and query_params
        """
        metadata = {}

        # Extract type arguments from TypedRequest<...>
        # Pattern: TypedRequest<BodyType, ParamsType, QueryType>
        match = re.search(r"TypedRequest<([^>]+)>", type_text)
        if not match:
            return metadata

        type_args = [arg.strip() for arg in match.group(1).split(",")]

        # First type arg is body type
        if len(type_args) >= 1:
            body_type = type_args[0]
            if body_type != "void" and body_type in interfaces:
                metadata["request_body"] = interfaces[body_type]

        # Third type arg is query type (if present)
        if len(type_args) >= 3:
            query_type_text = type_args[2]
            # Parse inline type like { page?: string }
            query_params = self._parse_inline_query_type(query_type_text)
            if query_params:
                metadata["query_params"] = query_params

        return metadata

    def _parse_inline_query_type_node(self, object_type_node: Node, source_code: bytes) -> List[Parameter]:
        """
        Parse inline query type object from AST node.

        Args:
            object_type_node: Object type node
            source_code: Source code bytes

        Returns:
            List of Parameter objects
        """
        params = []

        # Look for property_signature nodes
        for child in object_type_node.children:
            if child.type == "property_signature":
                param_name = None
                param_type = "string"
                is_optional = False

                for prop_child in child.children:
                    if prop_child.type == "property_identifier":
                        param_name = self.parser.get_node_text(prop_child, source_code)
                    elif prop_child.type == "?":
                        is_optional = True
                    elif prop_child.type == "type_annotation":
                        # Extract type
                        for type_child in prop_child.children:
                            if type_child.type in ("type_identifier", "predefined_type"):
                                type_text = self.parser.get_node_text(type_child, source_code)
                                param_type = self._map_typescript_type(type_text)
                                break

                if param_name:
                    params.append(
                        Parameter(
                            name=param_name,
                            location=ParameterLocation.QUERY,
                            type=param_type,
                            required=not is_optional,
                        )
                    )

        return params

    def _parse_inline_query_type(self, type_text: str) -> List[Parameter]:
        """
        Parse inline query type like { page?: string }.

        Args:
            type_text: Type text

        Returns:
            List of Parameter objects
        """
        params = []

        # Simple regex parsing for { key?: type }
        pattern = r"(\w+)(\?)?:\s*(\w+)"
        matches = re.finditer(pattern, type_text)

        for match in matches:
            param_name = match.group(1)
            is_optional = match.group(2) == "?"
            param_type = match.group(3)

            params.append(
                Parameter(
                    name=param_name,
                    location=ParameterLocation.QUERY,
                    type=self._map_typescript_type(param_type),
                    required=not is_optional,
                )
            )

        return params

    def _parse_typed_response_node(
        self, type_annotation_node: Node, source_code: bytes, interfaces: Dict[str, Schema]
    ) -> Optional[Schema]:
        """
        Parse TypedResponse<ResponseType> from AST node.

        Args:
            type_annotation_node: Type annotation node
            source_code: Source code bytes
            interfaces: Dictionary of interface schemas

        Returns:
            Response schema or None
        """
        # Find generic_type node
        generic_type_node = None
        for child in type_annotation_node.children:
            if child.type == "generic_type":
                generic_type_node = child
                break

        if not generic_type_node:
            return None

        # Find type_arguments node
        type_args_node = None
        for child in generic_type_node.children:
            if child.type == "type_arguments":
                type_args_node = child
                break

        if not type_args_node:
            return None

        # Get first type argument (response type)
        for child in type_args_node.children:
            if child.type == "type_identifier":
                response_type = self.parser.get_node_text(child, source_code)
                if response_type in interfaces:
                    return interfaces[response_type]
            elif child.type == "array_type":
                # Handle array types: Type[]
                for array_child in child.children:
                    if array_child.type == "type_identifier":
                        base_type = self.parser.get_node_text(array_child, source_code)
                        if base_type in interfaces:
                            return Schema(
                                type="array",
                                items=interfaces[base_type],
                            )

        return None

    def _parse_typed_response(self, type_text: str, interfaces: Dict[str, Schema]) -> Optional[Schema]:
        """
        Parse TypedResponse<ResponseType>.

        Args:
            type_text: Type annotation text
            interfaces: Dictionary of interface schemas

        Returns:
            Response schema or None
        """
        # Extract type argument from TypedResponse<...>
        match = re.search(r"TypedResponse<([^>]+)>", type_text)
        if not match:
            return None

        response_type = match.group(1).strip()

        # Handle array types: User[]
        if "[]" in response_type:
            base_type = response_type.replace("[]", "").strip()
            if base_type in interfaces:
                return Schema(
                    type="array",
                    items=interfaces[base_type],
                )
        elif response_type in interfaces:
            return interfaces[response_type]

        return None

    def _extract_javascript_metadata(
        self, handler_node: Node, source_code: bytes
    ) -> Dict[str, Any]:
        """
        Extract metadata from JavaScript handler (minimal extraction).

        Args:
            handler_node: Handler function node
            source_code: Source code bytes

        Returns:
            Metadata dictionary with query_params
        """
        metadata = {}

        # Get function body
        body_node = handler_node.child_by_field_name("body")
        if not body_node:
            return metadata

        # Extract query parameters from req.query.paramName patterns
        query_params = self._extract_query_params_from_body(body_node, source_code)
        if query_params:
            metadata["query_params"] = query_params

        return metadata

    def _extract_query_params_from_body(
        self, body_node: Node, source_code: bytes
    ) -> List[Parameter]:
        """
        Extract query parameters from req.query.paramName patterns.

        Args:
            body_node: Function body node
            source_code: Source code bytes

        Returns:
            List of Parameter objects
        """
        params = []
        seen_params = set()

        # Recursively search for req.query.paramName patterns
        def search_query_params(node):
            if node.type == "member_expression":
                # Check if it's req.query.paramName
                node_text = self.parser.get_node_text(node, source_code)
                if "req.query." in node_text:
                    # Extract param name
                    parts = node_text.split(".")
                    if len(parts) >= 3 and parts[1] == "query":
                        param_name = parts[2]
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

            for child in node.children:
                search_query_params(child)

        search_query_params(body_node)
        return params

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects.

        Overridden to handle TypeScript interfaces and JavaScript patterns.

        Args:
            route: Route object

        Returns:
            List of Endpoint objects (one per HTTP method)
        """
        endpoints = []

        for method in route.methods:
            # Normalize path first to ensure consistent parameter extraction
            normalized_path = self._normalize_path(route.raw_path)

            # Skip invalid paths that don't start with / (invalid OpenAPI format)
            if not normalized_path.startswith('/'):
                continue

            # Parse path parameters from normalized path
            parameters = self._extract_path_parameters(normalized_path)

            # Add query parameters from metadata
            if "query_params" in route.metadata:
                parameters.extend(route.metadata["query_params"])

            # Get request body from metadata
            request_body = route.metadata.get("request_body")

            # Get response schema from metadata
            response_schema = route.metadata.get("response_schema")

            # Create response
            responses = [
                Response(
                    status_code="200",
                    description="Success",
                    content_type="application/json",
                    response_schema=response_schema,
                )
            ]

            endpoint = Endpoint(
                path=normalized_path,
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

    def _detect_and_extract_validation_schemas(
        self, tree, source_code: bytes, language: str, file_path: str
    ) -> None:
        """
        Detect validation libraries and extract schemas.

        Args:
            tree: Tree-sitter syntax tree
            source_code: Source code bytes
            language: Language (javascript or typescript)
            file_path: Path to the file being parsed
        """
        # Always initialize parsers (they may be needed for cross-file imports)
        # even if current file doesn't directly import the validation library
        if not self.joi_parser:
            self.joi_parser = JoiParser(self.parser)
        if not self.zod_parser:
            self.zod_parser = ZodParser(self.parser)
        if not self.json_schema_parser:
            self.json_schema_parser = JSONSchemaParser(self.parser)

        # Extract schemas if this file has direct imports
        has_joi = self._has_import(tree, source_code, language, ["joi", "celebrate"])
        if has_joi:
            joi_schemas = self.joi_parser.extract_schemas_from_file(
                tree, source_code, language, file_path
            )
            self.validation_schemas.update(joi_schemas)

        # Check for Zod imports
        has_zod = self._has_import(tree, source_code, language, ["zod"])
        if has_zod:
            zod_schemas = self.zod_parser.extract_schemas_from_file(
                tree, source_code, language, file_path
            )
            self.validation_schemas.update(zod_schemas)

        # Check for JSON Schema / ajv imports
        has_json_schema = self._has_import(
            tree, source_code, language, ["ajv", "express-json-validator-middleware"]
        )
        if has_json_schema:
            json_schemas = self.json_schema_parser.extract_schemas_from_file(
                tree, source_code, language, file_path
            )
            self.validation_schemas.update(json_schemas)

        # Also load cross-file imports for all parsers (e.g., route files importing validation files)
        joi_schemas = self.joi_parser.extract_schemas_from_file(
            tree, source_code, language, file_path
        )
        self.validation_schemas.update(joi_schemas)

        zod_schemas = self.zod_parser.extract_schemas_from_file(
            tree, source_code, language, file_path
        )
        self.validation_schemas.update(zod_schemas)

        json_schemas = self.json_schema_parser.extract_schemas_from_file(
            tree, source_code, language, file_path
        )
        self.validation_schemas.update(json_schemas)

    def _has_import(
        self, tree, source_code: bytes, language: str, package_names: List[str]
    ) -> bool:
        """
        Check if file imports any of the given packages.

        Args:
            tree: Tree-sitter syntax tree
            source_code: Source code bytes
            language: Language (javascript or typescript)
            package_names: List of package names to check

        Returns:
            True if any package is imported
        """
        # Query for import statements
        import_query = """
        (import_statement
          source: (string) @import_source)
        """

        # Query for require statements
        require_query = """
        (call_expression
          function: (identifier) @func_name
          arguments: (arguments
            (string) @require_source))
        """

        # Check imports
        import_matches = self.parser.query(tree, import_query, language)
        for match in import_matches:
            import_source_node = match.get("import_source")
            if import_source_node:
                import_text = self.parser.extract_string_value(
                    import_source_node, source_code
                )
                if any(pkg in import_text for pkg in package_names):
                    return True

        # Check requires
        require_matches = self.parser.query(tree, require_query, language)
        for match in require_matches:
            func_name_node = match.get("func_name")
            require_source_node = match.get("require_source")

            if func_name_node and require_source_node:
                func_name = self.parser.get_node_text(func_name_node, source_code)
                if func_name == "require":
                    require_text = self.parser.extract_string_value(
                        require_source_node, source_code
                    )
                    if any(pkg in require_text for pkg in package_names):
                        return True

        return False

    def _extract_validation_from_middleware(
        self, arg_nodes: List[Node], source_code: bytes
    ) -> Dict[str, Any]:
        """
        Extract validation schemas from middleware in route arguments.

        Args:
            arg_nodes: List of argument nodes (path, middleware..., handler)
            source_code: Source code bytes

        Returns:
            Metadata dictionary with validation schemas
        """
        metadata = {}

        # Skip first argument (path) and last argument (handler)
        # Check middle arguments for validation middleware
        middleware_nodes = arg_nodes[1:-1] if len(arg_nodes) > 2 else []

        for middleware_node in middleware_nodes:
            if middleware_node.type != "call_expression":
                continue

            # Try all parsers and collect results
            parser_results = []

            if self.joi_parser:
                joi_result = self.joi_parser.detect_middleware_pattern(
                    middleware_node, source_code
                )
                if joi_result:
                    parser_results.append(joi_result)

            if self.zod_parser:
                zod_result = self.zod_parser.detect_middleware_pattern(
                    middleware_node, source_code
                )
                if zod_result:
                    parser_results.append(zod_result)

            if self.json_schema_parser:
                json_schema_result = self.json_schema_parser.detect_middleware_pattern(
                    middleware_node, source_code
                )
                if json_schema_result:
                    parser_results.append(json_schema_result)

            # Use the first result that has either:
            # 1. An inline schema (has 'schema' key)
            # 2. A schema_ref that exists in validation_schemas AND matches parser type
            # 3. A celebrate/config pattern (has 'celebrate' or 'config' key)
            for result in parser_results:
                # Handle celebrate/config patterns (multiple locations)
                if result.get("celebrate") or result.get("config"):
                    # These have nested schemas - let _process_validation_result handle validation
                    metadata.update(self._process_validation_result(result))
                    break

                # Handle inline schema
                elif "schema" in result:
                    metadata.update(self._process_validation_result(result))
                    break

                # Handle schema reference
                elif "schema_ref" in result:
                    schema_ref = result["schema_ref"]
                    if schema_ref in self.validation_schemas:
                        # Check if parser type matches
                        validation_schema = self.validation_schemas[schema_ref]
                        result_parser_type = result.get("type")  # "joi", "zod", "json_schema"

                        # Match if parser_type matches or if schema doesn't have a parser_type
                        if validation_schema.parser_type == result_parser_type or not validation_schema.parser_type:
                            metadata.update(self._process_validation_result(result))
                            break

        return metadata

    def _process_validation_result(
        self, validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process validation middleware result and convert to route metadata.

        Args:
            validation_result: Result from validation parser

        Returns:
            Metadata dictionary for route
        """
        metadata = {}

        # Handle celebrate/config pattern (multiple locations)
        if validation_result.get("celebrate") or validation_result.get("config"):
            schemas = validation_result.get("schemas", {})
            for location, schema_info in schemas.items():
                if "schema_ref" in schema_info:
                    # Look up schema by reference
                    schema_ref = schema_info["schema_ref"]
                    if schema_ref in self.validation_schemas:
                        validation_schema = self.validation_schemas[schema_ref]
                        if location == "body":
                            metadata["request_body"] = validation_schema.schema
                        elif location == "query":
                            # Convert schema properties to query parameters
                            query_params = self._schema_to_query_params(
                                validation_schema.schema
                            )
                            metadata["query_params"] = query_params
                elif "schema" in schema_info:
                    # Inline schema
                    schema = schema_info["schema"]
                    if location == "body":
                        metadata["request_body"] = schema
                    elif location == "query":
                        query_params = self._schema_to_query_params(schema)
                        metadata["query_params"] = query_params
        else:
            # Single location validation
            location = validation_result.get("location", "body")

            if "schema_ref" in validation_result:
                # Look up schema by reference
                schema_ref = validation_result["schema_ref"]
                if schema_ref in self.validation_schemas:
                    validation_schema = self.validation_schemas[schema_ref]
                    if location == "body":
                        metadata["request_body"] = validation_schema.schema
                    elif location == "query":
                        query_params = self._schema_to_query_params(
                            validation_schema.schema
                        )
                        metadata["query_params"] = query_params
            elif "schema" in validation_result:
                # Inline schema
                schema = validation_result["schema"]
                if location == "body":
                    metadata["request_body"] = schema
                elif location == "query":
                    query_params = self._schema_to_query_params(schema)
                    metadata["query_params"] = query_params

        return metadata

    def _schema_to_query_params(self, schema: Schema) -> List[Parameter]:
        """
        Convert schema to query parameters.

        Args:
            schema: OpenAPI schema

        Returns:
            List of Parameter objects
        """
        if not schema or schema.type != "object" or not schema.properties:
            return []

        params = []
        required_fields = schema.required or []

        for prop_name, prop_schema in schema.properties.items():
            # Extract type from nested dict if needed
            if isinstance(prop_schema, dict):
                param_type = prop_schema.get("type", "string")
            else:
                param_type = getattr(prop_schema, "type", "string")

            param = Parameter(
                name=prop_name,
                location=ParameterLocation.QUERY,
                type=param_type,
                required=prop_name in required_fields,
            )
            params.append(param)

        return params
