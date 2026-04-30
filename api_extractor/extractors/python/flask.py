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
        self.namespaces: Dict[str, str] = {}  # namespace_var -> url_prefix (Flask-RESTX)

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

        # Extract imports to resolve schema references
        imports = self._extract_imports(tree, source_code, file_path)

        # Find Pydantic models (if any)
        pydantic_models = self._find_pydantic_models(tree, source_code)

        # Find Marshmallow schemas
        marshmallow_schemas = self._find_marshmallow_schemas(tree, source_code)

        # Resolve imported schemas
        imported_schemas = self._resolve_imported_schemas(imports, file_path)
        marshmallow_schemas.update(imported_schemas)

        # First pass: Find Blueprint and Namespace definitions using query
        self._extract_blueprints_query(tree, source_code)
        self._extract_namespaces_query(tree, source_code)

        # Second pass: Find Flask-RESTX Resource classes (must be before regular routes)
        restx_routes = self._extract_restx_resources(tree, source_code, file_path)
        routes.extend(restx_routes)

        # Third pass: Find route decorators using query
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

                # Extract all decorators (for schema information)
                func_def_node = func_name_node.parent if func_name_node.parent else None
                decorated_def_node = func_def_node.parent if func_def_node and func_def_node.parent.type == "decorated_definition" else None

                # Extract schema decorators (@marshal_with, @use_kwargs)
                schema_metadata = {}
                if decorated_def_node:
                    schema_metadata = self._extract_schema_decorators(
                        decorated_def_node, source_code, marshmallow_schemas
                    )

                # Extract function parameters for schemas
                metadata = self._extract_function_metadata(
                    func_def_node, source_code, pydantic_models
                ) if func_def_node else {}

                # Merge schema metadata
                metadata.update(schema_metadata)

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

                # Extract all decorators (for schema information)
                func_def_node = func_name_node.parent if func_name_node.parent else None
                decorated_def_node = func_def_node.parent if func_def_node and func_def_node.parent.type == "decorated_definition" else None

                # Extract schema decorators (@marshal_with, @use_kwargs)
                schema_metadata = {}
                if decorated_def_node:
                    schema_metadata = self._extract_schema_decorators(
                        decorated_def_node, source_code, marshmallow_schemas
                    )

                # Extract function parameters for schemas
                metadata = self._extract_function_metadata(
                    func_def_node, source_code, pydantic_models
                ) if func_def_node else {}

                # Merge schema metadata
                metadata.update(schema_metadata)

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

    def _extract_namespaces_query(self, tree, source_code: bytes) -> None:
        """
        Extract Flask-RESTX Namespace definitions using queries.

        Args:
            tree: Syntax tree
            source_code: Source code bytes
        """
        # Query for Namespace assignments: var_name = Namespace(...)
        namespace_query = """
        (expression_statement
          (assignment
            left: (identifier) @var_name
            right: (call
              function: (identifier) @func_name
              arguments: (argument_list) @args)))
        """

        namespace_matches = self.parser.query(tree, namespace_query, "python")

        for match in namespace_matches:
            var_name_node = match.get("var_name")
            func_name_node = match.get("func_name")
            args_node = match.get("args")

            if not var_name_node or not func_name_node:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)
            if func_name != "Namespace":
                continue

            var_name = self.parser.get_node_text(var_name_node, source_code)

            # Namespace paths come from api.add_namespace(ns, path='/prefix') calls
            # which are often in different files. Default to "" (empty) for all namespaces.
            # The actual route paths (from @namespace.route()) will define the full path.
            self.namespaces[var_name] = ""

    def _extract_namespace_name(self, args_node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract namespace name from Namespace arguments.

        Args:
            args_node: argument_list node
            source_code: Source code bytes

        Returns:
            Namespace name or None
        """
        # First argument should be the namespace name
        for child in args_node.children:
            if child.type == "string":
                return self.parser.extract_string_value(child, source_code)
        return None

    def _extract_restx_resources(self, tree, source_code: bytes, file_path: str) -> List[Route]:
        """
        Extract Flask-RESTX Resource classes with @namespace.route() decorators.

        Args:
            tree: Syntax tree
            source_code: Source code bytes
            file_path: Path to current file

        Returns:
            List of Route objects
        """
        routes = []

        # Query for decorated class definitions
        resource_query = """
        (decorated_definition
          (decorator
            (call
              function: (attribute
                object: (identifier) @namespace_var
                attribute: (identifier) @method_name)
              arguments: (argument_list) @args))
          definition: (class_definition
            name: (identifier) @class_name
            body: (block) @class_body))
        """

        resource_matches = self.parser.query(tree, resource_query, "python")

        for match in resource_matches:
            namespace_var_node = match.get("namespace_var")
            method_name_node = match.get("method_name")
            args_node = match.get("args")
            class_name_node = match.get("class_name")
            class_body_node = match.get("class_body")

            if not all([namespace_var_node, method_name_node, class_name_node, class_body_node]):
                continue

            namespace_var = self.parser.get_node_text(namespace_var_node, source_code)
            method_name = self.parser.get_node_text(method_name_node, source_code)

            # Check if it's a namespace route decorator
            if method_name != "route":
                continue

            # If namespace var is not known, add it with default "" prefix
            # (namespaces might be imported from other files)
            if namespace_var not in self.namespaces:
                self.namespaces[namespace_var] = ""

            # Extract path from decorator arguments
            path = self._extract_path_from_arguments(args_node, source_code)
            if not path:
                continue

            # Ensure path has leading slash
            if not path.startswith("/"):
                path = "/" + path

            # Get namespace prefix (default to "" if not found)
            namespace_prefix = self.namespaces.get(namespace_var, "")

            # Combine prefix and path, avoiding double slashes
            if namespace_prefix:
                # Remove trailing slash from prefix if present
                namespace_prefix = namespace_prefix.rstrip("/")
                full_path = namespace_prefix + path
            else:
                full_path = path

            class_name = self.parser.get_node_text(class_name_node, source_code)
            location = self.parser.get_node_location(class_name_node)

            # Extract HTTP methods from Resource class body
            http_methods = self._extract_resource_methods(class_body_node, source_code)

            if not http_methods:
                # If no HTTP methods found, skip this resource
                continue

            # Create a route for each HTTP method
            for http_method in http_methods:
                route = Route(
                    path=full_path,
                    methods=[http_method],
                    handler_name=f"{class_name}.{http_method.value.lower()}",
                    framework=self.framework,
                    raw_path=full_path,
                    source_file=file_path,
                    source_line=location["start_line"],
                    metadata={"restx_resource": True, "class_name": class_name},
                )
                routes.append(route)

        return routes

    def _extract_resource_methods(self, class_body_node: Node, source_code: bytes) -> List[HTTPMethod]:
        """
        Extract HTTP methods from Flask-RESTX Resource class body.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes

        Returns:
            List of HTTPMethod enums
        """
        methods = []
        http_method_names = ["get", "post", "put", "delete", "patch", "head", "options"]

        # Look for method definitions in class body (can be decorated or not)
        for child in class_body_node.children:
            func_def_node = None

            if child.type == "function_definition":
                func_def_node = child
            elif child.type == "decorated_definition":
                # Get the function definition from decorated_definition
                func_def_node = child.child_by_field_name("definition")

            if func_def_node and func_def_node.type == "function_definition":
                name_node = func_def_node.child_by_field_name("name")
                if name_node:
                    method_name = self.parser.get_node_text(name_node, source_code)
                    if method_name in http_method_names:
                        try:
                            methods.append(HTTPMethod[method_name.upper()])
                        except KeyError:
                            pass

        return methods

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
                    # Flask uses both lists and tuples: methods=['GET'] or methods=('GET',)
                    if value_node and value_node.type in ("list", "tuple"):
                        # Extract strings from list or tuple
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
        Also handles OpenAPI {param} format for normalized paths.

        Args:
            path: Route path

        Returns:
            List of Parameter objects
        """
        parameters = []
        seen_params = set()

        # Find all <param> patterns (Flask format)
        flask_pattern = r"<(?:([^:>]+):)?([^>]+)>"
        matches = re.finditer(flask_pattern, path)

        for match in matches:
            param_type = match.group(1) if match.group(1) else "string"
            param_name = match.group(2)

            if param_name in seen_params:
                continue
            seen_params.add(param_name)

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

        # Also find {param} patterns (OpenAPI format) in case path is already normalized
        openapi_pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
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

            # Get request body from metadata (Pydantic or Marshmallow)
            request_body = route.metadata.get("request_body") or route.metadata.get("request_schema")

            # Build responses list
            responses = []

            # Check for response schema from @marshal_with
            if "response_schema" in route.metadata:
                responses.append(
                    Response(
                        status_code="200",
                        description="Success",
                        response_schema=route.metadata["response_schema"],
                        content_type="application/json",
                    )
                )
            else:
                # Default response without schema
                responses.append(
                    Response(
                        status_code="200",
                        description="Success",
                        content_type="application/json",
                    )
                )

            # Generate unique operation ID
            # OpenAPI requires operation IDs to be unique across all operations
            normalized_path = self._normalize_path(route.raw_path)
            clean_path = normalized_path.replace("{", "").replace("}", "").replace("/", "_")
            clean_path = clean_path.lstrip("_")
            if not normalized_path.endswith("/") or normalized_path == "/":
                clean_path = clean_path.rstrip("_")

            method_lower = method.value.lower()

            if route.handler_name == "<anonymous>":
                # Anonymous handler: method_path
                operation_id = f"{method_lower}_{clean_path}" if clean_path else method_lower
            else:
                # Named handler: handler_method_path
                operation_id = f"{route.handler_name}_{method_lower}_{clean_path}" if clean_path else f"{route.handler_name}_{method_lower}"

            endpoint = Endpoint(
                path=normalized_path,
                method=method,
                parameters=parameters,
                request_body=request_body,
                responses=responses,
                tags=[self.framework.value],
                operation_id=operation_id,
                source_file=route.source_file,
                source_line=route.source_line,
            )

            endpoints.append(endpoint)

        return endpoints

    def _extract_imports(
        self, tree, source_code: bytes, file_path: str
    ) -> Dict[str, str]:
        """
        Extract import statements to resolve schema references.

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes
            file_path: Path to current file

        Returns:
            Dictionary mapping imported names to module paths
        """
        imports = {}

        # Query for import_from_statement nodes
        import_query = "(import_from_statement) @import_stmt"

        matches = self.parser.query(tree, import_query, "python")

        for match in matches:
            import_node = match.get("import_stmt")
            if not import_node:
                continue

            # Get module name
            module_name_node = import_node.child_by_field_name("module_name")
            if not module_name_node:
                continue

            module_path = self.parser.get_node_text(module_name_node, source_code)

            # Get name or names list
            name_node = import_node.child_by_field_name("name")
            if not name_node:
                continue

            # Handle both single imports and import lists
            if name_node.type == "dotted_name" or name_node.type == "identifier":
                # Single import: from x import y
                import_name = self.parser.get_node_text(name_node, source_code)
                imports[import_name] = f"{module_path}.{import_name}"

            elif name_node.type == "aliased_import":
                # Aliased import: from x import y as z
                actual_name_node = name_node.child_by_field_name("name")
                alias_name_node = name_node.child_by_field_name("alias")
                if actual_name_node and alias_name_node:
                    import_name = self.parser.get_node_text(actual_name_node, source_code)
                    alias_name = self.parser.get_node_text(alias_name_node, source_code)
                    imports[alias_name] = f"{module_path}.{import_name}"

            elif hasattr(name_node, 'children'):
                # Import list: from x import (y, z as w, ...)
                for child in name_node.children:
                    if child.type == "dotted_name" or child.type == "identifier":
                        import_name = self.parser.get_node_text(child, source_code)
                        imports[import_name] = f"{module_path}.{import_name}"
                    elif child.type == "aliased_import":
                        actual_name_node = child.child_by_field_name("name")
                        alias_name_node = child.child_by_field_name("alias")
                        if actual_name_node and alias_name_node:
                            import_name = self.parser.get_node_text(actual_name_node, source_code)
                            alias_name = self.parser.get_node_text(alias_name_node, source_code)
                            imports[alias_name] = f"{module_path}.{import_name}"

        return imports

    def _find_marshmallow_schemas(
        self, tree, source_code: bytes
    ) -> Dict[str, Schema]:
        """
        Find all Marshmallow Schema classes in the file.

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping schema names to Schema objects
        """
        schemas = {}

        # Query for classes inheriting from Schema
        schema_query = """
        (class_definition
          name: (identifier) @class_name
          superclasses: (argument_list) @superclasses
          body: (block) @class_body)
        """

        matches = self.parser.query(tree, schema_query, "python")

        for match in matches:
            class_name_node = match.get("class_name")
            superclasses_node = match.get("superclasses")
            class_body_node = match.get("class_body")

            if not all([class_name_node, superclasses_node, class_body_node]):
                continue

            # Check if Schema is in superclasses
            superclasses_text = self.parser.get_node_text(superclasses_node, source_code)
            if "Schema" not in superclasses_text:
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)

            # Parse fields from class body
            schema = self._parse_marshmallow_schema_body(class_body_node, source_code)
            schemas[class_name] = schema

        return schemas

    def _parse_marshmallow_schema_body(
        self, class_body_node, source_code: bytes
    ) -> Schema:
        """
        Parse Marshmallow schema fields from class body.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes

        Returns:
            Schema object with properties
        """
        properties = {}
        required_fields = []

        # Iterate through class body children
        for child in class_body_node.children:
            if child.type != "expression_statement":
                continue

            # Check if it's an assignment
            assignment_node = None
            for subchild in child.children:
                if subchild.type == "assignment":
                    assignment_node = subchild
                    break

            if not assignment_node:
                continue

            # Extract field name and call
            field_name = None
            call_node = None

            for node in assignment_node.children:
                if node.type == "identifier" and field_name is None:
                    field_name = self.parser.get_node_text(node, source_code)
                elif node.type == "call":
                    call_node = node

            if not field_name or not call_node:
                continue

            # Extract field type from call: fields.Str(), fields.Email(), etc.
            function_node = call_node.child_by_field_name("function")
            if not function_node or function_node.type != "attribute":
                continue

            # Get object and attribute
            object_node = function_node.child_by_field_name("object")
            attribute_node = function_node.child_by_field_name("attribute")

            if not object_node or not attribute_node:
                continue

            module = self.parser.get_node_text(object_node, source_code)
            field_type = self.parser.get_node_text(attribute_node, source_code)

            # Check if it's a fields.* call
            if module != "fields":
                continue

            # Map Marshmallow field types to OpenAPI types
            openapi_type = self._marshmallow_to_openapi_type(field_type)

            properties[field_name] = {
                "type": openapi_type
            }

        return Schema(
            type="object",
            properties=properties,
            required=required_fields,
        )

    def _marshmallow_to_openapi_type(self, marshmallow_type: str) -> str:
        """
        Convert Marshmallow field type to OpenAPI type.

        Args:
            marshmallow_type: Marshmallow field type name

        Returns:
            OpenAPI type string
        """
        type_map = {
            "Str": "string",
            "String": "string",
            "Int": "integer",
            "Integer": "integer",
            "Float": "number",
            "Number": "number",
            "Bool": "boolean",
            "Boolean": "boolean",
            "DateTime": "string",
            "Date": "string",
            "Time": "string",
            "Email": "string",
            "Url": "string",
            "URL": "string",
            "Dict": "object",
            "List": "array",
            "Nested": "object",
        }

        return type_map.get(marshmallow_type, "string")

    def _resolve_imported_schemas(
        self, imports: Dict[str, str], current_file_path: str
    ) -> Dict[str, Schema]:
        """
        Resolve imported Marshmallow schemas by parsing their source files.

        Args:
            imports: Dictionary mapping names to module paths
            current_file_path: Path to current file for relative resolution

        Returns:
            Dictionary mapping schema names to Schema objects
        """
        schemas = {}

        for schema_name, module_path in imports.items():
            # Only process if it looks like a schema (ends with Schema or schema)
            if not ("schema" in schema_name.lower() or "Schema" in schema_name):
                continue

            # Try to resolve the module path to a file path
            file_path = self._resolve_module_to_file(module_path, current_file_path)

            if not file_path:
                continue

            # Parse the file to extract Marshmallow schemas
            try:
                source_code = self._read_file(file_path)
                if not source_code:
                    continue

                tree = self.parser.parse_source(source_code, "python")
                if not tree:
                    continue

                # Find all Marshmallow schemas in the imported file
                imported_schemas = self._find_marshmallow_schemas(tree, source_code)

                # Add the specific imported schema if it exists
                if schema_name in imported_schemas:
                    schemas[schema_name] = imported_schemas[schema_name]
                else:
                    # Check if it's a schema instance (e.g., profile_schema = ProfileSchema())
                    # Look for the class name without "schema" suffix
                    class_name = schema_name.replace("_schema", "").replace("_", " ").title().replace(" ", "") + "Schema"
                    if class_name in imported_schemas:
                        schemas[schema_name] = imported_schemas[class_name]

            except Exception:
                # Skip files that can't be parsed
                continue

        return schemas

    def _resolve_module_to_file(
        self, module_path: str, current_file_path: str
    ) -> Optional[str]:
        """
        Resolve a Python module path to a file path.

        Args:
            module_path: Module path like ".serializers.ProfileSchema"
            current_file_path: Current file path for relative resolution

        Returns:
            Resolved file path or None
        """
        from pathlib import Path

        # Handle relative imports (starting with .)
        if module_path.startswith("."):
            current_dir = Path(current_file_path).parent
            parts = module_path.lstrip(".").split(".") if module_path != "." else []

            # Count leading dots for parent directory traversal
            dot_count = len(module_path) - len(module_path.lstrip("."))

            # Go up the directory tree
            target_dir = current_dir
            for _ in range(dot_count - 1):
                target_dir = target_dir.parent

            # Build file path from remaining parts
            if parts:
                file_path = target_dir
                for part in parts[:-1]:
                    file_path = file_path / part

                # Last part could be a module or a class
                last_part = parts[-1]
                final_file = file_path / last_part

                # Try .py file
                if final_file.with_suffix(".py").exists():
                    return str(final_file.with_suffix(".py"))

                # Try as a package with __init__.py
                if (final_file / "__init__.py").exists():
                    return str(final_file / "__init__.py")

                # Try the parent directory as a .py file (last part might be a class name)
                if file_path.with_suffix(".py").exists():
                    return str(file_path.with_suffix(".py"))
            else:
                # Just "." - current directory's __init__.py
                if (target_dir / "__init__.py").exists():
                    return str(target_dir / "__init__.py")

            return None

        # Handle absolute imports - same logic as FastAPI extractor
        else:
            current_dir = Path(current_file_path).parent

            # Look for common project root indicators
            max_levels = 10
            for _ in range(max_levels):
                # Convert module path to file path
                parts = module_path.split(".")
                potential_file = current_dir / "/".join(parts)

                # Try .py file
                if potential_file.with_suffix(".py").exists():
                    return str(potential_file.with_suffix(".py"))

                # Try package with __init__.py
                if (potential_file / "__init__.py").exists():
                    return str(potential_file / "__init__.py")

                # Try one level up
                if current_dir.parent == current_dir:
                    break
                current_dir = current_dir.parent

        return None

    def _extract_schema_decorators(
        self, decorated_def_node, source_code: bytes, marshmallow_schemas: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Extract schema information from flask-apispec decorators.

        Looks for:
        - @marshal_with(schema) - response schema
        - @use_kwargs(schema) - request schema

        Args:
            decorated_def_node: decorated_definition node
            source_code: Source code bytes
            marshmallow_schemas: Available Marshmallow schemas

        Returns:
            Dictionary with response_schema and/or request_schema
        """
        metadata = {}

        # Find all decorator nodes
        for child in decorated_def_node.children:
            if child.type != "decorator":
                continue

            # Extract decorator function name and arguments
            decorator_call = child.children[1] if len(child.children) > 1 else None
            if not decorator_call or decorator_call.type != "call":
                continue

            function_node = decorator_call.child_by_field_name("function")
            if not function_node:
                continue

            function_name = self.parser.get_node_text(function_node, source_code)

            # Check for @marshal_with(schema)
            if function_name == "marshal_with":
                args_node = decorator_call.child_by_field_name("arguments")
                if args_node:
                    schema_name = self._extract_first_argument(args_node, source_code)
                    if schema_name and schema_name in marshmallow_schemas:
                        metadata["response_schema"] = marshmallow_schemas[schema_name]

            # Check for @use_kwargs(schema)
            elif function_name == "use_kwargs":
                args_node = decorator_call.child_by_field_name("arguments")
                if args_node:
                    schema_name = self._extract_first_argument(args_node, source_code)
                    if schema_name and schema_name in marshmallow_schemas:
                        metadata["request_schema"] = marshmallow_schemas[schema_name]

        return metadata

    def _extract_first_argument(self, args_node, source_code: bytes) -> Optional[str]:
        """
        Extract the first argument from an argument list.

        Args:
            args_node: argument_list node
            source_code: Source code bytes

        Returns:
            Argument text or None
        """
        for child in args_node.children:
            if child.type in ("identifier", "attribute"):
                return self.parser.get_node_text(child, source_code)

        return None
