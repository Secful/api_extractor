"""NestJS framework extractor."""

import re
import os
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any
from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.parser import find_child_by_type
from api_extractor.extractors.javascript.typescript_config import TypeScriptConfig
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


class NestJSExtractor(BaseExtractor):
    """Extract API routes from NestJS applications."""

    # HTTP method decorators
    HTTP_METHOD_DECORATORS = ["Get", "Post", "Put", "Delete", "Patch", "Head", "Options"]

    def __init__(self) -> None:
        """Initialize NestJS extractor."""
        super().__init__(FrameworkType.NESTJS)
        self.tsconfig: Optional[TypeScriptConfig] = None

    def get_file_extensions(self) -> List[str]:
        """Get TypeScript file extensions."""
        return [".ts"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a NestJS file.

        Args:
            file_path: Path to TypeScript file

        Returns:
            List of Route objects
        """
        routes = []

        # Load tsconfig on first file (cache for subsequent files)
        if self.tsconfig is None:
            self.tsconfig = TypeScriptConfig.find_tsconfig(file_path)

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, "typescript")
        if not tree:
            return routes

        # First, find all DTO classes
        dto_classes = self._find_dto_classes(tree, source_code)

        # Query for all class declarations (works for both exported and non-exported)
        class_query = """
        (class_declaration
          name: (type_identifier) @class_name
          body: (class_body) @class_body)
        """

        all_classes = self.parser.query(tree, class_query, "typescript")

        for match in all_classes:
            class_name_node = match.get("class_name")
            class_body_node = match.get("class_body")

            if not class_name_node or not class_body_node:
                continue

            # Check if this class has @Controller decorator
            # We need to check the parent nodes for decorators
            controller_info = self._find_controller_decorator(class_name_node, source_code)
            if not controller_info:
                continue

            # Extract routes from this controller
            class_routes = self._extract_routes_from_controller_query(
                class_body_node, source_code, file_path, controller_info, tree, dto_classes
            )
            routes.extend(class_routes)

        return routes

    def _find_controller_decorator(
        self, class_name_node: Node, source_code: bytes
    ) -> Optional[Dict[str, any]]:
        """
        Find @Controller decorator for a class by checking parent nodes.

        Args:
            class_name_node: Class name identifier node
            source_code: Source code bytes

        Returns:
            Controller info dict or None
        """
        # Walk up to find decorators
        current = class_name_node.parent  # class_declaration
        if not current:
            return None

        # Check parent's siblings for decorators
        parent = current.parent
        if not parent:
            return None

        # Look for decorator among siblings or parent's children
        for sibling in parent.children:
            if sibling.type == "decorator":
                decorator_text = self.parser.get_node_text(sibling, source_code)
                if "Controller" in decorator_text:
                    return self._extract_controller_info(sibling, source_code)

        return None

    def _extract_routes_from_controller_query(
        self,
        class_body_node: Node,
        source_code: bytes,
        file_path: str,
        controller_info: Dict[str, any],
        tree,
        dto_classes: Dict[str, Schema],
    ) -> List[Route]:
        """
        Extract routes from controller using queries.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes
            file_path: Path to source file
            controller_info: Controller path and version info
            tree: Full syntax tree
            dto_classes: Dictionary of DTO schemas

        Returns:
            List of Route objects
        """
        routes = []

        # Get controller path and version
        controller_path = controller_info["path"]
        version = controller_info["version"]

        # Add version prefix if present
        if version:
            controller_path = f"/v{version}{controller_path}"

        # Extract imports for type resolution
        imports = self._extract_imports(tree, source_code)

        # Iterate through class_body children and pair decorators with methods
        # In TypeScript AST, decorators immediately precede their method
        # There can be multiple decorators before a method
        children = class_body_node.children
        i = 0
        while i < len(children):
            child = children[i]

            # Look for decorator(s) followed by method_definition
            if child.type == "decorator":
                # Collect all consecutive decorators
                decorators = [child]
                j = i + 1
                while j < len(children) and children[j].type == "decorator":
                    decorators.append(children[j])
                    j += 1

                # Check if decorators are followed by a method_definition
                if j < len(children) and children[j].type == "method_definition":
                    method_node = children[j]

                    # Look through all decorators for HTTP method decorator
                    for decorator_node in decorators:
                        decorator_text = self.parser.get_node_text(decorator_node, source_code)

                        for http_decorator in self.HTTP_METHOD_DECORATORS:
                            # Match decorator that starts with @<HttpMethod>(
                            if decorator_text.strip().startswith(f"@{http_decorator}("):
                                # Extract path from decorator
                                method_path = self._extract_method_path(decorator_node, source_code)

                                # Combine controller and method paths
                                full_path = self._combine_paths(controller_path, method_path)

                                # Get method name from first child (property_identifier)
                                if method_node.children:
                                    method_name_node = method_node.children[0]
                                    method_name = self.parser.get_node_text(method_name_node, source_code)

                                    # Get location
                                    location = self.parser.get_node_location(method_name_node)

                                    # Extract method parameters for schemas
                                    metadata = self._extract_method_parameters(
                                        method_node, source_code, dto_classes
                                    )

                                    # Resolve return type schema if available
                                    return_type_name = metadata.get("return_type_name")
                                    if return_type_name:
                                        schema = self._resolve_type_schema(
                                            return_type_name, file_path, imports
                                        )
                                        if schema:
                                            metadata["response_schema"] = schema

                                    # Resolve request body type if needed
                                    request_body_type_name = metadata.get("request_body_type_name")
                                    if request_body_type_name and not metadata.get("request_body"):
                                        schema = self._resolve_type_schema(
                                            request_body_type_name, file_path, imports
                                        )
                                        if schema:
                                            metadata["request_body"] = schema

                                    # Create route
                                    try:
                                        http_method = HTTPMethod[http_decorator.upper()]
                                        route = Route(
                                            path=full_path,
                                            methods=[http_method],
                                            handler_name=method_name,
                                            framework=self.framework,
                                            raw_path=full_path,
                                            source_file=file_path,
                                            source_line=location["start_line"],
                                            metadata=metadata,
                                        )
                                        routes.append(route)
                                        break  # Only one HTTP method per method
                                    except KeyError:
                                        pass

                    # Skip past all decorators and the method
                    i = j

            i += 1

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

    def _extract_controller_info(
        self, decorator_node: Node, source_code: bytes
    ) -> Optional[Dict[str, any]]:
        """
        Extract controller information from @Controller decorator.

        Handles both:
        - @Controller('users')
        - @Controller({ path: 'users', version: '1' })

        Args:
            decorator_node: decorator node
            source_code: Source code bytes

        Returns:
            Dict with 'path' and optional 'version', or None
        """
        # Find call expression
        call_expr = find_child_by_type(decorator_node, "call_expression")
        if not call_expr:
            return {"path": "", "version": None}

        # Get arguments
        args = self.parser.find_child_by_field(call_expr, "arguments")
        if not args:
            return {"path": "", "version": None}

        # Check first argument
        for child in args.children:
            # Simple string path: @Controller('users')
            if child.type == "string":
                path = self.parser.extract_string_value(child, source_code)
                return {
                    "path": f"/{path}" if path and not path.startswith("/") else path or "",
                    "version": None,
                }

            # Object syntax: @Controller({ path: 'users', version: '1' })
            elif child.type == "object":
                return self._parse_controller_object(child, source_code)

        return {"path": "", "version": None}

    def _parse_controller_object(self, obj_node: Node, source_code: bytes) -> Dict[str, any]:
        """
        Parse @Controller({ path: 'users', version: '1' }) object.

        Args:
            obj_node: object node
            source_code: Source code bytes

        Returns:
            Dict with path and version
        """
        result = {"path": "", "version": None}

        for child in obj_node.children:
            if child.type == "pair":
                # Get key and value
                key_node = self.parser.find_child_by_field(child, "key")
                value_node = self.parser.find_child_by_field(child, "value")

                if not key_node or not value_node:
                    continue

                key = self.parser.get_node_text(key_node, source_code).strip("'\"")

                if key == "path":
                    if value_node.type == "string":
                        path = self.parser.extract_string_value(value_node, source_code)
                        result["path"] = (
                            f"/{path}" if path and not path.startswith("/") else path or ""
                        )

                elif key == "version":
                    if value_node.type == "string":
                        result["version"] = self.parser.extract_string_value(value_node, source_code)
                    elif value_node.type == "number":
                        result["version"] = self.parser.get_node_text(value_node, source_code)

        return result

    def _combine_paths(self, base: str, method: str) -> str:
        """
        Combine base and method paths properly.

        Args:
            base: Base path from controller
            method: Method path from decorator

        Returns:
            Combined path
        """
        # Normalize paths
        base = base.rstrip("/") if base else ""
        method = method.lstrip("/") if method else ""

        if not method:
            return base or "/"

        if not base:
            return f"/{method}"

        return f"{base}/{method}"

    def _extract_method_path(self, decorator_node: Node, source_code: bytes) -> str:
        """
        Extract path from HTTP method decorator.

        Handles:
        - @Get() → empty string
        - @Get(':id') → ':id'
        - @Get('profile') → 'profile'

        Args:
            decorator_node: decorator node
            source_code: Source code bytes

        Returns:
            Method path (may be empty for root)
        """
        # Find call expression
        call_expr = find_child_by_type(decorator_node, "call_expression")
        if not call_expr:
            return ""

        # Get arguments
        args = self.parser.find_child_by_field(call_expr, "arguments")
        if not args:
            return ""

        # Get first argument (path string)
        for child in args.children:
            if child.type == "string":
                path = self.parser.extract_string_value(child, source_code)
                return path or ""

        return ""

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from NestJS path.

        NestJS uses :paramName syntax.

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
        Normalize NestJS path to OpenAPI format.

        Convert :param to {param}.

        Args:
            path: NestJS path

        Returns:
            Normalized path
        """
        # Replace :param with {param}
        normalized = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", path)
        return normalized

    def _find_dto_classes(self, tree, source_code: bytes) -> Dict[str, Schema]:
        """
        Find all DTO classes (TypeScript classes used for data transfer).

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping class names to Schema objects
        """
        dtos = {}

        # Query for all class declarations
        class_query = """
        (class_declaration
          name: (type_identifier) @class_name
          body: (class_body) @class_body)
        """

        matches = self.parser.query(tree, class_query, "typescript")

        for match in matches:
            class_name_node = match.get("class_name")
            class_body_node = match.get("class_body")

            if not all([class_name_node, class_body_node]):
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)

            # Skip controller classes
            if "Controller" in class_name:
                continue

            # Parse properties from class body
            schema = self._parse_dto_class_body(class_body_node, source_code)
            if schema.properties:  # Only add if it has properties
                dtos[class_name] = schema

        return dtos

    def _parse_dto_class_body(self, class_body_node: Node, source_code: bytes) -> Schema:
        """
        Parse DTO class properties.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        properties = {}
        required = []

        # Look for public_field_definition and property_signature nodes
        for child in class_body_node.children:
            if child.type in ("public_field_definition", "property_signature"):
                field_info = self._parse_dto_field(child, source_code)
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

    def _parse_dto_field(self, field_node: Node, source_code: bytes) -> Optional[Tuple]:
        """
        Parse a DTO field definition.

        Args:
            field_node: Field node
            source_code: Source code bytes

        Returns:
            Tuple of (field_name, field_schema_dict, is_required) or None
        """
        # Get field name
        name_node = None
        type_node = None
        is_optional = False

        for child in field_node.children:
            if child.type == "property_identifier":
                name_node = child
            elif child.type == "?":
                is_optional = True
            elif child.type == "type_annotation":
                # Get the type inside type_annotation
                for type_child in child.children:
                    if type_child.type != ":":
                        type_node = type_child
                        break

        if not name_node:
            return None

        field_name = self.parser.get_node_text(name_node, source_code)

        # Get type
        field_type = "string"  # default
        if type_node:
            type_text = self.parser.get_node_text(type_node, source_code)
            field_type = self._parse_typescript_type(type_text)

        is_required = not is_optional

        field_schema = {"type": field_type}

        return (field_name, field_schema, is_required)

    def _parse_typescript_type(self, type_text: str) -> str:
        """
        Convert TypeScript type to OpenAPI type.

        Args:
            type_text: TypeScript type string

        Returns:
            OpenAPI type string
        """
        # Clean up type text
        type_text = type_text.strip()

        # Type mapping
        type_map = {
            "string": "string",
            "number": "number",
            "boolean": "boolean",
            "any": "object",
            "object": "object",
        }

        # Check for array types
        if type_text.endswith("[]") or type_text.startswith("Array<"):
            return "array"

        # Direct mapping
        if type_text in type_map:
            return type_map[type_text]

        # If it's a custom type (DTO), treat as object
        return "object"

    def _extract_method_parameters(
        self, method_node: Node, source_code: bytes, dto_classes: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Extract method parameters to identify request body and query/param decorators.
        Also extracts return type.

        Args:
            method_node: Method definition node
            source_code: Source code bytes
            dto_classes: Dictionary of DTO schemas

        Returns:
            Dictionary with request_body, query_params, return_type_name, etc.
        """
        metadata = {}
        query_params = []
        path_params = []
        request_body_type_name = None

        # Find formal_parameters node
        params_node = None
        for child in method_node.children:
            if child.type == "formal_parameters":
                params_node = child
                break

        if params_node:
            # Process each parameter
            for param in params_node.children:
                if param.type in ("required_parameter", "optional_parameter"):
                    param_info = self._analyze_nestjs_parameter(param, source_code, dto_classes)
                    if param_info:
                        param_type, param_data, type_name = param_info
                        if param_type == "body":
                            if param_data:  # Only set if we have actual schema
                                metadata["request_body"] = param_data
                            if type_name:
                                request_body_type_name = type_name
                        elif param_type == "query":
                            query_params.append(param_data)
                        elif param_type == "param":
                            path_params.append(param_data)

        if query_params:
            metadata["query_params"] = query_params
        if path_params:
            metadata["path_params"] = path_params
        if request_body_type_name:
            metadata["request_body_type_name"] = request_body_type_name

        # Extract return type
        return_type_name = self._extract_return_type(method_node, source_code)
        if return_type_name:
            metadata["return_type_name"] = return_type_name

        return metadata

    def _analyze_nestjs_parameter(
        self, param_node: Node, source_code: bytes, dto_classes: Dict[str, Schema]
    ) -> Optional[Tuple]:
        """
        Analyze a NestJS method parameter.
        Supports both named types and inline object literals.

        Args:
            param_node: Parameter node
            source_code: Source code bytes
            dto_classes: Dictionary of DTO schemas

        Returns:
            Tuple of (param_type, param_data, type_name) or None
        """
        # Look for decorator
        decorator_node = None
        param_name = None
        type_name = None
        type_annotation_node = None

        for child in param_node.children:
            if child.type == "decorator":
                decorator_node = child
            elif child.type == "identifier":
                param_name = self.parser.get_node_text(child, source_code)
            elif child.type == "type_annotation":
                type_annotation_node = child
                # Get the type - could be type_identifier, predefined_type, or object_type
                for type_child in child.children:
                    if type_child.type in ("type_identifier", "predefined_type"):
                        type_name = self.parser.get_node_text(type_child, source_code)
                        break

        if not decorator_node:
            return None

        decorator_text = self.parser.get_node_text(decorator_node, source_code)

        # Check for @Body() decorator
        if "@Body()" in decorator_text:
            # First check for inline object literal
            if type_annotation_node:
                inline_schema = self._extract_inline_object_type(type_annotation_node, source_code)
                if inline_schema:
                    # Found inline object literal - use it directly
                    return ("body", inline_schema, None)

            # Fall back to named type resolution
            if type_name:
                # Return schema if available
                if type_name in dto_classes:
                    return ("body", dto_classes[type_name], type_name)
                else:
                    # Type not in dto_classes, will need to be resolved later
                    # Return a placeholder that will be resolved in route processing
                    return ("body", None, type_name)
            return None

        # Check for @Param decorator
        if "@Param(" in decorator_text:
            # Extract parameter name from decorator
            param_match = re.search(r"@Param\(['\"]([^'\"]+)['\"]\)", decorator_text)
            if param_match:
                param_name_from_decorator = param_match.group(1)
                # Determine type from type annotation
                param_type = "string"
                if type_name:
                    param_type = self._parse_typescript_type(type_name)

                param_obj = Parameter(
                    name=param_name_from_decorator,
                    location=ParameterLocation.PATH,
                    type=param_type,
                    required=True,
                )
                return ("param", param_obj, type_name)

        # Check for @Query decorator
        if "@Query(" in decorator_text:
            # Extract parameter name from decorator
            param_match = re.search(r"@Query\(['\"]([^'\"]+)['\"]\)", decorator_text)
            if param_match:
                param_name_from_decorator = param_match.group(1)
                # Determine type from type annotation
                param_type = "string"
                if type_name:
                    param_type = self._parse_typescript_type(type_name)

                # Check if optional (has ? in parameter)
                is_required = "?" not in self.parser.get_node_text(param_node, source_code)

                param_obj = Parameter(
                    name=param_name_from_decorator,
                    location=ParameterLocation.QUERY,
                    type=param_type,
                    required=is_required,
                )
                return ("query", param_obj, type_name)

        return None

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects.

        Overridden to handle DTO schemas.

        Args:
            route: Route object

        Returns:
            List of Endpoint objects (one per HTTP method)
        """
        endpoints = []

        for method in route.methods:
            # Parse path parameters from path
            parameters = self._extract_path_parameters(route.raw_path)

            # Add parameters from metadata
            if "query_params" in route.metadata:
                parameters.extend(route.metadata["query_params"])
            if "path_params" in route.metadata:
                # Replace auto-extracted path params with decorated ones which have types
                # Remove auto-extracted params that are in decorated params
                decorated_param_names = {p.name for p in route.metadata["path_params"]}
                parameters = [p for p in parameters if p.name not in decorated_param_names]
                parameters.extend(route.metadata["path_params"])

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

            # Get response schema from metadata if available
            response_schema = route.metadata.get("response_schema")
            if response_schema:
                responses = [
                    Response(
                        status_code="200",
                        description="Success",
                        response_schema=response_schema,
                        content_type="application/json",
                    )
                ]

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

    def _extract_return_type(self, method_node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract return type from method signature.

        Handles:
        - Promise<TypeName>
        - Observable<TypeName>
        - Direct TypeName
        - void

        Args:
            method_node: Method definition node
            source_code: Source code bytes

        Returns:
            Type name string or None
        """
        # Look for type_annotation in method children
        for child in method_node.children:
            if child.type == "type_annotation":
                # Get the type after the colon
                for type_child in child.children:
                    if type_child.type == ":":
                        continue

                    # Get the type text
                    type_text = self.parser.get_node_text(type_child, source_code)

                    # Handle Promise<Type>
                    promise_match = re.match(r"Promise<([^>]+)>", type_text)
                    if promise_match:
                        return promise_match.group(1)

                    # Handle Observable<Type>
                    observable_match = re.match(r"Observable<([^>]+)>", type_text)
                    if observable_match:
                        return observable_match.group(1)

                    # Return direct type (skip void)
                    if type_text != "void":
                        return type_text

        return None

    def _extract_imports(self, tree, source_code: bytes) -> Dict[str, str]:
        """
        Extract import statements from file.

        Args:
            tree: Tree-sitter tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping type names to import paths
        """
        imports = {}

        # Query for import statements
        import_query = """
        (import_statement
          source: (string) @source)
        """

        matches = self.parser.query(tree, import_query, "typescript")

        for match in matches:
            source_node = match.get("source")
            if not source_node:
                continue

            # Get the full import statement
            import_node = source_node.parent
            if not import_node:
                continue

            import_text = self.parser.get_node_text(import_node, source_code)

            # Parse import statement
            # Handle: import { TypeName } from './path'
            # Handle: import TypeName from './path'
            # Handle: import * as Name from './path'

            import_path = self.parser.extract_string_value(source_node, source_code)

            # Extract imported names
            names = self._parse_import_names(import_node, source_code)
            for name in names:
                imports[name] = import_path

        return imports

    def _parse_import_names(self, import_node: Node, source_code: bytes) -> List[str]:
        """
        Parse imported names from import statement.

        Args:
            import_node: Import statement node
            source_code: Source code bytes

        Returns:
            List of imported names
        """
        names = []

        # Look for import_clause
        for child in import_node.children:
            if child.type == "import_clause":
                # Handle named imports: import { A, B } from './path'
                for clause_child in child.children:
                    if clause_child.type == "named_imports":
                        for import_child in clause_child.children:
                            if import_child.type == "import_specifier":
                                # Get name from import_specifier
                                for spec_child in import_child.children:
                                    if spec_child.type == "identifier":
                                        name = self.parser.get_node_text(spec_child, source_code)
                                        names.append(name)
                    # Handle default imports: import A from './path'
                    elif clause_child.type == "identifier":
                        name = self.parser.get_node_text(clause_child, source_code)
                        names.append(name)

        return names

    def _resolve_import_path(
        self, import_path: str, current_file: str
    ) -> Optional[str]:
        """
        Resolve import path to absolute file path.
        Tries tsconfig aliases first, then falls back to relative imports.

        Args:
            import_path: Import path from import statement
            current_file: Current file path

        Returns:
            Resolved absolute file path or None
        """
        # Try tsconfig path alias resolution first
        if self.tsconfig and not import_path.startswith("."):
            resolved = self.tsconfig.resolve_alias(import_path, current_file)
            if resolved:
                return resolved

        # Handle relative imports
        if import_path.startswith("."):
            current_dir = os.path.dirname(current_file)
            resolved = os.path.normpath(os.path.join(current_dir, import_path))

            # Try with .ts extension
            if os.path.exists(resolved + ".ts"):
                return resolved + ".ts"
            # Try with /index.ts
            if os.path.exists(os.path.join(resolved, "index.ts")):
                return os.path.join(resolved, "index.ts")
            # Try as-is
            if os.path.exists(resolved):
                return resolved

        return None

    def _parse_type_definition(
        self, type_name: str, file_path: str
    ) -> Optional[Schema]:
        """
        Parse TypeScript type definition into Schema.
        Handles barrel exports (index.ts files that re-export from other files).

        Args:
            type_name: Name of the type to find
            file_path: File path where type is defined

        Returns:
            Schema object or None
        """
        # Read and parse the file
        source_code = self._read_file(file_path)
        if not source_code:
            return None

        tree = self.parser.parse_source(source_code, "typescript")
        if not tree:
            return None

        # Look for interface - query all interfaces
        interface_query = """
        (interface_declaration
          name: (type_identifier) @name
          body: (interface_body) @body)
        """

        matches = self.parser.query(tree, interface_query, "typescript")
        for match in matches:
            name_node = match.get("name")
            if not name_node:
                continue

            name = self.parser.get_node_text(name_node, source_code)
            if name == type_name:
                body_node = match.get("body")
                if body_node:
                    return self._parse_interface_body(body_node, source_code)

        # Look for type alias - query all type aliases
        type_query = """
        (type_alias_declaration
          name: (type_identifier) @name
          value: (_) @value)
        """

        matches = self.parser.query(tree, type_query, "typescript")
        for match in matches:
            name_node = match.get("name")
            if not name_node:
                continue

            name = self.parser.get_node_text(name_node, source_code)
            if name == type_name:
                value_node = match.get("value")
                if value_node:
                    return self._parse_type_value(value_node, source_code)

        # Look for class declaration - query all classes
        class_query = """
        (class_declaration
          name: (type_identifier) @name
          body: (class_body) @body)
        """

        matches = self.parser.query(tree, class_query, "typescript")
        for match in matches:
            name_node = match.get("name")
            if not name_node:
                continue

            name = self.parser.get_node_text(name_node, source_code)
            if name == type_name:
                body_node = match.get("body")
                if body_node:
                    return self._parse_class_body(body_node, source_code)

        # If not found and this is an index.ts (barrel export), follow re-exports
        if file_path.endswith("index.ts") or file_path.endswith("/index.ts"):
            re_export_path = self._find_re_export(type_name, tree, source_code, file_path)
            if re_export_path:
                # Recursively parse the actual definition file
                return self._parse_type_definition(type_name, re_export_path)

        return None

    def _parse_interface_body(
        self, body_node: Node, source_code: bytes
    ) -> Schema:
        """
        Parse interface body into Schema.

        Args:
            body_node: Object type body node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        properties = {}
        required = []

        # Look for property_signature nodes
        for child in body_node.children:
            if child.type == "property_signature":
                prop_info = self._parse_property_signature(child, source_code)
                if prop_info:
                    name, prop_schema, is_required = prop_info
                    properties[name] = prop_schema
                    if is_required:
                        required.append(name)

        return Schema(
            type="object",
            properties=properties,
            required=required,
        )

    def _parse_class_body(
        self, body_node: Node, source_code: bytes
    ) -> Schema:
        """
        Parse class body into Schema.

        Args:
            body_node: Class body node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        properties = {}
        required = []

        # Look for public_field_definition nodes
        for child in body_node.children:
            if child.type == "public_field_definition":
                prop_info = self._parse_class_property(child, source_code)
                if prop_info:
                    name, prop_schema, is_required = prop_info
                    properties[name] = prop_schema
                    if is_required:
                        required.append(name)

        return Schema(
            type="object",
            properties=properties,
            required=required,
        )

    def _parse_class_property(
        self, prop_node: Node, source_code: bytes
    ) -> Optional[Tuple[str, Dict[str, Any], bool]]:
        """
        Parse a class property definition with recursive type resolution.

        Args:
            prop_node: Public field definition node
            source_code: Source code bytes

        Returns:
            Tuple of (name, schema_dict, is_required) or None
        """
        prop_name = None
        prop_schema = None
        is_optional = False

        for child in prop_node.children:
            # Skip decorators
            if child.type == "decorator":
                continue
            elif child.type == "property_identifier":
                prop_name = self.parser.get_node_text(child, source_code)
            elif child.type == "?":
                is_optional = True
            elif child.type == "type_annotation":
                # Parse the type recursively
                for type_child in child.children:
                    if type_child.type != ":":
                        prop_schema = self._parse_type_node_to_schema(type_child, source_code)
                        break

        if not prop_name:
            return None

        # If we couldn't parse the type, fall back to string
        if not prop_schema:
            prop_schema = {"type": "string"}

        return (prop_name, prop_schema, not is_optional)

    def _parse_property_signature(
        self, prop_node: Node, source_code: bytes
    ) -> Optional[Tuple[str, Dict[str, Any], bool]]:
        """
        Parse a property signature with recursive type resolution.

        Args:
            prop_node: Property signature node
            source_code: Source code bytes

        Returns:
            Tuple of (name, schema_dict, is_required) or None
        """
        prop_name = None
        prop_schema = None
        is_optional = False

        for child in prop_node.children:
            if child.type == "property_identifier":
                prop_name = self.parser.get_node_text(child, source_code)
            elif child.type == "?":
                is_optional = True
            elif child.type == "type_annotation":
                # Parse the type recursively
                for type_child in child.children:
                    if type_child.type != ":":
                        prop_schema = self._parse_type_node_to_schema(type_child, source_code)
                        break

        if not prop_name:
            return None

        # If we couldn't parse the type, fall back to string
        if not prop_schema:
            prop_schema = {"type": "string"}

        return (prop_name, prop_schema, not is_optional)

    def _parse_type_value(self, value_node: Node, source_code: bytes) -> Schema:
        """
        Parse type alias value into Schema.

        Args:
            value_node: Type value node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        type_text = self.parser.get_node_text(value_node, source_code)

        # Handle union types (string literals for enums)
        # e.g., 'option1' | 'option2' | 'option3'
        if "|" in type_text:
            # Extract string literals
            enum_values = []
            parts = type_text.split("|")
            for part in parts:
                part = part.strip().strip("'\"")
                if part:
                    enum_values.append(part)

            return Schema(
                type="string",
                enum=enum_values if enum_values else None,
            )

        # Handle object types
        if value_node.type == "object_type":
            return self._parse_interface_body(value_node, source_code)

        # Handle array types
        if type_text.endswith("[]") or type_text.startswith("Array<"):
            return Schema(type="array")

        # Default to string
        return Schema(type=self._parse_typescript_type(type_text))

    def _resolve_type_schema(
        self, type_name: str, current_file: str, imports: Dict[str, str]
    ) -> Optional[Schema]:
        """
        Resolve a type name to a Schema by following imports.

        Args:
            type_name: Name of the type to resolve
            current_file: Current file path
            imports: Dictionary of imports

        Returns:
            Schema object or None (inlined schema, not ref for now)
        """
        # First check if it's a built-in type
        if type_name in ["string", "number", "boolean", "any", "object"]:
            return Schema(type=self._parse_typescript_type(type_name))

        # Check if type is in imports
        if type_name not in imports:
            # Type might be defined in same file
            schema = self._parse_type_definition(type_name, current_file)
            if schema:
                return schema
            # Can't resolve - return None
            return None

        # Resolve import path
        import_path = imports[type_name]
        resolved_path = self._resolve_import_path(import_path, current_file)

        if not resolved_path:
            # Can't resolve path
            return None

        # Parse type definition from resolved file
        schema = self._parse_type_definition(type_name, resolved_path)
        return schema

    def _find_re_export(
        self, type_name: str, tree, source_code: bytes, current_file: str
    ) -> Optional[str]:
        """
        Find where a type is re-exported from in a barrel export file.

        Args:
            type_name: Name of the type to find
            tree: Parsed tree
            source_code: Source code bytes
            current_file: Current file path (the index.ts)

        Returns:
            File path where type is actually defined, or None
        """
        # Look for import statements that import the type
        # Pattern: import type { TypeName } from './path';
        import_query = """
        (import_statement
          source: (string) @source)
        """

        matches = self.parser.query(tree, import_query, "typescript")
        for match in matches:
            source_node = match.get("source")
            if not source_node:
                continue

            import_node = source_node.parent
            if not import_node:
                continue

            # Check if this import includes our type
            import_text = self.parser.get_node_text(import_node, source_code)
            if type_name in import_text:
                # Extract the import path
                import_path = self.parser.extract_string_value(source_node, source_code)
                # Resolve it relative to current file
                resolved_path = self._resolve_import_path(import_path, current_file)
                if resolved_path:
                    return resolved_path

        return None

    def _extract_inline_object_type(
        self, type_annotation_node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Extract schema from inline object type literal.
        Generic implementation that handles any inline object: { prop: type; ... }

        Args:
            type_annotation_node: Type annotation node
            source_code: Source code bytes

        Returns:
            Schema object if inline object found, None otherwise
        """
        # Look for object_type node (inline object literal)
        for child in type_annotation_node.children:
            if child.type == "object_type":
                # Parse it using the same logic as interface_body
                # Both contain property_signature nodes
                return self._parse_interface_body(child, source_code)

        return None

    def _parse_type_node_to_schema(
        self, type_node: Node, source_code: bytes
    ) -> Dict[str, Any]:
        """
        Recursively parse a TypeScript type node to a schema dict.
        Handles arrays, objects, primitives, and type references.

        Args:
            type_node: Type node from AST
            source_code: Source code bytes

        Returns:
            Schema dictionary
        """
        # Handle array types: T[] or Array<T>
        if type_node.type == "array_type":
            # array_type has an element type as a child
            element_node = None
            for child in type_node.children:
                if child.type not in ("[", "]"):
                    element_node = child
                    break

            if element_node:
                item_schema = self._parse_type_node_to_schema(element_node, source_code)
                return {"type": "array", "items": item_schema}
            else:
                return {"type": "array"}

        # Handle inline object types: { prop: type; ... }
        elif type_node.type == "object_type":
            # Recursively parse the object properties
            schema_obj = self._parse_interface_body(type_node, source_code)
            return {
                "type": "object",
                "properties": schema_obj.properties,
                "required": schema_obj.required
            }

        # Handle primitive types: string, number, boolean, etc.
        elif type_node.type == "predefined_type":
            type_text = self.parser.get_node_text(type_node, source_code)
            return {"type": self._parse_typescript_type(type_text)}

        # Handle type references: Tag, User, Account, etc.
        elif type_node.type == "type_identifier":
            # For now, just mark as object
            # TODO: Could resolve the referenced type in future enhancement
            return {"type": "object"}

        # Handle generic types: Array<T>, Promise<T>, etc.
        elif type_node.type == "generic_type":
            # Extract the base type name
            type_name = None
            type_args = []

            for child in type_node.children:
                if child.type == "type_identifier":
                    type_name = self.parser.get_node_text(child, source_code)
                elif child.type == "type_arguments":
                    # Get type arguments
                    for arg_child in child.children:
                        if arg_child.type not in ("<", ">", ","):
                            type_args.append(arg_child)

            # Handle Array<T>
            if type_name == "Array" and type_args:
                item_schema = self._parse_type_node_to_schema(type_args[0], source_code)
                return {"type": "array", "items": item_schema}
            else:
                # Other generics - just treat as object
                return {"type": "object"}

        # Handle union types: string | number
        elif type_node.type == "union_type":
            # For now, just use the first type in the union
            # TODO: Could generate oneOf/anyOf in future
            for child in type_node.children:
                if child.type not in ("|",):
                    return self._parse_type_node_to_schema(child, source_code)
            return {"type": "string"}

        # Fallback for unknown types
        else:
            type_text = self.parser.get_node_text(type_node, source_code)
            return {"type": self._parse_typescript_type(type_text)}
