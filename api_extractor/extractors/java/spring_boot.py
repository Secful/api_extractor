"""Spring Boot framework extractor."""

from __future__ import annotations

import re
from typing import List, Optional, Dict, Tuple, Any
from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.parser import find_child_by_type
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


class SpringBootExtractor(BaseExtractor):
    """Extract API routes from Spring Boot applications."""

    # HTTP method annotations (both shorthand and RequestMapping)
    HTTP_METHOD_ANNOTATIONS = {
        "GetMapping": HTTPMethod.GET,
        "PostMapping": HTTPMethod.POST,
        "PutMapping": HTTPMethod.PUT,
        "DeleteMapping": HTTPMethod.DELETE,
        "PatchMapping": HTTPMethod.PATCH,
    }

    # Java type to OpenAPI type mapping
    JAVA_TYPE_MAP = {
        "String": "string",
        "Integer": "integer",
        "int": "integer",
        "Long": "integer",
        "long": "integer",
        "Boolean": "boolean",
        "boolean": "boolean",
        "Double": "number",
        "double": "number",
        "Float": "number",
        "float": "number",
        "BigDecimal": "number",
        "Date": "string",
        "LocalDate": "string",
        "LocalDateTime": "string",
        "UUID": "string",
        "List": "array",
        "Set": "array",
        "Collection": "array",
        "Map": "object",
    }

    def __init__(self) -> None:
        """Initialize Spring Boot extractor."""
        super().__init__(FrameworkType.SPRING_BOOT)

    def get_file_extensions(self) -> List[str]:
        """Get Java file extensions."""
        return [".java"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a Spring Boot controller file.

        Args:
            file_path: Path to Java file

        Returns:
            List of Route objects
        """
        routes = []

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, "java")
        if not tree:
            return routes

        # First, find all DTO classes in the file
        dto_classes = self._find_dto_classes(tree, source_code)

        # Query for all class declarations
        class_query = """
        (class_declaration
          name: (identifier) @class_name
          body: (class_body) @class_body)
        """

        all_classes = self.parser.query(tree, class_query, "java")

        for match in all_classes:
            class_name_node = match.get("class_name")
            class_body_node = match.get("class_body")

            if not class_name_node or not class_body_node:
                continue

            # Check if this class has @RestController or @Controller decorator
            controller_info = self._find_controller_annotation(class_name_node, source_code)
            if not controller_info:
                continue

            # Extract routes from this controller
            class_routes = self._extract_routes_from_controller(
                class_body_node, source_code, file_path, controller_info, tree, dto_classes
            )
            routes.extend(class_routes)

        return routes

    def _find_controller_annotation(
        self, class_name_node: Node, source_code: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Find @RestController or @Controller annotation for a class.

        Args:
            class_name_node: Class name identifier node
            source_code: Source code bytes

        Returns:
            Controller info dict with path and whether it's a RestController
        """
        # Walk up to find modifiers
        current = class_name_node.parent  # class_declaration
        if not current:
            return None

        # Look for modifiers node
        modifiers = find_child_by_type(current, "modifiers")
        if not modifiers:
            return None

        # Check for @RestController or @Controller annotations
        is_controller = False
        for child in modifiers.children:
            if child.type in ("marker_annotation", "annotation"):
                annotation_text = self.parser.get_node_text(child, source_code)
                if "@RestController" in annotation_text or "@Controller" in annotation_text:
                    is_controller = True
                    break

        if not is_controller:
            return None

        # Now look for @RequestMapping to get base path
        base_path = ""
        for child in modifiers.children:
            if child.type in ("marker_annotation", "annotation"):
                annotation_text = self.parser.get_node_text(child, source_code)
                if "@RequestMapping" in annotation_text:
                    base_path = self._extract_path_from_annotation(child, source_code)
                    break

        return {"path": base_path, "is_rest_controller": True}

    def _extract_path_from_annotation(self, annotation_node: Node, source_code: bytes) -> str:
        """
        Extract path from @RequestMapping or method mapping annotations.

        Args:
            annotation_node: Annotation node
            source_code: Source code bytes

        Returns:
            Path string or empty string
        """
        annotation_text = self.parser.get_node_text(annotation_node, source_code)

        # Try to match path = "/something" or value = "/something"
        path_match = re.search(r'(?:path|value)\s*=\s*"([^"]+)"', annotation_text)
        if path_match:
            return path_match.group(1)

        # Try to match just the string argument like @GetMapping("/path")
        simple_match = re.search(r'@\w+\("([^"]+)"', annotation_text)
        if simple_match:
            return simple_match.group(1)

        # Try to match path without quotes (path = /something)
        # Actually not valid Java, skip this

        return ""

    def _extract_routes_from_controller(
        self,
        class_body_node: Node,
        source_code: bytes,
        file_path: str,
        controller_info: Dict[str, Any],
        tree,
        dto_classes: Dict[str, Schema],
    ) -> List[Route]:
        """
        Extract routes from controller class body.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes
            file_path: Path to source file
            controller_info: Controller path info
            tree: Full syntax tree
            dto_classes: Dictionary of DTO schemas

        Returns:
            List of Route objects
        """
        routes = []
        controller_path = controller_info["path"]

        # Query for method declarations with annotations
        method_query = """
        (method_declaration
          (modifiers) @modifiers
          name: (identifier) @method_name
          parameters: (formal_parameters) @params) @method_decl
        """

        methods = self.parser.query(tree, method_query, "java")

        for match in methods:
            modifiers_node = match.get("modifiers")
            method_name_node = match.get("method_name")
            params_node = match.get("params")
            method_decl_node = match.get("method_decl")

            if not modifiers_node or not method_name_node or not method_decl_node:
                continue

            # Check if this method is inside our class body
            if not self._is_descendant_of(method_name_node, class_body_node):
                continue

            # Extract mapping annotations
            mapping_info = self._extract_mapping_annotation(modifiers_node, source_code)
            if not mapping_info:
                continue

            # Build full path
            method_path = mapping_info["path"]
            full_path = self._combine_paths(controller_path, method_path)
            if not full_path.startswith("/"):
                full_path = "/" + full_path

            # Extract HTTP method(s)
            http_methods = mapping_info["methods"]

            # Extract parameters
            parameters = self._extract_method_parameters(params_node, source_code)

            # Link method schemas (request body and response)
            schema_metadata = self._link_method_schemas(
                method_decl_node, params_node, source_code, dto_classes
            )

            # Extract source location
            source_line = method_name_node.start_point[0] + 1

            # Create route for each HTTP method
            for http_method in http_methods:
                route = Route(
                    path=full_path,
                    methods=[http_method],
                    handler_name=self.parser.get_node_text(method_name_node, source_code),
                    framework=self.framework,
                    raw_path=full_path,
                    source_file=file_path,
                    source_line=source_line,
                    metadata={
                        "parameters": parameters,
                        "dto_classes": dto_classes,
                        **schema_metadata,  # Merge schema metadata
                    },
                )
                routes.append(route)

        return routes

    def _is_descendant_of(self, node: Node, ancestor: Node) -> bool:
        """Check if node is a descendant of ancestor."""
        current = node
        while current:
            if current == ancestor:
                return True
            current = current.parent
        return False

    def _extract_mapping_annotation(
        self, modifiers_node: Node, source_code: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Extract mapping annotation from method modifiers.

        Args:
            modifiers_node: Modifiers node
            source_code: Source code bytes

        Returns:
            Dict with path and methods, or None
        """
        for child in modifiers_node.children:
            if child.type not in ("marker_annotation", "annotation"):
                continue

            annotation_text = self.parser.get_node_text(child, source_code)

            # Check for shorthand annotations (@GetMapping, etc.)
            for annotation_name, http_method in self.HTTP_METHOD_ANNOTATIONS.items():
                if f"@{annotation_name}" in annotation_text:
                    path = self._extract_path_from_annotation(child, source_code)
                    return {"path": path, "methods": [http_method]}

            # Check for @RequestMapping
            if "@RequestMapping" in annotation_text:
                path = self._extract_path_from_annotation(child, source_code)
                methods = self._extract_methods_from_request_mapping(annotation_text)
                return {"path": path, "methods": methods}

        return None

    def _extract_methods_from_request_mapping(self, annotation_text: str) -> List[HTTPMethod]:
        """
        Extract HTTP methods from @RequestMapping annotation.

        Args:
            annotation_text: Annotation text

        Returns:
            List of HTTP methods (defaults to [GET] if not specified)
        """
        methods = []

        # Look for method = POST or method = {POST, PUT}
        method_match = re.search(r"method\s*=\s*(?:RequestMethod\.)?(\w+)", annotation_text)
        if method_match:
            method_str = method_match.group(1).upper()
            if method_str in HTTPMethod.__members__:
                methods.append(HTTPMethod[method_str])
        else:
            # Default to GET if no method specified
            methods.append(HTTPMethod.GET)

        return methods

    def _extract_method_parameters(
        self, params_node: Node, source_code: bytes
    ) -> List[Parameter]:
        """
        Extract parameters from method signature.

        Args:
            params_node: Formal parameters node
            source_code: Source code bytes

        Returns:
            List of Parameter objects
        """
        parameters = []

        for child in params_node.children:
            if child.type != "formal_parameter":
                continue

            # Look for parameter annotations
            param_annotations = []
            param_name = ""
            param_type = "string"

            for param_child in child.children:
                if param_child.type == "modifiers":
                    for annotation_child in param_child.children:
                        if annotation_child.type in ("marker_annotation", "annotation"):
                            param_annotations.append(
                                self.parser.get_node_text(annotation_child, source_code)
                            )

                elif param_child.type == "type_identifier" or param_child.type in (
                    "integral_type",
                    "floating_point_type",
                    "boolean_type",
                ):
                    type_text = self.parser.get_node_text(param_child, source_code)
                    param_type = self._parse_java_type(type_text)

                elif param_child.type == "generic_type":
                    # Handle List<T>, etc.
                    type_text = self.parser.get_node_text(param_child, source_code)
                    param_type = self._parse_java_type(type_text)

                elif param_child.type == "identifier":
                    param_name = self.parser.get_node_text(param_child, source_code)

            # Determine parameter location based on annotations
            if any("@PathVariable" in ann for ann in param_annotations):
                # Extract parameter name from annotation value if present
                # @PathVariable("id") or @PathVariable(value = "id")
                annotation_param_name = None
                for ann in param_annotations:
                    if "@PathVariable" in ann:
                        annotation_param_name = self._extract_annotation_value(ann)
                        break

                # Use annotation value if present, otherwise use variable name
                final_param_name = annotation_param_name if annotation_param_name else param_name

                parameters.append(
                    self._create_parameter(
                        name=final_param_name,
                        location=ParameterLocation.PATH,
                        param_type=param_type,
                        required=True,
                    )
                )
            elif any("@RequestParam" in ann for ann in param_annotations):
                # Extract parameter name from annotation value if present
                # @RequestParam("query") or @RequestParam(value = "query")
                annotation_param_name = None
                required = True
                for ann in param_annotations:
                    if "@RequestParam" in ann:
                        if not annotation_param_name:
                            annotation_param_name = self._extract_annotation_value(ann)
                        if "required = false" in ann or "required=false" in ann:
                            required = False

                # Use annotation value if present, otherwise use variable name
                final_param_name = annotation_param_name if annotation_param_name else param_name

                parameters.append(
                    self._create_parameter(
                        name=final_param_name,
                        location=ParameterLocation.QUERY,
                        param_type=param_type,
                        required=required,
                    )
                )
            elif any("@RequestBody" in ann for ann in param_annotations):
                # Request body is handled separately in OpenAPI
                pass

        return parameters

    def _extract_annotation_value(self, annotation: str) -> str | None:
        """
        Extract value from annotation like @PathVariable("id") or @RequestParam(value = "query").

        Args:
            annotation: Annotation string

        Returns:
            Extracted value or None if not found
        """
        import re

        # Try to match @Annotation("value")
        match = re.search(r'@\w+\("([^"]+)"\)', annotation)
        if match:
            return match.group(1)

        # Try to match @Annotation(value = "value")
        match = re.search(r'@\w+\(value\s*=\s*"([^"]+)"\)', annotation)
        if match:
            return match.group(1)

        # Try to match @Annotation(name = "value") - alternative parameter name
        match = re.search(r'@\w+\(name\s*=\s*"([^"]+)"\)', annotation)
        if match:
            return match.group(1)

        return None

    def _parse_java_type(self, type_text: str) -> str:
        """
        Parse Java type to OpenAPI type.

        Args:
            type_text: Java type string

        Returns:
            OpenAPI type string
        """
        # Handle generic types like List<User>
        if "<" in type_text:
            base_type = type_text.split("<")[0].strip()
            return self.JAVA_TYPE_MAP.get(base_type, "string")

        return self.JAVA_TYPE_MAP.get(type_text.strip(), "string")

    def _combine_paths(self, base_path: str, method_path: str) -> str:
        """
        Combine controller base path with method path.

        Args:
            base_path: Controller base path
            method_path: Method path

        Returns:
            Combined path
        """
        # Handle empty paths
        if not base_path:
            return method_path or "/"
        if not method_path:
            return base_path

        # Ensure base_path starts with /
        if not base_path.startswith("/"):
            base_path = "/" + base_path

        # Remove trailing slash from base_path
        base_path = base_path.rstrip("/")

        # Ensure method_path starts with /
        if not method_path.startswith("/"):
            method_path = "/" + method_path

        return base_path + method_path

    def _find_dto_classes(self, tree, source_code: bytes) -> Dict[str, Schema]:
        """
        Find DTO/POJO classes in the file.

        Args:
            tree: Syntax tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping class names to Schema objects
        """
        dto_classes = {}

        # Query for class declarations
        class_query = """
        (class_declaration
          name: (identifier) @class_name
          body: (class_body) @class_body)
        """

        classes = self.parser.query(tree, class_query, "java")

        for match in classes:
            class_name_node = match.get("class_name")
            class_body_node = match.get("class_body")

            if not class_name_node or not class_body_node:
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)

            # Extract fields from class
            properties = self._extract_class_properties(class_body_node, source_code)

            if properties:
                schema = Schema(
                    type="object",
                    properties=properties,
                    required=[],
                )
                dto_classes[class_name] = schema

        return dto_classes

    def _extract_class_properties(self, class_body_node: Node, source_code: bytes) -> Dict[str, Any]:
        """
        Extract properties from class body.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes

        Returns:
            Dictionary of properties
        """
        properties = {}

        # Look for field declarations
        for child in class_body_node.children:
            if child.type == "field_declaration":
                field_info = self._extract_field_info(child, source_code)
                if field_info:
                    properties[field_info["name"]] = {"type": field_info["type"]}

        return properties

    def _extract_field_info(self, field_node: Node, source_code: bytes) -> Optional[Dict[str, str]]:
        """
        Extract field information.

        Args:
            field_node: Field declaration node
            source_code: Source code bytes

        Returns:
            Dict with name and type, or None
        """
        field_name = None
        field_type = "string"

        for child in field_node.children:
            if child.type in ("type_identifier", "integral_type", "floating_point_type", "boolean_type"):
                type_text = self.parser.get_node_text(child, source_code)
                field_type = self._parse_java_type(type_text)

            elif child.type == "generic_type":
                type_text = self.parser.get_node_text(child, source_code)
                field_type = self._parse_java_type(type_text)

            elif child.type == "variable_declarator":
                # Get variable name
                name_node = find_child_by_type(child, "identifier")
                if name_node:
                    field_name = self.parser.get_node_text(name_node, source_code)

        if field_name:
            return {"name": field_name, "type": field_type}

        return None

    def _extract_return_type(
        self, method_node: Node, source_code: bytes
    ) -> Optional[str]:
        """
        Extract return type from Java method declaration.

        Handles generic types like:
        - User
        - List<User>
        - ResponseEntity<Product>
        - Optional<User>

        Args:
            method_node: Method declaration node
            source_code: Source code bytes

        Returns:
            Return type string, or None if not found
        """
        # Find the type node (return type) in method declaration
        for child in method_node.children:
            if child.type in ("type_identifier", "generic_type", "integral_type",
                            "floating_point_type", "boolean_type", "void_type"):
                return self.parser.get_node_text(child, source_code)

        return None

    def _resolve_generic_type(self, type_text: str) -> Tuple[str, Optional[str]]:
        """
        Parse generic type to extract base and inner type.

        Examples:
            - List<User> → ('List', 'User')
            - ResponseEntity<Product> → ('ResponseEntity', 'Product')
            - Optional<User> → ('Optional', 'User')
            - User → ('User', None)

        Args:
            type_text: Generic type string

        Returns:
            Tuple of (base_type, inner_type)
        """
        from api_extractor.extractors.schema_utils import resolve_generic_type_recursive

        base_type, type_args = resolve_generic_type_recursive(type_text)

        if type_args:
            # Return first type argument as inner type
            return (base_type, type_args[0])

        return (base_type, None)

    def _link_method_schemas(
        self,
        method_node: Node,
        params_node: Node,
        source_code: bytes,
        dto_classes: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Link method parameters and return type to schemas.

        Extracts:
        - Request body from @RequestBody parameter
        - Response schema from return type

        Args:
            method_node: Method declaration node
            params_node: Formal parameters node
            source_code: Source code bytes
            dto_classes: Dictionary of DTO schemas

        Returns:
            Dict with request_body, response_schema, and type names
        """
        from api_extractor.extractors.schema_utils import (
            strip_wrapper_types,
            is_collection_type,
            wrap_array_schema,
            normalize_type_name
        )

        metadata = {}

        # Extract return type
        return_type_raw = self._extract_return_type(method_node, source_code)
        if return_type_raw and return_type_raw != "void":
            # Strip wrapper types like ResponseEntity, Optional
            return_type = strip_wrapper_types(return_type_raw, language='java')

            # Normalize type name
            return_type = normalize_type_name(return_type, language='java')

            # Store type name for later resolution
            metadata["response_type_name"] = return_type

            # Check if it's a collection type
            if is_collection_type(return_type, language='java'):
                # Extract inner type from List<User> → User
                _, inner_type = self._resolve_generic_type(return_type)
                if inner_type:
                    inner_type = normalize_type_name(inner_type, language='java')
                    # Try to find schema for inner type
                    if inner_type in dto_classes:
                        # Wrap in array schema
                        metadata["response_schema"] = wrap_array_schema(dto_classes[inner_type])
                    else:
                        metadata["response_type_name"] = inner_type
                        metadata["is_array_response"] = True
            else:
                # Try to find schema directly
                if return_type in dto_classes:
                    metadata["response_schema"] = dto_classes[return_type]

        # Extract @RequestBody parameter type
        for child in params_node.children:
            if child.type != "formal_parameter":
                continue

            # Look for @RequestBody annotation
            has_request_body = False
            param_type = None

            for param_child in child.children:
                if param_child.type == "modifiers":
                    for annotation_child in param_child.children:
                        if annotation_child.type in ("marker_annotation", "annotation"):
                            annotation_text = self.parser.get_node_text(annotation_child, source_code)
                            if "@RequestBody" in annotation_text:
                                has_request_body = True

                if param_child.type in ("type_identifier", "generic_type"):
                    param_type = self.parser.get_node_text(param_child, source_code)

            if has_request_body and param_type:
                # Normalize type name
                param_type = normalize_type_name(param_type, language='java')

                # Store type name for later resolution
                metadata["request_body_type_name"] = param_type

                # Try to find schema
                if param_type in dto_classes:
                    metadata["request_body"] = dto_classes[param_type]
                elif is_collection_type(param_type, language='java'):
                    # Extract inner type from List<User> → User
                    _, inner_type = self._resolve_generic_type(param_type)
                    if inner_type:
                        inner_type = normalize_type_name(inner_type, language='java')
                        if inner_type in dto_classes:
                            metadata["request_body"] = wrap_array_schema(dto_classes[inner_type])
                        else:
                            metadata["request_body_type_name"] = inner_type
                            metadata["is_array_request"] = True

                break  # Only one @RequestBody per method

        return metadata

    def _normalize_path(self, path: str) -> str:
        """
        Normalize Spring Boot path to OpenAPI format.

        Spring Boot already uses {param} format, so no normalization needed.

        Args:
            path: Spring Boot path

        Returns:
            OpenAPI path
        """
        return path

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from Spring Boot path.

        Args:
            path: Path with parameters

        Returns:
            List of Parameter objects
        """
        params = []
        pattern = r"\{([^}:]+)(?::[^}]+)?\}"  # Matches {id} or {id:[0-9]+}

        for match in re.finditer(pattern, path):
            param_name = match.group(1)
            params.append(
                self._create_parameter(
                    name=param_name,
                    location=ParameterLocation.PATH,
                    param_type="string",
                    required=True,
                )
            )

        return params

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
            path_parameters = self._extract_path_parameters(route.raw_path)

            # Add query/header parameters from metadata if available
            # Use dict to deduplicate by (name, location)
            param_dict = {}

            # First add path parameters
            for param in path_parameters:
                key = (param.name, param.location.value)
                param_dict[key] = param

            # Then add metadata parameters (which override path params if duplicate)
            # Metadata params have more info (type from annotations)
            if route.metadata and "parameters" in route.metadata:
                for param in route.metadata["parameters"]:
                    key = (param.name, param.location.value)
                    param_dict[key] = param

            # Convert back to list
            all_parameters = list(param_dict.values())

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
                parameters=all_parameters,
                request_body=request_body,
                responses=responses,
                tags=[self.framework.value],
                operation_id=operation_id,
                source_file=route.source_file,
                source_line=route.source_line,
            )

            endpoints.append(endpoint)

        return endpoints
