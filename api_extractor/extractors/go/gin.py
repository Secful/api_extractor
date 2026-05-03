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
    Schema,
    Endpoint,
    Response,
)


class GinExtractor(BaseExtractor):
    """Extract API routes from Gin applications."""

    # HTTP methods - Gin uses uppercase
    HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

    def __init__(self) -> None:
        """Initialize Gin extractor."""
        super().__init__(FrameworkType.GIN)
        self.router_groups: Dict[str, str] = {}  # var_name -> mount_path
        # Multi-pass extraction support
        self.base_path: str = ""
        self.package_registry: Dict[str, Dict[str, Schema]] = {}  # pkg_path -> {struct_name: Schema}
        self.handler_registry: Dict[str, Dict[str, Dict[str, str]]] = {}  # pkg_path -> {handler_name: {request_type, response_type}}

    def get_file_extensions(self) -> List[str]:
        """Get Go file extensions."""
        return [".go"]

    def extract(self, path: str):
        """
        Override extract for multi-pass processing.

        Pass 1: Scan all files to build struct registry
        Pass 2: Scan all files to build handler registry
        Pass 3: Extract routes with cross-file resolution

        Args:
            path: Path to codebase directory

        Returns:
            ExtractionResult with endpoints and any errors
        """
        from pathlib import Path
        from api_extractor.core.models import ExtractionResult

        self.endpoints = []
        self.errors = []
        self.warnings = []
        self.base_path = str(Path(path).resolve())
        self.package_registry = {}
        self.handler_registry = {}

        # Find all relevant files
        files = self._find_source_files(path)

        # Pass 1: Build struct registry
        for file_path in files:
            try:
                self._register_structs(file_path)
            except Exception as e:
                # Non-critical, continue extraction
                self.warnings.append(f"Warning registering structs from {file_path}: {str(e)}")

        # Pass 2: Build handler registry
        for file_path in files:
            try:
                self._register_handlers(file_path)
            except Exception as e:
                # Non-critical, continue extraction
                self.warnings.append(f"Warning registering handlers from {file_path}: {str(e)}")

        # Pass 3: Extract routes with resolution
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
                self.errors.append(f"Error converting route {route.path}: {str(e)}")

        return ExtractionResult(
            success=len(self.endpoints) > 0,
            endpoints=self.endpoints,
            errors=self.errors,
            warnings=self.warnings,
            frameworks_detected=[self.framework],
        )

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a Gin file.

        Args:
            file_path: Path to Go file

        Returns:
            List of Route objects
        """
        routes = []

        # Skip test files (files ending with _test.go)
        if file_path.endswith('_test.go'):
            return routes

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, "go")
        if not tree:
            return routes

        # Store current tree for helper methods
        self._current_tree = tree

        # Reset router groups for this file
        self.router_groups = {}

        # First pass: Find struct definitions for schema extraction
        struct_schemas = self._find_struct_definitions(tree, source_code)

        # Second pass: Find RouterGroup creation using queries
        self._extract_router_groups(tree, source_code)

        # Third pass: Find route definitions using queries
        routes.extend(self._extract_routes_query(tree, source_code, file_path, struct_schemas))

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

    def _extract_routes_query(self, tree, source_code: bytes, file_path: str, struct_schemas: Dict[str, Schema]) -> List[Route]:
        """
        Extract router method calls using tree-sitter queries.

        Finds patterns like: router.GET("/path", handler)
        """
        from pathlib import Path

        routes = []

        # Extract imports for resolving qualified handlers
        imports = self._extract_imports(tree, source_code, file_path)

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

            # Extract handler info from second argument
            handler_info = self._extract_handler_from_args(args_node, source_code)
            if not handler_info:
                continue

            # Get handler name for display
            handler_display_name = handler_info["name"]
            if handler_info["is_qualified"]:
                handler_display_name = f"{handler_info['package']}.{handler_info['name']}"

            # Apply router group prefix if applicable
            router_var = self.parser.get_node_text(router_var_node, source_code)
            if router_var in self.router_groups:
                prefix = self.router_groups[router_var]
                path = self._compose_paths(prefix, path)

            # Normalize path
            normalized_path = self._normalize_path(path)

            # Extract path parameters
            parameters = self._extract_path_parameters(normalized_path)

            # Extract handler schemas
            handler_schemas = {}

            if handler_info["is_qualified"]:
                # Cross-file handler: package.HandlerName
                package_alias = handler_info["package"]
                handler_name = handler_info["name"]

                if package_alias in imports:
                    import_path = imports[package_alias]
                    package_dir = self._resolve_import_to_directory(import_path, file_path)

                    if package_dir:
                        try:
                            package_rel_path = str(Path(package_dir).relative_to(Path(self.base_path)))

                            # Look up handler in registry
                            if package_rel_path in self.handler_registry:
                                handler_data = self.handler_registry[package_rel_path].get(handler_name)

                                if handler_data:
                                    # Resolve schemas from package registry
                                    if handler_data.get("request_type"):
                                        request_schema = self._resolve_type_in_package(
                                            handler_data["request_type"],
                                            package_rel_path
                                        )
                                        if request_schema:
                                            handler_schemas["request_body"] = request_schema

                                    if handler_data.get("response_type"):
                                        response_schema = self._resolve_type_in_package(
                                            handler_data["response_type"],
                                            package_rel_path
                                        )
                                        if response_schema:
                                            handler_schemas["response_schema"] = response_schema
                        except ValueError:
                            # Package outside base_path
                            pass

            else:
                # Same-file handler - check package registry too
                if handler_info["name"] != "<anonymous>":
                    handler_name = handler_info["name"]

                    # Try package registry first (for cross-file types in same package)
                    try:
                        from pathlib import Path
                        file_abs = Path(file_path).resolve()
                        base_abs = Path(self.base_path).resolve()
                        package_rel_path = str(file_abs.parent.relative_to(base_abs))

                        # Look up handler in registry
                        if package_rel_path in self.handler_registry:
                            handler_data = self.handler_registry[package_rel_path].get(handler_name)

                            if handler_data:
                                # Resolve schemas from package registry
                                if handler_data.get("request_type"):
                                    request_schema = self._resolve_type_in_package(
                                        handler_data["request_type"],
                                        package_rel_path
                                    )
                                    if request_schema:
                                        handler_schemas["request_body"] = request_schema

                                if handler_data.get("response_type"):
                                    response_schema = self._resolve_type_in_package(
                                        handler_data["response_type"],
                                        package_rel_path
                                    )
                                    if response_schema:
                                        handler_schemas["response_schema"] = response_schema
                    except (ValueError, AttributeError):
                        pass

                    # Fallback: Same-file extraction (for inline types)
                    if not handler_schemas:
                        self._current_file_structs = struct_schemas
                        handler_schemas = self._extract_handler_schemas(
                            handler_name, tree, source_code, struct_schemas
                        )
                        self._current_file_structs = {}

            # Create route
            route = Route(
                path=normalized_path,
                methods=[HTTPMethod[method_name]],
                handler_name=handler_display_name,
                framework=FrameworkType.GIN,
                raw_path=path,
                source_file=file_path,
                source_line=method_name_node.start_point[0] + 1,
                metadata={
                    "parameters": [p.model_dump() for p in parameters],
                    "struct_schemas": struct_schemas,
                    **handler_schemas,  # Merge handler schemas (request_body, response_schema)
                },
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

    def _extract_handler_from_args(self, args_node: Node, source_code: bytes) -> Optional[Dict[str, Any]]:
        """
        Extract handler function info from arguments.

        Args:
            args_node: Argument list node
            source_code: Source code bytes

        Returns:
            Dict with handler info: {name, package, is_qualified}
            or None if no handler found
        """
        # Get second argument (handler function)
        arg_count = 0
        for child in args_node.children:
            if child.type not in ("(", ")", ","):
                arg_count += 1
                if arg_count == 2:  # Second argument
                    if child.type == "identifier":
                        # Simple handler: HandlerName
                        handler_name = self.parser.get_node_text(child, source_code)
                        return {
                            "name": handler_name,
                            "package": None,
                            "is_qualified": False,
                        }
                    elif child.type == "selector_expression":
                        # Qualified handler: package.HandlerName
                        package_name = None
                        handler_name = None
                        for selector_child in child.children:
                            if selector_child.type == "identifier":
                                package_name = self.parser.get_node_text(selector_child, source_code)
                            elif selector_child.type == "field_identifier":
                                handler_name = self.parser.get_node_text(selector_child, source_code)

                        if package_name and handler_name:
                            return {
                                "name": handler_name,
                                "package": package_name,
                                "is_qualified": True,
                            }
                    elif child.type == "func_literal":
                        # Anonymous function
                        return {
                            "name": "<anonymous>",
                            "package": None,
                            "is_qualified": False,
                        }
        return None

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from Gin path or OpenAPI path.

        Gin uses :paramName for regular params and *paramName for wildcards.
        OpenAPI uses {paramName}.

        Args:
            path: Route path (Gin or OpenAPI format)

        Returns:
            List of Parameter objects
        """
        parameters = []
        seen_params = set()

        # Find all :param patterns (Gin format)
        pattern = r":([a-zA-Z_][a-zA-Z0-9_]*)"
        matches = re.finditer(pattern, path)

        for match in matches:
            param_name = match.group(1)
            if param_name not in seen_params:
                seen_params.add(param_name)
                param = Parameter(
                    name=param_name,
                    location=ParameterLocation.PATH,
                    type="string",
                    required=True,
                )
                parameters.append(param)

        # Find all *param patterns (Gin wildcard/catch-all)
        wildcard_pattern = r"\*([a-zA-Z_][a-zA-Z0-9_]*)"
        wildcard_matches = re.finditer(wildcard_pattern, path)

        for match in wildcard_matches:
            param_name = match.group(1)
            if param_name not in seen_params:
                seen_params.add(param_name)
                param = Parameter(
                    name=param_name,
                    location=ParameterLocation.PATH,
                    type="string",
                    required=True,
                )
                parameters.append(param)

        # Find all {param} patterns (OpenAPI format)
        openapi_pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
        openapi_matches = re.finditer(openapi_pattern, path)

        for match in openapi_matches:
            param_name = match.group(1)
            if param_name not in seen_params:
                seen_params.add(param_name)
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

        Convert :param to {param} and *param to {param}.
        Empty paths are converted to /.

        Args:
            path: Gin path

        Returns:
            Normalized path (always starts with /)
        """
        # Handle empty path - convert to root
        if not path or path == '':
            return '/'

        # Replace :param with {param}
        normalized = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", path)
        # Replace *param with {param} (wildcard/catch-all parameters)
        normalized = re.sub(r"\*([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", normalized)

        # Ensure path starts with /
        if not normalized.startswith('/'):
            normalized = '/' + normalized

        return normalized

    def _find_struct_definitions(self, tree, source_code: bytes) -> Dict[str, Schema]:
        """
        Find all struct definitions in the Go file.

        Args:
            tree: Syntax tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping struct names to Schema objects
        """
        struct_schemas = {}

        # Query for type declarations with struct types
        struct_query = """
        (type_declaration
          (type_spec
            name: (type_identifier) @struct_name
            type: (struct_type) @struct_body))
        """

        matches = self.parser.query(tree, struct_query, "go")

        for match in matches:
            struct_name_node = match.get("struct_name")
            struct_body_node = match.get("struct_body")

            if not struct_name_node or not struct_body_node:
                continue

            struct_name = self.parser.get_node_text(struct_name_node, source_code)

            # Parse struct fields
            schema = self._parse_struct_fields(struct_body_node, source_code)
            if schema:
                struct_schemas[struct_name] = schema

        return struct_schemas

    def _parse_struct_fields(self, struct_node: Node, source_code: bytes) -> Optional[Schema]:
        """
        Parse struct fields with Go tags.

        Enhancement: Handle inline struct types for nested field extraction.

        Args:
            struct_node: Struct type node
            source_code: Source code bytes

        Returns:
            Schema object or None
        """
        properties = {}
        required = []

        # Find field_declaration_list
        field_list = None
        for child in struct_node.children:
            if child.type == "field_declaration_list":
                field_list = child
                break

        if not field_list:
            return None

        # Parse each field
        for field in field_list.children:
            if field.type != "field_declaration":
                continue

            field_info = self._parse_struct_field(field, source_code)
            if field_info:
                field_name = field_info["name"]

                # Check if this field has an inline struct definition
                if field_info.get("inline_struct_schema"):
                    # Store the full inline struct schema
                    properties[field_name] = field_info["inline_struct_schema"].model_dump(exclude_none=True)
                else:
                    properties[field_name] = {
                        "type": field_info["type"]
                    }

                if field_info.get("required", False):
                    required.append(field_name)

        if not properties:
            return None

        schema_dict = {
            "type": "object",
            "properties": properties,
        }

        if required:
            schema_dict["required"] = required

        return Schema(**schema_dict)

    def _parse_struct_field(self, field_node: Node, source_code: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse a single struct field with Go tags.

        Enhancement: Store actual type name for nested type resolution and extract inline struct schemas.

        Args:
            field_node: Field declaration node
            source_code: Source code bytes

        Returns:
            Dict with name, type, type_name, inline_struct_schema, and required, or None
        """
        field_name = None
        field_type = "string"
        field_type_name = None  # Store actual type name
        inline_struct_schema = None  # Store inline struct schema
        inline_struct_node = None  # Store struct node for later parsing
        is_required = False
        json_name = None

        # Extract field identifier
        for child in field_node.children:
            if child.type == "field_identifier":
                field_name = self.parser.get_node_text(child, source_code)
            elif child.type in ("type_identifier", "pointer_type", "slice_type", "map_type", "qualified_type", "struct_type"):
                type_text = self.parser.get_node_text(child, source_code)
                field_type = self._parse_go_type(type_text)
                # Store the actual type name for nested resolution
                if child.type == "type_identifier":
                    field_type_name = type_text
                elif child.type == "struct_type":
                    # Inline struct definition - parse it
                    field_type_name = None
                    inline_struct_node = child
            elif child.type == "raw_string_literal":
                # Parse Go tags
                tag_text = self.parser.get_node_text(child, source_code)
                tag_info = self._parse_go_tag(tag_text)

                # Get JSON name if specified
                if "json" in tag_info:
                    json_name = tag_info["json"]
                    # Check for omitempty
                    if not tag_info.get("omitempty", False):
                        is_required = True

                # Check binding tag for required
                if "binding" in tag_info and "required" in tag_info["binding"]:
                    is_required = True

        if not field_name:
            return None

        # Parse inline struct if present
        if inline_struct_node:
            inline_struct_schema = self._parse_struct_fields(inline_struct_node, source_code)

        # Use json tag name if specified, otherwise use field name
        name = json_name if json_name else field_name

        result = {
            "name": name,
            "type": field_type,
            "type_name": field_type_name,  # For named type resolution
            "required": is_required
        }

        if inline_struct_schema:
            result["inline_struct_schema"] = inline_struct_schema

        return result

    def _parse_go_tag(self, tag_text: str) -> Dict[str, Any]:
        """
        Parse Go struct tag string.

        Args:
            tag_text: Go tag string like `json:"user_id,omitempty" binding:"required"`

        Returns:
            Dict with parsed tag information
        """
        result = {}

        # Remove backticks
        tag_text = tag_text.strip('`')

        # Parse each tag: key:"value,options"
        pattern = r'(\w+):"([^"]*)"'
        matches = re.finditer(pattern, tag_text)

        for match in matches:
            key = match.group(1)
            value = match.group(2)

            if key == "json":
                # Parse JSON tag: "field_name,omitempty"
                parts = value.split(",")
                if parts[0] and parts[0] != "-":
                    result["json"] = parts[0]
                # Check for omitempty
                if "omitempty" in parts:
                    result["omitempty"] = True
            elif key == "binding":
                result["binding"] = value

        return result

    def _parse_go_type(self, type_text: str) -> str:
        """
        Parse Go type to OpenAPI type.

        Args:
            type_text: Go type string

        Returns:
            OpenAPI type string
        """
        # Handle pointers
        if type_text.startswith("*"):
            type_text = type_text[1:]

        # Go type mapping
        type_map = {
            "string": "string",
            "int": "integer",
            "int32": "integer",
            "int64": "integer",
            "uint": "integer",
            "uint32": "integer",
            "uint64": "integer",
            "float32": "number",
            "float64": "number",
            "bool": "boolean",
            "time.Time": "string",
        }

        # Check for slices (arrays)
        if type_text.startswith("[]"):
            return "array"

        # Check for maps (objects)
        if type_text.startswith("map["):
            return "object"

        return type_map.get(type_text, "object")

    def _extract_handler_schemas(
        self,
        handler_name: str,
        tree,
        source_code: bytes,
        struct_schemas: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Find handler function and extract request/response types.

        Args:
            handler_name: Name of handler function
            tree: Syntax tree
            source_code: Source code bytes
            struct_schemas: Available struct schemas

        Returns:
            Dict with request_body and response_schema
        """
        from api_extractor.extractors.schema_utils import wrap_array_schema

        metadata = {}

        # Query for function declaration
        func_query = f"""
        (function_declaration
          name: (identifier) @func_name
          body: (block) @func_body)
        """

        matches = self.parser.query(tree, func_query, "go")

        for match in matches:
            func_name_node = match.get("func_name")
            func_body_node = match.get("func_body")

            if not func_name_node or not func_body_node:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)
            if func_name != handler_name:
                continue

            # Search for c.BindJSON, c.ShouldBindJSON, c.Bind calls (request body)
            request_type = self._find_bind_call(func_body_node, source_code)
            if request_type:
                # Check if it's a slice first
                if request_type.startswith("[]"):
                    inner_type = request_type[2:]
                    if inner_type in struct_schemas:
                        metadata["request_body"] = wrap_array_schema(struct_schemas[inner_type])
                elif request_type in struct_schemas:
                    metadata["request_body"] = struct_schemas[request_type]

            # Search for c.JSON calls (response body)
            response_type = self._find_json_call(func_body_node, source_code)
            if response_type:
                # Check if it's a slice first
                if response_type.startswith("[]"):
                    inner_type = response_type[2:]
                    if inner_type in struct_schemas:
                        metadata["response_schema"] = wrap_array_schema(struct_schemas[inner_type])
                elif response_type in struct_schemas:
                    metadata["response_schema"] = struct_schemas[response_type]

            break

        return metadata

    def _find_bind_call(self, body_node: Node, source_code: bytes) -> Optional[str]:
        """
        Find request binding and extract type.

        Supports:
        1. Direct: var req Type; c.BindJSON(&req)
        2. Direct composite: c.ShouldBindJSON(&TypeName{})
        3. Indirect: validator := NewValidator(); validator.Bind(c)
        4. Nested: Extract validator.User field from validator struct

        Args:
            body_node: Function body node
            source_code: Source code bytes

        Returns:
            Type name or None
        """
        from api_extractor.extractors.schema_utils import (
            extract_nested_field_from_struct,
            find_type_in_variable_chain
        )

        body_text = self.parser.get_node_text(body_node, source_code)

        # Pattern 1: c.BindJSON(&variable) or c.ShouldBindJSON(&variable)
        # Need to find the variable declaration first
        bind_match = re.search(r'(?:BindJSON|ShouldBindJSON|Bind)\s*\(\s*&(\w+)', body_text)
        if bind_match:
            var_name = bind_match.group(1)
            # Find variable declaration: var varName TypeName
            var_pattern = rf'\bvar\s+{var_name}\s+(\[?\]?\*?\w+(?:\.\w+)?)'
            var_match = re.search(var_pattern, body_text)
            if var_match:
                return var_match.group(1)

        # Pattern 2: c.ShouldBindJSON(&TypeName{})
        composite_match = re.search(r'(?:BindJSON|ShouldBindJSON|Bind)\s*\(\s*&(\[?\]?\w+(?:\.\w+)?)\{', body_text)
        if composite_match:
            return composite_match.group(1)

        # Pattern 3: Indirect - validator.Bind(c)
        # Find: variable.Bind(c) where variable has a custom type
        indirect_match = re.search(r'(\w+)\.Bind\s*\(\s*c\s*\)', body_text)
        if indirect_match:
            validator_var = indirect_match.group(1)

            # Find validator type from variable declaration
            validator_type = find_type_in_variable_chain(
                validator_var, body_node, source_code, "go", self.parser
            )

            if validator_type:
                # Look up validator struct in all_structs (same-file structs)
                # First, check current file structs
                current_file_structs = getattr(self, '_current_file_structs', {})

                if validator_type in current_file_structs:
                    validator_schema = current_file_structs[validator_type]

                    # Pattern 3a: Check for nested struct field (common pattern)
                    # type UserValidator struct { User struct {...} `json:"user"` }
                    # Common convention: nested field named after entity
                    # Try common field names (both capitalized and lowercase for JSON names)
                    for field_name in ['User', 'user', 'Data', 'data', 'Model', 'model', 'Request', 'request']:
                        nested_schema = extract_nested_field_from_struct(
                            validator_schema,
                            field_path=field_name
                        )
                        if nested_schema:
                            # Return a marker indicating nested type
                            return f"{validator_type}.{field_name}"

                # Pattern 3b: Validator itself is the request type
                # Return type name even if not in current file - will be resolved later via package registry
                return validator_type

        return None

    def _find_json_call(self, body_node: Node, source_code: bytes) -> Optional[str]:
        """
        Find JSON response and extract type.

        Supports:
        1. Direct: c.JSON(200, UserResponse{})
        2. Variable: response := UserResponse{}; c.JSON(200, response)
        3. Serializer: serializer.Response() → trace return type
        4. Wrapped: gin.H{"user": serializer.Response()} → extract inner type

        Args:
            body_node: Function body node
            source_code: Source code bytes

        Returns:
            Type name or None
        """
        from api_extractor.extractors.schema_utils import find_type_in_variable_chain

        body_text = self.parser.get_node_text(body_node, source_code)

        # Pattern 1: c.JSON(status, TypeName{...}) or c.JSON(status, []TypeName{...})
        # Status can be a number or constant like http.StatusOK
        composite_match = re.search(r'\.JSON\s*\(\s*[\w.]+\s*,\s*(\[?\]?\w+(?:\.\w+)?)\s*\{', body_text)
        if composite_match:
            type_name = composite_match.group(1)
            # Skip gin.H or other package.Type error responses (contain dots)
            if '.' not in type_name:
                return type_name

        # Pattern 2: gin.H wrapper with serializer - gin.H{"user": serializer.Response()}
        # Find all c.JSON calls with gin.H
        gin_h_matches = re.finditer(
            r'\.JSON\s*\(\s*[\w.]+\s*,\s*gin\.H\s*\{[^}]*"(\w+)":\s*(\w+)\.(\w+)\(\)',
            body_text
        )

        for match in gin_h_matches:
            json_key = match.group(1)  # e.g., "user"
            serializer_var = match.group(2)  # e.g., "serializer"
            method_name = match.group(3)  # e.g., "Response"

            # Find serializer type
            serializer_type = find_type_in_variable_chain(
                serializer_var, body_node, source_code, "go", self.parser
            )

            if serializer_type:
                # Trace Response() method to find return type
                return_type = self._trace_serializer_method(
                    serializer_type, method_name, source_code
                )
                if return_type:
                    return return_type

        # Pattern 3: Direct serializer - c.JSON(status, serializer.Response())
        serializer_match = re.search(r'\.JSON\s*\(\s*[\w.]+\s*,\s*(\w+)\.(\w+)\(\)', body_text)
        if serializer_match:
            serializer_var = serializer_match.group(1)
            method_name = serializer_match.group(2)

            serializer_type = find_type_in_variable_chain(
                serializer_var, body_node, source_code, "go", self.parser
            )

            if serializer_type:
                return_type = self._trace_serializer_method(
                    serializer_type, method_name, source_code
                )
                if return_type:
                    return return_type

        # Pattern 4: c.JSON(status, variable) - try to find variable type
        # Status can be a number or constant like http.StatusOK
        # Match all c.JSON calls and find the last one (usually the success response)
        var_matches = list(re.finditer(r'\.JSON\s*\(\s*[\w.]+\s*,\s*([\w.]+)\s*\)', body_text))

        # Process matches from last to first (prefer success responses over error responses)
        for var_match in reversed(var_matches):
            var_ref = var_match.group(1)

            # Skip gin.H or package.H (map literals used for errors)
            if '.' in var_ref:
                # This is like gin.H or http.StatusXX
                continue

            var_name = var_ref

            # Try to find variable declaration or assignment
            # var response TypeName or response := TypeName{} or response := []TypeName{}
            # Match: varName := Type{
            type_pattern = rf'{var_name}\s*:=\s*(\[?\]?\*?\w+(?:\.\w+)?)\s*\{{'
            type_match = re.search(type_pattern, body_text)
            if type_match:
                return type_match.group(1)

            # Try: var varName Type
            var_decl_pattern = rf'\bvar\s+{var_name}\s+(\[?\]?\*?\w+(?:\.\w+)?)'
            var_decl_match = re.search(var_decl_pattern, body_text)
            if var_decl_match:
                return var_decl_match.group(1)

        return None

    def _trace_serializer_method(
        self,
        serializer_type: str,
        method_name: str,
        source_code: bytes
    ) -> Optional[str]:
        """
        Find serializer method and extract its return type.

        Note: Since serializers are often in separate files, we use a naming convention:
        - UserSerializer.Response() → UserResponse
        - ProfileSerializer.Response() → ProfileResponse

        Args:
            serializer_type: Serializer type name (e.g., "UserSerializer")
            method_name: Method name to find (e.g., "Response")
            source_code: Source code bytes

        Returns:
            Return type name or None if not found

        Examples:
            serializer_type = "UserSerializer"
            method_name = "Response"

            Returns: "UserResponse" (by convention)
        """
        # Common naming pattern: XSerializer.Response() → XResponse
        if serializer_type.endswith("Serializer") and method_name == "Response":
            # Extract base name: "UserSerializer" → "User"
            base_name = serializer_type[:-10]  # Remove "Serializer"
            response_type = f"{base_name}Response"
            return response_type

        # Fallback: Try to find in current tree (same-file method)
        from api_extractor.extractors.schema_utils import trace_method_return_type

        current_tree = getattr(self, '_current_tree', None)
        if current_tree:
            return_type = trace_method_return_type(
                method_name=method_name,
                source_tree=current_tree,
                source_code=source_code,
                language="go",
                parser=self.parser
            )
            if return_type:
                return return_type

        return None

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects with schema support.

        Args:
            route: Route object with schema metadata

        Returns:
            List of Endpoint objects (one per HTTP method)
        """
        endpoints = []

        for method in route.methods:
            # Parse path parameters
            path_parameters = self._extract_path_parameters(route.path)

            # Create default response
            responses = [
                Response(
                    status_code="200",
                    description="Success",
                    content_type="application/json",
                )
            ]

            # Add response schema if available
            if route.metadata and "response_schema" in route.metadata:
                responses[0].response_schema = route.metadata["response_schema"]

            # Extract request body schema from metadata
            request_body = None
            if route.metadata and "request_body" in route.metadata:
                request_body = route.metadata["request_body"]

            # Generate unique operation ID
            # OpenAPI requires operation IDs to be unique across all operations
            # Include method and path to ensure global uniqueness
            clean_path = route.path.replace("{", "").replace("}", "").replace("/", "_")
            # Strip leading underscores but preserve trailing to distinguish /path vs /path/
            clean_path = clean_path.lstrip("_")
            # If path ends with trailing slash, keep the trailing underscore for uniqueness
            # Otherwise strip it: /slug/ -> slug_ vs /slug -> slug
            if not route.path.endswith("/") or route.path == "/":
                clean_path = clean_path.rstrip("_")

            method_lower = method.value.lower()

            if route.handler_name == "<anonymous>":
                # Anonymous handler: method_path
                # e.g., GET /api/users/{id} -> get_api_users_id
                operation_id = f"{method_lower}_{clean_path}" if clean_path else method_lower
            else:
                # Named handler: handler_method_path
                # e.g., signCheck + GET + /d/path -> signCheck_get_d_path
                operation_id = f"{route.handler_name}_{method_lower}_{clean_path}" if clean_path else f"{route.handler_name}_{method_lower}"

            endpoint = Endpoint(
                path=route.path,
                method=method,
                parameters=path_parameters,
                request_body=request_body,
                responses=responses,
                tags=[self.framework.value],
                operation_id=operation_id,
                source_file=route.source_file,
                source_line=route.source_line,
            )

            endpoints.append(endpoint)

        return endpoints

    def _compose_paths(self, prefix: str, path: str) -> str:
        """
        Compose prefix and path, handling edge cases like double slashes.

        Args:
            prefix: Mount prefix (e.g., '/api', '/')
            path: Route path (e.g., '/users', '/')

        Returns:
            Composed path without double slashes (always starts with /)
        """
        # Handle empty path - convert to root
        if not path or path == '':
            path = '/'

        # Handle empty prefix
        if not prefix or prefix == '':
            # Ensure path starts with '/'
            if not path.startswith('/'):
                path = '/' + path
            return path

        # Handle root prefix '/' specially
        if prefix == '/':
            # Ensure path starts with '/'
            if not path.startswith('/'):
                path = '/' + path
            return path

        # Ensure prefix doesn't end with '/' unless it's root
        if prefix.endswith('/'):
            prefix = prefix.rstrip('/')

        # Ensure path starts with '/'
        if not path.startswith('/'):
            path = '/' + path

        return prefix + path

    def _extract_imports(
        self, tree, source_code: bytes, file_path: str
    ) -> Dict[str, str]:
        """
        Extract import statements from a Go file.

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes
            file_path: Path to current file (for context)

        Returns:
            Dictionary mapping package aliases to import paths
            Example: {"handles": "github.com/alist-org/alist/v3/server/handles"}
        """
        imports = {}

        # Query for import_declaration nodes
        import_query = "(import_declaration) @import_decl"
        matches = self.parser.query(tree, import_query, "go")

        for match in matches:
            import_node = match.get("import_decl")
            if not import_node:
                continue

            # Find import_spec_list
            for child in import_node.children:
                if child.type == "import_spec_list":
                    # Process each import_spec
                    for spec_child in child.children:
                        if spec_child.type == "import_spec":
                            self._parse_import_spec(spec_child, source_code, imports)
                elif child.type == "import_spec":
                    # Single import without parentheses
                    self._parse_import_spec(child, source_code, imports)

        return imports

    def _parse_import_spec(
        self, spec_node: Node, source_code: bytes, imports: Dict[str, str]
    ) -> None:
        """
        Parse a single import_spec node.

        Args:
            spec_node: import_spec Node
            source_code: Source code bytes
            imports: Dictionary to populate with imports
        """
        import_path = None
        alias = None

        # Extract components
        for child in spec_node.children:
            if child.type == "interpreted_string_literal":
                # Remove quotes from import path
                path_text = self.parser.get_node_text(child, source_code)
                import_path = path_text.strip('"')
            elif child.type == "package_identifier":
                # Aliased import
                alias = self.parser.get_node_text(child, source_code)

        if not import_path:
            return

        # Determine package alias
        if alias:
            # Explicit alias: import m "path"
            package_alias = alias
        else:
            # Derive alias from path: "github.com/user/repo/pkg" → "pkg"
            parts = import_path.rstrip("/").split("/")
            package_alias = parts[-1]

        imports[package_alias] = import_path

    def _resolve_import_to_directory(
        self, import_path: str, current_file: str
    ) -> Optional[str]:
        """
        Resolve a Go import path to an actual directory.

        Args:
            import_path: Import path like "github.com/alist-org/alist/v3/server/handles"
                        or "./internal/model"
            current_file: Current file path for relative resolution

        Returns:
            Resolved directory path or None if not found
        """
        from pathlib import Path

        # Handle relative imports (starting with .)
        if import_path.startswith("."):
            current_dir = Path(current_file).parent
            # Convert ./path or ../path to actual path
            resolved_path = (current_dir / import_path).resolve()

            if resolved_path.exists() and resolved_path.is_dir():
                # Verify it's a Go package (has .go files)
                if list(resolved_path.glob("*.go")):
                    return str(resolved_path)

            return None

        # Handle absolute/project imports
        # Try to find package in project tree
        # e.g., "github.com/alist-org/alist/v3/server/handles" might be in "server/handles"
        base_path = Path(self.base_path)
        parts = import_path.split("/")

        # Try progressively shorter suffixes of the import path
        for i in range(len(parts)):
            candidate = "/".join(parts[i:])
            potential_dir = base_path / candidate

            if potential_dir.exists() and potential_dir.is_dir():
                # Verify it's a Go package (has .go files)
                if list(potential_dir.glob("*.go")):
                    return str(potential_dir)

        # External package or not found
        return None

    def _register_structs(self, file_path: str) -> None:
        """
        Register struct definitions from a Go file.

        Extracts all struct definitions and stores them in package_registry.

        Args:
            file_path: Path to Go file
        """
        from pathlib import Path

        # Read file
        source_code = self._read_file(file_path)
        if not source_code:
            return

        # Parse with tree-sitter
        tree = self.parser.parse_source(source_code, "go")
        if not tree:
            return

        # Extract struct definitions
        struct_schemas = self._find_struct_definitions(tree, source_code)
        if not struct_schemas:
            return

        # Determine package path (relative to base_path)
        try:
            file_abs = Path(file_path).resolve()
            base_abs = Path(self.base_path).resolve()
            package_dir = file_abs.parent.relative_to(base_abs)
            package_key = str(package_dir)
        except ValueError:
            # File is outside base_path, skip
            return

        # Store in registry (merge with existing structs in this package)
        if package_key not in self.package_registry:
            self.package_registry[package_key] = {}

        self.package_registry[package_key].update(struct_schemas)

    def _register_handlers(self, file_path: str) -> None:
        """
        Register handler functions from a Go file.

        Extracts all exported handler functions with their request/response types.

        Args:
            file_path: Path to Go file
        """
        from pathlib import Path

        # Read file
        source_code = self._read_file(file_path)
        if not source_code:
            return

        # Parse with tree-sitter
        tree = self.parser.parse_source(source_code, "go")
        if not tree:
            return

        # Store current tree for helper methods
        self._current_tree = tree

        # Find struct definitions in this file for _find_bind_call to use
        struct_schemas = self._find_struct_definitions(tree, source_code)

        # Also load structs from the same package (already registered)
        # This allows _find_bind_call to resolve validators from other files in the package
        try:
            file_abs = Path(file_path).resolve()
            base_abs = Path(self.base_path).resolve()
            package_dir = file_abs.parent.relative_to(base_abs)
            package_key = str(package_dir)

            # Merge same-file structs with package structs
            all_package_structs = {}
            if package_key in self.package_registry:
                all_package_structs.update(self.package_registry[package_key])
            all_package_structs.update(struct_schemas)  # Override with same-file structs

            self._current_file_structs = all_package_structs
        except (ValueError, AttributeError):
            # Fallback to just same-file structs
            self._current_file_structs = struct_schemas

        # Find all functions
        func_query = """
        (function_declaration
          name: (identifier) @func_name
          parameters: (parameter_list) @params
          body: (block) @body)
        """

        matches = self.parser.query(tree, func_query, "go")

        handlers = {}
        for match in matches:
            func_name_node = match.get("func_name")
            params_node = match.get("params")
            body_node = match.get("body")

            if not func_name_node or not params_node or not body_node:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)

            # Check if it's an exported function (starts with uppercase)
            if not func_name[0].isupper():
                continue

            # Check if it has gin.Context parameter
            params_text = self.parser.get_node_text(params_node, source_code)
            if "gin.Context" not in params_text:
                continue

            # Extract request/response type names from function body
            body_text = self.parser.get_node_text(body_node, source_code)

            request_type = self._find_bind_call(body_node, source_code)
            response_type = self._find_json_call(body_node, source_code)

            handlers[func_name] = {
                "request_type": request_type,
                "response_type": response_type,
            }

        # Clear temp state
        self._current_file_structs = {}

        if not handlers:
            return

        # Determine package path (relative to base_path)
        try:
            file_abs = Path(file_path).resolve()
            base_abs = Path(self.base_path).resolve()
            package_dir = file_abs.parent.relative_to(base_abs)
            package_key = str(package_dir)
        except ValueError:
            # File is outside base_path, skip
            return

        # Store in registry (merge with existing handlers in this package)
        if package_key not in self.handler_registry:
            self.handler_registry[package_key] = {}

        self.handler_registry[package_key].update(handlers)

    def _resolve_type_in_package(
        self, type_name: str, package_path: str
    ) -> Optional[Schema]:
        """
        Resolve a type name to a Schema by looking in the package registry.

        Supports:
        - Simple types: "User"
        - Array types: "[]User"
        - Nested fields: "UserValidator.user" (extracts nested field from parent struct)

        Args:
            type_name: Type name like "User", "[]User", or "UserValidator.user"
            package_path: Package path relative to base_path

        Returns:
            Schema object or None if not found
        """
        from api_extractor.extractors.schema_utils import wrap_array_schema, extract_nested_field_from_struct

        # Handle slices: []User
        if type_name.startswith("[]"):
            inner_type = type_name[2:]
            inner_schema = self._resolve_type_in_package(inner_type, package_path)
            if inner_schema:
                return wrap_array_schema(inner_schema)
            return None

        # Handle nested fields: Type.field
        if '.' in type_name:
            parts = type_name.split('.', 1)  # Split into parent type and field path
            parent_type = parts[0]
            field_path = parts[1]

            # Look up parent type in registry
            if package_path in self.package_registry:
                structs = self.package_registry[package_path]
                if parent_type in structs:
                    parent_schema = structs[parent_type]
                    # Extract nested field
                    nested_schema = extract_nested_field_from_struct(
                        parent_schema,
                        field_path=field_path
                    )
                    if nested_schema:
                        return nested_schema

            return None

        # Look up in package registry
        if package_path in self.package_registry:
            structs = self.package_registry[package_path]
            if type_name in structs:
                return structs[type_name]

        return None
