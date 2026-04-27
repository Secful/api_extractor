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
          parameters: (formal_parameters) @params)
        """

        methods = self.parser.query(tree, method_query, "java")

        for match in methods:
            modifiers_node = match.get("modifiers")
            method_name_node = match.get("method_name")
            params_node = match.get("params")

            if not modifiers_node or not method_name_node:
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
                parameters.append(
                    self._create_parameter(
                        name=param_name,
                        location=ParameterLocation.PATH,
                        param_type=param_type,
                        required=True,
                    )
                )
            elif any("@RequestParam" in ann for ann in param_annotations):
                # Check if required
                required = True
                for ann in param_annotations:
                    if "@RequestParam" in ann and "required = false" in ann:
                        required = False
                        break

                parameters.append(
                    self._create_parameter(
                        name=param_name,
                        location=ParameterLocation.QUERY,
                        param_type=param_type,
                        required=required,
                    )
                )
            elif any("@RequestBody" in ann for ann in param_annotations):
                # Request body is handled separately in OpenAPI
                pass

        return parameters

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
