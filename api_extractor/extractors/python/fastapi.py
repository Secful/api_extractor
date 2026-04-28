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
    Schema,
    Endpoint,
    Response,
    ParameterLocation,
)


class FastAPIExtractor(BaseExtractor):
    """Extract API routes from FastAPI applications."""

    # HTTP method decorators
    HTTP_METHODS = ["get", "post", "put", "delete", "patch", "head", "options"]

    def __init__(self) -> None:
        """Initialize FastAPI extractor."""
        super().__init__(FrameworkType.FASTAPI)
        # Map of file paths to router variable names and their prefixes
        # e.g., {"/path/to/endpoints.py": {"router": "/organizations"}}
        self.router_definitions: Dict[str, Dict[str, str]] = {}
        # Map of router variable names to their URL prefixes after include
        # e.g., {"/v1": {"/organizations": "organization_router"}}
        self.router_includes: Dict[str, Dict[str, str]] = {}
        # Base path for the project (set during extract())
        self.base_path: str = ""
        # Global prefix from main router file (api.py, main.py, app.py)
        self.global_prefix: Optional[str] = None

    def get_file_extensions(self) -> List[str]:
        """Get Python file extensions."""
        return [".py"]

    def extract(self, path: str):
        """
        Override extract to do multi-pass extraction:
        1. First pass: scan files to find APIRouter(prefix="...") definitions
        2. Second pass: scan files to find router.include_router() calls
        3. Third pass: extract routes with correct prefix chains

        Args:
            path: Path to codebase directory

        Returns:
            ExtractionResult with endpoints and any errors
        """
        self.endpoints = []
        self.errors = []
        self.warnings = []
        self.router_definitions = {}
        self.router_includes = {}
        self.base_path = path
        self.global_prefix = None

        # Find all relevant files
        files = self._find_source_files(path)

        # Pass 1: Extract router definitions to find prefixes
        # Also detect global prefix from main router files
        for file_path in files:
            try:
                self._extract_router_definitions(file_path)
                # Check if this is a main aggregator file
                filename = file_path.split('/')[-1]
                if filename in ('api.py', 'main.py', 'app.py') and self.global_prefix is None:
                    # Try to extract prefix from this file's router
                    if file_path in self.router_definitions:
                        routers = self.router_definitions[file_path]
                        # Use the first router's prefix as global prefix
                        if routers:
                            self.global_prefix = next(iter(routers.values()))
            except Exception as e:
                self.errors.append(f"Error extracting router definitions from {file_path}: {str(e)}")

        # Pass 2: Extract router includes to build hierarchy
        for file_path in files:
            try:
                self._extract_router_includes(file_path)
            except Exception as e:
                self.errors.append(f"Error extracting router includes from {file_path}: {str(e)}")

        # Pass 3: Extract routes from all files (now with prefix info)
        all_routes = []
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
                self.errors.append(f"Error converting route to endpoint: {str(e)}")

        # Determine success
        success = len(self.endpoints) > 0 and len(self.errors) == 0

        from api_extractor.core.models import ExtractionResult
        return ExtractionResult(
            success=success,
            endpoints=self.endpoints,
            errors=self.errors,
            warnings=self.warnings,
            frameworks_detected=[self.framework],
        )

    def _extract_router_definitions(self, file_path: str) -> None:
        """
        Extract APIRouter definitions and their prefixes from a file.

        Parses patterns like:
        router = APIRouter(prefix="/organizations")
        organization_router = APIRouter(prefix="/orgs", tags=["orgs"])

        Builds mapping of file paths to router variable names and prefixes.

        Args:
            file_path: Path to Python file
        """
        source_code = self._read_file(file_path)
        if not source_code:
            return

        tree = self.parser.parse_source(source_code, "python")
        if not tree:
            return

        # Query for router assignments: router = APIRouter(...)
        router_query = """
        (assignment
          left: (identifier) @var_name
          right: (call
            function: (identifier) @func_name
            arguments: (argument_list) @args))
        """

        matches = self.parser.query(tree, router_query, "python")

        file_routers = {}
        for match in matches:
            var_name_node = match.get("var_name")
            func_name_node = match.get("func_name")
            args_node = match.get("args")

            if not all([var_name_node, func_name_node, args_node]):
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)
            if func_name != "APIRouter":
                continue

            var_name = self.parser.get_node_text(var_name_node, source_code)

            # Extract prefix from arguments
            prefix = self._extract_prefix_from_arguments(args_node, source_code)
            if prefix:
                file_routers[var_name] = prefix

        if file_routers:
            self.router_definitions[file_path] = file_routers

    def _extract_prefix_from_arguments(self, args_node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract prefix parameter from APIRouter arguments.

        Args:
            args_node: argument_list node
            source_code: Source code bytes

        Returns:
            Prefix string or None
        """
        for child in args_node.children:
            if child.type == "keyword_argument":
                key_node = child.child_by_field_name("name")
                value_node = child.child_by_field_name("value")

                if key_node and value_node:
                    key_text = self.parser.get_node_text(key_node, source_code)
                    if key_text == "prefix":
                        if value_node.type == "string":
                            return self.parser.extract_string_value(value_node, source_code)

        return None

    def _extract_router_includes(self, file_path: str) -> None:
        """
        Extract router.include_router() calls to build inclusion hierarchy.

        Parses patterns like:
        router.include_router(organization_router)
        app.include_router(router)

        Builds mapping of parent prefixes to child routers.

        Args:
            file_path: Path to Python file
        """
        source_code = self._read_file(file_path)
        if not source_code:
            return

        tree = self.parser.parse_source(source_code, "python")
        if not tree:
            return

        # Query for include_router calls: router.include_router(other_router)
        include_query = """
        (expression_statement
          (call
            function: (attribute
              object: (identifier) @parent_router
              attribute: (identifier) @method_name)
            arguments: (argument_list) @args))
        """

        matches = self.parser.query(tree, include_query, "python")

        for match in matches:
            parent_router_node = match.get("parent_router")
            method_name_node = match.get("method_name")
            args_node = match.get("args")

            if not all([parent_router_node, method_name_node, args_node]):
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)
            if method_name != "include_router":
                continue

            parent_router_name = self.parser.get_node_text(parent_router_node, source_code)

            # Extract child router name from arguments
            child_router_name = None
            for child in args_node.children:
                if child.type == "identifier":
                    child_router_name = self.parser.get_node_text(child, source_code)
                    break

            if not child_router_name:
                continue

            # Look up parent router prefix in current file
            parent_prefix = None
            if file_path in self.router_definitions:
                parent_prefix = self.router_definitions[file_path].get(parent_router_name)

            # Store the relationship
            if parent_prefix is not None:
                if parent_prefix not in self.router_includes:
                    self.router_includes[parent_prefix] = {}
                self.router_includes[parent_prefix][child_router_name] = child_router_name

    def _get_router_prefix_for_file(self, file_path: str) -> Optional[str]:
        """
        Get the complete URL prefix chain for routes in a given file.

        Looks up router definition in the file, then composes with global prefix.

        Args:
            file_path: Absolute path to the file

        Returns:
            Full URL prefix (e.g., '/v1/organizations') or None
        """
        # Check if this is the main router file (api.py, main.py, app.py)
        filename = file_path.split('/')[-1]
        if filename in ('api.py', 'main.py', 'app.py'):
            # Main router file only gets its own prefix (the global one)
            if file_path in self.router_definitions:
                file_routers = self.router_definitions[file_path]
                if file_routers:
                    return next(iter(file_routers.values()))
            return None

        # Check if this file has router definitions
        if file_path not in self.router_definitions:
            # No local router, apply only global prefix if available
            return self.global_prefix

        # Get the first router definition in the file
        file_routers = self.router_definitions[file_path]
        if not file_routers:
            return self.global_prefix

        local_prefix = next(iter(file_routers.values()))

        # Compose global prefix + local prefix
        if self.global_prefix:
            # Ensure prefixes are properly formatted
            global_part = self.global_prefix.rstrip("/")
            local_part = local_prefix.rstrip("/")
            if not global_part.startswith("/"):
                global_part = "/" + global_part
            if not local_part.startswith("/"):
                local_part = "/" + local_part
            return global_part + local_part

        # No global prefix, just return local
        return local_prefix

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

        # First, build a registry of Pydantic models
        pydantic_models = self._find_pydantic_models(tree, source_code)

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
            response_model_name = None
            if args_node:
                path = self._extract_path_from_arguments(args_node, source_code)
                response_model_name = self._extract_response_model(args_node, source_code)

            if not path:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)
            location = self.parser.get_node_location(func_name_node)

            # Get the function definition node to analyze parameters
            # The function_definition is the sibling after the decorator
            func_def_node = None
            if func_name_node.parent and func_name_node.parent.type == "function_definition":
                func_def_node = func_name_node.parent

            # Extract function parameters for request body and query/header params
            metadata = {}
            if func_def_node:
                params_metadata = self._extract_function_parameters(
                    func_def_node, source_code, pydantic_models
                )
                metadata.update(params_metadata)

            # Add response model if present
            if response_model_name and response_model_name in pydantic_models:
                metadata["response_model"] = pydantic_models[response_model_name]

            # Convert method name to HTTPMethod enum
            http_method = HTTPMethod[method_name.upper()]

            # Apply router prefix if available
            router_prefix = self._get_router_prefix_for_file(file_path)
            full_path = path
            if router_prefix:
                # Ensure prefix starts with / and doesn't end with /
                prefix = router_prefix.rstrip("/")
                if not prefix.startswith("/"):
                    prefix = "/" + prefix
                # Ensure path starts with /
                if not path.startswith("/"):
                    path = "/" + path
                full_path = prefix + path
            else:
                # Ensure path starts with /
                if not path.startswith("/"):
                    full_path = "/" + path

            route = Route(
                path=full_path,
                methods=[http_method],
                handler_name=func_name,
                framework=self.framework,
                raw_path=full_path,
                source_file=file_path,
                source_line=location["start_line"],
                metadata=metadata,
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

    def _find_pydantic_models(self, tree, source_code: bytes) -> Dict[str, Schema]:
        """
        Find all Pydantic BaseModel classes in the file.

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

            # Parse fields from class body
            schema = self._parse_pydantic_class_body(class_body_node, source_code)
            models[class_name] = schema

        return models

    def _parse_pydantic_class_body(self, class_body_node: Node, source_code: bytes) -> Schema:
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

        # Look for typed assignments: name: str, age: Optional[int] = None
        for child in class_body_node.children:
            if child.type == "expression_statement":
                # Check if it's a typed assignment
                for expr_child in child.children:
                    if expr_child.type == "assignment":
                        field_info = self._parse_pydantic_field(expr_child, source_code)
                        if field_info:
                            name, field_schema, is_required = field_info
                            properties[name] = field_schema
                            if is_required:
                                required.append(name)
                    elif expr_child.type == "type_alias_statement":
                        # Handle: name: str (no default value)
                        field_info = self._parse_type_alias(expr_child, source_code)
                        if field_info:
                            name, field_schema, is_required = field_info
                            properties[name] = field_schema
                            if is_required:
                                required.append(name)

        return Schema(
            type="object",
            properties=properties,
            required=required,
        )

    def _parse_pydantic_field(
        self, assignment_node: Node, source_code: bytes
    ) -> Optional[tuple]:
        """
        Parse a Pydantic field definition.

        Args:
            assignment_node: Assignment node
            source_code: Source code bytes

        Returns:
            Tuple of (field_name, field_schema_dict, is_required) or None
        """
        # Get left side (annotated_assignment with name and type)
        left = assignment_node.child_by_field_name("left")
        if not left or left.type != "identifier":
            return None

        field_name = self.parser.get_node_text(left, source_code)

        # Get type annotation
        type_node = assignment_node.child_by_field_name("type")
        if not type_node:
            return None

        type_text = self.parser.get_node_text(type_node, source_code)
        field_type, is_optional = self._parse_type_annotation(type_text)

        # Check if there's a default value
        right = assignment_node.child_by_field_name("right")
        has_default = right is not None

        # Field is required if it's not Optional and has no default
        is_required = not is_optional and not has_default

        field_schema = {"type": field_type}

        return (field_name, field_schema, is_required)

    def _parse_type_alias(self, type_alias_node: Node, source_code: bytes) -> Optional[tuple]:
        """
        Parse a type alias statement (field without default value).

        Args:
            type_alias_node: Type alias node
            source_code: Source code bytes

        Returns:
            Tuple of (field_name, field_schema_dict, is_required) or None
        """
        field_name_node = type_alias_node.child_by_field_name("name")
        type_node = type_alias_node.child_by_field_name("value")

        if not field_name_node or not type_node:
            return None

        field_name = self.parser.get_node_text(field_name_node, source_code)
        type_text = self.parser.get_node_text(type_node, source_code)

        field_type, is_optional = self._parse_type_annotation(type_text)

        # No default value, so required unless Optional
        is_required = not is_optional

        field_schema = {"type": field_type}

        return (field_name, field_schema, is_required)

    def _parse_type_annotation(self, type_text: str) -> tuple:
        """
        Parse Python type annotation to OpenAPI type.

        Args:
            type_text: Type annotation text

        Returns:
            Tuple of (openapi_type, is_optional)
        """
        is_optional = "Optional" in type_text or "None" in type_text

        # Extract base type
        if "Optional[" in type_text:
            # Extract type from Optional[Type]
            start = type_text.find("[") + 1
            end = type_text.rfind("]")
            base_type = type_text[start:end].strip()
        elif "|" in type_text and "None" in type_text:
            # Handle Union syntax: str | None
            parts = [p.strip() for p in type_text.split("|")]
            base_type = next((p for p in parts if p != "None"), "str")
        else:
            base_type = type_text.strip()

        # Map Python types to OpenAPI types
        type_map = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "List": "array",
            "dict": "object",
            "Dict": "object",
        }

        # Check for List[T] pattern
        if "List[" in base_type or "list[" in base_type:
            return ("array", is_optional)

        openapi_type = type_map.get(base_type, "string")

        return (openapi_type, is_optional)

    def _extract_response_model(
        self, args_node: Node, source_code: bytes
    ) -> Optional[str]:
        """
        Extract response_model from decorator arguments.

        Args:
            args_node: Arguments node
            source_code: Source code bytes

        Returns:
            Response model class name or None
        """
        for child in args_node.children:
            if child.type == "keyword_argument":
                key_node = child.child_by_field_name("name")
                value_node = child.child_by_field_name("value")

                if key_node and value_node:
                    key_text = self.parser.get_node_text(key_node, source_code)
                    if key_text == "response_model":
                        return self.parser.get_node_text(value_node, source_code)

        return None

    def _extract_function_parameters(
        self, func_def_node: Node, source_code: bytes, pydantic_models: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Extract function parameters to identify request body and query/header params.

        Args:
            func_def_node: Function definition node
            source_code: Source code bytes
            pydantic_models: Dictionary of Pydantic models

        Returns:
            Dictionary with request_body, query_params, header_params
        """
        metadata = {}
        query_params = []
        header_params = []

        # Get parameters node
        params_node = func_def_node.child_by_field_name("parameters")
        if not params_node:
            return metadata

        for param in params_node.children:
            if param.type in ("typed_parameter", "typed_default_parameter"):
                param_info = self._analyze_parameter(param, source_code, pydantic_models)
                if param_info:
                    param_type, param_data = param_info
                    if param_type == "body":
                        metadata["request_body"] = param_data
                    elif param_type == "query":
                        query_params.append(param_data)
                    elif param_type == "header":
                        header_params.append(param_data)

        if query_params:
            metadata["query_params"] = query_params
        if header_params:
            metadata["header_params"] = header_params

        return metadata

    def _analyze_parameter(
        self, param_node: Node, source_code: bytes, pydantic_models: Dict[str, Schema]
    ) -> Optional[tuple]:
        """
        Analyze a function parameter to determine its type.

        Args:
            param_node: Parameter node
            source_code: Source code bytes
            pydantic_models: Dictionary of Pydantic models

        Returns:
            Tuple of (param_type, param_data) or None
        """
        # Get parameter name and type from children
        # Structure: identifier : type or identifier : type = default
        name_node = None
        type_node = None

        for child in param_node.children:
            if child.type == "identifier" and not name_node:
                name_node = child
            elif child.type == "type":
                type_node = child

        if not name_node or not type_node:
            return None

        param_name = self.parser.get_node_text(name_node, source_code)
        type_text = self.parser.get_node_text(type_node, source_code)

        # Check if type is a Pydantic model (request body)
        if type_text in pydantic_models:
            return ("body", pydantic_models[type_text])

        # Check for Query/Header default values
        if param_node.type == "typed_default_parameter":
            # Find the default value (after =)
            default_node = None
            for child in param_node.children:
                if child.type == "call":
                    default_node = child
                    break

            if default_node:
                default_text = self.parser.get_node_text(default_node, source_code)

                # Check for Query(...)
                if default_text.startswith("Query("):
                    param_data = self._parse_query_parameter(
                        param_name, type_text, default_text
                    )
                    return ("query", param_data)

                # Check for Header(...)
                if default_text.startswith("Header("):
                    param_data = self._parse_header_parameter(
                        param_name, type_text, default_text
                    )
                    return ("header", param_data)

        return None

    def _parse_query_parameter(
        self, param_name: str, type_text: str, default_text: str
    ) -> Parameter:
        """
        Parse a Query parameter.

        Args:
            param_name: Parameter name
            type_text: Type annotation
            default_text: Default value text (Query(...))

        Returns:
            Parameter object
        """
        param_type, _ = self._parse_type_annotation(type_text)

        # Extract description from Query(..., description="...")
        description = None
        if 'description="' in default_text:
            start = default_text.find('description="') + len('description="')
            end = default_text.find('"', start)
            description = default_text[start:end]
        elif "description='" in default_text:
            start = default_text.find("description='") + len("description='")
            end = default_text.find("'", start)
            description = default_text[start:end]

        # Check if required (Query(...) vs Query with default)
        required = "..." in default_text.split(",")[0]

        return Parameter(
            name=param_name,
            location=ParameterLocation.QUERY,
            type=param_type,
            required=required,
            description=description,
        )

    def _parse_header_parameter(
        self, param_name: str, type_text: str, default_text: str
    ) -> Parameter:
        """
        Parse a Header parameter.

        Args:
            param_name: Parameter name
            type_text: Type annotation
            default_text: Default value text (Header(...))

        Returns:
            Parameter object
        """
        param_type, _ = self._parse_type_annotation(type_text)

        # Extract description from Header(..., description="...")
        description = None
        if 'description="' in default_text:
            start = default_text.find('description="') + len('description="')
            end = default_text.find('"', start)
            description = default_text[start:end]
        elif "description='" in default_text:
            start = default_text.find("description='") + len("description='")
            end = default_text.find("'", start)
            description = default_text[start:end]

        # Check if required
        required = "..." in default_text.split(",")[0]

        return Parameter(
            name=param_name,
            location=ParameterLocation.HEADER,
            type=param_type,
            required=required,
            description=description,
        )

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects.

        Overridden to handle Pydantic model schemas.

        Args:
            route: Route object

        Returns:
            List of Endpoint objects (one per HTTP method)
        """
        endpoints = []

        for method in route.methods:
            # Parse path parameters
            parameters = self._extract_path_parameters(route.raw_path)

            # Add query and header parameters from metadata
            if "query_params" in route.metadata:
                parameters.extend(route.metadata["query_params"])
            if "header_params" in route.metadata:
                parameters.extend(route.metadata["header_params"])

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

            # Add response schema if present
            if "response_model" in route.metadata:
                responses = [
                    Response(
                        status_code="200",
                        description="Success",
                        response_schema=route.metadata["response_model"],
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
